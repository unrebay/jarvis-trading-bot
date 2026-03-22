# JARVIS — System Architecture v1.0

> Last updated: 2026-03-22
> Status: Foundation complete. Ready for VPS deploy + KB loading.

---

## 1. Цель системы

JARVIS — мультимодальная AI-система для обучения трейдингу на основе методологии ICT/SMC.

**Сейчас:** Telegram-бот с базой знаний из курса DT Trading (Discord).
**Позже:** стратегии → Freqtrade → автоматическое тестирование.

---

## 2. Инфраструктура

```
┌──────────────────────────────────────────────────────────────────┐
│  iMac (Core)           │  MacBook (Parallel)    │  VPS (Runtime) │
│  • Claude App          │  • Claude App          │  • Ubuntu      │
│  • Discord scraping    │  • Dev + testing       │  • 1 core      │
│  • Embedding gen       │  • Parallel tasks      │  • Telegram    │
│  • Architecture work   │  • Git push/pull       │  • bot 24/7    │
└──────────────────────────────────────────────────────────────────┘
                              │
                        GitHub (canon)
                  unrebay/jarvis-trading-bot
                              │
                        Supabase (DB)
                  jarvis-knowledge-base (eu-central-1)
```

| Машина | Роль | Ограничения |
|--------|------|------------|
| iMac | Основная работа, scraping, embeddings | Нужен включённым |
| MacBook | Параллельные задачи, dev | Remote control |
| VPS (1 core) | Telegram bot 24/7 | Только лёгкие задачи |
| GitHub | Хранение кода и знаний | Proxy 403 из VM |
| Supabase | Vector DB + история диалогов | Бесплатный tier |

---

## 3. Целевая архитектура (Data Flow)

```
╔══════════════════════════════════════════════════════════╗
║  SOURCES                                                  ║
║  Discord/Notion → Chrome MCP → .md files                 ║
╚══════════════╦═══════════════════════════════════════════╝
               ↓
╔══════════════╩═══════════════════════════════════════════╗
║  INGESTION   knowledge/raw/*.md (63 files сейчас)        ║
║  skills: knowledge-ingestion.md                          ║
╚══════════════╦═══════════════════════════════════════════╝
               ↓
╔══════════════╩═══════════════════════════════════════════╗
║  KNOWLEDGE BASE                                           ║
║  Structured: knowledge/lessons|rules|patterns/            ║
║  Vector: Supabase → knowledge_documents (embedding 1536) ║
║  skills: knowledge-structurer.md                         ║
╚══════════════╦═══════════════════════════════════════════╝
               ↓
╔══════════════╩═══════════════════════════════════════════╗
║  RETRIEVAL                                                ║
║  • Keyword search: search_knowledge_by_keywords()         ║
║  • Semantic search: match_knowledge_documents()           ║
║  • Fallback: local knowledge_base.json (RAG)              ║
╚══════════════╦═══════════════════════════════════════════╝
               ↓
╔══════════════╩═══════════════════════════════════════════╗
║  CLAUDE CORE                                              ║
║  • ClaudeClient (bot/logic/claude_client.py)              ║
║  • ask_mentor()    → Haiku (fast, cheap)                  ║
║  • structure_knowledge() → Sonnet (structuring)           ║
║  • analyze_complex()     → Opus (rare, deep analysis)     ║
║  • Prompt caching: system/prompts/mentor.md               ║
╚══════════════╦═══════════════════════════════════════════╝
               ↓
╔══════════════╩═══════════════════════════════════════════╗
║  TELEGRAM INTERFACE                                       ║
║  jarvis_bot.py v2 (Supabase + history)                    ║
║  Commands: /start, /level, /stats, /help                  ║
║  History: Supabase → conversations table (last 10 msgs)   ║
╚══════════════════════════════════════════════════════════╝

                    (Future)
                       ↓
            Strategy Extractor → Freqtrade
```

---

## 4. Структура репозитория

