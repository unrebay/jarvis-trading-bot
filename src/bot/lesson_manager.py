"""
lesson_manager.py — Structured ICT/SMC learning system (v1.0)

Provides:
  /lesson [topic]   — generate a structured lesson from the knowledge base
  /quiz [topic]     — generate 3 questions as Telegram QUIZ polls (auto-check)
  /progress         — learning progress report from user memory
  get_next_topic()  — suggest next topic based on user level + known topics

Learning curriculum:
  Beginner      → Market Structure, BOS, CHoCH, Liquidity
  Intermediate  → FVG, Order Block, POI, Premium/Discount
  Advanced      → Entry Models, AMD, Killzones, IPDA
  Professional  → Institutional flow, psychology, advanced setups
"""

import json
from typing import Optional

from .claude_client import ClaudeClient, HAIKU
from .rag_search import RAGSearch


# ── Structured curriculum ──────────────────────────────────────────────────────

CURRICULUM: dict[str, list[str]] = {
    "Beginner": [
        "Market Structure",
        "Support and Resistance",
        "Candlestick Basics",
        "Trend",
        "BOS",         # Break of Structure
        "CHoCH",       # Change of Character
        "Liquidity",
        "Risk Management",
    ],
    "Intermediate": [
        "FVG",                    # Fair Value Gap
        "Order Block",
        "Breaker Block",
        "POI",                    # Point of Interest
        "Premium / Discount",
        "Equilibrium",
        "Displacement",
        "MSS",                    # Market Structure Shift
        "Liquidity Sweep",
    ],
    "Advanced": [
        "Entry Model",
        "AMD",                    # Accumulation Manipulation Distribution
        "ICT Killzones",
        "Mitigation Block",
        "Multi-Timeframe Analysis",
        "OTE",                    # Optimal Trade Entry
    ],
    "Professional": [
        "IPDA",                   # Institutional Price Delivery Algorithm
        "Institutional Order Flow",
        "Smart Money Concepts",
        "Trading Psychology",
        "Portfolio Management",
    ],
}

# All topics flat list (for fuzzy matching)
ALL_TOPICS = [t for topics in CURRICULUM.values() for t in topics]


