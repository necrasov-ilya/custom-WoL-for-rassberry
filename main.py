from __future__ import annotations
"""Entry point for WoL-only Telegram bot.
Run: python -m main  (or python main.py)
"""
import asyncio
import logging
import logging.handlers
import random
from pathlib import Path
from typing import Dict, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from src.config import Host, Settings, load_settings
from src.wol import send_magic_packet
logger = logging.getLogger("wolbot")
FACTS = [
    "Вы знали? Если ударить по системному блоку — он не включится быстрее.",
    "Факт: 90% проблем решаются перезагрузкой. Остальные 10% — тоже.",
    "Забавный факт: MAC не про яблоки, а про сетевые карты.",
    "Вы знали? Wake-on-LAN не работает через интернет без танцев с NAT.",
    "Факт: Если долго смотреть на ПК, он быстрее не загрузится.",
    "Совет: Любите свой SSD, и он ответит скоростью.",
    "Лайфхак: Не храните пароли в passwords.txt на рабочем столе.",
    "Факт: Любой 'быстрый фикс' живёт дольше всех.",
    "Вы знали? Пыль внутри корпуса — идеальный теплоизолятор (это плохо).",
    "Факт: Anydesk ID лучше помнить, чем искать в панике.",
    "Вы знали? Чем больше RGB, тем больше FPS (почти).",
    "Лайфхак: Кнопка питания — это не кнопка 'решить всё'.",
    "Факт: Если не работает — проверь кабель.",
    "Вы знали? Этот бот любит ваши пакеты (WoL пакеты).",
    "Факт: Иногда компьютер выключен. Именно поэтому вы его не видите в сети.",
]

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
                try:
                    if update.effective_message:
                        await update.effective_message.reply_text("Нет доступа")
                except Exception:
                    pass
                return
            return await func(update, context)
        return wrapper
    return decorator

def main_menu_keyboard(hosts: List[Host]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for h in hosts:
        rows.append([InlineKeyboardButton(h.name, callback_data=f"host:{h.name}")])
    return InlineKeyboardMarkup(rows + [[InlineKeyboardButton("Обновить", callback_data="refresh_root")]])

def host_menu_keyboard(host: Host, notifications: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Включить (WoL)", callback_data=f"wake:{host.name}")],
        [InlineKeyboardButton("Статус", callback_data=f"status:{host.name}")],
        [InlineKeyboardButton(
            "Отключить уведомления" if notifications else "Включить уведомления",
            callback_data=f"toggle_notify:{host.name}"
        )],
        [InlineKeyboardButton("Назад", callback_data="back")],
    ])

async def ping_host(ip: Optional[str]) -> bool:
    if not ip:
        return False
    cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(proc.communicate(), timeout=3)
        return proc.returncode == 0
    except Exception:
        return False

def random_fact() -> str:
    return "\n💡 " + random.choice(FACTS)

async def wake_host(host: Host) -> str:
    try:
        await send_magic_packet(host.mac, host.broadcast_ip or "255.255.255.255")
        logger.info("Sent WoL to %s (%s) via %s", host.name, host.mac, host.broadcast_ip)
        return f"📡 Пакет отправлен: {host.name}" + random_fact()
    except Exception as e:
        logger.exception("WoL failed for %s: %s", host.name, e)
        return f"❌ Не удалось отправить пакет {host.name}: {e}" + random_fact()

