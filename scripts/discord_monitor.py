#!/usr/bin/env python3
"""
Discord Stream-Recordings Monitor
===================================
Polls the DT Trading Discord stream-recordings channel for new lesson links.
When a new Google Drive link is found, it:
  1. Adds the video to data/video_manifest.json (with transcribed=false)
  2. Optionally sends a Telegram notification to the admin

Usage:
  python scripts/discord_monitor.py              # one-shot check
  python scripts/discord_monitor.py --loop       # run every 30 min (for VPS)
  python scripts/discord_monitor.py --dry-run    # check without writing

Environment variables required:
  DISCORD_BOT_TOKEN  — Discord bot token with READ_MESSAGES permission
  SUPABASE_URL       — Supabase project URL
  SUPABASE_ANON_KEY  — Supabase anon key
  TELEGRAM_BOT_TOKEN — (optional) for admin notifications
  ADMIN_CHAT_ID      — (optional) Telegram user/chat ID for notifications
"""

import os
import json
import re
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [discord_monitor] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────────

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# DT Trading Discord — stream-recordings channel
STREAM_RECORDINGS_CHANNEL_ID = "1145806812709404834"

# Discord API base
DISCORD_API = "https://discord.com/api/v10"

# Path to manifest
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "video_manifest.json"

# Poll interval (seconds) when running in --loop mode
POLL_INTERVAL = 30 * 60  # 30 minutes

# Google Drive URL patterns
GDRIVE_PATTERNS = [
    r"https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
    r"https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
    r"https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)",
]

# Lesson title patterns (e.g. "Урок 14" or "#14" or "Lesson 14")
LESSON_NUMBER_PATTERN = r"(?:урок|lesson|#|№)\s*(\d+)"


# ─── Discord API helpers ────────────────────────────────────────────────────────

def discord_headers() -> dict:
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN or DISCORD_BOT_TOKEN is not set in environment")
    # Support both bot tokens (prefixed "Bot ") and user tokens (raw token)
    if DISCORD_TOKEN.startswith("Bot ") or DISCORD_TOKEN.startswith("Bearer "):
        auth = DISCORD_TOKEN
    else:
        # Try as bot token first; if it's a user token, use without prefix
        # User tokens from Discord exporters are raw base64 strings
        auth = f"Bot {DISCORD_TOKEN}"
    return {
        "Authorization": auth,
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/jarvis-trading-bot, 1.0)",
    }


def fetch_channel_messages(channel_id: str, after_message_id: Optional[str] = None, limit: int = 50) -> list:
    """Fetch recent messages from a Discord channel."""
    params = {"limit": limit}
    if after_message_id:
        params["after"] = after_message_id

    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    resp = requests.get(url, headers=discord_headers(), params=params, timeout=10)

    if resp.status_code == 401:
        raise ValueError("Discord token is invalid or bot lacks permissions")
    if resp.status_code == 403:
        raise ValueError(f"Bot lacks access to channel {channel_id}")
    if resp.status_code != 200:
        raise RuntimeError(f"Discord API error {resp.status_code}: {resp.text[:200]}")

    return resp.json()


# ─── Manifest helpers ───────────────────────────────────────────────────────────

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"videos": [], "last_checked_message_id": None}


def save_manifest(manifest: dict):
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_existing_drive_ids(manifest: dict) -> set:
    """Return set of all known Google Drive IDs."""
    return {v["drive_id"] for v in manifest.get("videos", []) if v.get("drive_id")}


def get_next_lesson_number(manifest: dict) -> int:
    """Get the next sequential lesson number for stream-recordings."""
    sr_lessons = [
        v.get("lesson", 0)
        for v in manifest.get("videos", [])
        if v.get("category") == "stream-recording" and v.get("lesson")
    ]
    return max(sr_lessons, default=0) + 1


# ─── URL extraction ─────────────────────────────────────────────────────────────

def extract_drive_urls(text: str) -> list[tuple[str, str]]:
    """Extract (full_url, drive_id) tuples from message text."""
    results = []
    for pattern in GDRIVE_PATTERNS:
        for match in re.finditer(pattern, text):
            drive_id = match.group(1)
            full_url = match.group(0)
            results.append((full_url, drive_id))
    return results


