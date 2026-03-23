# JARVIS Architecture Diagram

## Complete System Overview

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         USER INTERACTION LAYER                            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃   📱 Telegram               📊 Chart Images            🎥 Videos           ┃
┃   ├─ /start                 ├─ Chart screenshot       ├─ Educational     ┃
┃   ├─ /help                  ├─ With caption           ├─ Recordings      ┃
┃   ├─ Text messages          └─ Real-time charts       └─ Tutorials       ┃
┃   └─ Commands                                                             ┃
┃                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                     ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      TELEGRAM BOT APPLICATION LAYER                       ┃
┃                          src/bot/main.py                                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃  ┌─────────────────────────────────────────────────────────────────────┐  ┃
┃  │  MESSAGE ROUTING & HANDLERS                                         │  ┃
┃  │  ─────────────────────────────────────────────────────────────────  │  ┃
┃  │                                                                     │  ┃
┃  │  ┌──────────────────────┐  ┌──────────────────┐  ┌────────────┐  │  ┃
┃  │  │ Text Messages        │  │ Photo Upload     │  │  Commands │  │  ┃
┃  │  │ ─────────────────    │  │ ─────────────    │  │  ────────  │  │  ┃
┃  │  │ handle_message()     │  │ handle_photo()   │  │ /start     │  │  ┃
┃  │  │ ↓                    │  │ ↓                │  │ /help      │  │  ┃
┃  │  │ RAGSearch           │  │ ImageHandler     │  │ /level     │  │  ┃
┃  │  │ ↓                    │  │ ↓                │  │            │  │  ┃
┃  │  │ ClaudeClient        │  │ ChartAnnotator   │  └────────────┘  │  ┃
┃  │  └──────────────────────┘  └──────────────────┘                  │  ┃
┃  │                                                                     │  ┃
┃  └─────────────────────────────────────────────────────────────────────┘  ┃
┃                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                    ↓                    ↓                    ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━━━━━━━┓   ┏━━━━━━━━━━━━━━━┓
┃   LAYER 1: SEARCH     ┃   ┃  LAYER 2: VISION  ┃   ┃ LAYER 3: AI   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━┫   ┣━━━━━━━━━━━━━━━━━━━━━┫   ┣━━━━━━━━━━━━━━━┫
┃                       ┃   ┃                   ┃   ┃               ┃
┃  RAGSearch           ┃   ┃ ImageHandler     ┃   ┃ ClaudeClient  ┃
┃  ────────────────    ┃   ┃ ─────────────    ┃   ┃ ─────────────  ┃
┃                       ┃   ┃                   ┃   ┃               ┃
┃  semantic_search()    ┃   ┃  process_image()  ┃   ┃ ask_mentor()  ┃
┃  ├─ Supabase pgvector │   │  ├─ Vision API    │   │ ├─ Haiku      ┃
┃  ├─ Embeddings       │   │  │ (Claude Opus)  │   │ ├─ Sonnet     ┃
┃  └─ Semantic match   │   │  ├─ Chart analysis│   │ └─ Opus       ┃
┃                       ┃   │  └─ Entity create │   │               ┃
┃  keyword_search()     ┃   ┃                   ┃   ┃ Cost Router:  ┃
┃  ├─ Full-text search │   ┃ ChartAnnotator   ┃   ┃ ─────────────  ┃
┃  └─ Fallback         │   ┃ ─────────────    ┃   ┃               ┃
┃                       ┃   ┃                   ┃   ┃ Haiku $0.80/M ┃
┃ format_context()      ┃   ┃  analyze_chart()  ┃   ┃ Sonnet $3.00/M┃
┃ ├─ Prepare KB data   │   │  ├─ ICT patterns   │   │ Opus $15.00/M ┃
┃ └─ Context for LLM   │   │  ├─ Key levels    │   │               ┃
┃                       ┃   │  ├─ Confluence   │   │ Token cache:  ┃
┃                       ┃   │  └─ JSON output  │   │ mentor.md 5KB ┃
┃                       ┃   ┃                   ┃   ┃ 10% savings   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━┛   ┗━━━━━━━━━━━━━━━━━━━━━┛   ┗━━━━━━━━━━━━━━━┛
          ↓                           ↓                           ↓
          └───────────────────────────┴───────────────────────────┘
                                      ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                    KNOWLEDGE BASE LAYER (Source of Truth)                 ┃
