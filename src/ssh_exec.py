from __future__ import annotations

import asyncio
import shlex
from typing import Tuple


class SSHError(Exception):
    pass


async def run_ssh_command(host: str, user: str, port: int, key_path: str, command: str, timeout: float = 20.0) -> Tuple[int, str, str]:
    """Run a fixed SSH command with timeout.

    Returns (returncode, stdout, stderr).
    Security: inputs are validated and used directly without shell expansion; no arbitrary templates.
    """
    # Validate simple inputs to avoid command injection vectors
    def _safe(s: str) -> str:
        # allow common chars
        if not s or any(c in s for c in "\n\r\0"):
            raise SSHError("Invalid SSH parameter")
        return s

    host = _safe(host)
    user = _safe(user)
    key_path = _safe(key_path)
    command = _safe(command)

    args = [
        "ssh",
        "-i",
        key_path,
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        f"{user}@{host}",
        command,
    ]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise SSHError("SSH command timed out")

    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")