def extract_lesson_number(text: str) -> Optional[int]:
    """Try to extract lesson number from message text."""
    match = re.search(LESSON_NUMBER_PATTERN, text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def extract_title(text: str) -> str:
    """Extract a short title from message text."""
    # Take first non-empty line, strip markdown
    for line in text.strip().split("\n"):
        line = line.strip().lstrip("#*_`").rstrip("#*_`").strip()
        if line and len(line) > 3:
            return line[:100]
    return "Stream Recording"


# ─── Telegram notification ──────────────────────────────────────────────────────

def send_telegram_notification(message: str):
    """Send admin notification via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=5)
    except Exception as e:
        log.warning(f"Failed to send Telegram notification: {e}")


# ─── Main monitor logic ─────────────────────────────────────────────────────────

def check_for_new_lessons(dry_run: bool = False) -> list[dict]:
    """
    Check stream-recordings channel for new Google Drive links.
    Returns list of newly discovered videos.
    """
    manifest = load_manifest()
    existing_ids = get_existing_drive_ids(manifest)
    last_message_id = manifest.get("last_checked_message_id")

    log.info(f"Checking stream-recordings channel (last msg ID: {last_message_id})")

    try:
        messages = fetch_channel_messages(
            STREAM_RECORDINGS_CHANNEL_ID,
            after_message_id=last_message_id,
            limit=50
        )
    except ValueError as e:
        log.error(f"Auth error: {e}")
        return []
    except Exception as e:
        log.error(f"Failed to fetch messages: {e}")
        return []

    if not messages:
        log.info("No new messages found")
        return []

    # Messages come newest-first from Discord — sort oldest-first
    messages.sort(key=lambda m: m["id"])
    log.info(f"Found {len(messages)} new messages to scan")

    new_videos = []

    for msg in messages:
        content = msg.get("content", "")
        # Also check embeds
        for embed in msg.get("embeds", []):
            content += "\n" + embed.get("url", "") + "\n" + embed.get("description", "")

        drive_links = extract_drive_urls(content)
        if not drive_links:
            continue

        for full_url, drive_id in drive_links:
            if drive_id in existing_ids:
                log.debug(f"Drive ID {drive_id} already in manifest, skipping")
                continue

            lesson_num = extract_lesson_number(content)
            if lesson_num is None:
                lesson_num = get_next_lesson_number(manifest)

            title = extract_title(content)
            msg_date = msg.get("timestamp", datetime.now(timezone.utc).isoformat())[:10]

            video_entry = {
                "id": f"sr-{lesson_num:02d}",
                "lesson": lesson_num,
                "title": title,
                "drive_url": full_url,
                "drive_id": drive_id,
                "source_channel": "stream-recordings",
                "discord_message_id": msg["id"],
                "presenter": "DT Trading",
                "date": msg_date,
                "priority": "HIGH",
                "category": "stream-recording",
                "section": "beginners",
                "topic": f"lesson_{lesson_num:02d}",
                "transcribed": False,
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            }

            new_videos.append(video_entry)
            existing_ids.add(drive_id)
            log.info(f"🆕 New lesson found: #{lesson_num} — {title} (ID: {drive_id})")

    # Update manifest
    newest_msg_id = messages[-1]["id"] if messages else last_message_id

    if new_videos and not dry_run:
        manifest["videos"].extend(new_videos)
        manifest["last_checked_message_id"] = newest_msg_id
        manifest["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest(manifest)
        log.info(f"✅ Manifest updated: added {len(new_videos)} video(s)")

        # Send Telegram notification
        for v in new_videos:
            notif = (
                f"🎬 <b>Новый урок в stream-recordings!</b>\n"
                f"Урок #{v['lesson']}: {v['title']}\n"
                f"🔗 <a href='{v['drive_url']}'>Открыть на Google Drive</a>\n\n"
                f"Скачай видео и запусти video_ingestion.py"
            )
            send_telegram_notification(notif)

    elif not dry_run:
        # Still update the last checked message ID even if no new videos
        manifest["last_checked_message_id"] = newest_msg_id
        manifest["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        save_manifest(manifest)

    if dry_run and new_videos:
        log.info(f"[DRY RUN] Would add {len(new_videos)} video(s) — not writing")

    return new_videos


def run_loop(interval: int = POLL_INTERVAL):
    """Run the monitor in a loop."""
    log.info(f"Starting Discord monitor loop (interval: {interval}s)")
    while True:
        try:
            new = check_for_new_lessons()
            if new:
                log.info(f"Added {len(new)} new lesson(s) to manifest")
            else:
                log.info("No new lessons found")
        except Exception as e:
            log.error(f"Unexpected error in monitor loop: {e}")

        log.info(f"Sleeping {interval}s until next check...")
        time.sleep(interval)


# ─── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discord stream-recordings monitor")
    parser.add_argument("--loop", action="store_true", help="Run continuously (every 30 min)")
    parser.add_argument("--dry-run", action="store_true", help="Check without writing to manifest")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL, help="Loop interval in seconds")
    args = parser.parse_args()

    # Load .env if present
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    if args.loop:
        run_loop(interval=args.interval)
    else:
        new_videos = check_for_new_lessons(dry_run=args.dry_run)
        if new_videos:
            print(f"\n✅ Found {len(new_videos)} new lesson(s):")
            for v in new_videos:
                print(f"  #{v['lesson']}: {v['title']} — {v['drive_url']}")
        else:
            print("No new lessons found.")
