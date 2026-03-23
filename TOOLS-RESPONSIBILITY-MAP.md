# 🛠️ JARVIS Tools Responsibility Map

Visual guide showing what each component does and how they interact.

---

## 1️⃣ USER INTERACTION TOOLS

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT                             │
│                 src/bot/main.py                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Responsibility: Route all user input to correct handlers  │
│                                                             │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐│
│  │ /start       │  │ /help         │  │ /level           ││
│  │ /search      │  │ /history      │  │ [commands]       ││
│  └──────────────┘  └───────────────┘  └──────────────────┘│
│         ↓                  ↓                    ↓           │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Text Messages    │  │ Photo Upload │  │ Sticker/     │ │
│  │ → handle_message │  │ → handle_     │  │ Other → pass │ │
│  │                  │  │   photo()    │  │             │ │
│  └──────────────────┘  └──────────────┘  └──────────────┘ │
│                                                             │
│  Output: Telegram message reply (markdown formatted)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2️⃣ KNOWLEDGE SEARCH TOOLS

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG SEARCH ENGINE                        │
│                src/bot/rag_search.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Responsibility: Find relevant KB content for user query   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Input: User query (text)                            │  │
│  │ "Что такое Judas Swing?"                           │  │
│  └─────────────────────────────────────────────────────┘  │
│                        ↓                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ semantic_search()                                   │  │
│  │ ├─ Query Supabase pgvector                         │  │
│  │ ├─ Find similar lessons (embeddings)               │  │
│  │ ├─ Calculate similarity scores                     │  │
│  │ └─ Return top-3 results                            │  │
│  └─────────────────────────────────────────────────────┘  │
│                        ↓                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ keyword_search() (fallback)                         │  │
│  │ ├─ Full-text search if embeddings fail             │  │
│  │ └─ Match keywords in titles/content                │  │
│  └─────────────────────────────────────────────────────┘  │
│                        ↓                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ format_context()                                    │  │
│  │ ├─ Prepare results for Claude                      │  │
│  │ ├─ Add sources and citations                       │  │
│  │ └─ Create prompt-ready context                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                        ↓                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Output: Structured context for LLM                 │  │
│  │ ├─ Top results: lesson_ict_judas_swing             │  │
│  │ ├─ Content snippets                                │  │
│  │ └─ Related patterns & rules                        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ IMAGE/VISION TOOLS

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMAGE HANDLER                                    │
│                src/bot/image_handler.py                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Responsibility: Process and analyze trading chart images          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Input: Chart image (screenshot from TradingView, etc)         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ _validate_and_optimize_image()                                │ │
│  │ ├─ Check: 400px+ width required                              │ │
│  │ ├─ Validate: PNG, JPG, GIF, WebP format                      │ │
│  │ ├─ Resize: Max 2400px (reduce API cost)                      │ │
│  │ ├─ Compress: Quality 85 (balance quality/size)               │ │
│  │ └─ Extract: Metadata (size, format, hash)                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ _analyze_with_vision()                                        │ │
│  │ ├─ Call Claude Opus 4.6 (most powerful)                      │ │
│  │ ├─ System: image_analyzer.md prompt (cached)                 │ │
│  │ ├─ Input: Image + context (title, description)               │ │
│  │ └─ Output: JSON with patterns, levels, analysis              │ │
│  │                                                               │ │
│  │   {                                                          │ │
│  │     "type": "chart",                                         │ │
│  │     "analysis_type": "chart",                                │ │
│  │     "confidence": 0.92,                                      │ │
│  │     "detected_patterns": [                                   │ │
│  │       "pattern_judas_swing",                                 │ │
│  │       "pattern_break_of_structure"                           │ │
│  │     ],                                                       │ │
│  │     "key_levels": [                                          │ │
│  │       {"level": 1.0850, "type": "support"}                   │ │
│  │     ]                                                        │ │
│  │   }                                                          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ _store_image()                                                │ │
│  │ ├─ Save locally to kb/media/images/processed/                │ │
│  │ ├─ Upload to Supabase storage                                │ │
│  │ └─ Return image_id for reference                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ _create_image_annotation_entity()                             │ │
│  │ ├─ Build image_annotation entity                             │ │
│  │ ├─ Link to patterns & lessons                                │ │
│  │ └─ Ready for Supabase storage                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ _store_entity()                                               │ │
│  │ ├─ Save image_annotation to Supabase                         │ │
│  │ └─ Generate embeddings for search                            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                           ↓                                        │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Output: Telegram reply                                       │ │
│  │ "📊 Анализ графика:                                         │ │
│  │  Обнаружены паттерны:                                        │ │
│  │  • Judas Swing (92% confidence)                             │ │
│  │  • BOS (85% confidence)                                     │ │
│  │  Ключевые уровни:                                           │ │
│  │  • Support: 1.0850 (strong, 3 тестов)"                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

         USED BY: TelegramHandler.handle_photo()
         API: Claude Opus 4.6 (vision)
         Cost: ~$0.15-0.30 per image
