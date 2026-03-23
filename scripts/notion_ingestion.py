#!/usr/bin/env python3
"""
notion_ingestion.py — Full knowledge base ingestion from silk-seahorse trading course.

Pipeline for each article:
  1. Read all article URLs from trading-theory/*.txt files (no API token needed)
  2. Open article in headless Chromium via Playwright (handles JS rendering)
  3. Extract full article text
  4. Screenshot every chart image on the page
  5. Send each image to Claude Haiku Vision → structured ICT/SMC analysis
  6. Combine article text + vision analyses → insert into Supabase knowledge_documents

Setup (run once):
  bash scripts/setup_notion_pipeline.sh

Usage:
  # Dry run — parse & screenshot, no DB inserts, no Vision API calls:
  python scripts/notion_ingestion.py --dry-run

  # Full run (all 87 articles):
  python scripts/notion_ingestion.py

  # One category only:
  python scripts/notion_ingestion.py --category block-types

  # Single article URL:
  python scripts/notion_ingestion.py --url https://silk-seahorse-538.notion.site/...

  # Resume (skip already-ingested articles):
  python scripts/notion_ingestion.py --resume

Environment (.env in project root):
  ANTHROPIC_API_KEY
  SUPABASE_URL
  SUPABASE_KEY
"""

import os, sys, re, json, time, base64, hashlib, argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Root & .env ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

def require_pkg(import_name, pip_name=None):
    try:
        return __import__(import_name)
    except ImportError:
        print(f"❌  Missing: pip install {pip_name or import_name}")
        sys.exit(1)

dotenv = require_pkg("dotenv", "python-dotenv")
dotenv.load_dotenv(ROOT / ".env")

anthropic_mod = require_pkg("anthropic")

try:
    from supabase import create_client
except ImportError:
    print("❌  Missing: pip install supabase"); sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")
TRADING_THEORY = Path(os.getenv("TRADING_THEORY_DIR",
                       str(ROOT.parent / "trading-theory")))

HAIKU = "claude-haiku-4-5-20251001"

# ── Category → section mapping ────────────────────────────────────────────────
FILE_TO_SECTION = {
    "block-types":             "structure-and-liquidity",
    "structure-and-liquidity": "structure-and-liquidity",
    "inefficiency-types":      "structure-and-liquidity",
    "work-with-imbalance":     "structure-and-liquidity",
    "tda-and-entry-models":    "tda-and-entry-models",
    "advanced-market-analysis":"market-mechanics",
    "sessions":                "market-mechanics",
    "timings":                 "market-mechanics",
    "order-flow-analysis":     "market-mechanics",
    "channels":                "market-mechanics",
    "channels2":               "market-mechanics",
    "manipulations":           "market-mechanics",
    "risk-management":         "risk-management",
    "backtest":                "risk-management",
    "discipline":              "psychology",
    "emotions":                "psychology",
    "technical-psychology":    "psychology",
    "homework":                "market-mechanics",
    "terminology":             "beginners",
    "first-steps":             "beginners",
}

# ── Parse URLs from trading-theory/*.txt ──────────────────────────────────────
def parse_articles(category_filter: Optional[str] = None) -> list[dict]:
    """
    Returns list of {title, url, desc, category, section} for all articles.
    """
    if not TRADING_THEORY.exists():
        print(f"❌  trading-theory folder not found: {TRADING_THEORY}")
        print("    Set TRADING_THEORY_DIR env var or place folder next to jarvis-trading-bot/")
        sys.exit(1)

    url_pat = re.compile(r'https://silk-seahorse-538\.notion\.site/[^\s)\]]+')
    articles = []
    seen_urls = set()

    for txt_file in sorted(TRADING_THEORY.glob("*.txt")):
        category = txt_file.stem
        if category_filter and category != category_filter:
            continue
        section = FILE_TO_SECTION.get(category, "market-mechanics")

        lines = txt_file.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = url_pat.search(line)
            if not m:
                continue
            url = m.group(0).split("?")[0].rstrip("/")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Title: nearest 📌 line above
            title = ""
            for j in range(i - 1, max(i - 6, -1), -1):
                l = lines[j].strip()
                if l.startswith("📌"):
                    title = l.lstrip("📌").strip(" *")
                    break

            # Description: first non-empty, non-URL line below
            desc = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                l = lines[j].strip()
                if l and not l.startswith("http") and not l.startswith("[") \
                        and not l.startswith("🐅") and not l.startswith("✅"):
                    desc = l
                    break

            if not title:
                # Derive from URL slug
                slug = url.rstrip("/").split("/")[-1]
                title = re.sub(r"-[a-f0-9]{32}$", "", slug).replace("-", " ").strip()
                if not title:
                    title = slug

            articles.append({
                "title":    title,
                "url":      url,
                "desc":     desc,
                "category": category,
                "section":  section,
            })

    print(f"📚 Found {len(articles)} unique articles across {len(set(a['category'] for a in articles))} categories")
    return articles


