#!/bin/bash
################################################################################
# push_to_vps.sh — Run this from your Mac (from the project root folder)
# Syncs all bot code to the VPS and runs setup.
#
# Usage (from project root):
#   bash deploy/push_to_vps.sh
#
# Requires: ssh, rsync (both pre-installed on Mac)
################################################################################

set -euo pipefail

VPS_HOST="77.110.126.107"
VPS_USER="root"
REMOTE_DIR="/opt/jarvis"

# ── Detect script location ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   Jarvis Bot — Push to VPS $VPS_HOST  ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""
info "Project root: $PROJECT_ROOT"
info "Destination:  $VPS_USER@$VPS_HOST:$REMOTE_DIR"
echo ""

# ── 1. Create remote directory ───────────────────────────────────────────────
info "Creating remote directory structure..."
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $REMOTE_DIR"
ok "Remote directory ready"

# ── 2. Sync code ─────────────────────────────────────────────────────────────
info "Syncing code files..."
rsync -az --progress \
    --exclude='venv/' \
    --exclude='archive/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='*.egg-info' \
    --exclude='.DS_Store' \
    "$PROJECT_ROOT/src/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/src/"

rsync -az \
    "$PROJECT_ROOT/system/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/system/"

# Sync knowledge base (smaller files only)
rsync -az \
    --exclude='*.mp4' --exclude='*.mov' \
    "$PROJECT_ROOT/kb/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/kb/" 2>/dev/null || true

rsync -az \
    "$PROJECT_ROOT/requirements.txt" \
    "$VPS_USER@$VPS_HOST:$REMOTE_DIR/requirements.txt"

rsync -az \
    "$PROJECT_ROOT/deploy/" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/deploy/"

ok "Code synced"

# ── 3. Sync .env ─────────────────────────────────────────────────────────────
if [ -f "$PROJECT_ROOT/.env" ]; then
    info "Syncing .env (secrets)..."
    scp "$PROJECT_ROOT/.env" "$VPS_USER@$VPS_HOST:$REMOTE_DIR/.env"
    ok ".env uploaded"
else
    echo -e "${YELLOW}[!]${NC} .env not found at project root — skipping (make sure it's on VPS already)"
fi

# ── 4. Make scripts executable ──────────────────────────────────────────────
ssh "$VPS_USER@$VPS_HOST" "chmod +x $REMOTE_DIR/deploy/setup_vps.sh"

# ── 5. Run setup on VPS ─────────────────────────────────────────────────────
echo ""
info "Running setup on VPS..."
ssh "$VPS_USER@$VPS_HOST" "bash $REMOTE_DIR/deploy/setup_vps.sh"

echo ""
echo -e "${GREEN}Done! Bot is running on VPS $VPS_HOST${NC}"
echo ""
echo -e "  Check status: ${YELLOW}ssh $VPS_USER@$VPS_HOST 'systemctl status jarvis-bot'${NC}"
echo -e "  Live logs:    ${YELLOW}ssh $VPS_USER@$VPS_HOST 'journalctl -u jarvis-bot -f'${NC}"
echo ""
