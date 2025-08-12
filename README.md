# Telegram WoL Bot for Raspberry Pi 3B

Production-ready Telegram bot to Wake-on-LAN and shutdown your PCs from a Raspberry Pi 3B (Raspberry Pi OS Lite 64-bit). Portable: runs from the repo folder without creating external directories.

Features
- Wake PCs via WoL magic packet.
- Shutdown via SSH command.
- Inline buttons per host: Wake, Shutdown, plus Status/Refresh/Cancel.
- Access restricted to allowed Telegram user IDs.

Tech
- Python 3.11+
- python-telegram-bot v21+, pyyaml, python-dotenv, wakeonlan (custom UDP), asyncio, subprocess for ssh
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
	bot.py
	config.py
	ssh_exec.py
	wol.py
tests/
	test_config.py
	test_wol.py
```

## Configuration

1) Copy `.env.example` to `.env` and set values:

```
TG_TOKEN=<TG_TOKEN>
ALLOWED_IDS=<ALLOWED_IDS>  # e.g. 12345,67890
LOG_FILE=./wolbot.log
```

2) Copy `hosts.yml.example` to `hosts.yml` and edit. Two example hosts included: `pc1` (windows) and `pc2` (linux).

Host fields:
- name
- mac
- broadcast_ip (defaults to 255.255.255.255)
- os: windows or linux
- shutdown.method: ssh
- shutdown.ssh: host, user, port, key_path, command

Example shutdown commands:
- windows: `shutdown /s /t 0`
- linux: `sudo poweroff`

## Setup on Raspberry Pi

1) Enable WoL in BIOS and OS of target PCs.

2) Install OpenSSH Server on Windows or Linux targets.

3) Create an SSH key on the Pi and copy to target users:

```
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host
```

4) For Linux targets, allow poweroff without password:

```
sudo visudo
# add line (adjust user):
pi ALL=(ALL) NOPASSWD: /sbin/poweroff
```

Or use a systemd-managed shutdown wrapper.

5) Run locally (portable)

```
python -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
python -m src.bot
```

Optional: Deploy as a systemd service (advanced)

```
sudo mkdir -p /var/log
sudo touch /var/log/wolbot.log
sudo chown pi:pi /var/log/wolbot.log

mkdir -p ~/wolbot
cp .env.example ~/wolbot/.env
cp hosts.yml.example ~/wolbot/hosts.yml
python3 -m venv ~/wolbot/venv
~/wolbot/venv/bin/pip install -U pip
~/wolbot/venv/bin/pip install -r requirements.txt

sed "s|%h|$HOME|g" telegram-wol.service | sed "s|/usr/bin/env bash -lc 'source %h|/usr/bin/env bash -lc 'source $HOME|" > /tmp/telegram-wol.service
sudo cp /tmp/telegram-wol.service /etc/systemd/system/telegram-wol.service
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-wol.service
```

Logs: `./wolbot.log` by default (or the path set in LOG_FILE).

## Usage

- Start a chat with your bot and send `/start`.
- Use inline buttons to pick a host then Wake/Shutdown.
- Commands:
	- `/wake <host>`
	- `/shutdown <host>`
	- `/status <host>`

Screenshots: add your screenshots here showing the inline buttons.

## Security notes

- Only chat IDs in `ALLOWED_IDS` can use the bot.
- SSH command is fixed per host; no arbitrary shell is executed.
- Reasonable timeouts and friendly error messages are implemented.

## Development

Run tests:

```
pytest -q
```

Run bot manually:

```
python -m src.bot
```

## License

MIT
