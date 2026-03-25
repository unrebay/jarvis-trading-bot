# JARVIS Microservices Architecture v1.0

**Дата:** 2026-03-22
**Концепция:** Узконаправленные боты + Central Hub + Shared Infrastructure
**Статус:** Planning (Pre-implementation)

---

## 1. Архитектурная Концепция

### Текущая проблема (Monolith)
```
jarvis-trading-bot/
└─ jarvis_bot.py (всё в одном месте)
    ├─ Telegram handler
    ├─ RAG search
    ├─ Claude routing
    └─ User management
```
**Проблемы:**
- Сложно масштабировать
- Сложно добавлять новые функции
- Нельзя развивать независимо
- Risk: одна ошибка падает весь бот

### Решение (Microservices)
```
jarvis-ecosystem/
├── core/
│   ├── jarvis-hub/           # Central message broker
│   └── shared-libs/          # Common code (RAG, DB, Auth)
│
├── bots/
│   ├── mentor-bot/           # 🎓 Trading education
│   ├── signals-bot/          # 📊 Trade signals & analysis
│   ├── journal-bot/          # 📝 Trading journal & P&L
│   └── research-bot/         # 🔬 Market research & news
│
├── services/
│   ├── knowledge-service/    # RAG + embeddings
│   ├── analytics-service/    # User metrics & stats
│   └── notification-service/ # Alerts & reminders
│
└── infrastructure/
    ├── docker-compose.yml
    ├── kubernetes/ (future)
    └── .env.example
```

---

## 2. Репозиторий Структура

### 2.1 GitHub Organization: `/jarvis-ecosystem`

**Репозитории (7 реп):**

```
jarvis-ecosystem/
├── 1️⃣ jarvis-core
│   └── Shared libraries, base classes, utilities
│   └── Language: Python
│   └── Modules: RAG, Supabase client, Claude router, DB models
│
├── 2️⃣ jarvis-mentor-bot
│   └── Trading education Telegram bot
│   └── Language: Python
│   └── Dependencies: jarvis-core
│
├── 3️⃣ jarvis-signals-bot
│   └── Technical analysis & trading signals
│   └── Language: Python
│   └── Dependencies: jarvis-core
│
├── 4️⃣ jarvis-journal-bot
│   └── Trading journal, P&L tracking
│   └── Language: Python
│   └── Dependencies: jarvis-core
│
├── 5️⃣ jarvis-research-bot
│   └── Market news, fundamentals, research
│   └── Language: Python
│   └── Dependencies: jarvis-core
│
├── 6️⃣ jarvis-hub
│   └── Central message broker & orchestration
│   └── Language: Python (FastAPI)
│   └── Role: Routes messages between bots
│
└── 7️⃣ jarvis-deploy
    └── Docker, K8s, infrastructure
    └── Languages: Docker, YAML
    └── Contains: docker-compose, deployment scripts
```

---

## 3. Бот Специализация

### 🎓 **Mentor Bot** (Current JARVIS)
**Назначение:** Trading education (ICT/SMC methodology)

**Функции:**
- Q&A по торговле (5 уровней)
- Объяснение концепций (FVG, POI, MSS, и т.д.)
- History + context awareness
- Adaptive level selection

**Input:** User questions → Telegram
**Output:** Educational response → Telegram
**Dependencies:**
- jarvis-core (RAG, Claude)
- Supabase (history, user profiles)

**Примерные команды:**
```
/ask Что такое fair value gap?
/level Advanced
/lesson Entry models
```

---

### 📊 **Signals Bot** (New)
**Назначение:** Trade signals & technical analysis

**Функции:**
- Real-time chart analysis
- Entry/Exit signals based on ICT rules
- Risk/Reward calculations
- Backtesting results
- Market structure analysis

**Input:**
- User chart uploads (image/data)
- Watchlist requests
- "Analyze this pattern"

**Output:**
- Signal with confidence score
- Risk/Reward ratio
- Entry/SL/TP levels

**Dependencies:**
- jarvis-core (Claude, analysis models)
- TradingView API (optional)
- TA-Lib (technical indicators)

**Примерные команды:**
```
/analyze [image] (upload chart)
/watchlist EURUSD
/signal BTC/USDT 4H
```

---

### 📝 **Journal Bot** (New)
**Назначение:** Trading journal & performance tracking

**Функции:**
- Log trades (entry, exit, P&L)
- Daily/Weekly/Monthly stats
- Win rate, drawdown, sharp ratio
- Trade reviews with notes
- Pattern recognition (losing trades analysis)

**Input:**
- Trade details (symbol, size, entry/exit)
- Screenshots with notes
- Voice/text reviews

**Output:**
- Trade logged → Supabase
- Stats dashboard
- Performance report

**Dependencies:**
- jarvis-core (Supabase models)
- Plotly/Matplotlib (charts)

