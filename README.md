# 🤖 JARVIS Trading Mentor Bot

**An AI-powered educational trading mentor powered by Claude, Telegram, and structured knowledge base.**

> "Education is the path to consistent profitability. Teach systems, not predictions."

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token
- Anthropic API Key (Claude models)
- Supabase Account (PostgreSQL + Vector embeddings)

### Setup

```bash
# 1. Clone and navigate
cd jarvis-trading-bot

# 2. Install dependencies
pip install python-telegram-bot anthropic supabase pillow requests --break-system-packages

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run migrations (if needed)
python scripts/migrate_knowledge_base.py

# 5. Start bot
python src/bot/main.py
```

### Your First Interaction

```
User: "Что такое Break of Structure?"
JARVIS: "Break of Structure (BOS) это момент, когда цена пробивает последний
        swing high/low и закрывается за ним..."
        [References to related lessons and patterns]

User: [Sends chart image]
JARVIS: "📊 Анализ графика:
        Обнаружены паттерны:
        • Judas Swing (92% confidence)
        • Break of Structure (85% confidence)
        Ключевые уровни:
        • Support: 1.0850 (strong, 3 tests)"
```

---

## 📁 Project Structure

```
jarvis-trading-bot/
├── src/
│   ├── bot/
│   │   ├── main.py                          # Entry point
│   │   ├── telegram_handler.py              # Message routing
│   │   ├── claude_client.py                 # Cost router
│   │   ├── rag_search.py                    # Semantic search
│   │   ├── image_handler.py                 # Vision analysis ✨ NEW
│   │   └── chart_annotator.py               # Pattern detection ✨ NEW
│   ├── ingestion/
│   │   └── load_knowledge_to_supabase.py    # KB loader
│   └── services/
│
├── kb/ (Knowledge Base - SOURCE OF TRUTH)
│   ├── lessons/                             # 63 educational lessons ✨
│   │   ├── beginners/ (3)
│   │   ├── principles/ (20)
│   │   ├── market-mechanics/ (15)
│   │   ├── risk-management/ (6)
│   │   ├── gold-mechanics/ (8)
│   │   ├── tda-and-entry-models/ (9)
│   │   ├── structure-and-liquidity/ (2)
│   │   └── _metadata.json
│   ├── schemas/                             # Entity type definitions
│   ├── relationships/                       # Entity relationships (YAML)
│   ├── prompts/                             # System prompts (cached)
│   └── ingestion-config/                    # Data source mappings
│
├── infra/
│   ├── docker/
│   ├── systemd/
│   └── k8s/
│
├── tests/
├── scripts/
│   ├── migrate_knowledge_base.py            # KB migration ✨
│   └── analyze_kb.py                        # KB analysis ✨
│
├── docs/
│   ├── ARCHITECTURE-DIAGRAM.md              # System architecture
│   ├── TOOLS-RESPONSIBILITY-MAP.md          # Component guide
│   ├── PHASE-1-IMPLEMENTATION.md            # Phase 1 details
│   └── README.md                            # This file
│
└── .env                                     # Secrets (NOT in git)
```

---

## 🎯 Phase Status

### Phase 0: ✅ Complete
- Architecture design
- Monorepo structure setup
- Initial bot framework

### Phase 1: ✅ In Progress
- ✅ Knowledge base migration (63 lessons)
- ✅ Image handler (vision analysis)
- ✅ Chart annotator (ICT pattern detection)
- ✅ Telegram integration (text + photo)
- ⏳ Testing with real charts
- ⏳ Embedding generation
- ⏳ Relationship validation

### Phase 1.5: Coming Next
- KB relationships validation
- Pattern extraction from lessons
- Discord bot ingestion setup
- Video processing pipeline

### Phase 2: Future
- Strategy extraction layer
- Trading signals generation
- Freqtrade integration
- Backtesting framework

---

## 📊 Components Overview

### Input Layer: Telegram
- Text messages → Educational mentoring
- Chart images → Vision analysis + pattern detection
- Commands → Configuration

