#!/bin/bash
################################################################################
# init_git_on_vps.sh — Run ONCE from your Mac.
# Converts the rsync-deployed /opt/jarvis into a proper git repo
# pointing at the production branch on GitHub.
# After this, GitHub Actions can do "git pull" instead of rsync.
#
# Usage:
#   bash deploy/init_git_on_vps.sh
################################################################################

VPS_HOST="77.110.126.107"
VPS_USER="root"
REMOTE_DIR="/opt/jarvis"
REPO_URL="https://github.com/unrebay/jarvis-trading-bot.git"
BRANCH="production"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}   Init Git Repo on VPS                   ${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""

info "Connecting to VPS and initializing git..."

ssh "$VPS_USER@$VPS_HOST" bash << REMOTE
set -e

cd $REMOTE_DIR

# Backup .env just in case
cp .env /tmp/jarvis_env_backup 2>/dev/null && echo "[✓] .env backed up to /tmp/jarvis_env_backup"

# Init git if not already
if [ ! -d ".git" ]; then
    git init
    git remote add origin $REPO_URL
    echo "[✓] Git initialized"
else
    echo "[✓] Git already initialized"
    git remote set-url origin $REPO_URL
fi

# Install git if needed
which git >/dev/null 2>&1 || apt-get install -y git -qq

# Fetch and checkout production branch
git fetch origin $BRANCH
git checkout -B $BRANCH origin/$BRANCH 2>/dev/null || git checkout $BRANCH

# Mark .env and venv as untouched (they're gitignored but let's be safe)
git update-index --assume-unchanged .env 2>/dev/null || true

echo ""
echo "[✓] Git repo ready on VPS"
echo "    Branch: \$(git branch --show-current)"
echo "    Remote: \$(git remote get-url origin)"
echo "    Latest commit: \$(git log --oneline -1)"
REMOTE

echo ""
ok "VPS git repo initialized on branch '$BRANCH'"
echo ""
echo "Now test the full flow:"
echo -e "  git add . && git commit -m 'test deploy' && git push origin $BRANCH"
echo ""
echo "Then check GitHub Actions tab in your repo."
echo ""
