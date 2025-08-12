from __future__ import annotations

import asyncio
import socket
from typing import Iterable


def build_magic_packet(mac: str) -> bytes:
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", "").lower())
    if len(mac_bytes) != 6:
        raise ValueError("MAC address must be 6 bytes")
    return b"\xff" * 6 + mac_bytes * 16


async def send_magic_packet(mac: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> None:
    packet = build_magic_packet(mac)

    def _send():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(packet, (broadcast_ip, port))

    # Offload blocking I/O to thread to avoid blocking asyncio loop
    await asyncio.to_thread(_send)
