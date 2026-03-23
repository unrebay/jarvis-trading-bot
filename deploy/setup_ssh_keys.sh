#!/bin/bash
################################################################################
# setup_ssh_keys.sh — Run this ONCE from your Mac to enable passwordless SSH
# After this, no more password prompts from any device that has the key.
#
# Usage:
#   bash deploy/setup_ssh_keys.sh
################################################################################

VPS_HOST="77.110.126.107"
VPS_USER="root"
KEY_FILE="$HOME/.ssh/jarvis_vps"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   SSH Key Setup for Jarvis VPS           ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""

# ── 1. Generate key if not exists ───────────────────────────────────────────
if [ -f "$KEY_FILE" ]; then
    ok "SSH key already exists: $KEY_FILE"
else
    info "Generating new SSH key pair..."
    mkdir -p "$HOME/.ssh"
    ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "jarvis-vps-$(hostname)"
    ok "SSH key generated: $KEY_FILE"
fi

# ── 2. Copy public key to VPS ────────────────────────────────────────────────
info "Uploading public key to VPS (you'll be asked for the password once)..."
ssh-copy-id -i "$KEY_FILE.pub" "$VPS_USER@$VPS_HOST"
ok "Public key installed on VPS"

# ── 3. Add SSH config entry ─────────────────────────────────────────────────
SSH_CONFIG="$HOME/.ssh/config"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

if grep -q "Host jarvis-vps" "$SSH_CONFIG" 2>/dev/null; then
    warn "SSH config entry 'jarvis-vps' already exists — skipping"
else
    info "Adding SSH config entry..."
    cat >> "$SSH_CONFIG" << EOF

# Jarvis Trading Bot VPS
Host jarvis-vps
    HostName $VPS_HOST
    User $VPS_USER
    IdentityFile $KEY_FILE
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
    ok "SSH config entry added"
fi

# ── 4. Test connection ───────────────────────────────────────────────────────
info "Testing passwordless connection..."
if ssh -o BatchMode=yes -i "$KEY_FILE" "$VPS_USER@$VPS_HOST" "echo OK" 2>/dev/null | grep -q "OK"; then
    ok "Passwordless SSH working!"
else
    warn "SSH test inconclusive — try manually: ssh jarvis-vps"
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   SSH Keys Configured!                   ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "  Now you can connect with just:"
echo -e "    ${YELLOW}ssh jarvis-vps${NC}"
echo ""
echo "  And deploy with:"
echo -e "    ${YELLOW}bash deploy/push_to_vps.sh${NC}"
echo ""
echo -e "${BLUE}To use from another device:${NC}"
echo "  Copy the private key to that device:"
echo -e "    ${YELLOW}cat $KEY_FILE${NC}   (then paste into ~/.ssh/jarvis_vps on the other device)"
echo ""
