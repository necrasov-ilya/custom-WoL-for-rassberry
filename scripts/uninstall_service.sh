#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="wolbot"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ $(id -u) -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl disable --now "${SERVICE_NAME}" || true
fi

if [[ -f "${UNIT_FILE}" ]]; then
  rm -f "${UNIT_FILE}"
  echo "[INFO] Removed ${UNIT_FILE}"
fi

systemctl daemon-reload

echo "[SUCCESS] Service '${SERVICE_NAME}' uninstalled."