┃                         kb/ directory                                     ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃  ┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ ┃
┃  │ SCHEMAS (Define)    │  │ LESSONS (Content)│  │ RELATIONSHIPS (Link) │ ┃
┃  │ ─────────────────── │  │ ──────────────── │  │ ────────────────────  │ ┃
┃  │ kb/schemas/         │  │ kb/lessons/      │  │ kb/relationships/    │ ┃
┃  │                     │  │                  │  │                      │ ┃
┃  │ • lesson.json       │  │ ├─ beginners/    │  │ • lesson-pattern.yaml│ ┃
┃  │ • pattern.json      │  │ │  ├─ lesson_*.  │  │ • pattern-rule.yaml  │ ┃
┃  │ • rule.json         │  │ │  │  json+md    │  │ • lesson-rule.yaml   │ ┃
┃  │ • term.json         │  │ │  └─ index.json │  │ • topic-*.yaml       │ ┃
┃  │ • chart_example.json│  │ │                │  │                      │ ┃
┃  │ • image_annotation. │  │ ├─ principles/   │  │ Total relationships: │ ┃
┃  │   json              │  │ │  (20 lessons)  │  │ ✅ Fully connected   │ ┃
┃  │ • video_segment.json│  │ │                │  │                      │ ┃
┃  │ • topic.json        │  │ ├─ market-      │  │                      │ ┃
┃  │ • mistake_case.json │  │ │  mechanics/    │  │                      │ ┃
┃  │ • _metadata.json    │  │ │  (15 lessons)  │  │                      │ ┃
┃  │                     │  │ │                │  │                      │ ┃
┃  │ Entity definitions  │  │ ├─ risk-        │  │                      │ ┃
┃  │ with JSON Schema    │  │ │  management/   │  │                      │ ┃
┃  │                     │  │ │  (6 lessons)   │  │                      │ ┃
┃  │ Ensures data        │  │ │                │  │                      │ ┃
┃  │ consistency         │  │ └─ ...           │  │                      │ ┃
┃  │                     │  │                  │  │                      │ ┃
┃  │ Total: 10 types     │  │ Total: 63       │  │ Enables semantic     │ ┃
┃  │                     │  │ lessons         │  │ understanding        │ ┃
┃  └─────────────────────┘  └──────────────────┘  └──────────────────────┘ ┃
┃                                                                            ┃
┃  ┌──────────────────────┐  ┌────────────────┐  ┌──────────────────────┐  ┃
┃  │ PROMPTS (Behavior)   │  │ CONFIGS (Rules)│  │ METADATA (Index)     │  ┃
┃  │ ──────────────────── │  │ ────────────── │  │ ────────────────────  │  ┃
┃  │ kb/prompts/          │  │ kb/ingestion-  │  │ kb/metadata/         │  ┃
┃  │                      │  │ config/        │  │                      │  ┃
┃  │ • mentor.md (5KB)    │  │                │  │ • indices.json       │  ┃
┃  │   - Main mentoring   │  │ • discord_*    │  │ • category_index.json│  ┃
┃  │   - Cached           │  │ • image_*      │  │ • search_index.json  │  ┃
┃  │   - 10% cost savings │  │ • video_*      │  │ • relationships.json │  ┃
┃  │                      │  │                │  │ • _metadata.json     │  ┃
┃  │ • image_analyzer.md  │  │ Defines:       │  │                      │  ┃
┃  │   - Vision task desc │  │ • Data source  │  │ KB state:            │  ┃
┃  │   - Analysis output  │  │   mapping      │  │ • 63 lessons indexed │  ┃
┃  │                      │  │ • Processing   │  │ • 8 categories       │  ┃
┃  │ • chart_annotator.md │  │   rules        │  │ • Updated 2026-03-22 │  ┃
┃  │   - ICT detection    │  │ • Quality      │  │ • Ready for          │  ┃
┃  │   - Pattern analysis │  │   checks       │  │   embeddings         │  ┃
┃  │                      │  │ • Rate limits  │  │                      │  ┃
┃  └──────────────────────┘  └────────────────┘  └──────────────────────┘  ┃
┃                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         PERSISTENCE LAYER (Storage)                       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃  ┌──────────────────────────────┐   ┌──────────────────────────────────┐ ┃
┃  │ SUPABASE (Database)          │   │ S3/STORAGE (Media)               │ ┃
┃  │ ──────────────────────────   │   │ ──────────────────────────────   │ ┃
┃  │                               │   │                                  │ ┃
┃  │ Tables:                       │   │ S3 Buckets:                      │ ┃
┃  │ • lessons                     │   │ • charts/                        │ ┃
┃  │   └─ 63 records               │   │ • images/                        │ ┃
┃  │   └─ embeddings (pgvector)    │   │ • videos/                        │ ┃
┃  │   └─ search index             │   │ • annotations/                   │ ┃
┃  │                               │   │                                  │ ┃
┃  │ • image_annotations           │   │ Storage types:                   │ ┃
┃  │   └─ analysis results         │   │ • PNG (charts) - optimized      │ ┃
┃  │   └─ image metadata           │   │ • WebP (compressed)             │ ┃
┃  │                               │   │ • MP4 (videos) - transcribed    │ ┃
┃  │ • conversations               │   │                                  │ ┃
┃  │   └─ user history             │   │ Organized by:                    │ ┃
┃  │   └─ message context          │   │ • Date (YYYY/MM/DD/)            │ ┃
┃  │                               │   │ • Type (charts/diagrams)        │ ┃
┃  │ • bot_users                   │   │ • Entity ID                      │ ┃
┃  │   └─ profiles                 │   │                                  │ ┃
┃  │   └─ preferences              │   │                                  │ ┃
┃  │   └─ statistics               │   │                                  │ ┃
┃  │                               │   │                                  │ ┃
┃  │ Access:                       │   │ Access:                          │ ┃
┃  │ • RAGSearch → semantic search │   │ • ImageHandler → upload/fetch   │ ┃
┃  │ • PostgreSQL/PostGIS          │   │ • Direct URL for display        │ ┃
┃  │ • HNSW indexing for speed     │   │ • Cloudflare CDN for performance│ ┃
┃  │                               │   │                                  │ ┃
┃  └──────────────────────────────┘   └──────────────────────────────────┘ ┃
┃                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      ↓
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                      ASYNC PROCESSING LAYER (n8n)                         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃   Future async workflows:                                                 ┃
┃   ├─ Discord ingestion (channel → KB entities)                            ┃
┃   ├─ Video processing (transcription + keyframe extraction)               ┃
┃   ├─ Image batch analysis (multiple charts at once)                       ┃
┃   ├─ Embedding generation (semantic search index)                         ┃
┃   └─ Scheduled KB maintenance (dedup, relationship updates)               ┃
┃                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Data Flow Examples