async def status_text(host: Host) -> str:
    online = await ping_host(host.ip)
    base = f"Статус {host.name}: {'🟢 ВКЛ' if online else '🔴 ВЫКЛ'}"
    if host.anydesk_id:
        base += f"\nAnydesk: {host.anydesk_id}"
    return base + random_fact()

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    await update.message.reply_text(
        "Выберите компьютер:", reply_markup=main_menu_keyboard(settings.hosts)
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings: Settings = context.bot_data["settings"]
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    notifications: Dict[str, bool] = context.bot_data.setdefault("notifications", {})
    if data == "refresh_root" or data == "back":
        await safe_edit(query, "Выберите компьютер:", main_menu_keyboard(settings.hosts))
        return
    if data.startswith("host:"):
        name = data.split(":", 1)[1]
        host = next((h for h in settings.hosts if h.name == name), None)
        if not host:
            await safe_edit(query, "Хост не найден", main_menu_keyboard(settings.hosts))
            return
        await safe_edit(query, f"{host.name}: выберите действие", host_menu_keyboard(host, notifications.get(host.name, False)))
        return
    try:
        action, name = data.split(":", 1)
    except ValueError:
        await safe_edit(query, "Некорректные данные", main_menu_keyboard(settings.hosts))
        return
    host = next((h for h in settings.hosts if h.name == name), None)
    if not host:
        await safe_edit(query, "Хост не найден", main_menu_keyboard(settings.hosts))
        return
    if action == "wake":
        msg = await wake_host(host)
        context.application.create_task(schedule_one_time_status(query, host, context))
        await safe_edit(query, msg, host_menu_keyboard(host, notifications.get(host.name, False)))
        return
    if action == "status":
        msg = await status_text(host)
        await safe_edit(query, msg, host_menu_keyboard(host, notifications.get(host.name, False)))
        return
    if action == "toggle_notify":
        enabled = notifications.get(host.name, False)
        if enabled:
            notifications[host.name] = False
            await safe_edit(query, f"Автоуведомления выключены для {host.name}", host_menu_keyboard(host, False))
        else:
            notifications[host.name] = True
            start_periodic_task(context, host.name)
            await safe_edit(query, f"Автоуведомления включены для {host.name}", host_menu_keyboard(host, True))
        return
    await safe_edit(query, "Неизвестное действие", main_menu_keyboard(settings.hosts))

async def schedule_one_time_status(query, host: Host, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(30)
    online = await ping_host(host.ip)
    text = (
        f"{host.name}: 🟢 УСПЕШНО ВКЛЮЧЕН — можете подключаться через Anydesk {host.anydesk_id}" if (online and host.anydesk_id) else
        f"{host.name}: 🟢 УСПЕШНО ВКЛЮЧЕН" if online else f"{host.name}: 🔴 Не удалось подтвердить включение"
    ) + random_fact()
    try:
        await query.message.reply_text(text)
    except Exception:
        pass

def start_periodic_task(context: ContextTypes.DEFAULT_TYPE, host_name: str):
    periodic_tasks: Dict[str, asyncio.Task] = context.bot_data.setdefault("periodic_tasks", {})
    if host_name in periodic_tasks and not periodic_tasks[host_name].done():
        return
    task = context.application.create_task(periodic_status_loop(context, host_name))
    periodic_tasks[host_name] = task

async def periodic_status_loop(context: ContextTypes.DEFAULT_TYPE, host_name: str):
    settings: Settings = context.bot_data["settings"]
    notifications: Dict[str, bool] = context.bot_data.get("notifications", {})
    host = next((h for h in settings.hosts if h.name == host_name), None)
    if not host:
        return
    while notifications.get(host_name, False):
        await asyncio.sleep(3600)
        if not notifications.get(host_name, False):
            break
        online = await ping_host(host.ip)
        if online:
            text = (
                f"Просто напоминаю, компьютер {host.name} включён — можете подключаться через Anydesk"
                + (f" {host.anydesk_id}" if host.anydesk_id else "")
            )
        else:
            text = f"Просто напоминаю, компьютер {host.name} сейчас не отвечает." + random_fact()
        for uid in settings.allowed_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
            except Exception:
                pass

async def safe_edit(query, text: str, markup: InlineKeyboardMarkup):
    try:
        current = query.message.text if query.message else None
        if current == text:
            await query.edit_message_reply_markup(reply_markup=markup)
        else:
            await query.edit_message_text(text, reply_markup=markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning("Edit failed: %s", e)
    except Exception as e:
        logger.warning("Edit exception: %s", e)

def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_file)
    logger.info("Starting WoL bot with %d hosts", len(settings.hosts))
    app = Application.builder().token(settings.tg_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["notifications"] = {}
    app.bot_data["periodic_tasks"] = {}
    app.add_handler(CommandHandler("start", restrict_access(settings.allowed_ids)(handle_start)))
    app.add_handler(CallbackQueryHandler(restrict_access(settings.allowed_ids)(handle_buttons)))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
