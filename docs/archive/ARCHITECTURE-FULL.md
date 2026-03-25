# JARVIS Trading Bot — Полная Архитектура v2.0

**Дата:** 2026-03-22
**Статус:** In Development (Knowledge Base ✅, Deployment 🔄)
**Команда:** iMac (архитектура, scraping) + MacBook (параллель dev) + VPS Ubuntu 1-core (production)

---

## 1. Цель Система

**JARVIS** — AI-ментор по трейдингу ICT/SMC методологии для сообщества на Telegram.

- Обучает 5 уровней: Beginner → Intermediate → Advanced → Professional → Master
- Использует RAG (семантический поиск по 39 документам + embeddings)
- Кэшит system prompt в Claude API (эффективность, стоимость)
- Маршрутизирует запросы по стоимости: Haiku → Sonnet → Opus
- Хранит историю диалогов в Supabase (контекст на 100+ сообщений)

---

## 2. Инфраструктура

### 2.1 Главные машины

| Устройство | ОС | Роль | Хранилище | Сеть |
|---|---|---|---|---|
| **iMac** | macOS | Разработка, архитектура, embeddings | 500GB SSD | WiFi |
| **MacBook** | macOS | Параллель dev, тесты, git push | 256GB SSD | WiFi |
| **VPS** | Ubuntu 22 (1-core) | Production bot 24/7 | 20GB | Internet |

### 2.2 Сервисы

| Сервис | URL | Назначение | Статус |
|---|---|---|---|
| **Supabase** | `ivifpljgzsmstirlrjar.supabase.co` | PostgreSQL + pgvector + RLS | ✅ Готов |
| **Telegram Bot API** | `api.telegram.org` | Bot updates | ✅ Готов |
| **OpenAI API** | `api.openai.com` | Embeddings (text-embedding-3-small) | ✅ Готов |
| **Anthropic API** | `api.anthropic.com` | Claude models (Haiku/Sonnet/Opus) | ✅ Готов |
| **GitHub** | `github.com/user/jarvis-trading-bot` | Source control | ⚠️ VM proxy issue |

### 2.3 Локальные папки

```
/sessions/tender-wizardly-gauss/mnt/
├── jarvis-trading-bot/               # Канонический репо (iMac)
│   ├── jarvis_bot.py                # Entry point (Telegram updates)
│   ├── bot/logic/
│   │   ├── claude_client.py          # Cost router (Haiku/Sonnet/Opus)
│   │   ├── rag_search.py             # Supabase semantic search
│   │   └── telegram_handler.py       # Message processing
│   ├── system/
│   │   ├── prompts/mentor.md         # JARVIS system prompt (cached)
│   │   └── schemas/                  # 8 KB entity schemas (JSON)
│   ├── knowledge/raw/                # 139 .md files (5 разделов)
│   ├── knowledge_base.json           # Indexed metadata (39 docs)
│   ├── load_knowledge_to_supabase.py # Embeddings loader
│   ├── deploy/
│   │   ├── jarvis.service           # systemd unit
│   │   ├── deploy.sh                # VPS setup script
│   │   ├── Makefile                 # Commands (make deploy, etc)
│   │   └── requirements.txt          # Python deps
│   ├── docs/
│   │   ├── JARVIS-ARCHITECTURE-v1.md
│   │   └── MERGE-PLAN.md
│   └── .env                          # Secrets (committed, будет rotated)
│
├── trading-theory/                   # Discord export + notes
│   └── server2/                      # 20+ .txt files per channel
│
└── Трейдинг-агент/                   # Legacy (интеграция завершена)
    └── (архивная, не используется)

GitHub repo (origin):
├── main                              # Production branch
└── feature/v2-architecture           # MacBook's branch (ready to merge)
```

---

## 3. Data Flow

### 3.1 User Message Flow

