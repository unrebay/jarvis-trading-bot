#!/bin/bash
################################################################################
# setup_github_actions.sh — Run ONCE from your Mac.
# Generates an SSH key for GitHub Actions and installs it on the VPS.
# After this, GitHub Actions can SSH into the VPS without a password.
#
# Usage:
#   bash deploy/setup_github_actions.sh
################################################################################

VPS_HOST="77.110.126.107"
VPS_USER="root"
KEY_FILE="$HOME/.ssh/jarvis_github_actions"
REPO="https://github.com/unrebay/jarvis-trading-bot"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
info()  { echo -e "${BLUE}[…]${NC} $1"; }
step()  { echo -e "\n${BOLD}$1${NC}"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   GitHub Actions Deploy Key Setup        ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"

# ── 1. Generate key for GitHub Actions ──────────────────────────────────────
step "Step 1 — Generate SSH key for GitHub Actions"
if [ -f "$KEY_FILE" ]; then
    ok "Key already exists: $KEY_FILE"
else
    ssh-keygen -t ed25519 -f "$KEY_FILE" -N "" -C "github-actions-jarvis"
    ok "Key generated: $KEY_FILE"
fi

# ── 2. Install public key on VPS ────────────────────────────────────────────
step "Step 2 — Install public key on VPS (enter password once)"
ssh-copy-id -i "$KEY_FILE.pub" "$VPS_USER@$VPS_HOST"
ok "Public key installed on VPS"

# ── 3. Test connection ───────────────────────────────────────────────────────
step "Step 3 — Test GitHub Actions key"
if ssh -o BatchMode=yes -i "$KEY_FILE" "$VPS_USER@$VPS_HOST" "echo OK" 2>/dev/null | grep -q "OK"; then
    ok "Passwordless SSH working!"
else
    echo -e "${YELLOW}[!]${NC} Test inconclusive — check manually"
fi

# ── 4. Print private key for GitHub Secret ──────────────────────────────────
step "Step 4 — Add these 3 secrets to GitHub"
echo ""
echo -e "${YELLOW}Go to: $REPO/settings/secrets/actions${NC}"
echo ""
echo -e "Add these secrets (Name → Value):"
echo ""
echo -e "  ${BOLD}VPS_HOST${NC}  →  $VPS_HOST"
echo -e "  ${BOLD}VPS_USER${NC}  →  $VPS_USER"
echo -e "  ${BOLD}VPS_SSH_KEY${NC}  →  (copy everything below, including the header/footer lines)"
echo ""
echo "────────────────────────────────────────"
cat "$KEY_FILE"
echo "────────────────────────────────────────"
echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}   Done! Next: run init_git_on_vps.sh     ${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "  bash deploy/init_git_on_vps.sh"
echo ""
