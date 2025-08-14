#!/usr/bin/env bash
# One-shot bootstrap: install service + auto-update (with rollback)
# Usage: bash scripts/bootstrap_full.sh [interval]
# interval examples: 30min (default), hourly, 2h, daily
set -euo pipefail
INTERVAL="${1:-30min}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
  echo "[ERROR] .env not found. Create it first." >&2
  exit 1
fi

bash "$SCRIPT_DIR/install_service.sh"
bash "$SCRIPT_DIR/install_auto_update.sh" "$INTERVAL"

echo "[SUCCESS] Installed service + auto-update ($INTERVAL)."
echo "Check: systemctl status wolbot.service"
echo "Updates: journalctl -u wolbot-update.service -f"
