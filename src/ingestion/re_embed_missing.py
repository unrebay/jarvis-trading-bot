"""
re_embed_missing.py — Generate embeddings for documents that have none.

Usage:
  cd ~/jarvis-trading-bot
  OPENAI_API_KEY=sk-... SUPABASE_URL=... SUPABASE_ANON_KEY=... \
    python -m src.ingestion.re_embed_missing

Or with .env:
  python -m src.ingestion.re_embed_missing

Finds all knowledge_documents WHERE embedding IS NULL and generates
text-embedding-3-small embeddings for them, then UPDATEs in place.

Cost estimate: 74 docs × ~1500 chars avg ≈ ~110k tokens ≈ $0.002 total.
"""

import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_DELAY     = 0.3   # seconds between API calls to avoid rate limits


def main():
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set. Export it or add to .env")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL / SUPABASE_ANON_KEY not set.")
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai not installed: pip install openai --break-system-packages")
        sys.exit(1)

    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    openai   = OpenAI(api_key=OPENAI_API_KEY)

    # Fetch all docs with missing embeddings
    res = supabase.table("knowledge_documents") \
        .select("id, title, content, section, source") \
        .is_("embedding", "null") \
        .execute()

    docs = res.data or []
    print(f"🔍 Found {len(docs)} documents without embeddings")

    if not docs:
        print("✅ All documents already have embeddings — nothing to do.")
        return

    # Estimate cost: text-embedding-3-small = $0.02 per 1M tokens ≈ free
    total_chars = sum(len(d["title"] + d["content"]) for d in docs)
    est_tokens  = total_chars // 4
    est_cost    = est_tokens * 0.02 / 1_000_000
    print(f"💰 Estimated cost: ~{est_tokens:,} tokens → ~${est_cost:.5f}")
    print()

    ok = 0
    errors = 0

    for i, doc in enumerate(docs, 1):
        doc_id  = doc["id"]
        title   = doc["title"] or ""
        content = doc["content"] or ""
        section = doc["section"] or ""

        # Truncate to 8191 tokens max (model limit) — ~32k chars
        embed_text = f"{title}\n\n{content}"[:32000]

        try:
            response = openai.embeddings.create(
                model = EMBEDDING_MODEL,
                input = embed_text,
            )
            vector = response.data[0].embedding

            supabase.table("knowledge_documents") \
                .update({"embedding": vector}) \
                .eq("id", doc_id) \
                .execute()

            print(f"  ✅ [{i:02d}/{len(docs)}] id={doc_id} [{section}] {title[:60]}")
            ok += 1

        except Exception as e:
            print(f"  ❌ [{i:02d}/{len(docs)}] id={doc_id} {title[:50]} — {e}")
            errors += 1

        if i < len(docs):
            time.sleep(BATCH_DELAY)

    print()
    print(f"{'='*50}")
    print(f"✅ Embedded: {ok}  ❌ Errors: {errors}")
    print(f"Run /progress in the bot — RAG will now find {ok} more documents!")


if __name__ == "__main__":
    main()
