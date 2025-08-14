# Telegram WoL Bot for Raspberry Pi 3B

Production-ready Telegram bot to Wake-on-LAN and shutdown your PCs from a Raspberry Pi 3B (Raspberry Pi OS Lite 64-bit). Portable: runs from the repo folder without creating external directories.

## Modes

Set MODE=wol in your .env for Wake-on-LAN only (no SSH required). Set MODE=ssh for advanced SSH features (future).

## Features
- Wake PCs via WoL magic packet.
- (Optional future) Shutdown via SSH command.
- Inline buttons per host: Wake, Status, plus Refresh/Cancel.
- Access restricted to allowed Telegram user IDs.
- Logging to ./wolbot.log by default (can change via LOG_FILE)

## Repository tree

```
LICENSE
README.md
.env.example
hosts.yml.example
requirements.txt
telegram-wol.service
src/
  __init__.py
  bot.py
  wol_only.py
  config.py
  ssh_exec.py
  wol.py
  ssh_setup_win/
    README.md
```

## Configuration

1) Copy `.env.example` to `.env` and set values:

```
TG_TOKEN=<TG_TOKEN>
ALLOWED_IDS=<ALLOWED_IDS>  # e.g. 12345,67890
LOG_FILE=./wolbot.log
MODE=wol
```

2) Copy `hosts.yml.example` to `hosts.yml` and edit. For WoL-only mode, only name, mac, and broadcast_ip are required:

```
hosts:
  - name: pc1
    mac: "AA:BB:CC:DD:EE:01"
    broadcast_ip: "192.168.1.255"
  - name: pc2
    mac: "AA:BB:CC:DD:EE:02"
    broadcast_ip: "192.168.1.255"
```

## Setup and Run (WoL-only mode)

```
python -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
python -m src.wol_only
```

## Usage

- Start a chat with your bot and send `/start`.
- Use inline buttons to pick a host then Wake/Status.
- Commands:
  - `/wake <host>`
  - `/status <host>`

## Security

- Only chat IDs in `ALLOWED_IDS` can use the bot (comma-separated list supported).
- No SSH or shutdown commands in WoL-only mode.
- Logging to ./wolbot.log by default; also logs to console.

## hosts.yml for WoL-only mode

- Only fields name, mac, broadcast_ip are used. Example:

```
hosts:
  - name: pc1
    mac: "AA:BB:CC:DD:EE:01"
    broadcast_ip: "192.168.1.255"
```

## SSH mode (future)

- For advanced SSH features, set MODE=ssh and see src/ssh_setup_win/ for future setup scripts.

## License

MIT
