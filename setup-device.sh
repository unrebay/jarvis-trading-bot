#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  JARVIS — setup-device.sh
#  Запускай ОДИН РАЗ при первом клонировании на новом устройстве.
#  Настраивает git hooks, алиасы и окружение.
#
#  Использование:
#    bash setup-device.sh
# ─────────────────────────────────────────────────────────────

set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo ""
echo -e "${BOLD}  JARVIS — Настройка устройства${NC}"
echo -e "${BLUE}────────────────────────────────────────${NC}"

# ── 1. Git hooks ──────────────────────────────────────────────
info "Устанавливаю git hooks..."

# post-merge: показывает что изменилось после pull
cp "$REPO_ROOT/deploy/hooks/post-merge" "$HOOKS_DIR/post-merge"
chmod +x "$HOOKS_DIR/post-merge"
ok "Хук post-merge установлен"

# ── 2. Git алиасы ─────────────────────────────────────────────
info "Настраиваю git алиасы..."

# `git start` — вместо bash start-work.sh
git config alias.start "!bash $(pwd)/start-work.sh"

# `git save` — быстрый коммит и пуш
git config alias.save '!f() { git add -A && git commit -m "${1:-wip: save progress}" && git push origin HEAD; }; f'

# `git deploy` — пушит текущую ветку в production
git config alias.deploy '!git push origin HEAD:production'

# `git sync` — подтянуть с production (для iMac)
git config alias.sync '!git fetch origin && git merge origin/production --no-edit'

ok "Алиасы настроены: git start | git save | git deploy | git sync"

# ── 3. Git настройки ──────────────────────────────────────────
info "Настраиваю git..."
git config pull.rebase false
git config push.autoSetupRemote true
ok "Git настроен"

# ── 4. Финал ──────────────────────────────────────────────────
echo ""
echo -e "${BLUE}────────────────────────────────────────${NC}"
echo -e "${BOLD}${GREEN}  ✅ Устройство готово!${NC}"
echo ""
echo -e "  ${BOLD}Начать работу:${NC}   git start"
echo -e "  ${BOLD}Сохранить:${NC}       git save \"описание\""
echo -e "  ${BOLD}Задеплоить:${NC}      git deploy"
echo -e "  ${BOLD}Синхр. iMac:${NC}     git sync"
echo ""
