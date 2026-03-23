#!/bin/bash
# webhook-deploy.sh — runs on VPS when GitHub pushes to production branch
# Called by webhook_server.py in a background subprocess

set -e

LOG="/var/log/jarvis-deploy.log"
JARVIS_DIR="/opt/jarvis"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🚀 Auto-deploy started"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$JARVIS_DIR"

log "[1/4] Pulling latest code from origin/production..."
git fetch origin >> "$LOG" 2>&1
git reset --hard origin/production >> "$LOG" 2>&1
log "      Commit: $(git log -1 --oneline)"

log "[2/4] Installing/updating dependencies..."
venv/bin/pip install -r requirements.txt -q --no-deps >> "$LOG" 2>&1
# Pin httpx for gotrue compatibility
venv/bin/pip install httpx==0.27.2 --force-reinstall --no-deps -q >> "$LOG" 2>&1

log "[3/4] Restarting jarvis-bot service..."
systemctl restart jarvis-bot >> "$LOG" 2>&1
sleep 3  # wait for service to start

log "[4/4] Checking bot status..."
if systemctl is-active --quiet jarvis-bot; then
    log "✅ Bot is running OK"
else
    log "❌ Bot failed to start! Check: journalctl -u jarvis-bot -n 30"
fi

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Deploy finished"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