### Processing Layer
| Tool | Purpose | Tech |
|------|---------|------|
| **RAGSearch** | Find relevant KB content | Supabase pgvector |
| **ImageHandler** | Analyze trading charts | Claude Opus vision |
| **ChartAnnotator** | Detect ICT patterns | Claude Opus + prompts |
| **ClaudeClient** | Route to appropriate model | Cost optimization |

### Knowledge Layer
- **63 Lessons** organized in 8 categories
- **10 Entity Types** with JSON Schema validation
- **15+ Relationships** linking concepts
- **3 System Prompts** (cached for cost reduction)

### Storage Layer
- **Supabase PostgreSQL**: Lessons, conversations, images
- **Supabase Vector (pgvector)**: Embeddings for semantic search
- **S3/Storage**: Chart images and media

---

## 💡 Key Features

### 1. Educational Mentoring
- Answers trading questions based on knowledge base
- Explains ICT methodology, market structure, risk management
- Adapts to user level (beginner/intermediate/advanced)
- **System prompt cached** → 10% cost savings

### 2. Vision Analysis
- Analyzes uploaded trading chart images
- Detects ICT patterns (Judas Swings, BOS, structure)
- Identifies support/resistance levels
- Calculates confluence zones
- Returns structured JSON output

### 3. Cost Optimization
```
Model Selection:
├─ Haiku ($0.80/M)    → Default, cheap tasks
├─ Sonnet ($3.00/M)   → Retrieval, reasoning
└─ Opus ($15.00/M)    → Vision, complex analysis

Monthly Cost: $18-30 ✅
├─ Text interactions: $8-12
├─ Vision analysis: $5-8
└─ Storage: $5-10
```

### 4. Semantic Search
- Full-text search with fallback
- pgvector embeddings for semantic matching
- Top-K retrieval with context preparation
- Formatted for LLM consumption

---

## 🚀 How to Use

### Test with Text
```bash
# Start bot
python src/bot/main.py

# In Telegram:
/start
/help
"Что такое Fair Value Gap?"
"Как правильно рассчитать risk/reward?"
```

### Test with Charts
```bash
# In Telegram:
[Send chart image]

# Bot analyzes and responds:
"📊 Обнаружены паттерны:
 • Judas Swing (92%)
 • BOS (85%)
 Ключевые уровни:
 • Support: 1.0850 (strong)"
```

### Check KB Health
```bash
# Analyze knowledge base
python scripts/analyze_kb.py

# Output:
# ✅ Total lessons: 63
# ✅ Schemas: 10 types
# ✅ Relationships: 15 defined
# ✅ Prompts: 3 configured
```

---

## 📈 Analytics

### Knowledge Base Stats
- **Lessons**: 63 (organized in 8 categories)
- **Total entities**: 60+ (with expansion for patterns/rules)
- **Schema fields**: 146 (across 10 types)
- **Relationships**: 15+ (lesson↔pattern, pattern↔rule, etc)
- **Prompts**: 3 (mentor, image_analyzer, chart_annotator)
- **Coverage**: Ready for embeddings & semantic search

### Cost Profile (Monthly)
```
Estimated: $18-30/month

Breakdown:
├─ API calls (Haiku default):    $5-8
├─ KB retrieval (Sonnet):        $8-12
├─ Vision analysis (Opus):       $5-8
├─ Token caching savings:        -$2-3
└─ Storage (Supabase):           $5-10
```

### Performance Targets
- ⏱️ Message response: <3 seconds
- 🖼️ Image analysis: <5 seconds
- 🔍 KB search: <100ms
- 💾 Cost per interaction: ~$0.01-0.10

---

## 🔐 Security

### Secrets Management
```bash
.env (NOT in git)
├─ TELEGRAM_BOT_TOKEN
├─ ANTHROPIC_API_KEY
├─ SUPABASE_URL
└─ SUPABASE_ANON_KEY
```

**⚠️ Never commit `.env` to git!**

### Environment Setup
```bash
# Copy template
cp .env.example .env

# Add your keys
export TELEGRAM_BOT_TOKEN="..."
export ANTHROPIC_API_KEY="..."
```

