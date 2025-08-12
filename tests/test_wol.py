from __future__ import annotations

from src.wol import build_magic_packet


def test_build_magic_packet_length():
    mac = "aa:bb:cc:dd:ee:ff"
    pkt = build_magic_packet(mac)
    assert len(pkt) == 6 + 16 * 6


def test_build_magic_packet_prefix():
    mac = "aa:bb:cc:dd:ee:ff"
    pkt = build_magic_packet(mac)
    assert pkt.startswith(b"\xff" * 6)


def test_build_magic_packet_repeats():
    mac = "aa:bb:cc:dd:ee:ff"
    pkt = build_magic_packet(mac)
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    assert pkt[6:] == mac_bytes * 16
