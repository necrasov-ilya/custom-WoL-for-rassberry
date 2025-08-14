# Telegram WoL Bot for Raspberry Pi 3B

Production-ready Telegram bot to Wake-on-LAN and shutdown your PCs from a Raspberry Pi 3B (Raspberry Pi OS Lite 64-bit). Portable: runs from the repo folder without creating external directories.

## Описание

Чистый бот для Wake-on-LAN. Никакого SSH, только отправка WoL пакетов, статус по ping (если указан IP), уведомления и удобное меню.

## Возможности
- Включение ПК через WoL (magic packet).
- Проверка статуса (ping, если указан ip).
- Автоуведомление через 30 сек после запуска WoL — включился ли ПК.
- Почасовые напоминания о том что ПК включён (опция).
- Показ AnyDesk ID (если указан в hosts.yml).
- Рандомные «факты» в ответах для развлечения.
- Доступ только для указанных Telegram ID.
- Локальный лог ./wolbot.log

## Запуск

```
LICENSE
README.md
.env.example
hosts.yml.example
requirements.txt
main.py
src/
  __init__.py
  config.py
  wol.py
tests/
  test_config.py
  test_wol.py
```

## Configuration

1) Скопируйте `.env.example` в `.env` и задайте значения:

```
TG_TOKEN=<TG_TOKEN>
ALLOWED_IDS=<ALLOWED_IDS>  # e.g. 12345,67890
LOG_FILE=./wolbot.log
```

2) Скопируйте `hosts.yml.example` в `hosts.yml` и заполните. Поля:
  - name — имя хоста (уникально)
  - mac — MAC адрес (формат AA:BB:CC:DD:EE:FF)
  - broadcast_ip — широковещательный адрес сети
  - ip — (опц., но рекоменд.) для ping статуса (если не указать — бот покажет статус «НЕИЗВЕСТНО»)
  - anydesk_id — (опц.) покажем в статусе и уведомлениях

```
hosts:
  - name: pc1
    mac: "AA:BB:CC:DD:EE:01"
    broadcast_ip: "192.168.1.255"
    ip: "192.168.1.10"  # чтобы работал статус
  - name: pc2
    mac: "AA:BB:CC:DD:EE:02"
    broadcast_ip: "192.168.1.255"
    ip: "192.168.1.11"
```

## Запуск

```
python -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
python -m main
```

## Использование

1. В Telegram: отправьте /start.
2. Выберите компьютер.
3. Выберите действие: Включить, Статус, Вкл/Выкл уведомления, Назад.
4. После «Включить» через 30 сек придёт автоответ о включении.

## Безопасность

- Только чат ID из ALLOWED_IDS (список через запятую).
- Никакого удалённого выполнения команд.
- Логи: ./wolbot.log

## Пример hosts.yml

```
hosts:
  - name: pc1
    mac: "AA:BB:CC:DD:EE:01"
    broadcast_ip: "192.168.1.255"
    ip: "192.168.1.10"
    anydesk_id: "123 456 789"
  - name: pc2
    mac: "AA:BB:CC:DD:EE:02"
    broadcast_ip: "192.168.1.255"
    ip: "192.168.1.11"
    anydesk_id: "987 654 321"
```

## Лицензия

MIT