---

## 📚 Documentation

**Core Documents**:
- [`ARCHITECTURE-DIAGRAM.md`](ARCHITECTURE-DIAGRAM.md) — System architecture & data flow
- [`TOOLS-RESPONSIBILITY-MAP.md`](TOOLS-RESPONSIBILITY-MAP.md) — What each component does
- [`PHASE-1-IMPLEMENTATION.md`](PHASE-1-IMPLEMENTATION.md) — Phase 1 detailed guide

**Knowledge Base**:
- `kb/lessons/` — All educational content organized by category
- `kb/schemas/` — Entity type definitions (JSON Schema)
- `kb/relationships/` — How concepts connect (YAML)
- `kb/prompts/` — System prompts (mentor, image_analyzer, chart_annotator)
- `kb/ingestion-config/` — Data source configurations

---

## 🛠️ Development

### Add a New Lesson
```bash
# Create JSON entity
cat > kb/lessons/principles/lesson_new_concept.json << EOF
{
  "id": "lesson_principles_new_concept",
  "title": "New Trading Concept",
  "category": "principles",
  "level": "intermediate",
  "content": "...",
  "learning_objectives": ["...", "..."],
  "created_at": "2026-03-22T..."
}
EOF
```

### Add a New Pattern
```bash
# Document in lesson relationships
vi kb/relationships/lesson-pattern.yaml
# Add mapping of lesson_id → [pattern_ids]
```

### Test Vision Analysis
```bash
from src.bot.image_handler import ImageHandler
from src.bot.claude_client import ClaudeClient

client = ClaudeClient(...)
handler = ImageHandler(client)
result = handler.process_image_url("https://chart.png")
print(result["analysis"]["detected_patterns"])
```

---

## 🐛 Troubleshooting

### Bot not responding
```
Check:
1. TELEGRAM_BOT_TOKEN is valid
2. ANTHROPIC_API_KEY is valid & has quota
3. Supabase credentials correct
4. Internet connection stable
5. Bot is running: python src/bot/main.py
```

### Image analysis failing
```
Check:
1. Image size > 400px width
2. Format: PNG, JPG, GIF, WebP
3. Claude API key valid
4. kb/prompts/image_analyzer.md exists
5. Check logs for specific error
```

### KB search returning nothing
```
Check:
1. Embeddings generated: python src/ingestion/load_knowledge_to_supabase.py
2. Supabase pgvector extension enabled
3. Lessons loaded to DB
4. Query terms match lesson content
5. Consider keyword_search() fallback
```

---

## 📞 Support & Contact

- **Issues**: Check docs/ folder and logs
- **Improvements**: Create detailed GitHub issues
- **Questions**: Refer to PHASE-1-IMPLEMENTATION.md

---

## 📄 License

MIT License - See LICENSE file

---

## 🎓 Learning Resources

This project teaches:
- **AI/ML**: Vision analysis, semantic search, cost routing
- **Architecture**: Modular design, separation of concerns
- **Trading**: ICT methodology, market structure, risk management
- **DevOps**: Deployment, monitoring, optimization

**Built with love for traders by traders.** ♠️

---

## 🚀 Next Steps

1. **Test with Real Charts** (Phase 1.5)
   - Verify pattern detection accuracy
   - Fine-tune chart_annotator prompts
   - Validate with traders

2. **Generate Embeddings**
   - `python src/ingestion/load_knowledge_to_supabase.py`
   - Enables full semantic search
   - Improves relevance

3. **Build Relationship Graph**
   - Extract trading rules from lessons
   - Link patterns to rules
   - Create visual knowledge graph

4. **Deploy to VPS**
   - Docker container setup
   - Systemd service
   - Monitor costs and performance

5. **Phase 1.5: Discord Integration**
   - Set up n8n workflows
   - Ingest Discord content
   - Expand knowledge base

---

**Version**: 1.0.0 | **Status**: Phase 1 In Progress | **Last Updated**: March 22, 2026

"The greatest trading strategy is the one you actually follow." 📈