```
User (Telegram)
    ↓
[telegram-bot-python] ←→ Telegram Bot API
    ↓
jarvis_bot.py (async handler)
    ├─→ Load conversation history
    │   └─→ Supabase conversations table (last 20 messages)
    │
    ├─→ Search knowledge base
    │   └─→ Supabase semantic search via match_knowledge_documents()
    │       • If OPENAI_API_KEY: use vector embeddings (cosine distance)
    │       • Else: use full-text search (GIN trigram index)
    │
    ├─→ Build context
    │   ├─→ System prompt: mentor.md (cached in Claude API)
    │   ├─→ Knowledge: top-3 semantic matches (title + snippet)
    │   └─→ History: last 20 messages from user
    │
    ├─→ Route request by complexity
    │   └─→ claude_client.ask_mentor()
    │       • Model: claude-haiku-4-5-20251001 ($0.80/$2.40 per 1M)
    │       • Speed: ~500ms, cost: ~$0.0001 per message
    │
    ├─→ Stream response
    │   └─→ Telegram formatting (markdown, emojis, code blocks)
    │
    └─→ Save to DB
        ├─→ INSERT bot_users if new
        ├─→ INSERT conversations (user message + assistant response)
        └─→ UPDATE bot_users (level, messages_count)

Response → Telegram → User
```

### 3.2 Knowledge Update Flow

```
Raw content
    ↓
Discord scraping (Notion MCP) → knowledge_base.json
    ↓
load_knowledge_to_supabase.py
    ├─→ Text chunking (no split, full docs)
    ├─→ OpenAI embeddings (text-embedding-3-small, 1536 dims)
    ├─→ Supabase INSERT
    │   └─→ knowledge_documents table
    │       • title, content, section, topic
    │       • embedding (pgvector 1536)
    │       • metadata (JSON: filename, headings, source_id)
    │
    └─→ Indexes auto-apply
        ├─→ HNSW (embedding similarity)
        ├─→ GIN trigram (full-text search)
        └─→ B-tree (section, topic, created_at)
```

---

## 4. Database Schema (Supabase)

### 4.1 Tables

#### `knowledge_documents` (39 rows, fully indexed)
```sql
id (bigint, PK)
title (text, unique with section)
content (text, ~1.5KB avg)
section (text, 5 values: beginners, market-mechanics, principles, structure-and-liquidity, tda-and-entry-models)
topic (text, nullable)
source (text, default: 'markdown')
embedding (vector[1536], pgvector, HNSW index)
metadata (jsonb: {filename, headings, source_id})
created_at (timestamptz, default: now())
updated_at (timestamptz, default: now())

Indexes:
  - PRIMARY KEY (id)
  - UNIQUE (title, section) -- prevent duplicates
  - HNSW (embedding, m=12, ef_construction=64) -- vector search
  - GIN (content, title) -- full-text search
  - B-tree (section, topic, created_at)
```

#### `bot_users` (user profiles)
```sql
id (bigint, PK)
telegram_id (bigint, UNIQUE)
username (text, nullable)
level (text, default: 'Intermediate', values: Beginner|Intermediate|Advanced|Professional|Master)
messages_count (int, default: 0)
created_at (timestamptz)
updated_at (timestamptz)

FK: conversations.user_id → bot_users.telegram_id
```

#### `conversations` (message history, full-text searchable)
```sql
id (bigint, PK)
user_id (bigint, FK to bot_users.telegram_id)
role (text, check: 'user' | 'assistant')
content (text, full message)
created_at (timestamptz, default: now())

Indexes:
  - B-tree (user_id, created_at DESC) -- get last N messages
  - GIN (content) -- search in chat history
```

### 4.2 Database Functions

```sql
match_knowledge_documents(
  query_embedding vector[1536],
  similarity_threshold float = 0.3,
  match_count int = 3
) → TABLE(id, title, content, section, similarity)
  Purpose: Semantic search via vector distance
  Cost: ~10ms per query

search_knowledge_by_keywords(
  search_query text
) → TABLE(id, title, content, section)
  Purpose: Full-text search (GIN trigram)
  Cost: ~5ms per query

get_user_history(
  user_telegram_id bigint,
  message_limit int = 20
) → TABLE(role, content, created_at)
  Purpose: Load conversation history
  Cost: ~2ms per call
```