```

---

## 4️⃣ CHART ANALYSIS TOOL

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHART ANNOTATOR                              │
│                src/bot/chart_annotator.py                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Responsibility: Detect ICT patterns and generate annotations  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Input: Chart image + context (instrument, timeframe)     │  │
│  │ Example: EURUSD 4H chart                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ _extract_chart_info()                                   │  │
│  │ ├─ Instrument: EURUSD                                   │  │
│  │ ├─ Timeframe: 4H                                        │  │
│  │ ├─ Price range: [1.0800, 1.1000]                       │  │
│  │ └─ Session: London/NY overlap                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ _analyze_patterns_and_levels()                          │  │
│  │ ├─ Claude Opus vision API                              │  │
│  │ ├─ System prompt: chart_annotator.md (cached)          │  │
│  │ ├─ Detect ICT patterns:                                │  │
│  │ │  • Judas Swing (confidence: 0.92)                    │  │
│  │ │  • Break of Structure (confidence: 0.85)             │  │
│  │ │  • Market Structure (HH/HL/LL/LH)                    │  │
│  │ │  • Liquidity Grabs                                   │  │
│  │ └─ Identify key levels with strength                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ _analyze_confluence()                                   │  │
│  │ ├─ Find zones with multiple support reasons            │  │
│  │ ├─ Calculate confluence score (0-100%)                 │  │
│  │ ├─ Assign trading probability                          │  │
│  │ └─ Example: Support at 1.0850                          │  │
│  │   - Multiple tests ✓                                   │  │
│  │   - Volume confirmation ✓                              │  │
│  │   - Fibonacci level ✓                                  │  │
│  │   → Confluence score: 95%                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ _generate_annotations()                                 │  │
│  │ ├─ Create geometric shapes:                            │  │
│  │ │  • Horizontal lines for levels                       │  │
│  │ │  • Rectangles for zones                              │  │
│  │ │  • Arrows for direction                              │  │
│  │ │  • Circles for key points                            │  │
│  │ ├─ Add labels & descriptions                          │  │
│  │ └─ Color coding:                                       │  │
│  │    - Red: Resistance                                   │  │
│  │    - Green: Support                                    │  │
│  │    - Magenta: Patterns                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ _build_annotation_json()                                │  │
│  │ └─ Structured output ready for storage                 │  │
│  │    or further processing                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Output: Detailed annotation JSON                        │  │
│  │ ├─ patterns_detected[*]                                │  │
│  │ │  - pattern_name: "Judas Swing"                      │  │
│  │ │  - confidence: 0.92                                 │  │
│  │ │  - entry_setup: {...}                              │  │
│  │ ├─ key_levels[*]                                      │  │
│  │ │  - level: 1.0850                                   │  │
│  │ │  - type: "support"                                 │  │
│  │ │  - strength: "strong"                              │  │
│  │ ├─ geometric_annotations[*]                           │  │
│  │ │  - type, coordinates, label, color                 │  │
│  │ └─ confluence analysis                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  USED BY: ImageHandler (for chart-specific analysis)           │
│  API: Claude Opus 4.6 (vision)                                 │
│  Cost: ~$0.20-0.40 per chart                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5️⃣ AI & COST ROUTING TOOL

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CLIENT                                │
│                src/bot/claude_client.py                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Responsibility: Route API calls to cheapest appropriate model │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │    HAIKU       │  │    SONNET      │  │     OPUS       │   │
│  │   $0.80/M      │  │   $3.00/M      │  │  $15.00/M      │   │
│  │  ─────────────  │  │  ─────────────  │  │  ─────────────  │   │
│  │ • Simple Q&A   │  │ • Retrieval    │  │ • Vision       │   │
│  │ • Summarize    │  │ • Reasoning    │  │ • Complex      │   │
│  │ • Format text  │  │ • Analysis     │  │   analysis     │   │
│  │ • Quick reply  │  │ • KB creation  │  │ • Accuracy    │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
│         ↑                    ↑                     ↑            │
│         │                    │                     │            │
│  ask_mentor() decision tree:                      │            │
│  ├─ Vision task? → Opus                          │            │
│  ├─ KB search + mention? → Sonnet                │            │
│  ├─ Token cache available? → 10% discount        │            │
│  └─ Simple reply? → Haiku (DEFAULT)              │            │
│                                                   │            │
│  ┌──────────────────────────────────────────┐    │            │
│  │ ask_mentor()                              │    │            │
│  │ Input:                                    │    │            │
│  │ • text: user message                      │    │            │
│  │ • context: system prompt (mentor.md)     │    │            │
│  │ • history: recent messages (10-20)       │    │            │
│  │                                           │    │            │
│  │ Processing:                               │    │            │
│  │ ├─ Estimate task complexity              │    │            │
│  │ ├─ Select model (Haiku/Sonnet/Opus)     │    │            │
│  │ ├─ Calculate costs                        │    │            │
│  │ └─ Call API                               │    │            │
│  │                                           │    │            │
│  │ Return: LLM response (text)               │    │            │
│  └──────────────────────────────────────────┘    │            │
│                                                   │            │
│  ┌──────────────────────────────────────────────┐│            │
│  │ Token tracking:                              ││            │
│  │ • Input tokens: text → model                 ││            │
│  │ • Output tokens: model → response            ││            │
│  │ • Cache tokens: mentor.md reused             ││            │
│  │ • Cost calculation per token                 ││            │
│  └──────────────────────────────────────────────┘│            │
│                                                   │            │
│  Monthly cost optimization:                      │            │
│  • Haiku default for 80% of messages             │            │
│  • Token caching saves 10% ($2-3/month)          │            │
│  • Batch processing for non-urgent tasks         │            │
│  • Total estimated: $18-30/month ✅              │            │
│                                                   │            │
└─────────────────────────────────────────────────────────────────┘

  USED BY: TelegramHandler for all LLM calls
  API: Anthropic (Claude models)
  Models: Haiku, Sonnet, Opus (auto-selected)
```