### 1️⃣ **Text Message Flow** (Educational Mentoring)

```
User: "Что такое Break of Structure?"
     ↓
Telegram → handle_message()
     ↓
RAGSearch:
  ├─ semantic_search("Break of Structure")
  ├─ Query Supabase pgvector
  └─ Find related lessons, patterns, rules
     ↓
ClaudeClient:
  ├─ Cost router selects Haiku (default)
  ├─ System prompt: mentor.md (cached 5KB)
  ├─ User message + KB context
  └─ Generate response
     ↓
Response stored in Supabase:
  └─ conversations table
     ↓
Reply via Telegram: "Break of Structure это когда цена пробивает..."
```

### 2️⃣ **Chart Image Flow** (Vision Analysis)

```
User: [Uploads EURUSD 4H chart]
     ↓
Telegram → handle_photo()
     ↓
ImageHandler:
  ├─ Download image
  ├─ Validate (400px+ width)
  ├─ Optimize (resize if needed)
  └─ Extract metadata
     ↓
ClaudeClient (Opus 4.6):
  ├─ Vision API call
  ├─ System prompt: image_analyzer.md
  ├─ Analyze patterns
  └─ Generate JSON response
     ↓
ChartAnnotator (Specialized):
  ├─ Detect ICT patterns
  │  ├─ Judas Swings
  │  ├─ Break of Structure
  │  └─ Market Structure
  ├─ Identify key levels
  │  ├─ Support/resistance strength
  │  └─ Confluence analysis
  └─ Generate geometric annotations
     ↓
Create entities:
  ├─ image_annotation (in Supabase)
  ├─ chart_example (if suitable)
  └─ Store images in S3
     ↓
Response: "Обнаружены паттерны: Judas Swing (92% confidence), BOS (85%)..."
```

