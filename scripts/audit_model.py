#!/usr/bin/env python3
"""
audit_model.py — Аудит качества ответов модели (полный пайплайн)

Тестирует: вопрос → RAG поиск → Claude ответ → оценка качества.
В отличие от audit_kb.py (проверяет только документы), этот скрипт
проверяет что JARVIS реально правильно отвечает на ICT вопросы.

Запуск:
    python3 scripts/audit_model.py
    python3 scripts/audit_model.py --verbose   # показать полные ответы
    python3 scripts/audit_model.py --export    # сохранить в docs/model_audit.md
"""

import os, sys, argparse, textwrap
from datetime import datetime
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
from src.bot.rag_search import RAGSearch

# ── 10 ключевых вопросов для аудита модели ────────────────────────────────────
# Охватывают самые важные ICT концепции.
# expected_keywords — ключевые слова КОТОРЫЕ ДОЛЖНЫ БЫТЬ в ответе Claude.

AUDIT_QUESTIONS = [
    {
        "question": "Что такое BOS (Break of Structure) и как он определяется?",
        # Принимаем и русские термины и английские эквиваленты
        "keywords": ["структур", "тренд", "пробо|слом|break", "максимум|хай|high", "минимум|лой|low"],
        "level": "Intermediate",
        "module": "Структура рынка",
    },
    {
        "question": "Что такое FVG (Fair Value Gap) и как его торговать?",
        "keywords": ["дисбаланс|gap|зона", "свеч|candle", "заполн|fill|вернёт", "бычий|медвежий|bullish|bearish"],
        "level": "Beginner",
        "module": "Неэффективности",
    },
    {
        "question": "Что такое Order Block и как его определить?",
        "keywords": ["блок|block", "свеч|candle", "разворот|импульс", "поддержк|сопротивл|support"],
        "level": "Beginner",
        "module": "Зоны интереса",
    },
    {
        "question": "Что такое Kill Zone в ICT и когда торговать?",
        "keywords": ["лондон|london", "нью-йорк|new york|новая", "сессия|session", "время|hour|часо"],
        "level": "Intermediate",
        "module": "Сессии",
    },
    {
        "question": "Как считать размер позиции при риске 1% от депозита?",
        "keywords": ["стоп|stop", "риск|risk", "депозит|счёт|capital", "лот|lot|объём"],
        "level": "Beginner",
        "module": "Риск-менеджмент",
    },
    {
        "question": "В чём разница между BOS и CHoCH?",
        "keywords": ["choch|смена|change", "разворот|reversal", "тренд|trend", "bos|слом|break"],
        "level": "Intermediate",
        "module": "Структура рынка",
    },
    {
        "question": "Что такое Judas Swing и как его распознать?",
        "keywords": ["ложн|false|ловушк", "ликвидност|liquidity", "разворот|reversal", "манипул|trap"],
        "level": "Intermediate",
        "module": "Манипуляции",
    },
    {
        "question": "Что такое Top-Down Analysis (TDA) в ICT?",
        "keywords": ["таймфрейм|timeframe", "старш|higher|htf", "направлени|direction|тренд", "дневн|d1|недельн|weekly"],
        "level": "Intermediate",
        "module": "Анализ",
    },
    {
        "question": "Что такое Premium и Discount зоны?",
        "keywords": ["50|половин|mid", "выше|above|premium", "ниже|below|discount", "fibonacci|фибоначч|зона"],
        "level": "Intermediate",
        "module": "Ценовые зоны",
    },
    {
        "question": "Как справляться с убыточными сделками психологически?",
        "keywords": ["эмоц|emotion|психолог", "убыток|loss|потер", "дисциплин|discipline", "журнал|дневник|план"],
        "level": "Intermediate",
        "module": "Психология",
    },
]

# ── ANSI цвета ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def score_answer(answer: str, keywords: list[str]) -> tuple[int, list[str]]:
    """
    Проверяет ключевые слова в ответе Claude (case-insensitive).
    Поддерживает OR-логику через '|': "хай|high|максимум" — достаточно одного варианта.
    """
    answer_lower = answer.lower()
    found, missing = [], []
    for kw in keywords:
        variants = [v.strip() for v in kw.split("|")]
        if any(v.lower() in answer_lower for v in variants):
            found.append(kw)
        else:
            missing.append(kw)
    score = int(100 * len(found) / len(keywords)) if keywords else 0
    return score, missing


def _load_system_prompt() -> str:
    """Загружает реальный системный промпт бота из system/prompts/mentor.md."""
    prompt_path = Path(__file__).parent.parent / "system" / "prompts" / "mentor.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "Ты — JARVIS, торговый ментор по методологии ICT/SMC. "
        "Отвечай чётко, по существу, используй термины курса на русском языке."
    )


