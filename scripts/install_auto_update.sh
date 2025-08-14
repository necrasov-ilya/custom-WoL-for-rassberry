#!/usr/bin/env bash
# Install systemd service + timer for periodic auto-update of wolbot repo.
# Usage: bash scripts/install_auto_update.sh [interval]
# interval example: 15min, 30min, hourly, daily (default: 30min)
set -euo pipefail

INTERVAL="${1:-30min}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATE_SCRIPT="${PROJECT_DIR}/scripts/update_and_restart.sh"
SERVICE_NAME="wolbot-update"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"
RUN_USER="${SUDO_USER:-${USER}}"

if [[ $(id -u) -ne 0 ]]; then
  echo "[INFO] Re-running with sudo..."
  exec sudo bash "$0" "$@"
fi

if [[ ! -x "$UPDATE_SCRIPT" ]]; then
  echo "[INFO] Making update script executable"; chmod +x "$UPDATE_SCRIPT"; fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Auto update wolbot repository
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${UPDATE_SCRIPT}
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF

# Map friendly interval to OnCalendar / OnUnitActiveSec
ON_CAL=""
ON_ACTIVE=""
case "$INTERVAL" in
  15min|15m) ON_ACTIVE="15min";;
  30min|30m) ON_ACTIVE="30min";;
  hourly|1h) ON_CAL="hourly";;
  2h) ON_ACTIVE="2h";;
  6h) ON_ACTIVE="6h";;
  daily|1d) ON_CAL="daily";;
  *) ON_ACTIVE="$INTERVAL";;
 esac

if [[ -n "$ON_CAL" ]]; then
  TIMER_CONTENT="OnCalendar=${ON_CAL}" 
else
  TIMER_CONTENT="OnUnitActiveSec=${ON_ACTIVE}" 
fi

cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Timer for auto update wolbot (${INTERVAL})

[Timer]
${TIMER_CONTENT}
Persistent=true
RandomizedDelaySec=60
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

chmod 644 "$SERVICE_FILE" "$TIMER_FILE"

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.timer"

systemctl list-timers --all | grep -i "${SERVICE_NAME}" || true

echo "[SUCCESS] Auto-update timer installed (${INTERVAL})."
echo "Check next run: systemctl list-timers | grep ${SERVICE_NAME}"
echo "Logs: journalctl -u ${SERVICE_NAME}.service -f"