### 3️⃣ **Knowledge Base Ingestion Flow** (Future)

```
Discord #trading-lessons channel
     ↓ (n8n scheduled ingestion)
Read messages
     ↓
Parse by channel mapping:
  ├─ #trading-lessons → lesson entities
  ├─ #chart-analysis → chart_example entities
  ├─ #pattern-library → pattern entities
  └─ #mistakes-to-avoid → mistake_case entities
     ↓
Validation:
  ├─ Check schema (JSON Schema validation)
  ├─ Deduplication (fuzzy matching)
  └─ Quality checks
     ↓
Enrichment:
  ├─ Auto-categorization
  ├─ Tag extraction
  ├─ Relationship linking
  └─ Vision analysis (if images)
     ↓
Store in KB:
  ├─ Save to kb/lessons/[category]/
  ├─ Create JSON+Markdown
  └─ Generate embeddings
     ↓
Update indices:
  ├─ Category index
  ├─ Search index
  └─ Metadata
```

---

## Component Responsibilities

| Component | File | Input | Process | Output |
|-----------|------|-------|---------|--------|
| **TelegramHandler** | `src/bot/telegram_handler.py` | User message/photo | Route by type | Telegram reply |
| **RAGSearch** | `src/bot/rag_search.py` | Query string | Semantic + keyword search | Top-K results + context |
| **ImageHandler** | `src/bot/image_handler.py` | Image bytes | Vision analysis + validation | JSON analysis + entities |
| **ChartAnnotator** | `src/bot/chart_annotator.py` | Image + context | ICT pattern detection | Structured annotations |
| **ClaudeClient** | `src/bot/claude_client.py` | Text + context | Cost routing + API calls | LLM response |
| **Supabase** | Cloud service | Queries | Store/retrieve data | Records + embeddings |
| **Knowledge Base** | `kb/` | Configuration | Source of truth | Schemas + content + relationships |

---

## Cost Model

```
Monthly Cost Estimation:
├─ Haiku API (~1000 msg/month, cheap tasks)
│  └─ $0.80/M tokens → ~$5-8/month
├─ Sonnet API (~200 msg/month, retrieval)
│  └─ $3.00/M tokens → ~$8-12/month
├─ Opus API (vision, 50 img/month)
│  └─ $15.00/M tokens → ~$5-8/month
├─ Prompt caching (mentor.md)
│  └─ 10% cost reduction → ~$2 saved
├─ Supabase (database + storage)
│  └─ ~$5-10/month
└─ Total: $18-30/month ✅
```

---

## Phase Progression

```
PHASE 0: ✅ COMPLETE
├─ Architecture design
├─ Monorepo structure
└─ Initial bot setup

PHASE 1: ✅ IN PROGRESS (NOW)
├─ Knowledge base migration (DONE)
├─ Image/chart handlers (DONE)
├─ Telegram integration (DONE)
├─ Relationship graph (NEXT)
├─ Embedding generation (NEXT)
└─ Bot testing with real charts (NEXT)

PHASE 1.5: (Coming)
├─ KB relationships validation
├─ Pattern extraction from lessons
├─ Rule identification
├─ Discord bot ingestion setup
└─ Video processing pipeline

PHASE 2: (Later)
├─ Strategy extraction layer
├─ Trading signals generation
├─ Freqtrade integration
└─ Backtesting framework
```

---

## Verification Checklist

- ✅ 63 lessons migrated to `kb/lessons/`
- ✅ 8 categories organized
- ✅ Category indices created
- ✅ Metadata generated
- ⏳ Embeddings generated (next)
- ⏳ Relationships validated (next)
- ⏳ Chart images tested (next)
- ⏳ Integration testing (next)

**Ready for:** Testing image analysis with real trading charts!
