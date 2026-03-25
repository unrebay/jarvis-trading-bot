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
        "BOS",             # Break of Structure
        "CHoCH",           # Change of Character
        "Liquidity",
        "Risk Management",
        "Терминология ICT",
        "Торговые инструменты",
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
        "Inducement",
        "BPR",                    # Balanced Price Range
        "Volume Imbalance",
        "SNR",                    # Support / Resistance refined
        "Sponsor Candle",
    ],
    "Advanced": [
        "Entry Model",
        "AMD",                    # Accumulation Manipulation Distribution (PO3)
        "ICT Killzones",
        "Mitigation Block",
        "Multi-Timeframe Analysis",
        "OTE",                    # Optimal Trade Entry
        "Rejection Block",
        "STB / BTS",             # Sell to Buy / Buy to Sell
        "Торговые сессии",        # London, NY, Asia timings
        "Тайминги",               # Kill zones, session timings
        "Gold Mechanics",        # XAUUSD specifics
        "TGIF Setup",
        "Judas Swing",
    ],
    "Professional": [
        "IPDA",                   # Institutional Price Delivery Algorithm
        "Institutional Order Flow",
        "Smart Money Concepts",
        "Trading Psychology",
        "Дисциплина",
        "Торговый план",
        "Backtest",
        "Управление рисками",     # Risk %, RR, position sizing
        "Wyckoff",
        "RTGS Theory",           # Real-Time Gross Settlement
        "Advanced Market Structure",
        "STDV Projection",       # Standard Deviation
        "Weekly Profiles",
        "DWMY Opens",            # Daily/Weekly/Monthly/Yearly
    ],
}

# All topics flat list (for fuzzy matching)
ALL_TOPICS = [t for topics in CURRICULUM.values() for t in topics]

# Level progression order
LEVEL_ORDER = ["Beginner", "Elementary", "Intermediate", "Advanced", "Professional"]

# XP rewards
XP_LESSON     = 50    # за прохождение урока
XP_QUIZ_PASS  = 100   # за пройденный тест
XP_QUESTION   = 20    # за правильный ответ в тесте
XP_LEVELUP    = 500   # за переход на новый уровень

# Badges: id → (emoji, название, условие-описание)
BADGES: dict[str, tuple[str, str, str]] = {
    "first_lesson":  ("📖", "Первый урок",     "пройден первый урок"),
    "first_quiz":    ("🧪", "Первый тест",      "пройден первый тест"),
    "quiz_streak_3": ("🔥", "На разогреве",     "3 теста подряд"),
    "topics_5":      ("🎯", "Любознательный",   "изучено 5 тем"),
    "topics_10":     ("📚", "Книжный червь",    "изучено 10 тем"),
    "level_up":      ("⬆️", "Следующий уровень", "повышение уровня"),
    "level_advanced":("🏆", "Продвинутый",      "достигнут уровень Advanced"),
    "level_pro":     ("💎", "Профессионал",     "достигнут уровень Professional"),
}