---

## 6️⃣ KNOWLEDGE BASE TOOLS

```
┌──────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                               │
│                    kb/ directory                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Responsibility: Store, organize, and provide all knowledge    │
│                                                                  │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐ │
│  │ SCHEMAS             │  │ LESSONS (Content)               │ │
│  │ kb/schemas/         │  │ kb/lessons/                      │ │
│  │ ─────────────────── │  │ ────────────────────────────────  │ │
│  │                     │  │ ├─ beginners/ (3)               │ │
│  │ Define entity types │  │ │  • instruments.json/md       │ │
│  │ with JSON Schema    │  │ │  • terminology.json/md       │ │
│  │                     │  │ │  • intro-principles.json/md  │ │
│  │ 10 types total:     │  │ ├─ principles/ (20)             │ │
│  │ ├─ lesson           │  │ │  • fair-value-gap            │ │
│  │ ├─ pattern          │  │ │  • supply-demand-zone        │ │
│  │ ├─ rule             │  │ │  • ... (20 more)             │ │
│  │ ├─ topic            │  │ ├─ market-mechanics/ (15)       │ │
│  │ ├─ term             │  │ │  • session-dynamics          │ │
│  │ ├─ mistake_case     │  │ │  • asia-london-reversal      │ │
│  │ ├─ chart_example    │  │ │  • ... (13 more)             │ │
│  │ ├─ image_annotation │  │ ├─ risk-management/ (6)         │ │
│  │ ├─ video_segment    │  │ │  • risk-management-intro     │ │
│  │ └─ _metadata        │  │ │  • ... (5 more)              │ │
│  │                     │  │ ├─ gold-mechanics/ (8)          │ │
│  │ Ensures consistency │  │ │  • fvg-price-behavior        │ │
│  │ and data quality    │  │ │  • ... (7 more)              │ │
│  │                     │  │ ├─ tda-and-entry-models/ (9)   │ │
│  │ 146 properties      │  │ │  • multi-tf-analysis         │ │
│  │ across all types    │  │ │  • ... (8 more)              │ │
│  │                     │  │ ├─ structure-and-liquidity/ (2) │ │
│  │                     │  │ │  • structural-liquidity      │ │
│  │                     │  │ │  • ... (1 more)              │ │
│  │                     │  │ └─ index.json (per category)   │ │
│  └─────────────────────┘  └──────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────┐  ┌───────────────────────────────────┐ │
│  │ RELATIONSHIPS      │  │ PROMPTS (Behavior)               │ │
│  │ kb/relationships/  │  │ kb/prompts/                       │ │
│  │ ────────────────── │  │ ────────────────────────────────  │ │
│  │                    │  │                                   │ │
│  │ Connect entities:  │  │ System prompts:                  │ │
│  │                    │  │ ├─ mentor.md (5KB, CACHED)      │ │
│  │ • lesson-pattern   │  │ │  └─ Main mentoring behavior   │ │
│  │ • pattern-rule     │  │ ├─ image_analyzer.md (4.4KB)    │ │
│  │ • lesson-rule      │  │ │  └─ Vision analysis spec      │ │
│  │ • topic-*          │  │ └─ chart_annotator.md (6.2KB)   │ │
│  │ • ... (more future)│  │    └─ Pattern detection         │ │
│  │                    │  │                                   │ │
│  │ 15 relationships   │  │ Total: 18.9 KB                  │ │
│  │ defined in YAML    │  │ Cached savings: 10%              │ │
│  │                    │  │                                   │ │
│  │ Enables semantic   │  │                                   │ │
│  │ understanding of   │  │                                   │ │
│  │ how concepts link  │  │                                   │ │
│  └────────────────────┘  └───────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │ INGESTION CONFIGS    │  │ METADATA                       │  │
│  │ kb/ingestion-config/ │  │ kb/metadata/ & _metadata.json │  │
│  │ ────────────────────  │  │ ────────────────────────────  │  │
│  │                       │  │                               │  │
│  │ Define data sources: │  │ Track KB state:              │  │
│  │ • discord_*yaml      │  │ • Version: 1.0.0             │  │
│  │ • image_*yaml        │  │ • Last updated: 2026-03-22   │  │
│  │ • video_*yaml        │  │ • Total lessons: 63          │  │
│  │                       │  │ • Categories: 8              │  │
│  │ How to ingest from:  │  │ • Embeddings: pending        │  │
│  │ • Discord channels   │  │ • Coverage metrics           │  │
│  │ • Image directories  │  │ • Quality notes              │  │
│  │ • Video files        │  │ • Next priorities            │  │
│  │ • Manual uploads     │  │                               │  │
│  │                       │  │ Enable monitoring & planning │  │
│  │ 13 data sources      │  │                               │  │
│  │ configured (future)  │  │                               │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
│                                                                  │
│  Usage:                                                         │
│  ├─ RAGSearch → semantic search on lessons                    │
│  ├─ ImageHandler → create entities from analysis              │
│  ├─ ClaudeClient → system prompts + context                   │
│  └─ Future tools → ingestion, embeddings, etc                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7️⃣ UTILITY SCRIPTS

```
┌────────────────────────────────────────────────────────┐
│              SCRIPTS (scripts/ directory)              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  migrate_knowledge_base.py                           │
│  ├─ Reads: knowledge_raw/63 markdown files          │
│  ├─ Creates: JSON entities + metadata               │
│  ├─ Organizes: kb/lessons/ by category              │
│  └─ Generates: category indices + KB metadata       │
│                                                        │
│  analyze_kb.py                                       │
│  ├─ Reports: KB statistics & coverage               │
│  ├─ Checks: Schema compliance                       │
│  ├─ Validates: Relationships                        │
│  └─ Recommends: Next steps                          │
│                                                        │
│  load_knowledge_to_supabase.py (src/ingestion/)     │
│  ├─ Reads: kb/lessons/ JSON files                   │
│  ├─ Generates: Embeddings via API                   │
│  ├─ Uploads: To Supabase pgvector                   │
│  └─ Deduplicates: Avoids re-indexing                │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## INTERACTION FLOW

