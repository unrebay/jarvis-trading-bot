# JARVIS — Action Plan

> Last updated: 2026-03-22
> Status: Foundation complete, moving to integration

---

## Текущее состояние (✅ сделано)

### iMac (этот сеанс)
- ✅ Репозиторий restructured (target structure)
- ✅ 8 KB-схем (lesson, topic, rule, pattern, example, mistake, checklist, strategy_card)
- ✅ Skills: knowledge-ingestion, knowledge-structurer, trading-mentor
- ✅ Operations docs (backup, restore, maintenance, cost-policy)
- ✅ Discord ingestion state сохранён (63 файлов, прогресс зафиксирован)
- ✅ Full Context Prompt сохранён в docs/
- ✅ Supabase: 3 таблицы + HNSW индекс + pgvector функции + full-text search + история диалогов

### MacBook (параллельный сеанс → запушено в GitHub)
- ✅ claude_client.py — cost routing (Haiku/Sonnet/Opus) + prompt caching
- ✅ Обновлённый jarvis_bot.py с Supabase + историей диалогов
- ✅ Системный промпт JARVIS (ICT/SMC, 5 уровней)
- ✅ Deploy infrastructure (jarvis.service, deploy.sh, Makefile, .env.example)

---

## Следующие шаги — по приоритету

### ЭТАП 1 — Синхронизация и запуск бота (сегодня/завтра)

#### Тебе на iMac Terminal:
```bash
cd ~/path/to/jarvis-trading-bot
git pull origin main
```
Это подтянет файлы с MacBook (claude_client.py, deploy.sh, Makefile и т.д.)

#### Установить расширения в Claude Desktop:
1. GitHub MCP — Settings → Extensions → найти GitHub MCP → Install
2. context7 — Settings → Extensions → найти context7 → Install

#### На VPS:
```bash
# 1. Зайти по SSH
ssh user@your-vps-ip

# 2. Клонировать репо
git clone https://github.com/unrebay/jarvis-trading-bot.git
cd jarvis-trading-bot

# 3. Заполнить .env
cp .env.example .env
nano .env
# BOT_TOKEN=твой_токен
# ANTHROPIC_API_KEY=твой_ключ
# SUPABASE_URL=https://ivifpljgzsmstirlrjar.supabase.co
# SUPABASE_KEY=твой_ключ

# 4. Задеплоить (если есть Makefile от MacBook)
make deploy
# или вручную: python jarvis_bot.py
```

---

### ЭТАП 2 — Загрузка знаний в Supabase (через 1-2 дня)

Supabase готов — таблицы и функции поиска созданы. Нужно загрузить 63 .md файла.

**Задача для iMac:** Написать скрипт `load_knowledge_to_supabase.py`:
- Читает все файлы из `knowledge/raw/**/*.md`
- Генерирует embeddings через `text-embedding-3-small` (дёшево)
- Загружает в `knowledge_documents` с topic/section
- После загрузки: semantic search будет работать в боте

**Задача для MacBook:** Параллельно можно начать knowledge-structurer — прогнать 63 raw .md файла через Claude, получить структурированные JSON-объекты в `knowledge/lessons/`, `knowledge/rules/` и т.д.

---

### ЭТАП 3 — Продолжение Discord ingestion (позже)

Каналы для обхода (из discord_ingestion_state.json):
- ⚠️ news-macro-analysis — RE-SCRAPE (8 страниц потеряны при краше)
- wyckoff older posts
- PSYCHO (3 канала)
- FUNDAMENTAL (6 каналов)
- MARKET PROFILE (7 каналов)
- DT LIBRARY (3 канала)

**Машина:** iMac (Chrome MCP)

---

### ЭТАП 4 — VPS production setup

После того как бот заработает локально:
- Перенести бота на VPS
- Настроить systemd service (jarvis.service от MacBook)
- Monitoring + alerts

**Внимание по VPS с 1 ядром:** Достаточно для Telegram бота. НЕ запускать на нём embedding generation — только на iMac.

---

## Разделение труда

| Задача | Машина | Статус |
|--------|--------|--------|
| Scraping Discord | iMac (Chrome MCP) | ⏸ Отложено |
| Knowledge structuring | MacBook (параллельно) | ⏳ Следующий шаг |
| Load KB to Supabase | iMac | ⏳ Следующий шаг |
| Bot development | MacBook или iMac | ⏳ Git pull нужен |
| VPS deployment | VPS + iMac | ⏳ После тестирования |
| Architecture | iMac | ✅ Готово |

---

## Supabase — что готово

**Проект:** `jarvis-knowledge-base` (eu-central-1)
**URL:** `https://ivifpljgzsmstirlrjar.supabase.co`

| Таблица | Назначение | Статус |
|---------|-----------|--------|
| `knowledge_documents` | KB + vector embeddings | ✅ Готова |
| `bot_users` | Пользователи бота | ✅ Готова |
| `conversations` | История диалогов | ✅ Готова |

| Функция | Назначение |
|---------|-----------|
| `match_knowledge_documents()` | Semantic search (vector similarity) |
| `search_knowledge_by_keywords()` | Full-text search (без embeddings) |
| `get_user_history()` | История сообщений пользователя |

---

## GitHub MCP — зачем и как

После установки GitHub MCP в Claude Desktop — я смогу:
- Напрямую делать commit + push из этой сессии
- Читать файлы в репо без git pull
- Создавать PR и ветки
- Больше не нужно "сделай, потом запушь вручную"

**Установить:** Claude Desktop → Settings → MCP Servers → Add → GitHub

---

## Критические напоминания

1. `.env` никогда не коммитить (уже в .gitignore)
2. VPS с 1 ядром — только для бота, не для heavy processing
3. `knowledge_base.json` исключён из git (137KB, пересоздаётся скриптом)
4. После git pull — проверить что структура /knowledge/raw/ не сломалась
