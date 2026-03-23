#!/usr/bin/env python3
"""
load_knowledge_to_supabase.py

Загружает knowledge_base.json в Supabase knowledge_documents.

Режимы:
  - без OPENAI_API_KEY → только текст (keyword-поиск через GIN-индексы)
  - с OPENAI_API_KEY   → текст + embeddings (семантический поиск)

Запуск:
  python load_knowledge_to_supabase.py           # загрузить всё
  python load_knowledge_to_supabase.py --dry-run # показать что будет загружено
  python load_knowledge_to_supabase.py --reset   # удалить всё и загрузить заново
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ── Конфиг ────────────────────────────────────────────────────────────────────

SUPABASE_URL     = os.getenv("SUPABASE_URL")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

EMBEDDING_MODEL  = "text-embedding-3-small"
EMBEDDING_DIMS   = 1536
RATE_LIMIT_DELAY = 0.15   # секунды между запросами к OpenAI

KB_PATH = Path(__file__).parent / "knowledge_base.json"

# ── Проверка окружения ─────────────────────────────────────────────────────────

def check_env() -> bool:
    ok = True
    if not SUPABASE_URL:
        print("❌  SUPABASE_URL не задан в .env")
        ok = False
    if not SUPABASE_KEY:
        print("❌  SUPABASE_ANON_KEY не задан в .env")
        ok = False
    if not ok:
        sys.exit(1)

    if OPENAI_API_KEY:
        print("✅  OPENAI_API_KEY найден → режим: текст + embeddings")
    else:
        print("⚠️   OPENAI_API_KEY не задан → режим: только текст (keyword-поиск)")

    return bool(OPENAI_API_KEY)

# ── Embeddings ─────────────────────────────────────────────────────────────────

def get_embedding(client, text: str) -> list[float]:
    """Генерирует embedding через OpenAI text-embedding-3-small."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8191],      # лимит OpenAI
        dimensions=EMBEDDING_DIMS,
    )
    return response.data[0].embedding


def estimate_cost(entries: list) -> float:
    """Примерная стоимость: $0.02 за 1M токенов."""
    total_chars  = sum(len(e.get("content", "")) + len(e.get("title", "")) for e in entries)
    total_tokens = total_chars / 4
    return (total_tokens / 1_000_000) * 0.02

# ── Загрузка ───────────────────────────────────────────────────────────────────

def load_entries(path: Path) -> list[dict]:
    """Читает все markdown-записи из knowledge_base.json."""
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)

    entries = kb.get("sources", {}).get("markdown", [])
    print(f"\n📚  Прочитано из knowledge_base.json: {len(entries)} документов")
    print(f"    Разделы: {sorted(set(e.get('section','?') for e in entries))}")
    return entries


def get_existing_keys(supabase: Client) -> set[tuple]:
    """Возвращает set (title, section) уже загруженных документов."""
    res  = supabase.table("knowledge_documents").select("title,section").execute()
    keys = {(r["title"], r["section"]) for r in (res.data or [])}
    return keys


def reset_table(supabase: Client):
    """Удаляет все записи из knowledge_documents (с подтверждением)."""
    count_res = supabase.table("knowledge_documents").select("id", count="exact").execute()
    total = count_res.count or 0
    print(f"\n⚠️   В таблице {total} документов. Удалить все? [y/N] ", end="")
    ans = input().strip().lower()
    if ans != "y":
        print("Отменено.")
        sys.exit(0)
    supabase.table("knowledge_documents").delete().neq("id", 0).execute()
    print("🗑️   Таблица очищена.")


def run(dry_run: bool = False, reset: bool = False):
    # 1. Проверка env
    use_embeddings = check_env()

    # 2. Загрузить knowledge_base
    entries = load_entries(KB_PATH)
    if not entries:
        print("❌  Нет документов для загрузки.")
        sys.exit(1)

    # 3. Dry-run
    if dry_run:
        print(f"\n🔍  DRY RUN — реальная загрузка не выполняется")
        if use_embeddings:
            cost = estimate_cost(entries)
            print(f"💰  Примерная стоимость embeddings: ~${cost:.5f}")
        print(f"\nДокументы к загрузке:")
        for e in entries:
            print(f"  [{e.get('section','?')}] {e.get('title', e.get('filename','?'))[:70]}")
        return

    # 4. Init Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 5. Reset если нужно
    if reset:
        reset_table(supabase)

    # 6. Проверить уже загруженные
    existing = get_existing_keys(supabase)
    print(f"📊  Уже в БД: {len(existing)} документов")

    # 7. Init OpenAI если нужно
    openai_client = None
    if use_embeddings:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            cost = estimate_cost(entries)
            print(f"💰  Примерная стоимость embeddings: ~${cost:.5f}")
        except ImportError:
            print("⚠️   openai не установлен: pip install openai --break-system-packages")
            print("     Продолжаю без embeddings...")
            use_embeddings = False

    # 8. Загружаем
    print(f"\n{'─'*55}")
    new_count    = 0
    skip_count   = 0
    error_count  = 0

    for i, entry in enumerate(entries, 1):
        title   = entry.get("title") or entry.get("filename", f"doc_{i}")
        section = entry.get("section", "unknown")
        topic   = entry.get("topic", "")
        content = entry.get("content", "")

        # Пропустить если уже загружен
        if (title, section) in existing:
            print(f"  ⏭️  [{i:02d}/{len(entries)}] {title[:55]}")
            skip_count += 1
            continue

        print(f"  ⚙️  [{i:02d}/{len(entries)}] {title[:55]}...", end="", flush=True)

        try:
            # Embedding
            embedding = None
            if use_embeddings and openai_client:
                embed_text = f"{title}\n\n{content}"
                embedding  = get_embedding(openai_client, embed_text)
                time.sleep(RATE_LIMIT_DELAY)

            # Metadata
            metadata = {
                "filename": entry.get("filename", ""),
                "headings": entry.get("headings", []),
                "source_id": entry.get("id", ""),
            }

            # Upsert
            row = {
                "title":    title,
                "content":  content,
                "section":  section,
                "topic":    topic,
                "source":   "markdown",
                "metadata": metadata,
            }
            if embedding:
                row["embedding"] = embedding

            supabase.table("knowledge_documents").insert(row).execute()
            new_count += 1
            print(" ✓")

        except Exception as e:
            print(f" ❌  {e}")
            error_count += 1
            time.sleep(1)

    # 9. Итог
    print(f"\n{'='*55}")
    print(f"✅  Загружено новых:      {new_count}")
    print(f"⏭️   Пропущено (уже есть): {skip_count}")
    print(f"❌  Ошибок:               {error_count}")
    print(f"📊  Всего в БД:           {len(existing) + new_count}")
    if not use_embeddings and new_count > 0:
        print(f"\n💡  Embeddings не загружены. Добавьте OPENAI_API_KEY в .env")
        print(f"    и запустите снова — скрипт пропустит уже загруженные и добавит векторы.")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузка knowledge_base.json в Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Показать что будет загружено без реальной загрузки")
    parser.add_argument("--reset",   action="store_true", help="Удалить всё из таблицы и загрузить заново")
    args = parser.parse_args()

    run(dry_run=args.dry_run, reset=args.reset)
