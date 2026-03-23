# JARVIS Phase 1 Implementation Guide

## Status: ✅ COMPLETE

**Date**: March 22, 2026
**Phase**: Phase 1 (Educational Bot - Contour A)
**Milestone**: Monorepo restructuring + Image/Chart analysis

---

## What We Built

### 1. **Hybrid Monorepo Structure**

```
jarvis-trading-bot/
├── src/
│   ├── bot/
│   │   ├── main.py              # Entry point
│   │   ├── claude_client.py      # Cost router (Haiku/Sonnet/Opus)
│   │   ├── rag_search.py         # Semantic search with pgvector
│   │   ├── telegram_handler.py   # Telegram message handling
│   │   ├── image_handler.py      # Image analysis with vision (NEW)
│   │   └── chart_annotator.py    # Chart annotation & pattern detection (NEW)
│   ├── ingestion/
│   │   └── load_knowledge_to_supabase.py  # KB ingestion script
│   ├── services/                  # (Future: trading signals, etc)
│   └── utils/                     # (Future: helpers)
├── kb/
│   ├── schemas/                  # Entity type definitions (JSON Schema)
│   │   ├── lesson.json
│   │   ├── topic.json
│   │   ├── rule.json
│   │   ├── pattern.json
│   │   ├── term.json
│   │   ├── mistake_case.json
│   │   ├── chart_example.json
│   │   ├── image_annotation.json
│   │   ├── video_segment.json
│   │   └── _metadata.json
│   ├── relationships/             # Entity relationships (YAML)
│   │   ├── lesson-pattern.yaml
│   │   ├── pattern-rule.yaml
│   │   └── lesson-rule.yaml
│   ├── prompts/                  # System prompts (KB cached)
│   │   ├── mentor.md             # Main mentoring prompt
│   │   ├── image_analyzer.md     # Image vision analysis
│   │   └── chart_annotator.md    # Chart analysis spec
│   ├── ingestion-config/         # Data source configs
│   │   ├── discord_ingestion.yaml
│   │   ├── image_ingestion.yaml
│   │   └── video_ingestion.yaml
│   ├── lessons/                  # (Future: organized lessons)
│   ├── metadata/                 # KB indices and metadata
│   └── media/                    # (Future: images, videos, charts)
├── docs/                         # Documentation
├── infra/                        # Deployment (Docker, systemd, k8s)
├── tests/                        # Test suites
├── scripts/                      # One-off utilities
└── PHASE-1-IMPLEMENTATION.md    # This guide
```

---

## Phase 1 Components

### 📊 Image Handler (`src/bot/image_handler.py`)

**Purpose**: Process trading chart images with Claude vision

**Features**:
- Image download and validation (400px+ width required)
- Image optimization (resize, compress for API)
- Vision analysis with Claude Opus 4.6 (with caching)
- Automatic pattern detection from image content
- Key level identification
- Image annotation entity creation
- Supabase storage integration

**Class**: `ImageHandler`

**Key Methods**:
```python
# Process image from URL
result = image_handler.process_image_url(
    "https://example.com/chart.png",
    context={
        "title": "EURUSD 4H Setup",
        "description": "Judas swing entry"
    }
)

# Process local image
result = image_handler.process_image_upload(
    "/path/to/chart.jpg",
    context={"title": "Gold 1H"}
)
```

**Output**:
```json
{
  "success": true,
  "image_id": "image_abc123",
  "metadata": {
    "file_name": "image_20260322_143022_abc123",
    "file_size_kb": 245.5,
    "dimensions": {"width": 1920, "height": 1080},
    "format": "PNG"
  },
  "analysis": {
    "analysis_type": "chart",
    "confidence": 0.92,
    "detected_patterns": ["pattern_judas_swing", "pattern_break_of_structure"],
    "key_levels": [
      {"level": 1.0850, "type": "support", "strength": "strong"}
    ],
    "learning_points": ["..."manifest]
  },
  "entity": { "image_annotation entity dict" }
}
```

### 📈 Chart Annotator (`src/bot/chart_annotator.py`)

**Purpose**: Specialized chart analysis with ICT pattern detection

**Features**:
- ICT pattern detection (Judas Swings, BOS, Market Structure, etc.)
- Key level identification with strength assessment
- Confluence analysis (multiple reasons at same level)
- Geometric annotation generation (lines, rectangles, arrows)
- Structured JSON annotation output

**Class**: `ChartAnnotator`

**Key Methods**:
```python
# Analyze chart and generate annotations
result = chart_annotator.analyze_chart(
    image_data=image_bytes,
    context={
        "instrument": "EURUSD",
        "timeframe": "4H",
        "price_range": [1.0800, 1.1000]
    }
)
```

