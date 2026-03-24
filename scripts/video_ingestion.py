#!/usr/bin/env python3
"""
video_ingestion.py — Knowledge base ingestion from trading stream recordings.

Pipeline:
  1. Read video file paths (local) or Google Drive links from a manifest file
  2. Transcribe each video using whisper.cpp (Metal-accelerated on M3 iMac)
  3. Structure the transcript with Claude Haiku → ICT/SMC educational content
  4. Insert into Supabase knowledge_documents

Usage:
  # Transcribe all videos in a folder:
  python scripts/video_ingestion.py --dir ~/Downloads/trading-videos/

  # Transcribe a single video file:
  python scripts/video_ingestion.py --file ~/Downloads/stream_2024-01-15.mp4

  # Use manifest file (list of paths, one per line):
  python scripts/video_ingestion.py --manifest scripts/video_manifest.txt

  # Dry run (transcribe only, no DB inserts):
  python scripts/video_ingestion.py --dir ~/Downloads/trading-videos/ --dry-run

  # Skip transcription if .txt sidecar already exists:
  python scripts/video_ingestion.py --dir ~/Downloads/trading-videos/ --skip-transcribed

Environment (.env):
  ANTHROPIC_API_KEY — Claude API key
  SUPABASE_URL      — Supabase project URL
  SUPABASE_KEY      — Supabase service role key
  WHISPER_BIN       — Path to whisper.cpp main binary (default: ~/whisper.cpp/main)
  WHISPER_MODEL     — Path to whisper model (default: ~/whisper.cpp/models/ggml-large-v3.bin)

whisper.cpp setup:
  Run scripts/setup_whisper.sh first to install whisper.cpp with Metal support.
"""

import os
import sys
import json
import time
import re
import hashlib
import argparse
import subprocess
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Dependency check ──────────────────────────────────────────────────────────
def require(pkg, import_as=None):
    try:
        return __import__(import_as or pkg)
    except ImportError:
        print(f"❌  Missing: pip install {pkg}")
        sys.exit(1)

anthropic = require("anthropic")
dotenv    = require("python_dotenv", "dotenv")

ROOT = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(ROOT / ".env")

try:
    from supabase import create_client
except ImportError:
    print("❌  Missing: pip install supabase")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")

WHISPER_BIN    = os.path.expanduser(
    os.getenv("WHISPER_BIN", "~/whisper.cpp/build/bin/whisper-cli")
)
WHISPER_MODEL  = os.path.expanduser(
    os.getenv("WHISPER_MODEL", "~/whisper.cpp/models/ggml-large-v3-turbo.bin")
)

HAIKU = "claude-haiku-4-5-20251001"

# Supported video extensions
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".flv"}

# ── Whisper transcription ──────────────────────────────────────────────────────
def check_whisper() -> bool:
    """Check if whisper.cpp binary exists and is executable."""
    if not Path(WHISPER_BIN).exists():
        print(f"❌  whisper.cpp not found at: {WHISPER_BIN}")
        print("   Run: bash scripts/setup_whisper.sh")
        return False
    if not Path(WHISPER_MODEL).exists():
        print(f"❌  Whisper model not found at: {WHISPER_MODEL}")
        print("   Run: bash scripts/setup_whisper.sh  (downloads model automatically)")
        return False
    return True


def extract_audio(video_path: Path, out_wav: Path) -> bool:
    """Extract audio from video using ffmpeg → 16kHz mono WAV (whisper input format)."""
    if not shutil.which("ffmpeg"):
        print("❌  ffmpeg not found. Install: brew install ffmpeg")
        return False
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-ar", "16000",   # 16kHz sample rate required by whisper
        "-ac", "1",       # mono
        "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ❌ ffmpeg error: {result.stderr[-300:]}")
        return False
    return True


def transcribe_audio(wav_path: Path, language: str = "ru") -> Optional[str]:
    """
    Transcribe audio using whisper.cpp.
    Returns transcript text or None on failure.

    Whisper.cpp outputs .txt sidecar next to the wav file automatically.
    Speed on M3 iMac with Metal: ~10x realtime (1h video ≈ 6 min).
    """
    cmd = [
        WHISPER_BIN,
        "-m",  WHISPER_MODEL,
        "-f",  str(wav_path),
        "-l",  language,
        "--output-txt",          # write .txt sidecar
        "--no-timestamps",       # cleaner text output
        "--threads", "8",        # M3 has plenty of cores
        "--processors", "1",
    ]

    print(f"    🎙️  Transcribing {wav_path.name} (this may take a few minutes)...")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"    ❌ Whisper error: {result.stderr[-400:]}")
        return None

    txt_path = wav_path.with_suffix(".txt")
    if txt_path.exists():
        transcript = txt_path.read_text(encoding="utf-8").strip()
        mins = len(transcript.split()) // 130  # ~130 words/min speech
        print(f"    ✅ Transcribed in {elapsed:.0f}s — ~{mins} min content, "
              f"{len(transcript)} chars")
        return transcript

    # Fallback: parse stdout
    if result.stdout.strip():
        return result.stdout.strip()

    return None


