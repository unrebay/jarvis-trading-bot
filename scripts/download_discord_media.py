#!/usr/bin/env python3
"""
Download Discord channel media (chart screenshots, prop passes, results)
via Discord API to get fresh, non-expired CDN URLs.

Usage:
  python scripts/download_discord_media.py --channel indices-us --limit 100
  python scripts/download_discord_media.py --channel students-feedback --limit 200
  python scripts/download_discord_media.py --all --limit 50

Channel IDs (from DT Trading Discord):
  indices-us:       1169030361725030411  (US indices charts)
  indices-eu:       (see export2.sh)
  eur:              (see export2.sh)
  students-feedback: 1156183561439809677
  prop-discussion:  (see export2.sh)
"""

import os
import re
import sys
import time
import json
import hashlib
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

# Load .env
for line in ENV_FILE.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
DISCORD_API = "https://discord.com/api/v10"

# Output folder
MEDIA_DIR = ROOT / "media" / "images"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Known channel IDs — add more from export2.sh as needed
CHANNELS = {
    "indices-us":        "1169030361725030411",
    "students-feedback": "1156183561439809677",
    "stream-recordings": "1145806812709404834",
    "prop-discussion":   None,   # fill in from export2.sh
    "indices-eu":        None,
    "eur":               None,
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def headers():
    token = DISCORD_TOKEN
    if not token:
        raise ValueError("DISCORD_TOKEN not set")
    # User token (no prefix) vs bot token
    if not (token.startswith("Bot ") or token.startswith("Bearer ")):
        # Try as user token
        return {"Authorization": token, "User-Agent": "Mozilla/5.0"}
    return {"Authorization": token}


def fetch_messages(channel_id: str, before: str = None, limit: int = 100) -> list:
    params = {"limit": min(limit, 100)}
    if before:
        params["before"] = before
    resp = requests.get(
        f"{DISCORD_API}/channels/{channel_id}/messages",
        headers=headers(), params=params, timeout=15
    )
    if resp.status_code == 401:
        raise ValueError("Invalid Discord token")
    if resp.status_code == 403:
        raise ValueError(f"No access to channel {channel_id}")
    resp.raise_for_status()
    return resp.json()


def extract_image_urls(message: dict) -> list[tuple[str, str]]:
    """Extract (url, filename) pairs from a message."""
    results = []

    # Attachments
    for att in message.get("attachments", []):
        url = att.get("url", "")
        filename = att.get("filename", "")
        ext = Path(filename).suffix.lower()
        if ext in IMAGE_EXTS or "image" in att.get("content_type", ""):
            results.append((url, filename))

    # Embeds with images
    for embed in message.get("embeds", []):
        if embed.get("image"):
            url = embed["image"].get("url", "")
            if url:
                filename = Path(urlparse(url).path).name or "embed.png"
                results.append((url, filename))
        if embed.get("thumbnail"):
            url = embed["thumbnail"].get("url", "")
            if url:
                filename = Path(urlparse(url).path).name or "thumb.png"
                results.append((url, filename))

    return results


def download_image(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            return True
        else:
            print(f"    ⚠️  HTTP {resp.status_code}: {url[:60]}")
            return False
    except Exception as e:
        print(f"    ❌ Error downloading {url[:60]}: {e}")
        return False


def download_channel_media(channel_id: str, channel_name: str,
                           limit: int = 200, dry_run: bool = False) -> dict:
    """Download images from a Discord channel."""
    out_dir = MEDIA_DIR / channel_name
    out_dir.mkdir(exist_ok=True)

    print(f"\n📸 Channel: {channel_name} (ID: {channel_id})")
    print(f"   Output: {out_dir}")

    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "total_messages": 0}
    before = None
    fetched = 0
    index_entries = []

    while fetched < limit:
        batch_size = min(100, limit - fetched)
        messages = fetch_messages(channel_id, before=before, limit=batch_size)
        if not messages:
            break

        stats["total_messages"] += len(messages)
        fetched += len(messages)
        before = messages[-1]["id"]  # paginate backwards

        for msg in messages:
            image_urls = extract_image_urls(msg)
            if not image_urls:
                continue

            msg_date = msg.get("timestamp", "")[:10]
            author = msg.get("author", {}).get("username", "unknown")

            for url, orig_filename in image_urls:
                # Generate stable filename from URL hash
                url_hash = hashlib.md5(url.split("?")[0].encode()).hexdigest()[:8]
                ext = Path(orig_filename).suffix.lower() or ".png"
                safe_name = f"{msg_date}_{author}_{url_hash}{ext}"
                dest = out_dir / safe_name

                if dest.exists():
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    print(f"    [DRY] {safe_name}")
                    stats["downloaded"] += 1
                    continue

                print(f"    ⬇️  {safe_name}")
                if download_image(url, dest):
                    stats["downloaded"] += 1
                    index_entries.append({
                        "filename": safe_name,
                        "original": orig_filename,
                        "url": url,
                        "author": author,
                        "date": msg_date,
                        "message_id": msg["id"],
                    })
                else:
                    stats["errors"] += 1

                time.sleep(0.1)  # be gentle

        if len(messages) < batch_size:
            break  # no more messages

    # Save index JSON
    if index_entries and not dry_run:
        index_path = out_dir / "_index.json"
        existing = []
        if index_path.exists():
            existing = json.loads(index_path.read_text())
        existing.extend(index_entries)
        index_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    print(f"   ✅ Downloaded: {stats['downloaded']} | Skipped: {stats['skipped']} | Errors: {stats['errors']}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Download Discord channel media")
    parser.add_argument("--channel", help="Channel name (see CHANNELS dict) or ID")
    parser.add_argument("--channel-id", help="Direct Discord channel ID")
    parser.add_argument("--all", action="store_true", help="Download from all known channels")
    parser.add_argument("--limit", type=int, default=100, help="Max messages to scan per channel")
    parser.add_argument("--dry-run", action="store_true", help="List files without downloading")
    args = parser.parse_args()

    if args.all:
        for name, cid in CHANNELS.items():
            if cid:
                download_channel_media(cid, name, args.limit, args.dry_run)
    elif args.channel_id:
        name = args.channel or "unknown"
        download_channel_media(args.channel_id, name, args.limit, args.dry_run)
    elif args.channel:
        cid = CHANNELS.get(args.channel)
        if not cid:
            print(f"❌ Unknown channel '{args.channel}'. Add its ID to CHANNELS dict.")
            sys.exit(1)
        download_channel_media(cid, args.channel, args.limit, args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