**Output**:
```json
{
  "success": true,
  "chart_info": {
    "instrument": "EURUSD",
    "timeframe": "4H"
  },
  "patterns": [
    {
      "pattern_name": "Judas Swing",
      "pattern_id": "pattern_judas_swing",
      "confidence": 0.92,
      "location": {
        "start_candle": 15,
        "end_candle": 22,
        "swing_low": 1.0825,
        "reversal_high": 1.0950
      },
      "entry_setup": {
        "trigger": "Retest of broken support",
        "risk_level": 1.0825,
        "target": 1.1050,
        "risk_reward": 3.0
      }
    }
  ],
  "key_levels": [
    {
      "level": 1.0850,
      "type": "support",
      "strength": "strong",
      "test_count": 3,
      "factors": ["multiple_tests", "volume_confirmation"]
    }
  ],
  "annotation_json": { "full annotation with geometric data" }
}
```

### 🤖 Updated Telegram Handler

**New Method**: `handle_photo()`

Telegram users can now send chart images and JARVIS will:
1. Download the image
2. Analyze with vision (pattern detection, level identification)
3. Generate structured analysis
4. Return interactive response with patterns and key levels

**Workflow**:
```
User sends chart image with caption "EURUSD 4H Judas swing?"
↓
handle_photo() → show "analyzing..."
↓
image_handler.process_image_upload()
↓
Returns analysis with detected patterns & levels
↓
Send formatted response to user
↓
Save analysis to conversation history
```

---

## Knowledge Base Schemas

### Entity Types (JSON Schema in `kb/schemas/`)

1. **lesson.json** - Educational content
   - title, description, category, level
   - learning_objectives, related_topics, related_rules, related_patterns
   - chart_examples, mistake_cases

2. **topic.json** - Conceptual nodes
   - name, description, category
   - parent/child topics, related lessons/rules
   - importance score

3. **rule.json** - Trading rules & principles
   - title, statement, category (risk-management, market-mechanics, etc)
   - importance (1-5), rationale, exceptions
   - related_lessons, related_patterns, violations_to_avoid

4. **pattern.json** - Trading patterns
   - name, description, category (ICT, price-action, structure, etc)
   - identification_criteria, entry/exit conditions
   - timeframes, risk_reward, win_rate
   - chart_examples, related_lessons

5. **term.json** - Glossary terms
   - term, definition, context
   - aliases, related_terms, example_usage

6. **mistake_case.json** - Common trading mistakes
   - title, description, frequency
   - why_it_happens, how_to_avoid
   - related_rules, severity (1-5)

7. **chart_example.json** - Annotated examples
   - title, image_url, instrument, timeframe, date
   - patterns_illustrated, lessons, entry/exit points
   - outcome (winner/loser/breakeven)
   - key_levels with prices

8. **image_annotation.json** - Visual annotations
   - image_url, type (chart/diagram/screenshot)
   - annotations (geometric + text)
   - related_patterns, related_lessons, related_rules

9. **video_segment.json** - Video content
   - title, video_url, duration_seconds
   - transcription (full/partial)
   - keyframes with timestamps and descriptions
   - chapters, difficulty_level

10. **_metadata.json** - KB state
    - version, last_updated
    - total_lessons, total_patterns, total_rules, etc
    - sources (where data came from)
    - completeness_metrics
    - next_priorities

### Relationships (YAML in `kb/relationships/`)

Describes how entities connect:

**lesson-pattern.yaml**
```yaml
- lesson_id: lesson_judas_swings
  pattern_ids:
    - pattern_judas_swing
    - pattern_break_of_structure
  description: "Detailed explanation of Judas swing mechanics"
```

**pattern-rule.yaml**
```yaml
- pattern_id: pattern_judas_swing
  rule_ids:
    - rule_never_trade_against_structure
    - rule_wait_for_confirmation
  description: "Judas swings follow specific rules about structure"
```

**lesson-rule.yaml**
```yaml
- lesson_id: lesson_risk_management
  rule_ids:
    - rule_risk_management_percentage
    - rule_breakeven_stop
  description: "Core risk management rules and their application"
```

---

## System Prompts

### Mentor Prompt (`kb/prompts/mentor.md`)

Main system prompt for educational mentoring. Includes:
- Core identity (JARVIS Trading Mentor)
- Knowledge base context (lessons, patterns, rules, etc)
- Teaching principles (risk-first, structure-respect, patience, psychology, education)
- Teaching methodology (different approaches for beginner/intermediate/advanced)
- Curriculum recommendations
- Guardrails (what NOT to do)

