#!/usr/bin/env bash
set -euo pipefail
SERVICE_NAME="wolbot-update"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

if [[ $(id -u) -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

systemctl disable --now "${SERVICE_NAME}.timer" 2>/dev/null || true
rm -f "$SERVICE_FILE" "$TIMER_FILE"
systemctl daemon-reload || true

echo "[SUCCESS] Auto-update timer removed."