class LessonManager:
    """Manages lessons, quizzes and learning progress for JARVIS students."""

    def __init__(self, claude: ClaudeClient, rag: RAGSearch):
        self.claude = claude
        self.rag    = rag

    # ── /lesson ────────────────────────────────────────────────────────────────

    def get_lesson(self, topic: str, level: str = "Intermediate") -> str:
        """
        Generate a structured ICT/SMC lesson using RAG context + Haiku.
        Returns formatted plain-text lesson.
        """
        results    = self.rag.search(topic, top_k=5)
        kb_context = self.rag.format_context(results) or ""

        prompt = (
            f"Составь структурированный урок по теме: «{topic}»\n"
            f"Уровень ученика: {level}\n\n"
            + (f"Материал из базы знаний:\n{kb_context[:1500]}\n\n" if kb_context else "")
            + "Формат урока (используй эти разделы):\n"
            "🔷 ЧТО ЭТО — определение простыми словами (2-3 предложения)\n"
            "🔷 КАК ВЫГЛЯДИТ НА ГРАФИКЕ — визуальные признаки, что искать\n"
            "🔷 КАК ТОРГОВАТЬ — правила входа, стоп, тейк\n"
            "🔷 ЧАСТЫЕ ОШИБКИ — что путают новички\n"
            "🔷 ЗАПОМНИ — 2-3 главных правила одной строкой\n\n"
            "Пиши по-русски. Чётко, практично, с примерами. Без лишней воды.\n"
            "В конце добавь: «Напиши /quiz {topic} чтобы проверить себя!»"
        )

        def _call():
            return self.claude.client.messages.create(
                model      = HAIKU,
                max_tokens = 1500,
                system     = [{
                    "type": "text",
                    "text": (
                        "Ты JARVIS — практикующий трейдер и педагог ICT/SMC. "
                        "Даёшь чёткие, структурированные уроки на русском языке."
                    ),
                }],
                messages = [{"role": "user", "content": prompt}],
            )

        try:
            resp = self.claude._retry_with_backoff(_call)
            # Wire into cost tracker
            try:
                from .cost_manager import cost_manager
                cost_manager.record_cost("haiku", "lesson",
                    resp.usage.input_tokens, resp.usage.output_tokens)
            except Exception:
                pass
            return resp.content[0].text
        except Exception as e:
            return f"❌ Не удалось сгенерировать урок: {e}"

    # ── /quiz — returns structured data for Telegram quiz polls ───────────────

    def get_quiz_questions(self, topic: str, level: str = "Intermediate") -> list[dict]:
        """
        Generate 3 quiz questions for Telegram QUIZ polls.

        Returns list of dicts:
          {
            "question":          "Что такое FVG?",
            "options":           ["Область дисбаланса...", "Уровень поддержки...", ...],
            "correct_option_id": 0,          # index of correct answer
            "explanation":       "FVG — это...",
          }
        """
        results    = self.rag.search(topic, top_k=3)
        kb_context = self.rag.format_context(results) or ""

        prompt = (
            f"Создай 3 вопроса теста по теме «{topic}» для уровня {level}.\n\n"
            + (f"Контекст:\n{kb_context[:1000]}\n\n" if kb_context else "")
            + "Важно: вопросы должны быть практическими, с применением знаний.\n"
            "Формат — только JSON (без markdown), массив из 3 объектов:\n"
            "[\n"
            "  {\n"
            '    "question": "вопрос (до 255 символов)",\n'
            '    "options": ["правильный ответ", "неверный вариант 2", "неверный вариант 3", "неверный вариант 4"],\n'
            '    "correct_option_id": 0,\n'
            '    "explanation": "объяснение почему первый вариант верный (до 200 символов)"\n'
            "  }\n"
            "]\n\n"
            "Правила:\n"
            "- correct_option_id всегда 0 (первый вариант всегда правильный)\n"
            "- Варианты ответов: 10-80 символов каждый\n"
            "- Вопрос: чёткий, однозначный\n"
            "- Ответы на русском языке"
        )

        def _call():
            return self.claude.client.messages.create(
                model      = HAIKU,
                max_tokens = 1200,
                system     = [{
                    "type": "text",
                    "text": "Ты создаёшь учебные тесты по трейдингу ICT/SMC. Отвечай ТОЛЬКО валидным JSON.",
                }],
                messages = [{"role": "user", "content": prompt}],
            )

        try:
            resp = self.claude._retry_with_backoff(_call)
            # Wire into cost tracker
            try:
                from .cost_manager import cost_manager
                cost_manager.record_cost("haiku", "quiz",
                    resp.usage.input_tokens, resp.usage.output_tokens)
            except Exception:
                pass
            text = resp.content[0].text.strip()

            # Strip markdown fences
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            questions = json.loads(text.strip())

            # Validate and sanitize
            validated = []
            for q in questions:
                if not all(k in q for k in ("question", "options", "correct_option_id", "explanation")):
                    continue
                options = q["options"][:4]  # Telegram max 10, we use 4
                while len(options) < 2:
                    options.append("—")
                validated.append({
                    "question":          str(q["question"])[:255],
                    "options":           [str(o)[:100] for o in options],
                    "correct_option_id": int(q["correct_option_id"]) % len(options),
                    "explanation":       str(q.get("explanation", ""))[:200],
                })

            return validated

        except Exception as e:
            print(f"⚠️ Quiz generation error: {e}")
            return []

    # ── /progress ──────────────────────────────────────────────────────────────

    def format_progress(self, memory: dict) -> str:
        """Format a human-readable learning progress report from user memory."""
        learning = memory.get("learning", {})
        profile  = memory.get("profile", {})
        convs    = memory.get("conversations", {})

        name    = profile.get("name") or "Трейдер"
        level   = learning.get("level", "Intermediate")
        known   = learning.get("topics_known", [])
        hard    = learning.get("topics_struggling", [])
        focus   = learning.get("current_focus")
        total   = convs.get("total_messages", 0)
        summary = convs.get("summary", "").strip()

        # Progress bar for curriculum
        curriculum_topics = CURRICULUM.get(level, [])
        done_count = sum(
            1 for t in curriculum_topics
            if any(t.lower() in k.lower() or k.lower() in t.lower() for k in known)
        )
        total_curr = len(curriculum_topics)
        bar_filled = int((done_count / max(total_curr, 1)) * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        lines = [
            f"📊 Прогресс: {name}",
            f"━━━━━━━━━━━━━━━━━━━",
            f"Уровень: {level}",
            f"Сообщений с JARVIS: {total}",
            "",
            f"Программа {level}:",
            f"[{bar}] {done_count}/{total_curr} тем",
        ]

        if known:
            lines += ["", f"✅ Изучено ({len(known)}):", "   " + ", ".join(known[:12])]

        if hard:
            lines += ["", "⚠️ Требуют внимания:", "   " + ", ".join(hard[:6])]

        if focus:
            lines += ["", f"🎯 Сейчас: {focus}"]

        # Suggest next topic
        next_topic = self.get_next_topic(level, known)
        if next_topic:
            lines += ["", f"💡 Рекомендую изучить: {next_topic}", f"   → /lesson {next_topic}"]

        if summary:
            lines += ["", f"📝 Заметки JARVIS:", summary]

        if total < 3:
            lines += [
                "",
                "🌱 Начни общаться — JARVIS будет автоматически",
                "   строить твой профиль обучения.",
            ]

        return "\n".join(lines)

    # ── Curriculum helpers ─────────────────────────────────────────────────────

    def get_next_topic(self, level: str, known_topics: list[str]) -> Optional[str]:
        """Suggest the next topic to study based on curriculum position."""
        curriculum = CURRICULUM.get(level, CURRICULUM["Intermediate"])
        known_lower = [k.lower() for k in known_topics]
        for topic in curriculum:
            already_known = any(
                topic.lower() in k or k in topic.lower()
                for k in known_lower
            )
            if not already_known:
                return topic
        return None

    def get_curriculum_text(self, level: str = "Intermediate") -> str:
        """Return formatted curriculum for the given level."""
        curriculum = CURRICULUM.get(level, CURRICULUM["Intermediate"])
        topics_text = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(curriculum))
        return (
            f"📚 Программа уровня {level}:\n\n"
            f"{topics_text}\n\n"
            f"Начать: /lesson {curriculum[0]}"
        )

    def get_topics_list(self) -> str:
        """Return all available topics for the /lesson command."""
        lines = ["📚 Доступные темы:\n"]
        for level, topics in CURRICULUM.items():
            lines.append(f"{'▸'} {level}:")
            for t in topics:
                lines.append(f"    • {t}")
        lines.append("\nПример: /lesson FVG   или   /lesson Order Block")
        return "\n".join(lines)