```
jarvis-trading-bot/
│
├── jarvis_bot.py              ← Telegram bot v2 (Supabase + history)
├── requirements.txt           ← python-telegram-bot, anthropic 0.49, supabase
├── .env                       ← Secrets (не в git в production)
├── .env.example               ← Шаблон переменных
│
├── bot/
│   └── logic/
│       ├── claude_client.py   ← Cost router: Haiku/Sonnet/Opus + caching
│       └── __init__.py
│
├── knowledge/
│   ├── raw/                   ← 63 .md файлов из Discord/Notion
│   │   ├── beginners/         ← instruments, live, terminology
│   │   ├── principles/        ← FVG, BPR, OB, liquidity, entry models
│   │   ├── structure-and-liquidity/
│   │   ├── market-mechanics/  ← sessions, AMD, PO3, TGIF
│   │   ├── gold-mechanics/    ← imbalance, timings, manipulations
│   │   ├── risk-management/   ← backtest, risk rules
│   │   ├── tda-and-entry-models/ ← TDA, static, wyckoff
│   │   └── psychology/        ← (pending)
│   ├── processed/             ← done markers
│   ├── lessons/               ← structured (pending)
│   ├── topics/
│   ├── rules/
│   ├── patterns/
│   ├── examples/
│   ├── mistakes/
│   ├── checklists/
│   └── strategy_cards/
│
├── system/
│   ├── prompts/
│   │   └── mentor.md          ← JARVIS system prompt (ICT/SMC, 5 levels)
│   ├── schemas/               ← 8 JSON schemas
│   │   ├── lesson.json
│   │   ├── topic.json
│   │   ├── rule.json
│   │   ├── pattern.json
│   │   ├── example.json
│   │   ├── mistake.json
│   │   ├── checklist.json
│   │   └── strategy_card.json
│   ├── skills/
│   │   ├── knowledge-ingestion.md
│   │   ├── knowledge-structurer.md
│   │   └── trading-mentor.md
│   └── progress/
│       └── discord_ingestion_state.json
│
├── deploy/
│   ├── jarvis.service         ← systemd service для VPS
│   ├── deploy.sh              ← one-shot deployment script
│   └── Makefile               ← make deploy | logs | restart | update | ssh
│
├── supabase/
│   └── schema.sql             ← Reference schema (actual tables already in Supabase)
│
├── operations/
│   ├── backup-policy.md
│   ├── restore.md
│   ├── maintenance.md
│   └── cost-policy.md
│
├── docs/
│   ├── JARVIS-ARCHITECTURE-v1.md  ← этот файл
│   ├── action-plan.md
│   ├── extensions-evaluation.md
│   ├── full-context-prompt.md
│   └── SETUP.md
│
├── media/                     ← images/videos/frames (пусто, для будущего)
├── strategies/                ← placeholder для Freqtrade
└── knowledge_base.json        ← local RAG fallback (в .gitignore)
```

---

## 5. Supabase

**Проект:** `jarvis-knowledge-base`
**ID:** `ivifpljgzsmstirlrjar`
**Region:** eu-central-1
**URL:** `https://ivifpljgzsmstirlrjar.supabase.co`

### Таблицы

| Таблица | Назначение | Ключевые поля |
|---------|-----------|---------------|
| `knowledge_documents` | База знаний + векторы | id, title, content, section, topic, source, embedding(1536) |
| `bot_users` | Пользователи бота | telegram_id, username, level, messages_count |
| `conversations` | История диалогов | user_id, role, content, created_at |

### SQL-функции

| Функция | Назначение |
|---------|-----------|
| `match_knowledge_documents(embedding, threshold, count)` | Semantic search (cosine similarity) |
| `search_knowledge_by_keywords(query, count)` | Full-text keyword search |
| `get_user_history(user_id, limit)` | История сообщений |

### Индексы
- HNSW на `embedding` (fast ANN search)
- GIN trigram на `content` и `title` (fast full-text)
- Индекс на `topic`, `section`
- Составной индекс на `user_id + created_at` (conversations)

---

## 6. KB Entities (8 схем)

| Сущность | Схема | Описание |
|----------|-------|----------|
| Lesson | `lesson.json` | Единица обучающего контента |
| Topic | `topic.json` | Тематический индекс (группировка) |
| Rule | `rule.json` | Торговое правило (entry/exit/risk/psychology) |
| Pattern | `pattern.json` | Ценовой паттерн с условиями входа |
| Example | `example.json` | Разбор конкретной сделки |
| Mistake | `mistake.json` | Типичная ошибка (антипаттерн) |
| Checklist | `checklist.json` | Чек-лист (pre/post trade, daily) |
| StrategyCard | `strategy_card.json` | Формализованная стратегия |

