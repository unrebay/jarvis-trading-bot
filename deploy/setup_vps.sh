#!/bin/bash
################################################################################
# setup_vps.sh — Runs ON the VPS to install/update Jarvis Bot
# Usage: bash /opt/jarvis/deploy/setup_vps.sh
################################################################################

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

[[ $EUID -ne 0 ]] && err "Run as root: sudo bash setup_vps.sh"

BOT_DIR="/opt/jarvis"
VENV_DIR="$BOT_DIR/venv"
SERVICE_SRC="$BOT_DIR/deploy/jarvis.service"
SERVICE_DST="/etc/systemd/system/jarvis-bot.service"

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   Jarvis Trading Bot — VPS Setup         ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""

# ── 1. System packages ──────────────────────────────────────────────────────
info "Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv python3-dev build-essential curl
ok "System packages ready"

# ── 2. System user ──────────────────────────────────────────────────────────
if ! id "jarvis" &>/dev/null; then
    info "Creating system user 'jarvis'..."
    useradd --system --home-dir "$BOT_DIR" --shell /bin/false --comment "Jarvis Bot Service" jarvis
    ok "User 'jarvis' created"
else
    ok "User 'jarvis' already exists"
fi

# ── 3. Python virtual environment ───────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
else
    ok "Virtual environment already exists"
fi

# ── 4. Python dependencies ──────────────────────────────────────────────────
info "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q
"$VENV_DIR/bin/pip" install -r "$BOT_DIR/requirements.txt" -q
ok "Python dependencies installed"

# ── 5. Check .env ────────────────────────────────────────────────────────────
if [ ! -f "$BOT_DIR/.env" ]; then
    err ".env file not found at $BOT_DIR/.env — copy it from your local machine first!"
fi
ok ".env file found"

# ── 6. Permissions ──────────────────────────────────────────────────────────
info "Setting permissions..."
chown -R jarvis:jarvis "$BOT_DIR"
chmod 750 "$BOT_DIR"
chmod 600 "$BOT_DIR/.env"
ok "Permissions set"

# ── 7. Systemd service ──────────────────────────────────────────────────────
info "Installing systemd service..."
if [ ! -f "$SERVICE_SRC" ]; then
    err "jarvis.service not found at $SERVICE_SRC"
fi
cp "$SERVICE_SRC" "$SERVICE_DST"
systemctl daemon-reload
systemctl enable jarvis-bot
ok "Systemd service installed and enabled"

# ── 8. Start / restart ──────────────────────────────────────────────────────
info "Starting jarvis-bot service..."
systemctl restart jarvis-bot
sleep 3

# ── 9. Status check ─────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}── Service Status ──────────────────────────${NC}"
systemctl status jarvis-bot --no-pager -l || true

echo ""
echo -e "${BLUE}── Last 20 log lines ───────────────────────${NC}"
journalctl -u jarvis-bot -n 20 --no-pager || true

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Setup complete!                        ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo -e "  Live logs:   ${YELLOW}journalctl -u jarvis-bot -f${NC}"
echo -e "  Restart:     ${YELLOW}systemctl restart jarvis-bot${NC}"
echo -e "  Stop:        ${YELLOW}systemctl stop jarvis-bot${NC}"
echo -e "  Status:      ${YELLOW}systemctl status jarvis-bot${NC}"
echo ""
