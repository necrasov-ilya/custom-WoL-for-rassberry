from __future__ import annotations

from pathlib import Path

import yaml

from src.config import ConfigError, load_settings


def test_load_settings_basic(tmp_path: Path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("TG_TOKEN=token\nALLOWED_IDS=1,2\n", encoding="utf-8")
    hosts = tmp_path / "hosts.yml"
    hosts.write_text(
        yaml.safe_dump(
            {
                "hosts": [
                    {
                        "name": "pc1",
                        "mac": "aa:bb:cc:dd:ee:ff",
                        "broadcast_ip": "255.255.255.255",
                        "ip": "192.168.1.10",
                        "anydesk_id": "123 456 789",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    s = load_settings(env_path=env, hosts_path=hosts)
    assert s.tg_token == "token"
    assert s.allowed_ids == [1, 2]
    assert s.hosts[0].name == "pc1"
    assert s.hosts[0].mac == "aa:bb:cc:dd:ee:ff"


def test_invalid_mac(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("TG_TOKEN=token\nALLOWED_IDS=1\n", encoding="utf-8")
    hosts = tmp_path / "hosts.yml"
    hosts.write_text(
        yaml.safe_dump(
            {
                "hosts": [
                    {"name": "pc1", "mac": "invalid-mac"}
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        load_settings(env_path=env, hosts_path=hosts)
        assert False, "Expected ConfigError"
    except ConfigError:
        pass