---

## 7. Skills

| Skill | Статус | Когда использовать |
|-------|--------|-------------------|
| `knowledge-ingestion` | ✅ Готов | Принять новый raw файл → сохранить в knowledge/raw/ |
| `knowledge-structurer` | ✅ Готов | Обработать raw .md → JSON-объекты в knowledge/lessons/ и т.д. |
| `trading-mentor` | ✅ Готов | Ответить на вопрос по трейдингу (в боте) |
| `image-analyst` | 🔮 Позже | Анализ скриншотов графиков |
| `video-processor` | 🔮 Позже | Извлечение знаний из видео |
| `strategy-extractor` | 🔮 Позже | Формализация стратегий из KB |

---

## 8. Cost Policy

| Модель | Использование | Стоимость примерно |
|--------|-------------|-------------------|
| Haiku (`claude-haiku-4-5`) | Telegram ответы, быстрые запросы | $0.25/M input |
| Sonnet (`claude-sonnet-4-6`) | Structuring KB, анализ | $3/M input |
| Opus (`claude-opus-4-6`) | Критический анализ, архитектура | $15/M input |

**Оптимизации:** prompt caching (mentor.md кешируется), chunking, no repeated work.

---

## 9. Extensions

| Extension | Статус | Назначение |
|-----------|--------|-----------|
| Supabase MCP | ✅ Активен | DB management прямо из Claude |
| Notion MCP | ✅ Активен | Scraping Notion страниц |
| Chrome MCP | ✅ Активен | Discord scraping |
| Skill Creator | ✅ Активен | Создание/улучшение skills |
| **GitHub MCP** | ❌ Установить | Прямой git push/commit из Claude |
| **context7** | ❌ Установить | Актуальные docs библиотек |
| n8n-mcp | ⏳ Позже | Автоматизация pipeline |
| Obsidian | ⏳ Позже | Если используется |

---

## 10. Discord Ingestion — Прогресс

| Секция | Каналы | Статус |
|--------|--------|--------|
| BEGINNERS | 3 | ✅ Done |
| PRINCIPLES | 6 | ✅ Done |
| MARKET-MECHANICS | 5 (3 video-only) | ✅ Done |
| GOLD-MECHANICS | 3 | ✅ Done |
| PLAYBOOK | partial | ⚠️ backtest+risk ✅, news-macro ❌ re-scrape, wyckoff older pending |
| PSYCHO | 3 | ❌ Pending |
| FUNDAMENTAL | 6 | ❌ Pending |
| MARKET PROFILE | 7 | ❌ Pending |
| DT LIBRARY | 3 | ❌ Pending |

**news-macro-analysis** channel ID: `1434296892077903962` — 8 страниц утеряны, нужен re-scrape.

---

## 11. Разделение труда

| Задача | Машина | Статус |
|--------|--------|--------|
| Discord scraping | iMac (Chrome MCP) | ⏸ Отложено |
| Knowledge structuring (63 raw files) | MacBook | ⏳ Next |
| Load KB → Supabase embeddings | iMac | ⏳ Next |
| Telegram bot development | MacBook/iMac | ✅ Bot v2 ready |
| VPS deployment | VPS + make deploy | ⏳ Ready to deploy |
| Architecture | iMac | ✅ Done |
| GitHub MCP + context7 setup | User | ⏳ Install in Claude Desktop |

---

## 12. Следующие шаги (приоритет)

1. **Установить расширения** — GitHub MCP + context7 в Claude Desktop
2. **git pull** на iMac Terminal + убедиться что merge применён
3. **VPS deploy** — `cd deploy && make deploy` после настройки `.env`
4. **Load KB** — написать `load_knowledge_to_supabase.py` (63 .md → embeddings → Supabase)
5. **Knowledge structuring** — запустить `knowledge-structurer` на raw файлах
6. **Re-scrape** — news-macro-analysis (8 страниц, channel ID 1434296892077903962)
7. **Continue ingestion** — wyckoff → PSYCHO → FUNDAMENTAL → MARKET PROFILE → DT LIBRARY