**Примерные команды:**
```
/log EURUSD 1.0820 1.0850 +50pips profit
/stats monthly
/review (link to trade)
/analyze_losses
```

---

### 🔬 **Research Bot** (New)
**Назначение:** Market research, fundamentals, news aggregation

**Функции:**
- News feeds (forex, crypto, stocks)
- Economic calendar events
- Earnings reports, earnings calls transcripts
- Macro analysis
- Sentiment analysis (news, social)

**Input:**
- User research requests
- Scheduled: daily news digest
- Economic events filter

**Output:**
- Research summaries
- Trading implications
- Risk assessments

**Dependencies:**
- jarvis-core (Claude, embeddings)
- NewsAPI / Alpha Vantage (data sources)
- Web scraping (MarketWatch, etc.)

**Примерные команды:**
```
/news USD inflation
/events today
/macro Fed rate decision
/sentiment crypto
```

---

## 4. Central Hub (Message Broker)

### 🔄 **Jarvis Hub** Role

```
┌─────────────────────────────────────────────────┐
│          Telegram Users                         │
│    (Mentor, Signals, Journal, Research)         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │   Telegram     │
        │  Bot Endpoint  │
        └────────┬───────┘
                 │
        ┌────────▼────────────────┐
        │   JARVIS HUB (FastAPI)  │
        │                         │
        │ Routes:                 │
        │ POST /message          │ ← Incoming message
        │ POST /callback         │ ← Bot response
        │ GET /status            │ ← Health check
        │ POST /broadcast        │ ← Send to multiple bots
        └────────┬─────┬───────┬─┘
                 │     │       │
        ┌────────▼─┐ ┌─▼──┐ ┌──▼────┐
        │ Mentor   │ │Sig │ │Journal │  etc.
        │ Bot      │ │Bot │ │Bot    │
        └──────────┘ └────┘ └───────┘
```

**Функции Hub:**
1. **Message Routing** — determine which bot should handle message
2. **Load Balancing** — distribute load across bot instances
3. **Service Discovery** — keep track of active bots
4. **Health Checks** — monitor bot status
5. **Logging/Monitoring** — centralized logs
6. **Rate Limiting** — prevent abuse
7. **Cross-bot Communication** — bot-to-bot messaging

**Примерная логика:**
```python
# hub.py
async def handle_message(message):
    # 1. Detect intent
    intent = detect_intent(message.text)
    # => "ask_mentor", "analyze_chart", "log_trade", "get_news"

    # 2. Route to appropriate bot
    if intent == "ask_mentor":
        response = await mentor_bot.handle(message)
    elif intent == "analyze_chart":
        response = await signals_bot.handle(message)
    # ... etc

    # 3. Return response
    return response
```

---

## 5. Shared Infrastructure (jarvis-core)

### 📦 **jarvis-core** Contains:

```python
jarvis_core/
├── rag/
│   ├── supabase_client.py      # Wrapper around Supabase
│   ├── embeddings.py           # OpenAI embeddings
│   └── search.py               # Semantic search
│
├── claude/
│   ├── client.py               # Claude API wrapper
│   ├── models.py               # Model constants (Haiku, Sonnet, Opus)
│   └── cost_router.py          # Route by cost
│
├── db/
│   ├── models.py               # SQLAlchemy models
│   │   ├── User
│   │   ├── Conversation
│   │   ├── Trade
│   │   ├── NewsArticle
│   │   └── Signal
│   └── migrations/
│
├── telegram/
│   ├── client.py               # python-telegram-bot wrapper
│   ├── decorators.py           # @rate_limit, @require_auth
│   └── formatters.py           # Markdown formatting utils
│
├── auth/
│   ├── jwt_handler.py          # Token verification
│   └── permissions.py          # Role-based access
│
└── utils/
    ├── logging.py
    ├── config.py               # Environment loading
    └── exceptions.py
```

**Usage в бота:**
```python
# mentor_bot/main.py
from jarvis_core.rag import RAGSearch
from jarvis_core.claude import ClaudeClient
from jarvis_core.db.models import User, Conversation
from jarvis_core.telegram import TelegramHandler

class MentorBot(TelegramHandler):
    def __init__(self):
        self.rag = RAGSearch()
        self.claude = ClaudeClient()

    async def handle_question(self, message):
        # Use shared components
        docs = await self.rag.search(message.text)
        response = await self.claude.ask_mentor(message.text, docs)
        return response
```

---

## 6. Development Workflow

### 6.1 Local Development

```bash
# Clone all repos
git clone https://github.com/jarvis-ecosystem/jarvis-core
git clone https://github.com/jarvis-ecosystem/jarvis-mentor-bot
git clone https://github.com/jarvis-ecosystem/jarvis-signals-bot
# ... etc

# Setup symlink for shared lib
cd jarvis-mentor-bot
pip install -e ../jarvis-core  # Editable install

# Run locally
python main.py  # Starts bot in dev mode
```

