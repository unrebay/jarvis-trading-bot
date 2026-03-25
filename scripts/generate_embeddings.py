#!/usr/bin/env python3
"""
generate_embeddings.py — Генерация эмбеддингов для документов без embedding

Находит все документы в knowledge_documents где embedding IS NULL
и генерирует их через OpenAI text-embedding-3-small.

Запуск:
    python3 scripts/generate_embeddings.py
    python3 scripts/generate_embeddings.py --dry-run   # только показать, не обновлять
"""

import os, sys, argparse
from pathlib import Path

# Загружаем env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from openai import OpenAI

def generate_embeddings(dry_run: bool = False):
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ["SUPABASE_KEY"]
    sb  = create_client(url, key)

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY не задан")
        sys.exit(1)

    oai = OpenAI(api_key=openai_key)

    # Найти документы без эмбеддинга
    response = (
        sb.table("knowledge_documents")
        .select("id, title, content, difficulty_level")
        .is_("embedding", "null")
        .execute()
    )
    docs = response.data or []

    if not docs:
        print("✅ Все документы уже имеют эмбеддинги")
        return

    print(f"📋 Документов без эмбеддинга: {len(docs)}\n")

    for doc in docs:
        title = doc["title"]
        doc_id = doc["id"]
        content = doc["content"][:8000]  # OpenAI limit

        print(f"  🔄 [{doc_id}] {title[:60]}")

        if dry_run:
            print(f"       (dry-run, пропускаем)")
            continue

        try:
            emb_response = oai.embeddings.create(
                model="text-embedding-3-small",
                input=content,
            )
            vector = emb_response.data[0].embedding

            sb.table("knowledge_documents").update(
                {"embedding": vector}
            ).eq("id", doc_id).execute()

            print(f"       ✅ эмбеддинг сгенерирован ({len(vector)} dims)")

        except Exception as e:
            print(f"       ❌ ошибка: {e}")

    if not dry_run:
        print(f"\n✅ Готово — {len(docs)} эмбеддингов сгенерировано")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Только показать, не обновлять")
    args = parser.parse_args()
    generate_embeddings(dry_run=args.dry_run)