---

## 5. Bot Logic (Python)

### 5.1 Cost Routing (`claude_client.py`)

```python
class ClaudeClient:
    def ask_mentor(text: str, context: str = "") -> str:
        """
        Route by complexity:
        - Simple Q&A (definitions, examples) → Haiku
        - Structure requests (analysis, plans) → Sonnet
        - Deep analysis (novel strategies) → Opus (rare)

        Metrics tracked:
          - input_tokens, output_tokens, cache_tokens
          - USD cost per model
          - prompt cache hit rate
        """

    def ask_complex(text: str) → str:
        """For rare complex analysis (analyze custom chart, etc)"""
```

**System Prompt Caching:**
```python
{
    "type": "text",
    "text": mentor_md,
    "cache_control": {"type": "ephemeral"}  # Cached for 5 min
}
```
Cost savings: 90% on prompt tokens after 1st call.

### 5.2 RAG Search (`rag_search.py`)

```python
class RAGSearch:
    def semantic_search(user_query: str, top_k=3) -> List[Doc]:
        """
        1. Embed user query (OpenAI text-embedding-3-small)
        2. Search Supabase: match_knowledge_documents()
        3. Return top-3 by cosine similarity
        4. Inject into context
        """

    def keyword_search(user_query: str, top_k=3) -> List[Doc]:
        """Fallback: full-text search (GIN trigram)"""
```

### 5.3 Telegram Handler (`telegram_handler.py`)

```python
async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    # Get/create user
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id, level="Intermediate")

    # Load history
    history = db.get_history(user_id, limit=20)

    # Search knowledge
    matches = rag.semantic_search(text)
    context_str = "\n\n".join([f"{m.title}\n{m.content[:500]}" for m in matches])

    # Get response
    response = client.ask_mentor(text, context=context_str)

    # Save to DB + send
    db.save_message(user_id, "user", text)
    db.save_message(user_id, "assistant", response)

    await update.message.reply_text(response, parse_mode="Markdown")
```

---

## 6. Deployment (VPS)

### 6.1 VPS Setup

**Server:** Ubuntu 22.04, 1 vCPU, 512MB RAM, 20GB SSD
**Service Manager:** systemd
**Entry Point:** `/opt/jarvis/jarvis_bot.py`

### 6.2 Deployment Process

```bash
# 1. Local: git push feature/v2-architecture
# 2. VPS: git clone + pull
# 3. VPS: make deploy (runs deploy.sh)
#    ├─→ Create jarvis system user
#    ├─→ Install Python 3.12
#    ├─→ Clone repo to /opt/jarvis
#    ├─→ Create venv + install deps
#    ├─→ Copy .env (secrets)
#    └─→ Install systemd service
# 4. VPS: systemctl start jarvis
# 5. VPS: systemctl enable jarvis (auto-start)
```

### 6.3 systemd Unit (`deploy/jarvis.service`)