def transcribe_video(video_path: Path, keep_wav: bool = False) -> Optional[str]:
    """Full pipeline: video → audio extract → whisper transcription."""
    # Check for cached transcript sidecar first
    txt_sidecar = video_path.with_suffix(".txt")
    if txt_sidecar.exists():
        print(f"    📝 Using cached transcript: {txt_sidecar.name}")
        return txt_sidecar.read_text(encoding="utf-8").strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / (video_path.stem + ".wav")

        print(f"    🎬 Extracting audio from: {video_path.name}")
        if not extract_audio(video_path, wav_path):
            return None

        transcript = transcribe_audio(wav_path)

    # Cache transcript as sidecar
    if transcript:
        txt_sidecar.write_text(transcript, encoding="utf-8")

    return transcript


# ── Claude structuring ─────────────────────────────────────────────────────────
def structure_transcript(client: anthropic.Anthropic, transcript: str,
                          video_title: str, chunk_index: int = 0,
                          total_chunks: int = 1) -> dict:
    """
    Send a transcript chunk to Claude Haiku for ICT/SMC structuring.
    Returns {title, content, section, topic}.

    Designed for beginner traders: concise, practical, no fluff.
    Target: ~300-500 words per lesson. Fast to read, easy to remember.
    """
    chunk_info = f" (часть {chunk_index+1}/{total_chunks})" if total_chunks > 1 else ""

    prompt = f"""Ты наставник по ICT трейдингу, который составляет короткие шпаргалки для новичков.

Название урока: "{video_title}"{chunk_info}

Ниже транскрипт обучающего стрима. Твоя задача — сделать МАКСИМАЛЬНО СЖАТЫЙ конспект.

ПРАВИЛА:
- Только суть, без воды и повторений
- Максимум 5-7 ключевых пунктов на урок
- Каждый пункт: 1-2 предложения, конкретно и понятно для новичка
- Практические правила — выдели отдельно ("Правило: ...")
- Термины объясняй в скобках при первом упоминании
- Никакой теории ради теории — только то, что применяется в торговле
- Длина контента: 300-500 слов максимум

ТРАНСКРИПТ:
{transcript[:8000]}

Выведи JSON:
{{
  "title": "Короткое конкретное название темы (не имя файла)",
  "section": "одно из: beginners|market-mechanics|structure-and-liquidity|tda-and-entry-models|risk-management|psychology|gold-mechanics",
  "topic": "ключевая_тема_snake_case",
  "content": "## Суть урока\\n[1-2 предложения — главная идея]\\n\\n## Ключевые концепции\\n- **Термин**: объяснение\\n- ...\\n\\n## Практические правила\\n- Правило: ...\\n- Правило: ...\\n\\n## Запомни\\n[1 главный вывод урока]"
}}

Только JSON, без обёрток markdown.
"""

    response = client.messages.create(
        model=HAIKU,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code blocks if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$",     "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract manually
        data = {
            "title":   video_title,
            "section": "market-mechanics",
            "topic":   video_title.lower().replace(" ", "_")[:50],
            "content": raw,
        }

    return data


def chunk_transcript(text: str, max_chars: int = 10000) -> list[str]:
    """Split long transcript into chunks at natural paragraph/sentence breaks."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        # Find last sentence boundary before max_chars
        cut = text[:max_chars].rfind(". ")
        if cut < max_chars // 2:
            cut = max_chars
        chunks.append(text[:cut+1].strip())
        text = text[cut+1:].strip()
    return chunks


# ── Supabase upsert ────────────────────────────────────────────────────────────
def upsert_document(supabase, title: str, content: str, section: str,
                    topic: str, metadata: dict, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY RUN] Would upsert: {title[:60]}")
        return False

    try:
        existing = (supabase.table("knowledge_documents")
                    .select("id")
                    .eq("title", title)
                    .execute())
        if existing.data:
            print(f"    ↻ Already exists: {title[:60]}")
            return False

        supabase.table("knowledge_documents").insert({
            "title":    title,
            "content":  content,
            "section":  section,
            "topic":    topic,
            "source":   "stream-recording",
            "metadata": metadata,
        }).execute()
        return True
    except Exception as e:
        print(f"    ❌ DB error: {e}")
        return False


# ── Process a single video file ────────────────────────────────────────────────
def process_video(video_path: Path, claude: anthropic.Anthropic,
                  supabase, dry_run: bool, skip_transcribed: bool = False) -> dict:
    """Full pipeline for one video: transcribe → structure → insert."""
    print(f"\n  🎬 {video_path.name}")

    # Skip if already in DB
    if not dry_run and supabase:
        existing = (supabase.table("knowledge_documents")
                    .select("id")
                    .ilike("metadata->>source_file", f"%{video_path.name}%")
                    .execute())
        if existing.data:
            print(f"    ↻ Already ingested, skipping")
            return {"skipped": True}

    # Skip if .txt transcript already exists and user wants to skip
    txt_sidecar = video_path.with_suffix(".txt")
    if skip_transcribed and txt_sidecar.exists() and not dry_run:
        transcript = txt_sidecar.read_text(encoding="utf-8").strip()
        print(f"    📝 Found cached transcript ({len(transcript)} chars)")
    else:
        transcript = transcribe_video(video_path)

    if not transcript:
        print(f"    ❌ Transcription failed")
        return {"error": "transcription_failed"}

    # Split into chunks if too long
    chunks = chunk_transcript(transcript)
    print(f"    📊 Transcript: {len(transcript)} chars → {len(chunks)} chunk(s)")

    inserted_count = 0

    for i, chunk in enumerate(chunks):
        print(f"    🤖 Structuring chunk {i+1}/{len(chunks)} with Claude...")
        structured = structure_transcript(claude, chunk, video_path.stem, i, len(chunks))

        title = structured.get("title", video_path.stem)
        if len(chunks) > 1:
            title = f"{title} — часть {i+1}"

        content = structured.get("content", chunk)
        section = structured.get("section", "market-mechanics")
        topic   = structured.get("topic", video_path.stem.lower()[:50])

        metadata = {
            "source_file":  video_path.name,
            "chunk_index":  i,
            "total_chunks": len(chunks),
            "transcript_chars": len(chunk),
            "ingested_at":  datetime.utcnow().isoformat(),
            "pipeline":     "video_ingestion",
        }

        inserted = upsert_document(
            supabase, title, content, section, topic,
            metadata=metadata, dry_run=dry_run,
        )
        if inserted:
            inserted_count += 1
            print(f"    ✅ Inserted: {title[:60]}")

        time.sleep(0.5)  # rate limit

    return {"inserted": inserted_count, "chunks": len(chunks)}


# ── Collect video files ────────────────────────────────────────────────────────
def collect_videos(args) -> list[Path]:
    videos = []

    if args.file:
        p = Path(args.file).expanduser().resolve()
        if p.exists() and p.suffix.lower() in VIDEO_EXTS:
            videos.append(p)
        else:
            print(f"❌  File not found or not a video: {args.file}")

    elif args.dir:
        d = Path(args.dir).expanduser().resolve()
        if not d.is_dir():
            print(f"❌  Directory not found: {args.dir}")
            return []
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() in VIDEO_EXTS:
                videos.append(f)

    elif args.manifest:
        m = Path(args.manifest).expanduser().resolve()
        if not m.exists():
            print(f"❌  Manifest not found: {args.manifest}")
            return []
        for line in m.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                p = Path(line).expanduser().resolve()
                if p.exists():
                    videos.append(p)
                else:
                    print(f"  ⚠️  Not found: {line}")

    return videos


# ── Main ───────────────────────────────────────────────────────────────────────
def run_pipeline(args):
    dry_run = args.dry_run
    mode_label = "DRY RUN" if dry_run else "LIVE"

    print(f"\n{'='*60}")
    print(f"  JARVIS Video Ingestion Pipeline [{mode_label}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Validate env
    missing = []
    if not ANTHROPIC_KEY:  missing.append("ANTHROPIC_API_KEY")
    if not SUPABASE_URL:   missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:   missing.append("SUPABASE_KEY")
    if not dry_run and missing:
        print(f"❌  Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    # Check whisper
    if not check_whisper():
        sys.exit(1)

    videos = collect_videos(args)
    if not videos:
        print("❌  No video files found. Provide --file, --dir, or --manifest.")
        sys.exit(1)

    print(f"📹 Found {len(videos)} video(s) to process\n")
    for v in videos:
        size_mb = v.stat().st_size / 1024 / 1024
        print(f"   • {v.name}  ({size_mb:.1f} MB)")

    claude   = anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

    stats = {"total": len(videos), "inserted": 0, "skipped": 0, "errors": 0}

    for i, video_path in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}]")
        try:
            result = process_video(
                video_path, claude, supabase, dry_run,
                skip_transcribed=args.skip_transcribed,
            )
            if result.get("skipped"):
                stats["skipped"] += 1
            elif result.get("error"):
                stats["errors"] += 1
            else:
                stats["inserted"] += result.get("inserted", 0)
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
            break
        except Exception as e:
            stats["errors"] += 1
            print(f"  ❌ Error: {e}")

    print(f"\n{'='*60}")
    print(f"  Pipeline complete [{mode_label}]")
    print(f"  Videos processed: {stats['total']}")
    print(f"  Chunks inserted:  {stats['inserted']}")
    print(f"  Skipped:          {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="JARVIS Video → Supabase ingestion")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file",     type=str, help="Single video file path")
    group.add_argument("--dir",      type=str, help="Directory of video files")
    group.add_argument("--manifest", type=str, help="Text file with one video path per line")

    parser.add_argument("--dry-run",          action="store_true",
                        help="Transcribe but don't insert to DB")
    parser.add_argument("--skip-transcribed", action="store_true",
                        help="Skip videos that already have a .txt sidecar")
    parser.add_argument("--language", type=str, default="ru",
                        help="Audio language for whisper (default: ru)")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