### 6.2 Testing Cross-Bot Communication

```bash
# Terminal 1: Start Hub
cd jarvis-hub
python main.py

# Terminal 2: Start Mentor Bot
cd jarvis-mentor-bot
python main.py

# Terminal 3: Start Signals Bot
cd jarvis-signals-bot
python main.py

# Now send message to Telegram, Hub routes it
```

### 6.3 Deployment (Docker)

```bash
# Deploy all services
cd jarvis-deploy
docker-compose up -d

# Check status
docker-compose ps
docker logs jarvis-mentor-bot
```

---

## 7. Database Schema Evolution

### Current (Single DB)
```
Supabase: jarvis_trading (all tables in one DB)
├── bot_users
├── conversations
├── knowledge_documents
└── ...
```

### Future (Distributed)
```
Supabase: jarvis_trading (shared)
├── bot_users (shared)
├── conversations (shared)
├── knowledge_documents (shared)

Per-Bot Databases:
├── Signals DB: trades, signals, patterns
├── Journal DB: journal_entries, trade_reviews, stats
└── Research DB: articles, news, sentiment
```

---

## 8. Deployment Targets

### Phase 1: Local + Single VPS (Current)
```
localhost:3000 ← Mentor Bot (dev)
localhost:3001 ← Signals Bot (dev)
localhost:3002 ← Journal Bot (dev)

VPS (production):
├── Mentor Bot (systemd)
├── Signals Bot (systemd)
└── Hub (systemd)
```

### Phase 2: Docker Compose
```
docker-compose.yml:
  - mentor_bot service
  - signals_bot service
  - journal_bot service
  - hub service
  - supabase service (optional: local postgres)
```

### Phase 3: Kubernetes (Future)
```
K8s Deployments:
  - mentor-bot (3 replicas)
  - signals-bot (2 replicas)
  - journal-bot (1 replica)
  - hub (2 replicas)
  - redis (message queue)
```

---

## 9. Inter-Bot Communication Examples

### Example 1: Mentor asks Signals Bot for analysis

```python
# mentor_bot/handlers.py
async def handle_chart_question(message):
    chart_url = extract_image_url(message)

    # Call signals bot via Hub
    response = await hub.call_service(
        service="signals_bot",
        action="analyze_chart",
        params={"chart_url": chart_url}
    )

    # Return analysis to user
    return response
```

### Example 2: Journal Bot notifies user about pattern

```python
# journal_bot/analyzers.py
async def analyze_losses():
    patterns = detect_losing_patterns()

    # Send to all bots
    await hub.broadcast(
        event="losing_pattern_detected",
        data=patterns
    )

    # Mentor Bot receives this and creates lesson
    # Signals Bot receives this and adjusts analysis
```

---

## 10. Implementation Roadmap

### Week 1: Setup Foundation
- [ ] Create jarvis-core repo + shared libs
- [ ] Refactor mentor-bot to use jarvis-core
- [ ] Setup GitHub org/repos

### Week 2-3: Build Additional Bots
- [ ] Create signals-bot
- [ ] Create journal-bot (basic)
- [ ] Create research-bot (basic)

### Week 4: Integration
- [ ] Build jarvis-hub (FastAPI router)
- [ ] Test cross-bot communication
- [ ] Deploy docker-compose

### Week 5+: Advanced Features
- [ ] Redis message queue
- [ ] Advanced analytics
- [ ] K8s deployment
- [ ] Auto-scaling

---

## 11. Technology Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.12+ |
| **Bots** | python-telegram-bot 20.7 |
| **Hub/API** | FastAPI 0.104+ |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **AI** | Anthropic Claude API + OpenAI embeddings |
| **Container** | Docker + Docker Compose |
| **Queue** | Redis (future) |
| **Orchestration** | Kubernetes (future) |
| **Monitoring** | Prometheus + Grafana (future) |

---

## 12. Success Metrics

### Per Bot
- Response time: < 2s
- Uptime: > 99%
- Error rate: < 0.1%
- Users: track per bot

### System-wide
- Cross-bot latency: < 100ms
- Hub throughput: > 100 req/s
- Total monthly cost: < $100

---

## Questions to Resolve

1. **Message Queue:** Redis or simple HTTP?
   - Pros/Cons of each approach

2. **Database Sharing:** Shared Supabase or separate DBs?
   - Data consistency vs. isolation

3. **Monitoring:** Prometheus+Grafana or simple logs?
   - Complexity vs. observability

4. **Authentication:** JWT between bots or simple API keys?
   - Security vs. simplicity

5. **Rate Limiting:** Per-user, per-bot, or global?
   - Fairness vs. abuse prevention

---

**Next Step:** Review this plan, get feedback, then start implementation