def ask_claude(question: str, context: str) -> str:
    """Вызывает Claude с реальным системным промптом и RAG контекстом."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system = _load_system_prompt()
    if context:
        system += f"\n\n{context}"

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text


def run_audit(verbose: bool = False, export: bool = False):
    url  = os.environ["SUPABASE_URL"]
    key  = os.environ.get("SUPABASE_ANON_KEY") or os.environ["SUPABASE_KEY"]
    sb   = create_client(url, key)
    rag  = RAGSearch(sb)

    results = []
    total_score = 0

    print()
    print(f"{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  JARVIS MODEL AUDIT — {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")
    print(f"  {len(AUDIT_QUESTIONS)} вопросов · RAG + Claude Haiku · keyword scoring")
    print(f"{BOLD}{'═'*70}{RESET}\n")

    for i, q in enumerate(AUDIT_QUESTIONS, 1):
        question = q["question"]
        keywords = q["keywords"]
        level    = q["level"]
        module   = q["module"]

        # 1. RAG поиск
        docs    = rag.search(question, top_k=3, level=level)
        context = rag.format_context(docs, max_chars=500) if docs else ""
        rag_ok  = "✅" if docs else "❌"

        # 2. Вызов Claude
        try:
            answer = ask_claude(question, context)
        except Exception as e:
            answer = f"[ОШИБКА: {e}]"

        # 3. Оценка ответа
        score, missing = score_answer(answer, keywords)
        total_score += score

        # 4. Вывод
        color = GREEN if score >= 60 else (YELLOW if score >= 30 else RED)
        icon  = "✅" if score >= 60 else ("⚠️ " if score >= 30 else "❌")
        label = f"[{i:02d}] {module:<22} {score:>3}%"
        print(f"  {icon} {color}{label}{RESET}  {question[:55]}")

        if missing:
            miss_str = ", ".join(missing)
            print(f"       {YELLOW}⚠ не найдено в ответе: {miss_str}{RESET}")

        if verbose:
            wrapped = textwrap.fill(answer, width=66, initial_indent="     │ ", subsequent_indent="     │ ")
            print(f"     ╔{'─'*64}╗")
            print(wrapped)
            print(f"     ╚{'─'*64}╝\n")

        results.append({
            "module": module,
            "question": question,
            "score": score,
            "missing": missing,
            "rag_docs": len(docs),
            "answer_preview": answer[:200],
        })

    # ── Итоги ─────────────────────────────────────────────────────────────────
    avg   = total_score // len(AUDIT_QUESTIONS)
    good  = sum(1 for r in results if r["score"] >= 60)
    weak  = sum(1 for r in results if 30 <= r["score"] < 60)
    bad   = sum(1 for r in results if r["score"] < 30)

    print()
    print(f"{BOLD}{'═'*70}{RESET}")
    print(f"{BOLD}  ИТОГО: {avg}% среднее качество ответов{RESET}")
    color = GREEN if avg >= 80 else (YELLOW if avg >= 60 else RED)
    print(f"  {color}✅ Хорошо (≥60%): {good}  ⚠️  Слабо (30-60%): {weak}  ❌ Плохо (<30%): {bad}{RESET}")
    print(f"{BOLD}{'─'*70}{RESET}")

    if avg >= 80:
        verdict = "✅ Модель готова к следующей фазе"
        verdict_color = GREEN
    elif avg >= 60:
        verdict = "⚠️  Модель требует улучшений (промпт или KB)"
        verdict_color = YELLOW
    else:
        verdict = "❌ Модель не готова — критические проблемы"
        verdict_color = RED

    print(f"\n  {verdict_color}{BOLD}{verdict}{RESET}\n")

    # ── Экспорт ───────────────────────────────────────────────────────────────
    if export:
        out_path = Path(__file__).parent.parent / "docs" / "model_audit.md"
        out_path.parent.mkdir(exist_ok=True)

        lines = [
            f"# JARVIS Model Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"\n**Итого: {avg}% | ✅ {good} | ⚠️ {weak} | ❌ {bad}**\n",
            "| # | Модуль | Вопрос | Score | Не найдено |",
            "|---|--------|--------|-------|------------|",
        ]
        for i, r in enumerate(results, 1):
            miss = ", ".join(r["missing"]) if r["missing"] else "—"
            icon = "✅" if r["score"] >= 60 else ("⚠️" if r["score"] >= 30 else "❌")
            lines.append(
                f"| {i} | {r['module']} | {r['question'][:60]} | {icon} {r['score']}% | {miss} |"
            )

        lines += [
            "\n## Вердикт",
            verdict,
            "\n## Методология",
            "- Каждый вопрос проходит RAG поиск → Claude Haiku → keyword scoring",
            "- Оценка: процент ключевых слов найденных в ответе модели",
            "- Порог готовности: ≥80% среднее",
        ]

        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  📄 Отчёт сохранён: {out_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JARVIS Model Quality Audit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Показать полные ответы")
    parser.add_argument("--export",  "-e", action="store_true", help="Сохранить отчёт в docs/model_audit.md")
    args = parser.parse_args()
    run_audit(verbose=args.verbose, export=args.export)
