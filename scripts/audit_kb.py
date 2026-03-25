#!/usr/bin/env python3
"""
audit_kb.py — Аудит качества базы знаний JARVIS

Прогоняет 30 ключевых ICT/SMC вопросов через RAG-поиск,
показывает что бот нашёл и оценивает покрытие.

Запуск:
    python3 scripts/audit_kb.py
    python3 scripts/audit_kb.py --verbose    # показать полный текст найденного
    python3 scripts/audit_kb.py --export     # сохранить в docs/kb_audit.md
"""

import os, sys, argparse, textwrap
from datetime import datetime

# Загружаем env
from pathlib import Path
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from src.bot.rag_search import RAGSearch

# ── 30 ключевых вопросов по ICT/SMC курсу ────────────────────────────────────
# Сгруппированы по модулю. Каждый вопрос имеет:
#   question    — сам вопрос
#   keywords    — ключевые слова которые ДОЛЖНЫ быть в ответе
#   level       — уровень ученика для поиска
#   module      — модуль курса

AUDIT_QUESTIONS = [
    # ── Структура рынка ──────────────────────────────────────────
    {
        "module": "Structure & Liquidity",
        "question": "Что такое BOS (Break of Structure) и как он определяется?",
        "keywords": ["bos", "break", "структур", "хай", "лой", "слом"],
        "level": "Intermediate",
    },
    {
        "module": "Structure & Liquidity",
        "question": "В чём разница между BOS и CHoCH?",
        "keywords": ["choch", "change of character", "bos", "тренд", "разворот"],
        "level": "Intermediate",
    },
    {
        "module": "Structure & Liquidity",
        "question": "Что такое сильные и слабые точки структуры?",
        "keywords": ["сильн", "слаб", "swing", "структур"],
        "level": "Intermediate",
    },
    # ── Ликвидность ──────────────────────────────────────────────
    {
        "module": "Liquidity",
        "question": "Что такое ликвидность в контексте ICT?",
        "keywords": ["ликвидност", "стоп", "охота", "liquidity", "equal"],
        "level": "Beginner",
    },
    {
        "module": "Liquidity",
        "question": "Что такое BSL и SSL?",
        "keywords": ["bsl", "ssl", "buy side", "sell side", "ликвидност"],
        "level": "Intermediate",
    },
    {
        "module": "Liquidity",
        "question": "Что такое inducement (IDM)?",
        "keywords": ["inducement", "idm", "ложн", "ликвидност", "приманк"],
        "level": "Intermediate",
    },
    # ── FVG и имбалансы ──────────────────────────────────────────
    {
        "module": "Inefficiency Types",
        "question": "Что такое FVG (Fair Value Gap) и как его торговать?",
        "keywords": ["fvg", "fair value", "gap", "имбаланс", "три свечи"],
        "level": "Beginner",
    },
    {
        "module": "Inefficiency Types",
        "question": "Чем отличается FVG от IFVG?",
        "keywords": ["ifvg", "inverted", "перевёрнут", "fvg"],
        "level": "Intermediate",
    },
    {
        "module": "Inefficiency Types",
        "question": "Что такое Volume Imbalance?",
        "keywords": ["volume imbalance", "объём", "имбаланс", "vi"],
        "level": "Intermediate",
    },
    # ── Блоки ────────────────────────────────────────────────────
    {
        "module": "Block Types",
        "question": "Что такое Order Block и как его определить?",
        "keywords": ["order block", "ob", "блок", "импульс", "свеча"],
        "level": "Beginner",
    },
    {
        "module": "Block Types",
        "question": "Что такое Breaker Block?",
        "keywords": ["breaker", "пробой", "block", "структур"],
        "level": "Intermediate",
    },
    {
        "module": "Block Types",
        "question": "Что такое Mitigation Block?",
        "keywords": ["mitigation", "митигейшн", "block", "возврат"],
        "level": "Intermediate",
    },
    {
        "module": "Block Types",
        "question": "Что такое Rejection Block?",
        "keywords": ["rejection", "отказ", "block", "хвост", "wick"],
        "level": "Intermediate",
    },
    # ── Order Flow ───────────────────────────────────────────────
    {
        "module": "Order Flow",
        "question": "Что такое Order Flow в SMC?",
        "keywords": ["order flow", "поток", "направлен", "структур"],
        "level": "Intermediate",
    },
    {
        "module": "Order Flow",
        "question": "Как подтвердить смену Order Flow?",
        "keywords": ["bos", "choch", "подтвержден", "смен", "order flow"],
        "level": "Advanced",
    },
    # ── TDA и модели входа ───────────────────────────────────────
    {
        "module": "TDA & Entry Models",
        "question": "Что такое Top-Down Analysis (TDA)?",
        "keywords": ["top-down", "tda", "старший", "таймфрейм", "контекст"],
        "level": "Intermediate",
    },
    {
        "module": "TDA & Entry Models",
        "question": "Опиши модель входа по FVG",
        "keywords": ["fvg", "вход", "модель", "entry", "стоп", "цель"],
        "level": "Intermediate",
    },
    {
        "module": "TDA & Entry Models",
        "question": "Что такое POI (Point of Interest)?",
        "keywords": ["poi", "point of interest", "зона", "интерес"],
        "level": "Beginner",
    },
    # ── Сессии ───────────────────────────────────────────────────
    {
        "module": "Sessions",
        "question": "Какие торговые сессии важны для ICT трейдинга?",
        "keywords": ["london", "new york", "азия", "сессия", "kill zone"],
        "level": "Intermediate",
    },
    {
        "module": "Sessions",
        "question": "Что такое Kill Zone в ICT?",
        "keywords": ["kill zone", "лондон", "нью-йорк", "время", "вход"],
        "level": "Intermediate",
    },
    {
        "module": "Sessions",
        "question": "Как работать с золотом по сессиям?",
        "keywords": ["gold", "золото", "xau", "сессия", "лондон", "нью-йорк"],
        "level": "Advanced",
    },
    # ── Риск-менеджмент ──────────────────────────────────────────
    {
        "module": "Risk Management",
        "question": "Какой % от депозита рисковать в одной сделке?",
        "keywords": ["процент", "риск", "депозит", "1%", "2%", "позиция"],
        "level": "Beginner",
    },
    {
        "module": "Risk Management",
        "question": "Как считать размер позиции?",
        "keywords": ["размер", "позиция", "лот", "стоп", "риск", "расчёт"],
        "level": "Beginner",
    },
    # ── Манипуляции ──────────────────────────────────────────────
    {
        "module": "Manipulations",
        "question": "Что такое Judas Swing?",
        "keywords": ["judas", "swing", "ложный", "манипуляция", "разворот"],
        "level": "Intermediate",
    },
    {
        "module": "Manipulations",
        "question": "Что такое AMD (Accumulation, Manipulation, Distribution)?",
        "keywords": ["amd", "accumulation", "manipulation", "distribution", "po3"],
        "level": "Intermediate",
    },
    # ── Психология ───────────────────────────────────────────────
    {
        "module": "Psychology",
        "question": "Почему дисциплина важна в трейдинге?",
        "keywords": ["дисциплин", "правил", "систем", "эмоци"],
        "level": "Beginner",
    },
    {
        "module": "Psychology",
        "question": "Как справляться с убыточными сделками?",
        "keywords": ["убыток", "эмоци", "потер", "психолог", "стресс"],
        "level": "Intermediate",
    },
    # ── Продвинутые темы ─────────────────────────────────────────
    {
        "module": "Advanced",
        "question": "Что такое Premium и Discount зоны?",
        "keywords": ["premium", "discount", "фибоначчи", "50%", "зона"],
        "level": "Intermediate",
    },
    {
        "module": "Advanced",
        "question": "Что такое Silver Bullet стратегия?",
        "keywords": ["silver bullet", "10:00", "11:00", "нью-йорк", "fvg"],
        "level": "Advanced",
    },
    {
        "module": "Advanced",
        "question": "Как использовать мультитаймфреймный анализ для входа?",
        "keywords": ["мультитаймфрейм", "multi", "таймфрейм", "htf", "ltf", "вход"],
        "level": "Advanced",
    },
]


