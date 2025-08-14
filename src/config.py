from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class SSHConfig:
    host: str
    user: str
    port: int
    key_path: str
    command: str


@dataclass(frozen=True)
class ShutdownConfig:
    method: str  # only 'ssh' supported
    ssh: SSHConfig


@dataclass(frozen=True)
class Host:
    name: str
    mac: str
    broadcast_ip: str
    os: str  # 'windows' | 'linux'
    shutdown: ShutdownConfig


@dataclass(frozen=True)
class Settings:
    tg_token: str
    allowed_ids: List[int]
    log_file: Path
    hosts: List[Host]


class ConfigError(Exception):
    pass


def _validate_mac(mac: str) -> str:
    import re

    if not re.fullmatch(r"(?i)([0-9a-f]{2}:){5}[0-9a-f]{2}", mac.strip()):
        raise ConfigError(f"Invalid MAC address: {mac}")
    return mac.lower()


def load_settings(env_path: Optional[Path] = None, hosts_path: Optional[Path] = None) -> Settings:
    """Load settings from .env and hosts.yml.

    Env vars:
      - TG_TOKEN: Telegram bot token
      - ALLOWED_IDS: comma-separated Telegram user IDs
      - BASE_DIR: base working directory (optional)
      - LOG_FILE: path to log file (optional; default /var/log/wolbot.log)
    """
    if env_path is None:
        env_path = Path(".env")
    if hosts_path is None:
        hosts_path = Path("hosts.yml")

    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    tg_token = os.getenv("TG_TOKEN")
    if not tg_token:
        raise ConfigError("TG_TOKEN is required in environment or .env")

    allowed_ids_raw = os.getenv("ALLOWED_IDS", "")
    try:
        allowed_ids = [int(x) for x in allowed_ids_raw.replace(" ", "").split(",") if x]
    except ValueError as e:
        raise ConfigError("ALLOWED_IDS must be a comma-separated list of integers") from e

    # Portable defaults: local log file in current directory
    log_file = Path(os.getenv("LOG_FILE", "./wolbot.log"))

    if not hosts_path.exists():
        raise ConfigError(f"Hosts file not found: {hosts_path}")

    with hosts_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict) or "hosts" not in data or not isinstance(data["hosts"], list):
        raise ConfigError("hosts.yml must contain a 'hosts' list")

    hosts: List[Host] = []
    for item in data["hosts"]:
        try:
            name = str(item["name"]).strip()
            mac = _validate_mac(str(item["mac"]).strip())
            broadcast_ip = str(item.get("broadcast_ip", "255.255.255.255")).strip()
            os_name = str(item.get("os", "linux")).strip().lower()
            if os_name not in {"windows", "linux"}:
                raise ConfigError(f"Unsupported OS for host {name}: {os_name}")

            # SSH fields are optional for WoL-only mode
            sd = item.get("shutdown", {})
            if str(sd.get("method", "ssh")) != "ssh":
                raise ConfigError(f"Only ssh shutdown supported for host {name}")
            ssd = sd.get("ssh", {})
            
            # Create dummy SSH config if not provided (for WoL-only mode)
            ssh = SSHConfig(
                host=str(ssd.get("host", "localhost")).strip(),
                user=str(ssd.get("user", "user")).strip(),
                port=int(ssd.get("port", 22)),
                key_path=str(ssd.get("key_path", "/dev/null")).strip(),
                command=str(ssd.get("command", "sudo poweroff")).strip(),
            )
            shutdown = ShutdownConfig(method="ssh", ssh=ssh)
            hosts.append(Host(name=name, mac=mac, broadcast_ip=broadcast_ip, os=os_name, shutdown=shutdown))
        except (KeyError, ValueError) as e:
            raise ConfigError(f"Invalid host configuration for {name}: {e}") from e

    return Settings(
        tg_token=tg_token,
        allowed_ids=allowed_ids,
        log_file=log_file,
        hosts=hosts,
    )
