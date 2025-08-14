from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from .config import Host, Settings, load_settings
from .wol import send_magic_packet

logger = logging.getLogger("wolbot")


def setup_logging(log_file: Path) -> None:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        handler = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except Exception:
        pass
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)


def restrict_access(allowed_ids: List[int]):
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            uid = update.effective_user.id if update.effective_user else None
            if uid not in allowed_ids:
                logger.warning("Unauthorized access attempt from %s", uid)
                await update.effective_message.reply_text("Unauthorized")
                return
            return await func(update, context)
        return wrapper
    return decorator


def build_keyboard(hosts: List[Host]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for h in hosts:
        rows.append([
            InlineKeyboardButton(f"{h.name} • Wake", callback_data=f"wake:{h.name}"),
            InlineKeyboardButton(f"{h.name} • Status", callback_data=f"status:{h.name}"),
        ])
    rows.append([
        InlineKeyboardButton("Refresh", callback_data="refresh"),
        InlineKeyboardButton("Cancel", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(rows)


async def wake_host(host: Host) -> str:
    try:
        await send_magic_packet(host.mac, host.broadcast_ip or "255.255.255.255")
        logger.info("Sent WoL to %s (%s) via %s", host.name, host.mac, host.broadcast_ip)
        return f"Wake signal sent to {host.name}"
    except Exception as e:
        logger.exception("WoL failed for %s: %s", host.name, e)
        return f"Failed to send WoL to {host.name}: {e}"


async def status_host(host: Host) -> str:
    # In WoL-only mode, status is always 'Unknown' (no SSH)
    return f"{host.name}: Status unknown (WoL-only mode)"


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    await update.message.reply_text(
        "Select a host and action:",
        reply_markup=build_keyboard(settings.hosts),
    )


async def handle_wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    if not context.args:
        await update.message.reply_text("Usage: /wake <host>")
        return
    host_name = context.args[0]
    host = next((h for h in settings.hosts if h.name == host_name), None)
    if not host:
        await update.message.reply_text("Unknown host")
        return
    msg = await wake_host(host)
    await update.message.reply_text(msg)


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    if not context.args:
        await update.message.reply_text("Usage: /status <host>")
        return
    host_name = context.args[0]
    host = next((h for h in settings.hosts if h.name == host_name), None)
    if not host:
        await update.message.reply_text("Unknown host")
        return
    msg = await status_host(host)
    await update.message.reply_text(msg)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "cancel":
        await query.edit_message_text("Cancelled")
        return
    if data == "refresh":
        await query.edit_message_reply_markup(reply_markup=build_keyboard(settings.hosts))
        return

    try:
        action, name = data.split(":", 1)
    except ValueError:
        await query.edit_message_text("Invalid action")
        return

    host = next((h for h in settings.hosts if h.name == name), None)
    if not host:
        await query.edit_message_text("Unknown host")
        return

    if action == "wake":
        msg = await wake_host(host)
    elif action == "status":
        msg = await status_host(host)
    else:
        msg = "Unknown action"

    await query.edit_message_text(msg, reply_markup=build_keyboard(settings.hosts))


def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_file)
    logger.info("Starting WoL-only bot with %d hosts", len(settings.hosts))

    app = Application.builder().token(settings.tg_token).build()
    app.bot_data["settings"] = settings

    app.add_handler(CommandHandler("start", restrict_access(settings.allowed_ids)(handle_start)))
    app.add_handler(CommandHandler("wake", restrict_access(settings.allowed_ids)(handle_wake)))
    app.add_handler(CommandHandler("status", restrict_access(settings.allowed_ids)(handle_status)))
    app.add_handler(CallbackQueryHandler(restrict_access(settings.allowed_ids)(handle_buttons)))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
