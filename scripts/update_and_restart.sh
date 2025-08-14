#!/usr/bin/env bash
# Auto-update script for wolbot. Intended to be run by systemd timer.
# Logic:
# 1. Fetch remote
# 2. If HEAD differs from remote tracking branch and no local uncommitted changes -> pull (fast-forward only)
# 3. If requirements changed -> reinstall dependencies
# 4. Restart wolbot.service
# 5. Health check: if service not active -> automatic rollback to previous commit (and restart again)
# Safe: skips if uncommitted changes. Rollback only touches repo (git reset --hard PREV_SHA).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

RUN_USER="${RUN_USER:-${SUDO_USER:-pi}}"
BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"
SERVICE_NAME="wolbot.service"
VENV_DIR="${PROJECT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
REQ_FILE="requirements.txt"

log(){ echo "[auto-update] $(date +%F_%T) $*"; }

if ! command -v git >/dev/null 2>&1; then
  log "git not installed; abort"; exit 0; fi

if [[ ! -d .git ]]; then
  log "Not a git repo; abort"; exit 0; fi

# Ensure ownership consistent (optional; ignore errors)
if [[ "$(id -u)" -eq 0 ]] && [[ -n "${RUN_USER}" ]]; then
  chown -R "${RUN_USER}" . 2>/dev/null || true
fi

# Fetch latest
sudo -u "${RUN_USER}" git fetch --quiet origin || { log "git fetch failed"; exit 0; }
PREV_SHA=$(sudo -u "${RUN_USER}" git rev-parse HEAD)
REMOTE=$(sudo -u "${RUN_USER}" git rev-parse "origin/${BRANCH}" || echo "$PREV_SHA")

if [[ "$PREV_SHA" == "$REMOTE" ]]; then
  log "Up-to-date ($BRANCH)"; exit 0; fi

STATUS=$(sudo -u "${RUN_USER}" git status --porcelain)
if [[ -n "$STATUS" ]]; then
  log "Local changes present; skipping pull"; exit 0; fi

log "Updating from $PREV_SHA -> $REMOTE"
# Record hash of requirements to detect changes
OLD_REQ_HASH=""
if [[ -f "$REQ_FILE" ]]; then
  OLD_REQ_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
fi

if ! sudo -u "${RUN_USER}" git pull --ff-only origin "$BRANCH"; then
  log "git pull failed (non fast-forward?)"; exit 0; 
fi

NEW_SHA=$(sudo -u "${RUN_USER}" git rev-parse HEAD)

if [[ -f "$REQ_FILE" ]]; then
  NEW_REQ_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
  if [[ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]]; then
    log "requirements.txt changed -> reinstalling deps"
    if [[ ! -d "$VENV_DIR" ]]; then
      python3 -m venv "$VENV_DIR"
    fi
    "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null 2>&1 || true
    "$PYTHON_BIN" -m pip install -r "$REQ_FILE" >/dev/null 2>&1 || log "pip install errors ignored"
  fi
fi

log "Restarting service ${SERVICE_NAME} (new revision ${NEW_SHA})"
if ! systemctl restart "$SERVICE_NAME"; then
  log "Restart command failed; attempting rollback";
  sudo -u "${RUN_USER}" git reset --hard "$PREV_SHA" && log "Rolled back to $PREV_SHA" || log "Rollback git reset failed";
  systemctl restart "$SERVICE_NAME" || log "Service still failing after rollback";
  exit 0;
fi

# Health check (give it a moment to start)
sleep 5
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  log "Service unhealthy after update -> rollback"
  sudo -u "${RUN_USER}" git reset --hard "$PREV_SHA" && log "Rolled back to $PREV_SHA" || log "Rollback git reset failed"
  systemctl restart "$SERVICE_NAME" || log "Service restart failed after rollback"
  exit 0
fi

log "Update OK: ${NEW_SHA}" 
exit 0
