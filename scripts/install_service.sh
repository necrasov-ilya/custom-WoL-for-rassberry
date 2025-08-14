#!/usr/bin/env bash
set -euo pipefail

# Install and enable systemd service for Telegram WoL bot (Raspberry Pi OS / Debian based)
# Usage: bash scripts/install_service.sh
# After success the bot will start on every boot.

SERVICE_NAME="wolbot"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
ENV_FILE="${PROJECT_DIR}/.env"
REQUIREMENTS="${PROJECT_DIR}/requirements.txt"
EXEC_START="${PYTHON_BIN} -m main"
RUN_USER="${SUDO_USER:-${USER}}"

if [[ $(id -u) -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

echo "[INFO] Installing systemd service '${SERVICE_NAME}' from ${PROJECT_DIR} (user=${RUN_USER})"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] .env file not found at ${ENV_FILE}. Create it before installing the service." >&2
  exit 1
fi

# Create virtual environment if missing
echo "[INFO] Ensuring virtual environment exists..."
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# Upgrade pip + install deps
echo "[INFO] Installing dependencies..."
"${PYTHON_BIN}" -m pip install --upgrade pip >/dev/null
if [[ -f "${REQUIREMENTS}" ]]; then
  "${PYTHON_BIN}" -m pip install -r "${REQUIREMENTS}" >/dev/null
else
  echo "[WARN] requirements.txt not found; skipping dependency install"
fi

# Create service file
cat > "${UNIT_FILE}" <<EOF
[Unit]
Description=Telegram WoL Bot (Wake-on-LAN)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${EXEC_START}
Restart=on-failure
RestartSec=5
# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF

echo "[INFO] Wrote unit file ${UNIT_FILE}" 

# Permissions
chmod 644 "${UNIT_FILE}"

# Reload + enable + start
echo "[INFO] Enabling and starting service..."
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"

# Show status summary
sleep 1
systemctl --no-pager --full status "${SERVICE_NAME}.service" | sed -n '1,15p'

echo "[SUCCESS] Service '${SERVICE_NAME}' installed and started."
echo "[INFO] Logs: journalctl -u ${SERVICE_NAME} -f"