# ── Playwright page fetch ──────────────────────────────────────────────────────
def fetch_article_with_playwright(url: str) -> dict:
    """
    Open article in headless Chromium, wait for render, return:
    {text, image_data_list: [{b64, media_type, caption}]}
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("❌  Missing: pip install playwright && playwright install chromium")
        sys.exit(1)

    result = {"text": "", "image_data_list": []}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except PWTimeout:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(4000)

        # Extra wait for Notion lazy-load
        page.wait_for_timeout(3000)

        # ── Extract text ──
        try:
            result["text"] = page.inner_text("main") or page.inner_text("body")
        except Exception:
            result["text"] = page.inner_text("body")

        # ── Screenshot every image block ──
        image_containers = page.query_selector_all(
            ".notion-image-block, figure, [class*='image']"
        )

        for idx, container in enumerate(image_containers):
            try:
                # Check that the image inside has loaded
                img_el = container.query_selector("img")
                if not img_el:
                    continue
                natural_w = page.evaluate("el => el.naturalWidth", img_el)
                if not natural_w or natural_w < 50:
                    continue

                # Scroll into view and screenshot just this element
                container.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                png_bytes = container.screenshot(type="png")

                # Convert to JPEG to save tokens
                try:
                    from PIL import Image as PILImage
                    import io
                    img_pil = PILImage.open(io.BytesIO(png_bytes)).convert("RGB")
                    # Resize if too large (Vision works fine at ~1280px wide)
                    max_w = 1280
                    if img_pil.width > max_w:
                        ratio = max_w / img_pil.width
                        img_pil = img_pil.resize(
                            (max_w, int(img_pil.height * ratio)),
                            PILImage.LANCZOS
                        )
                    buf = io.BytesIO()
                    img_pil.save(buf, format="JPEG", quality=85)
                    img_bytes = buf.getvalue()
                    media_type = "image/jpeg"
                except ImportError:
                    img_bytes = png_bytes
                    media_type = "image/png"

                b64 = base64.standard_b64encode(img_bytes).decode()

                # Caption: text node immediately after the image container
                caption = ""
                try:
                    cap_el = page.evaluate(
                        "el => el.nextElementSibling ? el.nextElementSibling.innerText : ''",
                        container
                    )
                    if cap_el and len(cap_el) < 100:
                        caption = cap_el.strip()
                except Exception:
                    pass

                result["image_data_list"].append({
                    "b64":        b64,
                    "media_type": media_type,
                    "caption":    caption or f"Figure {idx + 1}",
                    "width":      natural_w,
                })

            except Exception as e:
                print(f"    ⚠️  Image {idx}: {e}")
                continue

        browser.close()

    return result


# ── Claude Vision analysis ─────────────────────────────────────────────────────
VISION_PROMPT = """Ты эксперт по ICT (Inner Circle Trader) и Smart Money Concepts (SMC).
Это учебный чарт из образовательного курса по трейдингу на тему: "{title}".
{caption_hint}

Проанализируй изображение и опиши на русском языке:
1. **Что показано**: какой ICT/SMC паттерн или концепция проиллюстрирована
2. **Элементы графика**: ключевые уровни, зоны, стрелки, метки, выделенные области
3. **Торговая логика**: как это используется в реальной торговле (вход, стоп, цель)
4. **Структура рынка**: направление тренда, контекст, таймфрейм если виден

