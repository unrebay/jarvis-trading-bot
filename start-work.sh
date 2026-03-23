#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  JARVIS — start-work.sh
#  Запускай КАЖДЫЙ РАЗ когда садишься работать с любого устройства.
#  Гарантирует свежую версию кода перед началом работы.
#
#  Использование:
#    bash start-work.sh             # обычный запуск
#    bash start-work.sh --macbook   # явно указать MacBook
#    bash start-work.sh --imac      # явно указать iMac
# ─────────────────────────────────────────────────────────────

set -e

# ── Цвета ─────────────────────────────────────────────────────
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; CYAN='\033[0;36m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[…]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
sep()  { echo -e "${BLUE}────────────────────────────────────────${NC}"; }

echo ""
echo -e "${BOLD}${CYAN}  🤖 JARVIS — Начало рабочей сессии${NC}"
sep

# ── Определить устройство ──────────────────────────────────────
DEVICE=""
if [[ "$1" == "--macbook" ]]; then
    DEVICE="macbook"
elif [[ "$1" == "--imac" ]]; then
    DEVICE="imac"
else
    HOSTNAME_VAL=$(hostname | tr '[:upper:]' '[:lower:]')
    if echo "$HOSTNAME_VAL" | grep -q "macbook"; then
        DEVICE="macbook"
    elif echo "$HOSTNAME_VAL" | grep -q "imac"; then
        DEVICE="imac"
    else
        echo -e "${YELLOW}Не могу определить устройство автоматически.${NC}"
        echo "  1) MacBook (ветка: macbook-clean)"
        echo "  2) iMac    (ветка: main)"
        echo "  3) Другой  (ветка: спросит ниже)"
        printf "Выбор [1/2/3]: "
        read -r choice
        case "$choice" in
            1) DEVICE="macbook" ;;
            2) DEVICE="imac" ;;
            *) DEVICE="other" ;;
        esac
    fi
fi

# ── Установить целевую ветку ───────────────────────────────────
case "$DEVICE" in
    "macbook") TARGET_BRANCH="macbook-clean" ;;
    "imac")    TARGET_BRANCH="main" ;;
    *)
        printf "Введи имя ветки для работы: "
        read -r TARGET_BRANCH
        ;;
esac

echo -e "${BOLD}Устройство: ${CYAN}${DEVICE}${NC}  |  ${BOLD}Ветка: ${CYAN}${TARGET_BRANCH}${NC}"
sep

# ── Проверить незакоммиченные изменения ────────────────────────
info "Проверяю незакоммиченные изменения..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    warn "Есть незакоммиченные изменения:"
    git status --short
    echo ""
    printf "${YELLOW}Сохранить в stash и продолжить? [y/N]:${NC} "
    read -r stash_choice
    if [[ "$stash_choice" =~ ^[Yy]$ ]]; then
        git stash push -m "auto-stash before start-work $(date '+%Y-%m-%d %H:%M')"
        ok "Изменения сохранены в stash"
    else
        err "Отмена. Закоммить или сбрось изменения вручную."
        exit 1
    fi
else
    ok "Рабочее дерево чистое"
fi

# ── Переключиться на нужную ветку ──────────────────────────────
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]]; then
    info "Переключаюсь с ${CURRENT_BRANCH} на ${TARGET_BRANCH}..."
    git checkout "$TARGET_BRANCH"
    ok "Переключено на ${TARGET_BRANCH}"
else
    ok "Уже на ветке ${TARGET_BRANCH}"
fi

# ── Fetch — смотрим что есть на remote ────────────────────────
info "Получаю данные с GitHub..."
git fetch origin --prune 2>/dev/null
ok "Данные получены"

# ── Проверить отставание от remote ────────────────────────────
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/${TARGET_BRANCH}" 2>/dev/null || echo "")

if [[ -z "$REMOTE" ]]; then
    warn "Ветка origin/${TARGET_BRANCH} не найдена — пропускаю pull"
elif [[ "$LOCAL" == "$REMOTE" ]]; then
    ok "Уже на последней версии"
else
    BEHIND=$(git rev-list --count HEAD..origin/"$TARGET_BRANCH")
    AHEAD=$(git rev-list --count origin/"$TARGET_BRANCH"..HEAD)

    if [[ "$BEHIND" -gt 0 ]]; then
        info "Отстаём на ${BEHIND} коммит(а) — обновляюсь..."
        git pull origin "$TARGET_BRANCH" --ff-only 2>/dev/null || git pull origin "$TARGET_BRANCH" --rebase
        ok "Обновлено (+${BEHIND} коммитов)"
    fi

    if [[ "$AHEAD" -gt 0 ]]; then
        warn "Локальных коммитов не в remote: ${AHEAD} шт — не забудь запушить"
    fi
fi

# ── Показать последние изменения ──────────────────────────────
sep
echo -e "${BOLD}  Последние 5 коммитов в ${TARGET_BRANCH}:${NC}"
git log --oneline -5 --color=always | sed 's/^/  /'

# ── Показать статус production ────────────────────────────────
sep
echo -e "${BOLD}  Статус веток:${NC}"
git fetch origin production main macbook-clean 2>/dev/null || true

for BRANCH in main macbook-clean production; do
    REF=$(git rev-parse --short "origin/${BRANCH}" 2>/dev/null || echo "?")
    DATE=$(git log -1 --format="%cr" "origin/${BRANCH}" 2>/dev/null || echo "?")
    if [[ "$BRANCH" == "$TARGET_BRANCH" ]]; then
        echo -e "  ${GREEN}▶ ${BRANCH}${NC} (${REF}) — ${DATE}  ← ты здесь"
    else
        echo -e "  ${BLUE}  ${BRANCH}${NC} (${REF}) — ${DATE}"
    fi
done

# ── iMac: дополнительная проверка production ──────────────────
if [[ "$DEVICE" == "imac" ]]; then
    sep
    echo -e "${BOLD}  iMac — синхронизация с production:${NC}"
    PROD_REF=$(git rev-parse origin/production 2>/dev/null || echo "")
    MAIN_REF=$(git rev-parse origin/main 2>/dev/null || echo "")
    if [[ "$PROD_REF" == "$MAIN_REF" ]]; then
        ok "main и production синхронизированы"
    else
        DIFF=$(git rev-list --count origin/production..origin/main)
        if [[ "$DIFF" -gt 0 ]]; then
            warn "main опережает production на ${DIFF} коммит(а)"
            echo -e "  ${YELLOW}Для деплоя: git push origin main:production${NC}"
        fi
        DIFF2=$(git rev-list --count origin/main..origin/production)
        if [[ "$DIFF2" -gt 0 ]]; then
            warn "production опережает main на ${DIFF2} коммит(а) (VPS-фиксы)"
            echo -e "  ${YELLOW}Подтяни: git merge origin/production${NC}"
        fi
    fi
fi

# ── Финальное сообщение ────────────────────────────────────────
sep
echo -e "${BOLD}${GREEN}  ✅ Готово к работе!${NC}"
echo ""
echo -e "  ${BOLD}Сохранить работу:${NC}  git add . && git commit -m \"feat: ...\" && git push origin ${TARGET_BRANCH}"
if [[ "$DEVICE" == "macbook" ]]; then
echo -e "  ${BOLD}Задеплоить:${NC}       git push origin ${TARGET_BRANCH}:production"
fi
echo ""