**Cached** for cost reduction (5KB, ~10% API cost savings).

### Image Analyzer Prompt (`kb/prompts/image_analyzer.md`)

Vision analysis system prompt for:
- Chart image analysis
- Diagram interpretation
- Concept map extraction
- Pattern/level identification
- Educational value assessment

Output: Structured JSON with patterns, levels, confidence scores.

### Chart Annotator Prompt (`kb/prompts/chart_annotator.md`)

Specialized chart analysis for:
- ICT pattern detection (Judas Swing, BOS, structure)
- Key level identification with strength assessment
- Confluence analysis
- Geometric annotation generation
- Structured JSON output

Output: Detailed annotation JSON with patterns, levels, annotations, confluence.

---

## Ingestion Configs

Configuration YAML files define how data flows into the knowledge base:

### Discord Ingestion (`kb/ingestion-config/discord_ingestion.yaml`)

Maps Discord channels to KB entity types:
- `#trading-lessons` → lesson entities
- `#chart-analysis` → chart_example entities
- `#pattern-library` → pattern entities
- `#mistakes-to-avoid` → mistake_case entities
- `#glossary` → term entities

Handles:
- Rate limiting, message filtering
- Media downloading and optimization
- Deduplication (fuzzy match on title)
- Auto-enrichment (categorization, tagging)
- Error handling and retries

### Image Ingestion (`kb/ingestion-config/image_ingestion.yaml`)

Processes images from `kb/media/images/raw/`:
- Validation (min 400px width, max 25MB)
- Optimization (resize, compress to WebP)
- Vision analysis with Claude Opus
- Pattern/level detection
- Deduplication (perceptual hash)
- Automatic entity creation (image_annotation, chart_example)
- Batch processing with n8n

### Video Ingestion (`kb/ingestion-config/video_ingestion.yaml`)

Processes videos from `kb/media/videos/raw/`:
- Metadata extraction
- Transcription (Anthropic API)
- Keyframe extraction (every 30s)
- Keyframe analysis with vision
- Entity creation (video_segment)
- Batch processing with n8n (off-peak hours)
- Cost optimization ($0.5 per hour estimated)

---

## How to Use Phase 1

### 1. **Process a Trading Chart**

```python
from src.bot.image_handler import ImageHandler
from src.bot.claude_client import ClaudeClient

# Initialize
claude_client = ClaudeClient(anthropic_api)
image_handler = ImageHandler(claude_client, supabase)

# Process image
result = image_handler.process_image_url(
    "https://example.com/eurusd_4h.png",
    context={
        "title": "EURUSD 4H Judas Swing Setup",
        "description": "Entry potential with 1:3 risk/reward"
    }
)

if result["success"]:
    patterns = result["analysis"]["detected_patterns"]
    levels = result["analysis"]["key_levels"]
    print(f"Detected patterns: {patterns}")
    print(f"Key levels: {levels}")
```

### 2. **Analyze Chart for ICT Patterns**

```python
from src.bot.chart_annotator import ChartAnnotator

chart_annotator = ChartAnnotator(claude_client)

result = chart_annotator.analyze_chart(
    image_data=image_bytes,
    context={
        "instrument": "EURUSD",
        "timeframe": "4H",
        "price_range": [1.0800, 1.1000]
    }
)

if result["success"]:
    for pattern in result["patterns"]:
        print(f"Pattern: {pattern.pattern_name}")
        print(f"Confidence: {pattern.confidence:.0%}")
        print(f"Entry setup: {pattern.entry_setup}")
```

### 3. **Run Telegram Bot with Image Support**

```bash
cd /path/to/jarvis-trading-bot

# Set up environment
export TELEGRAM_BOT_TOKEN="your_token"
export ANTHROPIC_API_KEY="your_key"
export SUPABASE_URL="your_url"
export SUPABASE_ANON_KEY="your_key"

# Run bot
python src/bot/main.py
```

**User can now**:
- Send `/start` → Greeting
- Send `/help` → Commands and curriculum
- Send text messages → Mentor responses with KB search
- Send chart images → Vision analysis with pattern detection

### 4. **Ingest Discord Content**

```python
# (Future) Use n8n to ingest from Discord
# Currently documented in kb/ingestion-config/discord_ingestion.yaml

# Manual ingestion of markdown lessons
python src/ingestion/load_knowledge_to_supabase.py \
  --input-dir kb/lessons/ \
  --entity-type lesson \
  --generate-embeddings
```

---

## Next Steps (Phase 1.5 - KB Restructuring)