# Минимальный % тем для права на тест перехода уровня
LEVEL_UP_THRESHOLD = 0.8  # 80% тем текущего уровня должны быть пройдены


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

            try:
                questions = json.loads(text.strip())
            except json.JSONDecodeError as json_err:
                print(f"⚠️ Quiz JSON parse error: {json_err}")
                return []

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
        level   = learning.get("level", "Beginner")
        known   = learning.get("topics_known", [])
        hard    = learning.get("topics_struggling", [])
        focus   = learning.get("current_focus")
        total   = convs.get("total_messages", 0)
        summary = convs.get("summary", "").strip()
        xp      = learning.get("xp", 0)
        badges  = learning.get("badges", [])

        # Level position bar (e.g. Beginner = 1/5)
        level_idx = LEVEL_ORDER.index(level) + 1 if level in LEVEL_ORDER else 1
        level_bar = "▓" * level_idx + "░" * (len(LEVEL_ORDER) - level_idx)

        # Curriculum progress bar
        done_count, total_curr = self.count_done(level, known)
        bar_filled = int((done_count / max(total_curr, 1)) * 10)
        curr_bar = "█" * bar_filled + "░" * (10 - bar_filled)

        # XP bar (each level ~10 topics × 50xp = 500xp)
        xp_per_level = 500
        xp_in_level  = xp % xp_per_level
        xp_bar_n     = int((xp_in_level / xp_per_level) * 8)
        xp_bar       = "⚡" * xp_bar_n + "·" * (8 - xp_bar_n)

        lines = [
            f"📊 *Прогресс: {name}*",
            f"",
            f"*Уровень:* {level} [{level_bar}]",
            f"*XP:* {xp} [{xp_bar}]",
            f"*Сообщений:* {total}",
            f"",
            f"*Программа {level}:*",
            f"[{curr_bar}] {done_count}/{total_curr} тем",
        ]

        if known:
            lines += ["", f"✅ *Изучено ({len(known)}):*", "   " + ", ".join(known[:12])]
            if len(known) > 12:
                lines[-1] += f" (+{len(known)-12})"

        if hard:
            lines += ["", "⚠️ *Требуют внимания:*", "   " + ", ".join(hard[:6])]

        if focus:
            lines += ["", f"🎯 *Сейчас:* {focus}"]

        # Suggest next or level-up
        next_topic = self.get_next_topic(level, known)
        level_up_ready = self.check_level_up_ready(level, known)
        next_level = self.get_next_level(level)

        if level_up_ready and next_level:
            lines += [
                "",
                f"🏆 *Уровень {level} почти пройден!*",
                f"Сдай финальный тест чтобы перейти на {next_level}:",
                f"→ /levelup",
            ]
        elif next_topic:
            lines += ["", f"💡 *Следующая тема:* {next_topic}", f"   → /lesson {next_topic}"]

        # Badges
        if badges:
            badge_str = " ".join(BADGES[b][0] for b in badges if b in BADGES)
            lines += ["", f"*Значки:* {badge_str}"]

        if summary:
            lines += ["", f"📝 {summary}"]

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
        curriculum = CURRICULUM.get(level, CURRICULUM["Beginner"])
        known_lower = [k.lower() for k in known_topics]
        for topic in curriculum:
            already_known = any(
                topic.lower() in k or k in topic.lower()
                for k in known_lower
            )
            if not already_known:
                return topic
        return None

    def count_done(self, level: str, known_topics: list[str]) -> tuple[int, int]:
        """Return (done_count, total_count) for given level."""
        curriculum = CURRICULUM.get(level, [])
        done = sum(
            1 for t in curriculum
            if any(t.lower() in k.lower() or k.lower() in t.lower() for k in known_topics)
        )
        return done, len(curriculum)

    def check_level_up_ready(self, level: str, known_topics: list[str]) -> bool:
        """Return True if user has passed enough topics to attempt level-up test."""
        done, total = self.count_done(level, known_topics)
        if total == 0:
            return False
        return (done / total) >= LEVEL_UP_THRESHOLD

    def get_next_level(self, current_level: str) -> Optional[str]:
        """Return the next level name, or None if already at max."""
        idx = LEVEL_ORDER.index(current_level) if current_level in LEVEL_ORDER else -1
        if idx == -1 or idx >= len(LEVEL_ORDER) - 1:
            return None
        return LEVEL_ORDER[idx + 1]

    def get_levelup_quiz(self, level: str) -> list[dict]:
        """
        Generate a comprehensive 5-question level-up test covering the whole current level.
        User must pass to advance to next level.
        """
        topics_list = ", ".join(CURRICULUM.get(level, [])[:8])
        prompt = (
            f"Создай 5 вопросов итогового теста для перехода с уровня {level} на следующий.\n"
            f"Темы уровня: {topics_list}\n\n"
            "Вопросы должны проверять ПРАКТИЧЕСКОЕ понимание, а не просто память.\n"
            "Каждый вопрос — из разных тем уровня.\n"
            "Сложность: выше среднего.\n\n"
            "Формат — только JSON, массив из 5 объектов:\n"
            "[\n"
            "  {\n"
            '    "question": "вопрос (до 255 символов)",\n'
            '    "options": ["правильный ответ", "неверный вариант 2", "неверный вариант 3", "неверный вариант 4"],\n'
            '    "correct_option_id": 0,\n'
            '    "explanation": "объяснение (до 200 символов)"\n'
            "  }\n"
            "]\n\n"
            "correct_option_id всегда 0. Ответы на русском."
        )

        def _call():
            return self.claude.client.messages.create(
                model      = HAIKU,
                max_tokens = 2000,
                system     = [{"type": "text", "text": "Ты создаёшь учебные тесты ICT/SMC. Отвечай ТОЛЬКО валидным JSON."}],
                messages   = [{"role": "user", "content": prompt}],
            )

        try:
            resp = self.claude._retry_with_backoff(_call)
            text = resp.content[0].text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            questions = json.loads(text.strip())
            validated = []
            for q in questions:
                if not all(k in q for k in ("question", "options", "correct_option_id")):
                    continue
                options = q["options"][:4]
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
            print(f"⚠️ Level-up quiz error: {e}")
            return []

    # ── Gamification helpers ───────────────────────────────────────────────────

    @staticmethod
    def award_xp(memory: dict, amount: int) -> dict:
        """Add XP to user memory. Returns updated memory."""
        memory["learning"]["xp"] = memory["learning"].get("xp", 0) + amount
        return memory

    @staticmethod
    def award_badge(memory: dict, badge_id: str) -> tuple[dict, bool]:
        """
        Award badge if not already earned.
        Returns (updated_memory, was_new).
        """
        badges = memory["learning"].setdefault("badges", [])
        if badge_id not in badges:
            badges.append(badge_id)
            return memory, True
        return memory, False

    def get_curriculum_text(self, level: str = "Beginner") -> str:
        """Return formatted curriculum for the given level."""
        curriculum = CURRICULUM.get(level, CURRICULUM["Beginner"])
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

    def get_lesson_image(self, topic: str, supabase_client=None) -> dict | None:
        """
        Look up a static educational image for the given topic.
        Returns dict with {image_url, caption, concept_type} or None.
        """
        if not supabase_client:
            return None
        try:
            # Try exact topic match first, then fuzzy (ILIKE)
            resp = supabase_client.table("lesson_images").select(
                "image_url, caption, concept_type"
            ).ilike("topic", topic.strip()).limit(1).execute()
            if resp.data:
                return resp.data[0]
            # Fallback: match by concept keyword in topic name
            keyword = topic.split()[0].lower()
            resp2 = supabase_client.table("lesson_images").select(
                "image_url, caption, concept_type"
            ).ilike("concept_type", f"%{keyword}%").limit(1).execute()
            return resp2.data[0] if resp2.data else None
        except Exception as e:
            print(f"⚠️ get_lesson_image error: {e}")
            return None
