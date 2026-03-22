# JARVIS Trading Bot — Architecture

> Last updated: 2026-03-22
> Status: Restructured — unified from jarvis-trading-bot + Трейдинг-агент

---

## System Overview

```
iMac       = Core server: Claude App + backend + agent terminal
VPS        = Always-online runtime: Telegram bot + API (planned)
MacBook    = Remote management: Telegram / SSH / parallel tasks
GitHub     = Knowledge canon: source of truth
Claude     = Reasoning layer: intelligence
```

## Target Architecture

```
Sources (Discord/Notion/Web)
  ↓
Ingestion (Chrome MCP → .md files)
  ↓
Knowledge Base (/knowledge/raw/ → structured JSON)
  ↓
Retrieval (RAG full-text + keyword scoring)
  ↓
Claude Core (reasoning / structuring / mentor)
  ↓
Telegram Interface (Haiku for bot, Sonnet for complex)
  ↓
(Later: Strategy → Freqtrade)
```

## Repository Structure (CANONICAL)

```
jarvis-trading-bot/
├── knowledge/
│   ├── raw/                    ← Scraped .md files from Notion (63 files, 8 dirs)
│   │   ├── beginners/          ← instruments, live, terminology
│   │   ├── principles/         ← intro, structure, inefficiency, blocks, order-flow, tda
│   │   ├── structure-and-liquidity/
│   │   ├── market-mechanics/   ← sessions, advanced-market-analysis
│   │   ├── gold-mechanics/     ← imbalance, timings, manipulations
│   │   ├── risk-management/    ← risk rules, backtest methodology
│   │   ├── tda-and-entry-models/  ← TDA, static, wyckoff
│   │   └── psychology/         ← (pending: emotions, discipline, technical-psychology)
│   ├── processed/              ← Done markers after structuring
│   ├── lessons/                ← Structured lessons (lesson.json schema)
│   ├── topics/                 ← Topic indices
│   ├── rules/                  ← Trading rules (rule.json schema)
│   ├── patterns/               ← Price patterns (pattern.json schema)
│   ├── examples/               ← Trade examples (example.json schema)
│   ├── mistakes/               ← Common mistakes (mistake.json schema)
│   ├── checklists/             ← Trading checklists (checklist.json schema)
│   └── strategy_cards/         ← Strategy cards (strategy_card.json schema)
│
├── media/
│   ├── images/                 ← Chart screenshots
│   ├── videos/                 ← Educational videos
│   ├── frames/                 ← Video frames
│   └── annotations/            ← Media markup
│
├── system/
│   ├── prompts/                ← Agent system prompts
│   ├── skills/                 ← Skills: ingestion, structurer, mentor
│   ├── schemas/                ← JSON schemas (8 entity types)
│   ├── configs/                ← Agent and bot configs
│   └── progress/               ← Ingestion state, task progress
│
├── operations/
│   ├── backup-policy.md
│   ├── restore.md
│   ├── maintenance.md
│   └── cost-policy.md
│
├── bot/
│   ├── handlers/               ← Telegram command handlers
│   ├── logic/                  ← Business logic
│   └── routes/                 ← Command routing
│
├── docs/
│   ├── architecture.md         ← This file
│   └── full-context-prompt.md  ← Master plan from ChatGPT
│
├── strategies/                 ← Placeholder for future Freqtrade strategies
│
├── jarvis_bot.py               ← Current monolith bot (to be refactored into bot/)
├── knowledge_base.json         ← Current RAG base (needs rebuild)
├── load_rag_base.py            ← RAG loading script
├── .env                        ← Environment variables
├── Dockerfile                  ← Docker deployment
├── requirements.txt            ← Python dependencies
└── .gitignore
```

## KB Entity Types (8 schemas)