```ini
[Unit]
Description=JARVIS Trading Bot
After=network.target

[Service]
Type=simple
User=jarvis
WorkingDirectory=/opt/jarvis
ExecStart=/opt/jarvis/venv/bin/python3 /opt/jarvis/jarvis_bot.py
Restart=always
RestartSec=10

MemoryMax=512M
CPUQuota=50%
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### 6.4 Management Commands

```bash
make deploy           # Full setup
make start/stop/restart
make logs             # Real-time logs
make update           # git pull + systemctl restart
make ssh              # SSH into VPS
```

---

## 7. Current State

### ✅ Completed
- [x] Supabase project setup (tables, indexes, functions)
- [x] Knowledge base loaded (39 documents with embeddings)
- [x] Bot code v2 (Supabase integration, history)
- [x] Cost router (Haiku as default)
- [x] System prompt cached
- [x] Telegram handler ready
- [x] Deploy scripts ready
- [x] Context7 MCP connected

### 🔄 In Progress
- [ ] Deploy bot to VPS
- [ ] Test bot in Telegram
- [ ] Monitor logs + costs
- [ ] Iterate on prompts

### ⏳ Pending
- [ ] Discord ingestion (complete remaining channels)
- [ ] Knowledge base expansion (100+ documents)
- [ ] Advanced features (level adaptation, persistent memory, etc)
- [ ] GitHub MCP (alternative: manual `git push` from Mac)

---

## 8. Git Workflow

### Problem
VM cannot access GitHub (proxy 403). Workaround:
1. **iMac/MacBook:** `git commit` + `git push` (has internet)
2. **VM:** `git fetch origin branch`, then use `git show origin/branch:file`

### Branches
- **main** — production (tested, safe)
- **feature/v2-architecture** — MacBook's work (ready to merge into main)

### Merge Plan
1. Create backup: `cp -r jarvis-trading-bot jarvis-trading-bot-BACKUP-2026-03-22`
2. Review 5 critical files (see `MERGE-PLAN.md`)
3. Merge: `git merge --no-ff feature/v2-architecture`
4. Push: `git push origin main`
5. iMac: `git pull origin main`

---

## 9. Cost Analysis

### Monthly Estimate

| Service | Usage | Cost |
|---|---|---|
| **Claude Haiku** | 1000 msgs/day × 30 days, ~2KB per msg | ~$2.40 |
| **Claude Sonnet** | 100 complex/day × 30, ~5KB | ~$1.50 |
| **OpenAI Embeddings** | 39 docs + updates (~500 docs/month) | ~$0.01 |
| **Supabase** | 500 messages + 50 users (free tier) | ~$0 |
| **VPS (1-core)** | 24/7 uptime | $5/month |
| **Telegram Bot** | Unlimited | $0 |
| **Total** | | **~$9/month** |

---

## 10. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         JARVIS SYSTEM                            │
└─────────────────────────────────────────────────────────────────┘

         ┌──────────────┐          ┌──────────────┐
         │   iMac       │          │  MacBook     │
         │ Develop      │ ←→ Git   │ Parallel Dev │
         │ Scrape       │          │ Test         │
         └──────┬───────┘          └──────┬───────┘
                │                         │
                └────────────┬────────────┘
                             │
                        git push
                             │
                        ┌────▼─────┐
                        │  GitHub   │
                        │ (origin)  │
                        └────┬─────┘
                             │
                        git pull
                             │
                    ┌────────▼────────┐
                    │      VPS        │
                    │   Ubuntu 1-core │
                    │   jarvis_bot.py │
                    └────────┬────────┘
                             │
         ┌─────────┬─────────┼─────────┬─────────┐
         │         │         │         │         │
         ▼         ▼         ▼         ▼         ▼
     ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────┐
     │Telegram│ │Supabase  │ │OpenAI    │ │Claude│ │Claude│
     │Bot API │ │PostgreSQL│ │Embeddings│ │Haiku │ │Sonnet│
     └────────┘ └──────────┘ └──────────┘ └──────┘ └──────┘
         │           │            │          │        │
         ▼           ▼            ▼          ▼        ▼
      [Users]  [Knowledge]   [Vectors]  [Response] [Complex]
              [History]
              [Users]
```

---

## 11. Next Actions Priority

1. **Deploy bot to VPS** (make deploy)
2. **Test in Telegram** (send test message, verify response)
3. **Monitor logs** (make logs, check costs)
4. **Iterate prompts** (based on real feedback)
5. **Continue Discord ingestion** (wyckoff → PSYCHO → FUNDAMENTAL)
6. **Expand knowledge base** (100+ documents target)

---

**Last Updated:** 2026-03-22
**Next Review:** After VPS deployment + 100 test messages