After this implementation is deployed and tested:

1. **Organize Lessons** - Move knowledge from `knowledge_raw/` to `kb/lessons/` with proper structure
2. **Create Relationships** - Build comprehensive relationship graphs between lessons, patterns, rules
3. **Video Processing** - Set up n8n pipeline for video transcription and keyframe extraction
4. **Discord Bot** - Implement Discord bot for KB content ingestion
5. **Image Caching** - Implement prompt caching for vision analysis (cost reduction)

---

## Phase 2 Prerequisites (Freqtrade Integration)

Phase 1 must be **fully operational** before Phase 2:

✅ **Ready for Phase 2 when**:
- Educational bot is consistently responding correctly
- Image analysis is accurate on real trading charts
- Pattern detection matches user's manual analysis >80% of the time
- KB is fully indexed and searchable
- System is deployed on VPS with monitoring

⚠️ **NOT ready for Phase 2 if**:
- Bot is still learning or making mistakes
- Vision analysis is unreliable
- KB is incomplete or has gaps
- System stability is uncertain

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│          User (Telegram)                        │
└────────────────┬────────────────────────────────┘
                 │
                 ├─ Text Message
                 │  └──→ handle_message()
                 │       └──→ RAGSearch (semantic search)
                 │       └──→ ClaudeClient (Haiku cost routing)
                 │       └──→ TelegramHandler (response)
                 │
                 └─ Chart Image
                    └──→ handle_photo()
                        └──→ ImageHandler (vision analysis)
                            ├─ Claude Vision (Opus)
                            ├─ Pattern detection
                            └─ ChartAnnotator (specialized analysis)
                                ├─ ICT pattern detection
                                ├─ Key level identification
                                └─ Confluence analysis

┌─────────────────────────────────────────────────┐
│         Knowledge Base (Supabase)               │
│  ├─ lessons (semantic embeddings)              │
│  ├─ patterns (ICT-specific)                    │
│  ├─ rules (trading rules)                      │
│  ├─ topics (conceptual graph)                  │
│  ├─ chart_examples (visual learning)           │
│  ├─ image_annotations (analysis results)       │
│  ├─ conversations (user history)               │
│  └─ bot_users (user profiles)                  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│      Future: n8n Async Processing              │
│  ├─ Discord ingestion                          │
│  ├─ Video transcription & keyframe extraction  │
│  ├─ Image batch processing                     │
│  └─ Scheduled KB maintenance                   │
└─────────────────────────────────────────────────┘
```

---

## Cost Optimization

**Current** (Phase 1):
- Haiku: Most messages (cheap)
- Sonnet: KB search + retrieval (balanced)
- Opus: Vision analysis, chart annotation (for accuracy)

**Estimated Monthly Cost**:
- Text interactions: $8-12
- Vision analysis: $5-8
- Storage (Supabase): $5-10
- **Total: $18-30/month**

**Cost Reduction Strategies**:
- Prompt caching (mentor.md) - 10% reduction
- Batch vision analysis - off-peak processing
- Image compression before API - data cost reduction
- Local pattern matching - before vision analysis

---

## Deployment Checklist

Before going to VPS:

- [ ] All schemas created and validated
- [ ] Prompts loaded from kb/prompts/
- [ ] Image handler tested locally with real chart images
- [ ] Chart annotator tested for pattern detection accuracy
- [ ] Telegram handlers registered (text + photo)
- [ ] Supabase tables created (image_annotations, etc)
- [ ] Environment variables configured (.env NOT in git)
- [ ] Ingestion configs reviewed and updated
- [ ] Tests written and passing
- [ ] Documentation complete

---

## Support & Troubleshooting

### Image Analysis Failing

```
Check:
1. Image size > 400px width
2. Image format supported (PNG, JPG, GIF, WebP)
3. Claude API key valid
4. Supabase connection working
5. Vision model available (Opus 4.6)
```

### Pattern Detection Not Working

```
Check:
1. Chart clarity (not blurry)
2. Chart has visible patterns (not blank)
3. Instrument/timeframe context provided
4. Pattern definition in kb/schemas/pattern.json matches reality
5. Vision model prompt in kb/prompts/chart_annotator.md is loaded
```

### Bot Not Responding

```
Check:
1. TELEGRAM_BOT_TOKEN set correctly
2. ANTHROPIC_API_KEY valid and has quota
3. Supabase credentials correct
4. Internet connection stable
5. Check bot logs for errors
```

---

**Phase 1 Complete!** 🎉

Next: Test with real charts, refine prompts, prepare for Phase 1.5 KB restructuring.