```
User Message Flow:

1. User sends text via Telegram
   ↓
2. TelegramHandler.handle_message()
   ├─ Extract text
   └─ Show "typing" indicator
   ↓
3. RAGSearch.search(text)
   ├─ Query Supabase pgvector
   ├─ Find top-3 lessons
   └─ Format as context
   ↓
4. ClaudeClient.ask_mentor()
   ├─ Select model (usually Haiku)
   ├─ Include: system prompt + KB context + history
   └─ Call Anthropic API
   ↓
5. LLM generates response
   ↓
6. Save to Supabase
   ├─ User message
   ├─ Assistant response
   └─ Update user stats
   ↓
7. Send reply via Telegram (markdown format)


Chart Image Flow:

1. User sends chart image via Telegram
   ↓
2. TelegramHandler.handle_photo()
   ├─ Download image
   └─ Show "analyzing..." message
   ↓
3. ImageHandler.process_image_upload()
   ├─ Validate & optimize
   ├─ Extract metadata
   └─ Call vision API
   ↓
4. ClaudeClient (Opus) analyzes with image_analyzer.md prompt
   ├─ Detect patterns
   ├─ Identify levels
   └─ Generate JSON
   ↓
5. ChartAnnotator.analyze_chart()
   ├─ Specialized ICT pattern detection
   ├─ Confluence analysis
   └─ Geometric annotations
   ↓
6. Create entities
   ├─ image_annotation (in DB)
   └─ Store image (in S3)
   ↓
7. Send formatted response
   "📊 Analysis:
    • Judas Swing (92%)
    • Support: 1.0850 (strong)"
```

---

## SUMMARY TABLE

| Component | File | Purpose | Input | Output | Cost |
|-----------|------|---------|-------|--------|------|
| **TelegramHandler** | telegram_handler.py | Route messages | Text/Photo/Commands | Telegram reply | Free |
| **RAGSearch** | rag_search.py | Find KB content | Query string | Top-K results + context | Free (local) |
| **ImageHandler** | image_handler.py | Analyze charts | Image bytes | Analysis JSON + entity | ~$0.15-0.30 |
| **ChartAnnotator** | chart_annotator.py | Detect ICT patterns | Image + context | Annotation JSON | ~$0.20-0.40 |
| **ClaudeClient** | claude_client.py | Route to LLM | Text + context | Response | $0.80-15/M tokens |
| **Supabase** | Cloud service | Store data | Queries | Records | ~$5-10/month |
| **Knowledge Base** | kb/ | Store knowledge | Config | Content + schemas | Free (local) |

---

**Total Monthly Cost**: $18-30 ✅ (Haiku-first + token caching)

**Ready for**: Image analysis testing with real trading charts!