Будь конкретным и образовательным. Используй ICT/SMC терминологию."""


def analyze_image(claude, b64: str, media_type: str, title: str, caption: str) -> str:
    """Send one chart image to Claude Haiku Vision. Returns analysis text."""
    caption_hint = f"Подпись к графику: \"{caption}\"" if caption else ""
    prompt = VISION_PROMPT.format(title=title, caption_hint=caption_hint)

    resp = claude.messages.create(
        model=HAIKU,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return resp.content[0].text.strip()


# ── Supabase helpers ───────────────────────────────────────────────────────────
def already_ingested(supabase, title: str) -> bool:
    res = supabase.table("knowledge_documents").select("id").eq("title", title).execute()
    return bool(res.data)


def insert_document(supabase, *, title, content, section, topic, metadata) -> bool:
    try:
        supabase.table("knowledge_documents").insert({
            "title":    title,
            "content":  content,
            "section":  section,
            "topic":    topic,
            "source":   "silk-seahorse",
            "metadata": metadata,
        }).execute()
        return True
    except Exception as e:
        print(f"    ❌ DB: {e}")
        return False


# ── Process one article ────────────────────────────────────────────────────────
def process_article(article: dict, claude, supabase,
                    dry_run: bool, resume: bool) -> dict:
    title    = article["title"]
    url      = article["url"]
    section  = article["section"]
    category = article["category"]

    print(f"\n  📄 {title[:55]}")
    print(f"     {url[-55:]}")

    # Skip if already in DB
    if resume and not dry_run and supabase and already_ingested(supabase, title):
        print(f"     ↻ Already in DB, skipping")
        return {"skipped": True}

    # Fetch article via Playwright
    print(f"     🌐 Fetching (headless Chromium)...")
    try:
        fetched = fetch_article_with_playwright(url)
    except Exception as e:
        print(f"     ❌ Fetch failed: {e}")
        return {"error": str(e)}

    text      = fetched["text"].strip()
    images    = fetched["image_data_list"]
    img_count = len(images)
    print(f"     📝 Text: {len(text)} chars | 🖼️  Images: {img_count}")

    # Analyze images with Claude Vision
    vision_sections = []
    if images and not dry_run and claude:
        print(f"     🔍 Analyzing {img_count} image(s) with Claude Vision...")
        for i, img in enumerate(images, 1):
            try:
                analysis = analyze_image(
                    claude, img["b64"], img["media_type"],
                    title, img.get("caption", "")
                )
                vision_sections.append(
                    f"\n### График {i}"
                    + (f" — {img['caption']}" if img.get("caption") else "")
                    + f"\n{analysis}"
                )
                time.sleep(0.5)
            except Exception as e:
                print(f"     ⚠️  Vision error image {i}: {e}")
    elif dry_run and images:
        vision_sections = [f"\n### График {i+1}\n[DRY RUN]" for i in range(img_count)]

    # Build final content
    content_parts = [text] if text else [article.get("desc", "")]
    if vision_sections:
        content_parts.append("\n\n## Анализ графиков (Claude Vision)\n")
        content_parts.extend(vision_sections)
    content = "\n".join(content_parts).strip()

    topic = re.sub(r"[^a-z0-9_]", "_", title.lower())[:50].strip("_")

    metadata = {
        "source_url":   url,
        "category":     category,
        "image_count":  img_count,
        "ingested_at":  datetime.utcnow().isoformat(),
        "pipeline":     "notion_ingestion_v2",
    }

    # Insert to DB
    inserted = False
    if not dry_run and supabase:
        inserted = insert_document(
            supabase,
            title=title, content=content,
            section=section, topic=topic,
            metadata=metadata,
        )
        if inserted:
            print(f"     ✅ Inserted: {title[:50]}")
    else:
        print(f"     [DRY RUN] Would insert: {title[:50]}")
        inserted = True  # count as success in dry run

    return {"inserted": inserted, "images": img_count}


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Ingest silk-seahorse trading course → Supabase knowledge base"
    )
    parser.add_argument("--dry-run",  action="store_true",
                        help="Fetch & screenshot but don't call Vision API or write to DB")
    parser.add_argument("--resume",   action="store_true",
                        help="Skip articles already present in knowledge_documents")
    parser.add_argument("--category", type=str, default=None,
                        help="Process only one category (e.g. block-types)")
    parser.add_argument("--url",      type=str, default=None,
                        help="Process a single article URL")
    parser.add_argument("--limit",    type=int, default=None,
                        help="Max number of articles to process (for testing)")
    args = parser.parse_args()

    dry_run = args.dry_run
    label   = "DRY RUN" if dry_run else "LIVE"

    print(f"\n{'='*62}")
    print(f"  JARVIS Notion Ingestion v2 [{label}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*62}\n")

    # Validate env
    if not dry_run:
        missing = [k for k in ("ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_KEY")
                   if not os.getenv(k)]
        if missing:
            print(f"❌  Missing .env vars: {', '.join(missing)}")
            sys.exit(1)

    claude   = anthropic_mod.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

    # Build article list
    if args.url:
        slug  = args.url.rstrip("/").split("/")[-1]
        title = re.sub(r"-[a-f0-9]{32}$", "", slug).replace("-", " ").strip()
        articles = [{"title": title, "url": args.url,
                     "desc": "", "category": "custom", "section": "market-mechanics"}]
    else:
        articles = parse_articles(args.category)

    if args.limit:
        articles = articles[:args.limit]

    print(f"🚀 Processing {len(articles)} article(s)\n")

    stats = {"total": len(articles), "inserted": 0, "skipped": 0, "errors": 0}

    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}]", end="")
        try:
            res = process_article(article, claude, supabase, dry_run, args.resume)
            if res.get("skipped"):
                stats["skipped"] += 1
            elif res.get("error"):
                stats["errors"]  += 1
            elif res.get("inserted"):
                stats["inserted"] += 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted")
            break
        except Exception as e:
            stats["errors"] += 1
            print(f"  ❌ Unexpected error: {e}")
        time.sleep(1)

    print(f"\n{'='*62}")
    print(f"  Done [{label}]  —  {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Inserted : {stats['inserted']}")
    print(f"  Skipped  : {stats['skipped']}")
    print(f"  Errors   : {stats['errors']}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