# ── Scorer ────────────────────────────────────────────────────────────────────

def score_result(docs: list, keywords: list[str]) -> tuple[int, list[str]]:
    """Score how well docs cover the expected keywords. Returns (0-100, found_kws)."""
    if not docs:
        return 0, []
    combined = " ".join(d.get("content", "") for d in docs).lower()
    found = [kw for kw in keywords if kw.lower() in combined]
    score = int(len(found) / len(keywords) * 100) if keywords else 50
    return score, found


# ── Main ──────────────────────────────────────────────────────────────────────

def run_audit(verbose: bool = False, export: bool = False):
    url  = os.environ["SUPABASE_URL"]
    key  = os.environ["SUPABASE_ANON_KEY"]
    sb   = create_client(url, key)
    rag  = RAGSearch(sb)

    results = []
    module_scores: dict = {}

    print(f"\n{'═'*70}")
    print(f"  JARVIS KB AUDIT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {len(AUDIT_QUESTIONS)} вопросов · keyword scoring")
    print(f"{'═'*70}\n")

    for i, q in enumerate(AUDIT_QUESTIONS, 1):
        docs = rag.search(q["question"], q["level"])
        score, found_kws = score_result(docs, q["keywords"])

        status = "✅" if score >= 60 else ("⚠️ " if score >= 30 else "❌")
        print(f"  {status} [{i:02d}] {q['module']:<22} {score:3d}%  {q['question'][:55]}")

        if verbose and docs:
            for d in docs[:2]:
                excerpt = d.get("content", "")[:200].replace("\n", " ")
                print(f"       → [{d.get('topic','?')}] {excerpt}…")

        if score < 60 and not verbose:
            missing = [kw for kw in q["keywords"] if kw.lower() not in
                       " ".join(d.get("content","") for d in docs).lower()]
            if missing:
                print(f"       ⚠ не найдено: {', '.join(missing[:4])}")

        module = q["module"]
        module_scores.setdefault(module, []).append(score)
        results.append({**q, "score": score, "found": found_kws, "docs_count": len(docs)})

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print("  РЕЗУЛЬТАТЫ ПО МОДУЛЯМ")
    print(f"{'═'*70}")
    overall_scores = []
    for module, scores in module_scores.items():
        avg = sum(scores) / len(scores)
        overall_scores.extend(scores)
        status = "✅" if avg >= 60 else ("⚠️ " if avg >= 30 else "❌")
        bar = "█" * int(avg / 5) + "░" * (20 - int(avg / 5))
        print(f"  {status} {module:<25} [{bar}] {avg:5.0f}%")

    total_avg = sum(overall_scores) / len(overall_scores)
    passed    = sum(1 for s in overall_scores if s >= 60)
    warned    = sum(1 for s in overall_scores if 30 <= s < 60)
    failed    = sum(1 for s in overall_scores if s < 30)

    print(f"\n{'─'*70}")
    print(f"  ИТОГО: {total_avg:.0f}% среднее покрытие")
    print(f"  ✅ Хорошо (≥60%): {passed}  ⚠️  Слабо (30-60%): {warned}  ❌ Плохо (<30%): {failed}")
    print(f"{'─'*70}")

    if total_avg >= 80:
        print("\n  ✅ KB готова к следующей фазе (Фаза 2: TradingView)")
    elif total_avg >= 60:
        print("\n  ⚠️  KB удовлетворительна, но есть пробелы — рекомендуется исправить")
    else:
        print("\n  ❌ KB требует серьёзной доработки перед торговой автоматизацией")

    # ── Export ────────────────────────────────────────────────────────────
    if export:
        out_path = Path(__file__).parent.parent / "docs" / "kb_audit.md"
        lines = [
            f"# KB Audit Report — {datetime.now().strftime('%Y-%m-%d')}",
            f"\n**Итого:** {total_avg:.0f}% · ✅ {passed} / ⚠️  {warned} / ❌ {failed}\n",
            "| # | Модуль | Вопрос | Score | Статус |",
            "|---|--------|--------|-------|--------|",
        ]
        for i, r in enumerate(results, 1):
            status = "✅" if r["score"] >= 60 else ("⚠️" if r["score"] >= 30 else "❌")
            lines.append(f"| {i} | {r['module']} | {r['question'][:60]} | {r['score']}% | {status} |")
        lines += [
            "\n## Пробелы по модулям",
        ]
        for module, scores in module_scores.items():
            avg = sum(scores) / len(scores)
            if avg < 60:
                lines.append(f"\n### ❌ {module} ({avg:.0f}%)")
                for r in results:
                    if r["module"] == module and r["score"] < 60:
                        missing = [kw for kw in r["keywords"] if kw not in r["found"]]
                        lines.append(f"- **{r['question']}** — нет ключевых слов: {', '.join(missing)}")
        out_path.write_text("\n".join(lines))
        print(f"\n  📄 Отчёт сохранён: {out_path}")

    return total_avg


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Аудит базы знаний JARVIS")
    parser.add_argument("--verbose", action="store_true", help="Показать найденные документы")
    parser.add_argument("--export",  action="store_true", help="Сохранить отчёт в docs/kb_audit.md")
    args = parser.parse_args()
    run_audit(verbose=args.verbose, export=args.export)