| Schema | File | Description |
|--------|------|-------------|
| Lesson | `lesson.json` | Единица обучающего контента |
| Topic | `topic.json` | Тематический индекс |
| Rule | `rule.json` | Торговое правило |
| Pattern | `pattern.json` | Ценовой паттерн с условиями входа |
| Example | `example.json` | Пример сделки с разбором |
| Mistake | `mistake.json` | Типичная ошибка (антипаттерн) |
| Checklist | `checklist.json` | Чек-лист для проверки перед/после сделки |
| StrategyCard | `strategy_card.json` | Формализованная торговая стратегия |

## Skills

| Skill | Status | Purpose |
|-------|--------|---------|
| `knowledge-ingestion` | Active | Принять и сохранить сырой контент |
| `knowledge-structurer` | Active | Разобрать raw → JSON-объекты |
| `trading-mentor` | Active | Отвечать на вопросы по трейдингу |
| `image-analyst` | Planned | Анализ скриншотов графиков |
| `video-processor` | Planned | Извлечение контента из видео |
| `strategy-extractor` | Planned | Извлечение стратегий из KB |

## Data Pipeline

```
Discord/Notion → [Chrome MCP scraping] → knowledge/raw/*.md
                                              ↓
                         [knowledge-structurer] → knowledge/lessons|rules|patterns/*.json
                                                       ↓
                              [RAG rebuild] → knowledge_base.json
                                                  ↓
                              [trading-mentor] → Telegram responses
```

## Discord Ingestion Status

| Section | Status | Files |
|---------|--------|-------|
| BEGINNERS | ✅ Done | 3 channels |
| PRINCIPLES | ✅ Done | 6 channels |
| MARKET-MECHANICS | ✅ Done | 2 text + 3 video-only |
| GOLD-MECHANICS | ✅ Done | 3 channels |
| PLAYBOOK | ⚠️ Partial | backtest, risk ✅; news-macro needs re-scrape; wyckoff older posts pending |
| PSYCHO | ❌ Pending | 3 channels |
| FUNDAMENTAL | ❌ Pending | 6 channels |
| MARKET PROFILE | ❌ Pending | 7 channels |
| DT LIBRARY | ❌ Pending | 3 channels |

Details: `system/progress/discord_ingestion_state.json`

## Cost Strategy

| Model | Use Case | When |
|-------|----------|------|
| Haiku | Bot responses, simple queries | Default for Telegram |
| Sonnet | Knowledge structuring, analysis | Processing pipeline |
| Opus | Architecture decisions, complex reasoning | Rare, manual |

## Roles

| Who | Does |
|-----|------|
| User (Andy) | Загружает материалы, ставит задачи, тестирует |
| Claude (iMac) | Reasoning, обработка знаний, архитектура |
| Claude (MacBook) | Параллельные задачи по запросу |
| VPS | Telegram bot + API 24/7 (planned) |
| GitHub | Хранение кода и знаний (канон) |

## Extensions Evaluation

| Extension | Decision | Reason |
|-----------|----------|--------|
| Supabase MCP | ✅ Yes now | Already connected, useful for DB later |
| Claude Skill Creator | ✅ Yes now | Already available, helps create/improve skills |
| Notion MCP | ✅ Yes now | Already connected, direct page access |
| n8n-mcp | ⏳ Later | Automation useful but not critical now |
| context7 | ⏳ Later | Documentation lookup — nice-to-have |
| dev-browser | ❌ No | Chrome MCP already covers this |
| security guidance | ❌ No | Not relevant for current scope |

## Next Steps (Priority Order)

1. ~~Restructure repo to target structure~~ ✅
2. ~~Create all 8 KB schemas~~ ✅
3. ~~Save Full Context Prompt~~ ✅
4. ~~Update ingestion state~~ ✅
5. Run knowledge-structurer on 63 raw .md files → produce structured JSON
6. Rebuild knowledge_base.json (RAG base)
7. Continue Discord ingestion (re-scrape news-macro-analysis, then remaining sections)
8. Refactor jarvis_bot.py → modular bot/ structure
9. Set up GitHub repo and push
10. Set up VPS for 24/7 bot deployment
