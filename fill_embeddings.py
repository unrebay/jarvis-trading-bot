#!/usr/bin/env python3
"""
fill_embeddings.py — Генерирует embeddings для документов без векторов в Supabase.
Запуск: python3 fill_embeddings.py
"""
import os, sys, time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_ANON_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
    print("❌ Не хватает переменных: SUPABASE_URL, SUPABASE_ANON_KEY, OPENAI_API_KEY")
    sys.exit(1)

try:
    from supabase import create_client
    from openai import OpenAI
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
        "supabase", "openai", "python-dotenv", "--break-system-packages", "-q"])
    from supabase import create_client
    from openai import OpenAI

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai   = OpenAI(api_key=OPENAI_API_KEY)

# Получаем все документы без embeddings
print("🔍 Ищу документы без embeddings...")
res = supabase.table("knowledge_documents").select("id, title, content").is_("embedding", "null").execute()
docs = res.data or []
print(f"📋 Найдено: {len(docs)} документов без embeddings\n")

if not docs:
    print("✅ Все документы уже имеют embeddings!")
    sys.exit(0)

# Стоимость
total_chars  = sum(len(d.get("content","")) + len(d.get("title","")) for d in docs)
est_cost     = (total_chars / 4 / 1_000_000) * 0.02
print(f"💰 Примерная стоимость: ${est_cost:.4f}\n")

ok = input(f"Продолжить? (y/n): ").strip().lower()
if ok != "y":
    print("Отменено.")
    sys.exit(0)

# Генерируем embeddings
errors = 0
for i, doc in enumerate(docs, 1):
    title   = doc.get("title", "")
    content = doc.get("content", "")
    text    = f"{title}\n\n{content}"[:8191]

    try:
        resp = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536
        )
        embedding = resp.data[0].embedding

        supabase.table("knowledge_documents").update(
            {"embedding": embedding}
        ).eq("id", doc["id"]).execute()

        print(f"  [{i}/{len(docs)}] ✅ {title[:50]}")
        time.sleep(0.15)

    except Exception as e:
        print(f"  [{i}/{len(docs)}] ❌ {title[:40]}: {e}")
        errors += 1
        time.sleep(1)

print(f"\n✅ Готово! Обработано: {len(docs)-errors}, ошибок: {errors}")
