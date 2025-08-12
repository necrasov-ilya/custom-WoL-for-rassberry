from __future__ import annotations

import asyncio
import logging
import logging.handlers
from dataclasses import asdict
from pathlib import Path
from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from .config import Host, Settings, load_settings
from .ssh_exec import SSHError, run_ssh_command
from .wol import send_magic_packet

logger = logging.getLogger("wolbot")


def setup_logging(log_file: Path) -> None:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Try file logger but fall back to console if not writable
    try:
        handler = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    except Exception:
        pass
    # Always log to console for portability
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
            InlineKeyboardButton(f"{h.name} • Shutdown", callback_data=f"shutdown:{h.name}"),
        ])
    rows.append([
        InlineKeyboardButton("Status", callback_data="status"),
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


async def shutdown_host(host: Host) -> str:
    ssh = host.shutdown.ssh
    try:
        code, out, err = await run_ssh_command(ssh.host, ssh.user, ssh.port, ssh.key_path, ssh.command, timeout=20)
        if code == 0:
            logger.info("Shutdown command succeeded on %s: %s", host.name, out.strip())
            return f"Shutdown command sent to {host.name}"
        else:
            logger.warning("Shutdown command failed on %s: rc=%s err=%s", host.name, code, err.strip())
            return f"Shutdown failed on {host.name}: {err.strip() or out.strip() or 'unknown error'}"
    except SSHError as e:
        logger.warning("SSH error on %s: %s", host.name, e)
        return f"SSH error on {host.name}: {e}"
    except Exception as e:
        logger.exception("Unexpected error during shutdown on %s: %s", host.name, e)
        return f"Error on {host.name}: {e}"


async def status_host(host: Host) -> str:
    ssh = host.shutdown.ssh
    try:
        # Prefer remote ping via ssh to avoid ICMP perms on Pi
        if host.os == "windows":
            ping_cmd = (
                "powershell -NoProfile -Command \""
                "try { if (Test-Connection -ComputerName localhost -Count 1 -Quiet) { echo online } else { echo offline } }"
                " catch { echo offline }\""
            )
            code, out, _ = await run_ssh_command(ssh.host, ssh.user, ssh.port, ssh.key_path, ping_cmd, timeout=10)
        else:
            ping_cmd = "ping -c 1 -W 1 127.0.0.1 >/dev/null 2>&1 && echo online || echo offline"
            code, out, _ = await run_ssh_command(ssh.host, ssh.user, ssh.port, ssh.key_path, ping_cmd, timeout=10)
        online = "online" in out.lower()
        return f"{host.name}: {'Online' if online else 'Offline'}"
    except Exception as e:
        logger.warning("Status check failed for %s: %s", host.name, e)
        return f"{host.name}: Unknown (status check failed)"


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


async def handle_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    if not context.args:
        await update.message.reply_text("Usage: /shutdown <host>")
        return
    host_name = context.args[0]
    host = next((h for h in settings.hosts if h.name == host_name), None)
    if not host:
        await update.message.reply_text("Unknown host")
        return
    msg = await shutdown_host(host)
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
    if data == "status":
        # Aggregate status of all hosts
        results = await asyncio.gather(*(status_host(h) for h in settings.hosts))
        await query.edit_message_text("\n".join(results), reply_markup=build_keyboard(settings.hosts))
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
    elif action == "shutdown":
        msg = await shutdown_host(host)
    else:
        msg = "Unknown action"

    await query.edit_message_text(msg, reply_markup=build_keyboard(settings.hosts))


def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_file)
    logger.info("Starting bot with %d hosts", len(settings.hosts))

    app = Application.builder().token(settings.tg_token).build()

    # Inject settings
    app.bot_data["settings"] = settings

    # Access control wrappers
    app.add_handler(CommandHandler("start", restrict_access(settings.allowed_ids)(handle_start)))
    app.add_handler(CommandHandler("wake", restrict_access(settings.allowed_ids)(handle_wake)))
    app.add_handler(CommandHandler("shutdown", restrict_access(settings.allowed_ids)(handle_shutdown)))
    app.add_handler(CommandHandler("status", restrict_access(settings.allowed_ids)(handle_status)))
    app.add_handler(CallbackQueryHandler(restrict_access(settings.allowed_ids)(handle_buttons)))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
