"""
telegram_handler.py — Обработка Telegram сообщений (v2.6)

Changes v2.4:
- UserMemory: persistent student portrait stored in Supabase
  → loaded before every message → injected as context into Claude
  → updated every 5 messages via Haiku (async, after response sent)
  → JARVIS теперь помнит имя, опыт, стиль, темы ученика между сессиями

Changes v2.3 (iMac):
- Photo analysis: ChartAnnotator + ChartDrawer (annotated JPEG + text)
- /analyze command added
- ImageHandler kept for backward-compat

Previous fixes (v2.2):
- Баг #1: неправильные параметры ask_mentor()
- Баг #2: двойная инициализация Anthropic
- Баг #3: сломанный _update_user_stats()
- Интеграция CostManager (FULL/LITE/OFFLINE режимы)
"""

import asyncio
import io
import os
import time
from typing import Dict
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from supabase import Client

from .rag_search import RAGSearch
from .claude_client import ClaudeClient
from .image_handler import ImageHandler
from telegram import Poll
from .chart_annotator import ChartAnnotator
from .chart_drawer import ChartDrawer
from .chart_generator import ChartGenerator
from .lesson_manager import LessonManager
from .cost_manager import cost_manager, BotMode
from .user_memory import UserMemory


class TelegramHandler:
    # Per-user rate limiting (v2.6): max 1 request per RATE_LIMIT_SECONDS per user.
    # Prevents accidental API spam from rapid-fire messages.
    RATE_LIMIT_SECONDS = 3
    _last_request: Dict[int, float] = {}  # user_id → timestamp of last request

    def __init__(self, claude_client: ClaudeClient, supabase: Client, rag: RAGSearch):
        # Принимаем ClaudeClient напрямую (не сырой Anthropic)
        self.claude   = claude_client
        self.supabase = supabase
        self.rag      = rag

        # Chart analysis modules (v2.3)
        self.chart_annotator = ChartAnnotator(claude_client)

        # ImageHandler kept for legacy / fallback
        self.image_handler = ImageHandler(self.claude, supabase)

        # Persistent user memory / student portrait (v2.4)
        self.user_memory = UserMemory(supabase)

        # Live chart generation (v2.5)
        self.chart_generator = ChartGenerator()

        # Lesson / quiz / progress system (v2.5)
        self.lesson_manager = LessonManager(claude_client, rag)

    # ── Команды ───────────────────────────────────────────────────────────────

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        self._ensure_user_exists(user_id, username)

        await update.message.reply_text(
            "👋 Привет! Я JARVIS — AI-ментор по ICT/SMC трейдингу.\n\n"
            "Что умею:\n"
            "• Отвечаю на любые вопросы по ICT/SMC методологии\n"
            "• Провожу уроки и тесты по 51 теме (/lesson, /quiz)\n"
            "• Анализирую скриншоты графиков — рисую FVG, OB, BOS\n"
            "• Запоминаю твой уровень и прогресс (/profile)\n\n"
            "Просто напиши вопрос или отправь скриншот!\n\n"
            "👇 Нажми / для списка команд или используй /help"
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📖 *КОМАНДЫ JARVIS*\n\n"
            "💬 *Основное*\n"
            "/start — запустить бота\n"
            "/help — эта справка\n"
            "/status — бюджет и режим бота\n\n"
            "🎓 *Обучение*\n"
            "/lesson — следующая тема по программе\n"
            "/lesson FVG — урок по конкретной теме\n"
            "/lesson list — полный список тем (51)\n"
            "/quiz FVG — тест с проверкой ответа\n"
            "/progress — прогресс по программе\n"
            "/progress reset — сбросить прогресс\n"
            "/profile — что JARVIS помнит о тебе\n"
            "/profile reset — сбросить профиль\n\n"
            "📈 *Графики*\n"
            "/chart BTCUSDT 4h — чарт + ICT/SMC анализ\n"
            "/chart EURUSD 1d — любой инструмент\n"
            "📎 Отправь скриншот — нарисую FVG, OB, BOS\n\n"
            "👁 *Watchlist*\n"
            "/watch — показать список\n"
            "/watch add BTCUSDT 4h — добавить\n"
            "/watch remove BTCUSDT — удалить\n\n"
            "💬 Или просто пиши вопрос — отвечу без команд!",
            parse_mode="Markdown"
        )

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command — показывает текущий режим и бюджет."""
        # FIX: access tracker fields directly (get_daily_summary() returns a string, not dict)
        cost_manager.reset_daily_limit()  # ensure today's tracker is current
        # NOTE: Python GIL ensures this two-step read is safe even under concurrent async requests,
        # since reset_daily_limit() and tracker attribute access are both synchronous operations.
        tracker = cost_manager.tracker
        mode    = cost_manager.get_mode()

        mode_emoji = {"FULL": "🟢", "LITE": "🟡", "OFFLINE": "🔴"}.get(mode.value, "⚪")
        mode_desc  = {
            "FULL":    "все функции включены",
            "LITE":    "анализ графиков ограничен",
            "OFFLINE": "только база знаний (API лимит)"
        }.get(mode.value, "неизвестно")

        remaining = cost_manager.daily_budget - tracker.total_cost
        await update.message.reply_text(
            f"📊 JARVIS Status:\n\n"
            f"{mode_emoji} Режим: {mode.value} ({mode_desc})\n"
            f"💰 Потрачено сегодня: ${tracker.total_cost:.4f} / ${cost_manager.daily_budget:.2f}\n"
            f"💵 Остаток: ${remaining:.4f}\n"
            f"📈 Запросов: {tracker.request_count}\n"
            f"🖼 Анализов графиков: {tracker.vision_calls}"
        )

    # ── /chart — live chart generation + auto-analysis ───────────────────────

    async def handle_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        /chart [symbol] [timeframe]
        Generates a live candlestick chart, then runs ICT/SMC annotation.
        Examples: /chart BTCUSDT 4h   /chart EURUSD 1d   /chart NQ 1h
        """
        user_id = update.effective_user.id
        self._ensure_user_exists(user_id, update.effective_user.username or "Anonymous")

        args = context.args or []
        if not args:
            await update.message.reply_text(
                "📈 Использование: /chart СИМВОЛ ТАЙМФРЕЙМ\n\n"
                "Примеры:\n"
                "  /chart BTCUSDT 4h\n"
                "  /chart EURUSD 1d\n"
                "  /chart NQ 1h\n"
                "  /chart GOLD 1w\n\n"
                "Таймфреймы: 1m 5m 15m 1h 4h 1d 1w"
            )
            return

        if not cost_manager.can_use_vision():
            await update.message.reply_text("🟡 Лимит анализов исчерпан. Попробуй позже.")
            return

        symbol    = args[0].upper()
        timeframe = args[1].lower() if len(args) > 1 else "4h"

        await update.message.chat.send_action("upload_photo")
        await update.message.reply_text(f"📊 Генерирую чарт {symbol} {timeframe.upper()}...")

        # 1. Generate live chart
        gen_result = self.chart_generator.generate(symbol, timeframe)
        if not gen_result["success"]:
            await update.message.reply_text(f"❌ {gen_result['error']}")
            return

        image_bytes = gen_result["image"]
        info        = gen_result["info"]

        # 2. Load user memory for context
        memory     = self.user_memory.load(user_id)
        user_level = memory.get("learning", {}).get("level", "Intermediate")

        # 3. Run ICT/SMC annotation on the generated chart
        ann_ctx = {
            "instrument":    symbol,
            "timeframe":     timeframe,
            "student_level": user_level,
        }
        ann_result    = self.chart_annotator.analyze_chart(image_bytes, context=ann_ctx)
        drawing_instr = ann_result.get("drawing_instructions", {}) if ann_result.get("success") else {}
        analysis_text = ann_result.get("analysis_text", "") if ann_result.get("success") else ""

        # 4. Draw annotations on chart
        annotated_bytes = image_bytes
        has_drawings = any([
            drawing_instr.get("fvg_zones"),
            drawing_instr.get("sr_levels"),
            drawing_instr.get("bos_markers"),
            drawing_instr.get("order_blocks"),
            drawing_instr.get("liquidity_sweeps"),
        ])
        if has_drawings:
            try:
                from .chart_drawer import ChartDrawer
                drawer = ChartDrawer(image_bytes)
                annotated_bytes = drawer.draw(drawing_instr)
            except Exception as draw_err:
                print(f"⚠️ Drawing error: {draw_err}")

        # 5. Build caption
        change_sign = "+" if info["change_pct"] >= 0 else ""
        price_line  = f"{info['last_price']:,.4f}  ({change_sign}{info['change_pct']:.2f}%)"
        header      = f"📊 {symbol} · {timeframe.upper()} · {price_line}"
        caption     = f"{header}\n\n{analysis_text}"[:1020]

        # 6. Send annotated chart
        try:
            await update.message.reply_photo(
                photo   = InputFile(io.BytesIO(annotated_bytes), filename=f"{symbol}_{timeframe}.jpg"),
                caption = caption,
            )
        except Exception as e:
            print(f"⚠️ reply_photo failed: {e}")
            await update.message.reply_text(caption)

        # 7. Update memory counter + trigger portrait update if needed
        memory = self.user_memory.increment(memory)
        self.user_memory.save(user_id, memory)
        if self.user_memory.should_update(memory):
            asyncio.create_task(self._update_memory_async(user_id, memory))

    # ── /lesson ────────────────────────────────────────────────────────────────

    async def handle_lesson(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        /lesson [topic]
        Generates a structured ICT/SMC lesson on the requested topic.
        /lesson alone → shows list of all available topics.
        """
        user_id = update.effective_user.id
        self._ensure_user_exists(user_id, update.effective_user.username or "Anonymous")

        args  = context.args or []
        topic = " ".join(args).strip()

        memory     = self.user_memory.load(user_id)
        user_level = memory.get("learning", {}).get("level", "Intermediate")
        known      = memory.get("learning", {}).get("topics_known", [])

        # /lesson без аргументов → показываем следующий рекомендуемый урок
        if not topic:
            next_topic = self.lesson_manager.get_next_topic(user_level, known)
            curriculum = self.lesson_manager.CURRICULUM.get(user_level, [])
            done = sum(
                1 for t in curriculum
                if any(t.lower() in k.lower() or k.lower() in t.lower() for k in known)
            )
            total = len(curriculum)
            if next_topic:
                await update.message.reply_text(
                    f"📚 Программа {user_level}: {done}/{total} тем пройдено\n\n"
                    f"Следующая тема: *{next_topic}*\n\n"
                    f"→ /lesson {next_topic} — начать урок\n"
                    f"→ /lesson list — весь список тем",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"🎉 Уровень {user_level} завершён! Все {total} тем пройдены.\n\n"
                    f"→ /progress — посмотреть прогресс"
                )
            return

        # /lesson list — полный список тем
        if topic.lower() == "list":
            await update.message.reply_text(self.lesson_manager.get_topics_list())
            return

        if not cost_manager.can_use_api():
            await update.message.reply_text("⚠️ Дневной лимит API исчерпан.")
            return

        await update.message.chat.send_action("typing")
        await update.message.reply_text(f"📖 Готовлю урок: {topic}...")

        lesson_text = self.lesson_manager.get_lesson(topic, user_level)
        await update.message.reply_text(lesson_text)

        # Предлагаем следующий урок
        updated_known = known + [topic]
        next_up = self.lesson_manager.get_next_topic(user_level, updated_known)
        if next_up and next_up.lower() != topic.lower():
            await update.message.reply_text(
                f"✅ Тема изучена!\n\n"
                f"Следующая по программе: *{next_up}*\n"
                f"→ /lesson {next_up}",
                parse_mode="Markdown"
            )

        # Update memory: add topic to current_focus + trigger portrait update if needed
        memory["learning"]["current_focus"] = topic
        memory = self.user_memory.increment(memory)
        self.user_memory.save(user_id, memory)
        if self.user_memory.should_update(memory):
            asyncio.create_task(self._update_memory_async(user_id, memory))

    # ── /quiz — Telegram native quiz polls ─────────────────────────────────────

    async def handle_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        /quiz [topic]
        Generates 3 questions and sends them as native Telegram QUIZ polls
        (auto-checking correct answer with explanation).
        """
        user_id = update.effective_user.id
        self._ensure_user_exists(user_id, update.effective_user.username or "Anonymous")

        args  = context.args or []
        topic = " ".join(args).strip()

        if not topic:
            await update.message.reply_text(
                "🧠 Использование: /quiz ТЕМА\n\n"
                "Примеры:\n"
                "  /quiz FVG\n"
                "  /quiz Order Block\n"
                "  /quiz Market Structure\n\n"
                "Список тем: /lesson"
            )
            return

        if not cost_manager.can_use_api():
            await update.message.reply_text("⚠️ Дневной лимит API исчерпан.")
            return

        await update.message.chat.send_action("typing")
        await update.message.reply_text(f"🧠 Генерирую тест по теме: {topic}...")

        memory     = self.user_memory.load(user_id)
        user_level = memory.get("learning", {}).get("level", "Intermediate")

        questions = self.lesson_manager.get_quiz_questions(topic, user_level)

        if not questions:
            await update.message.reply_text(
                f"❌ Не удалось сгенерировать тест по теме '{topic}'.\n"
                "Попробуй другую тему или повтори позже."
            )
            return

        await update.message.reply_text(
            f"🧠 Тест: {topic}\n{len(questions)} вопроса — отвечай!"
        )

        # Send each question as a native Telegram QUIZ poll
        for i, q in enumerate(questions, 1):
            try:
                await update.message.reply_poll(
                    question          = f"Вопрос {i}: {q['question']}",
                    options           = q["options"],
                    type              = Poll.QUIZ,
                    correct_option_id = q["correct_option_id"],
                    explanation       = q.get("explanation", ""),
                    is_anonymous      = False,
                    open_period       = 60,   # 60 seconds to answer
                )
            except Exception as e:
                # Fallback: send as text if poll fails
                print(f"⚠️ Poll send error (q{i}): {e}")
                options_text = "\n".join(f"  {o}" for o in q["options"])
                correct      = q["options"][q["correct_option_id"]]
                await update.message.reply_text(
                    f"❓ {q['question']}\n{options_text}\n\n✅ Ответ: {correct}\n{q.get('explanation','')}"
                )

        # Update memory + trigger portrait update if needed
        memory = self.user_memory.increment(memory)
        self.user_memory.save(user_id, memory)
        if self.user_memory.should_update(memory):
            asyncio.create_task(self._update_memory_async(user_id, memory))

    # ── /progress ──────────────────────────────────────────────────────────────

    async def handle_progress(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /progress [reset] — show or reset learning progress."""
        user_id = update.effective_user.id
        self._ensure_user_exists(user_id, update.effective_user.username or "Anonymous")

        args = context.args or []
        if args and args[0].lower() == "reset":
            memory = self.user_memory.load(user_id)
            memory["learning"]["topics_known"]       = []
            memory["learning"]["topics_struggling"]  = []
            memory["learning"]["current_focus"]      = None
            memory["learning"]["questions_asked"]    = 0
            self.user_memory.save(user_id, memory)
            await update.message.reply_text(
                "🔄 Прогресс обучения сброшен.\n\n"
                "Изученные темы, фокус и история вопросов очищены.\n"
                "Уровень и профиль сохранены.\n\n"
                "→ /lesson — начать с первой темы программы"
            )
            return

        memory = self.user_memory.load(user_id)
        progress_text = self.lesson_manager.format_progress(memory)
        await update.message.reply_text(progress_text)


    # ── /profile — student portrait from user memory ───────────────────────────

    async def handle_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        /profile — show what JARVIS remembers about this student.
        /profile reset — wipe memory and start fresh.
        """
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        self._ensure_user_exists(user_id, username)

        args = context.args or []

        # ── /profile reset ────────────────────────────────────────────────────
        if args and args[0].lower() == "reset":
            from .user_memory import DEFAULT_MEMORY
            import copy
            self.user_memory.save(user_id, copy.deepcopy(DEFAULT_MEMORY))
            await update.message.reply_text(
                "🗑 Память сброшена.\n\n"
                "JARVIS начнёт знакомиться с тобой заново с следующего сообщения."
            )
            return

        # ── Показываем портрет ────────────────────────────────────────────────
        memory = self.user_memory.load(user_id)

        profile      = memory.get("profile", {})
        learning     = memory.get("learning", {})
        personality  = memory.get("personality", {})
        conversations = memory.get("conversations", {})

        # Profile block
        name       = profile.get("name") or username
        experience = profile.get("experience") or "не указан"
        style      = profile.get("style") or "не определён"
        pairs      = ", ".join(profile.get("pairs", [])) or "не указаны"
        timeframes = ", ".join(profile.get("timeframes", [])) or "не указаны"
        goals      = profile.get("goals") or "не указаны"

        # Learning block
        level          = learning.get("level", "Intermediate")
        known          = learning.get("topics_known", [])
        struggling     = learning.get("topics_struggling", [])
        focus          = learning.get("current_focus") or "нет"
        q_asked        = learning.get("questions_asked", 0)

        # Conversations
        total_msgs = conversations.get("total_messages", 0)
        summary    = conversations.get("summary", "")

        # Build level bar (5 levels)
        level_map = {"Beginner": 1, "Elementary": 2, "Intermediate": 3, "Advanced": 4, "Professional": 5}
        level_n   = level_map.get(level, 3)
        level_bar = "▓" * level_n + "░" * (5 - level_n)

        lines = [
            f"👤 *Профиль ученика — {name}*",
            "",
            f"*Уровень:* {level} [{level_bar}]",
            f"*Опыт торговли:* {experience}",
            f"*Стиль:* {style}",
            f"*Инструменты:* {pairs}",
            f"*Таймфреймы:* {timeframes}",
            f"*Цель:* {goals}",
            "",
            f"*Всего сообщений:* {total_msgs}",
            f"*Вопросов задано:* {q_asked}",
            f"*Текущий фокус:* {focus}",
        ]

        if known:
            known_str = ", ".join(known[:8])
            if len(known) > 8:
                known_str += f" (+{len(known)-8})"
            lines.append(f"*Знает:* {known_str}")

        if struggling:
            lines.append(f"*Сложно даётся:* {', '.join(struggling[:5])}")

        if summary:
            lines.append("")
            lines.append(f"*Резюме:* {summary}")

        lines.append("")
        lines.append("_/profile reset — сбросить память_")

        text = "\n".join(lines)
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text)

    # ── /watch — user watchlist management ─────────────────────────────────────

    async def handle_watch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        /watch                         — show watchlist
        /watch add BTCUSDT [4h]        — add symbol
        /watch remove BTCUSDT          — remove symbol
        """
        user_id = update.effective_user.id
        self._ensure_user_exists(user_id, update.effective_user.username or "Anonymous")

        args = context.args or []

        if not args or args[0].lower() not in ("add", "remove"):
            # Show current watchlist
            items = self._get_watchlist(user_id)
            if not items:
                await update.message.reply_text(
                    "📡 Watchlist пуст.\n\n"
                    "Добавить: /watch add BTCUSDT 4h\n"
                    "При срабатывании TradingView алерта — JARVIS пришлёт анализ!"
                )
            else:
                lines = ["📡 Твой watchlist:\n"]
                for item in items:
                    lines.append(f"  • {item['symbol']} · {item['timeframe'].upper()}")
                lines.append("\nУдалить: /watch remove BTCUSDT")
                await update.message.reply_text("\n".join(lines))
            return

        action = args[0].lower()

        if action == "add":
            if len(args) < 2:
                await update.message.reply_text("Использование: /watch add СИМВОЛ [таймфрейм]\nПример: /watch add BTCUSDT 4h")
                return
            symbol    = args[1].upper()
            timeframe = args[2].lower() if len(args) > 2 else "4h"
            self._add_watchlist(user_id, symbol, timeframe)
            await update.message.reply_text(
                f"✅ {symbol} · {timeframe.upper()} добавлен в watchlist!\n\n"
                f"Настрой алерт в TradingView → webhook на http://77.110.126.107:9000/alert\n"
                f"JARVIS пришлёт анализ когда сработает."
            )

        elif action == "remove":
            if len(args) < 2:
                await update.message.reply_text("Использование: /watch remove СИМВОЛ")
                return
            symbol = args[1].upper()
            self._remove_watchlist(user_id, symbol)
            await update.message.reply_text(f"🗑 {symbol} удалён из watchlist.")

    # ── Watchlist DB helpers ───────────────────────────────────────────────────

    def _get_watchlist(self, user_id: int) -> list:
        try:
            res = self.supabase.table("user_watchlist").select(
                "symbol, timeframe"
            ).eq("telegram_id", user_id).eq("active", True).execute()
            return res.data or []
        except Exception as e:
            print(f"⚠️ Watchlist get error: {e}")
            return []

    def _add_watchlist(self, user_id: int, symbol: str, timeframe: str) -> None:
        try:
            self.supabase.table("user_watchlist").upsert(
                {"telegram_id": user_id, "symbol": symbol, "timeframe": timeframe, "active": True},
                on_conflict="telegram_id,symbol",
            ).execute()
        except Exception as e:
            print(f"⚠️ Watchlist add error: {e}")

    def _remove_watchlist(self, user_id: int, symbol: str) -> None:
        try:
            self.supabase.table("user_watchlist").update(
                {"active": False}
            ).eq("telegram_id", user_id).eq("symbol", symbol).execute()
        except Exception as e:
            print(f"⚠️ Watchlist remove error: {e}")

    # ── Proactive chart send (called by TV alert handler) ─────────────────────

    async def send_alert_chart(
        self,
        bot,
        telegram_id: int,
        symbol: str,
        timeframe: str,
        alert_message: str = "",
    ) -> None:
        """
        Called when a TradingView alert fires for a watchlisted symbol.
        Generates chart, annotates it, sends to user's Telegram chat.
        """
        try:
            gen_result = self.chart_generator.generate(symbol, timeframe)
            if not gen_result["success"]:
                await bot.send_message(
                    chat_id = telegram_id,
                    text    = f"📡 Алерт: {symbol} · {timeframe.upper()}\n⚠️ {gen_result['error']}\n\n{alert_message}",
                )
                return

            image_bytes = gen_result["image"]
            info        = gen_result["info"]

            # Annotate
            ann_result    = self.chart_annotator.analyze_chart(image_bytes, context={"instrument": symbol, "timeframe": timeframe})
            drawing_instr = ann_result.get("drawing_instructions", {}) if ann_result.get("success") else {}
            analysis_text = ann_result.get("analysis_text", "") if ann_result.get("success") else ""

            annotated_bytes = image_bytes
            if any(drawing_instr.get(k) for k in ("fvg_zones", "sr_levels", "bos_markers", "order_blocks")):
                try:
                    from .chart_drawer import ChartDrawer
                    annotated_bytes = ChartDrawer(image_bytes).draw(drawing_instr)
                except Exception:
                    pass

            change_sign = "+" if info["change_pct"] >= 0 else ""
            caption = (
                f"📡 АЛЕРТ: {symbol} · {timeframe.upper()}\n"
                f"{info['last_price']:,.4f}  ({change_sign}{info['change_pct']:.2f}%)\n"
                + (f"\n{alert_message}\n" if alert_message else "")
                + (f"\n{analysis_text}" if analysis_text else "")
            )[:1020]

            await bot.send_photo(
                chat_id = telegram_id,
                photo   = InputFile(io.BytesIO(annotated_bytes), filename=f"{symbol}_alert.jpg"),
                caption = caption,
            )

        except Exception as e:
            print(f"⚠️ Alert chart send error (user {telegram_id}): {e}")

    # ── Текстовые сообщения ────────────────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular user text messages."""
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        text     = update.message.text

        self._ensure_user_exists(user_id, username)

        # Rate limit check (v2.6): silently drop duplicate requests < 3 sec apart
        now = time.monotonic()
        last = TelegramHandler._last_request.get(user_id, 0)
        if now - last < TelegramHandler.RATE_LIMIT_SECONDS:
            return  # ignore — user is sending too fast
        TelegramHandler._last_request[user_id] = now

        # Проверка бюджета
        if not cost_manager.can_use_api():
            await update.message.reply_text(
                "⚠️ Дневной лимит API исчерпан. Попробуй завтра!\n"
                "Бюджет сбрасывается каждый день в 00:00 UTC."
            )
            return

        await update.message.chat.send_action("typing")

        try:
            # 1. Загружаем портрет ученика (v2.4)
            memory      = self.user_memory.load(user_id)
            memory_ctx  = self.user_memory.format_as_context(memory)

            # 2. История диалога
            history = self._load_history(user_id, limit=20)

            # 3. Поиск по базе знаний
            search_results = self.rag.search(text, top_k=3)
            context_str    = self.rag.format_context(search_results)

            # 4. Собираем полный knowledge_context (память + база знаний)
            full_context_parts = []
            if memory_ctx:
                full_context_parts.append(memory_ctx)
            if context_str:
                full_context_parts.append(context_str)
            full_context = "\n\n".join(full_context_parts) or None

            # 5. Уровень: из памяти (актуальнее чем из bot_users)
            user_level = memory.get("learning", {}).get("level") or self._get_user_level(user_id)

            response = self.claude.ask_mentor(
                user_message      = text,
                history           = history,
                level             = user_level,
                knowledge_context = full_context,
            )

            # 6. Сохранение в БД
            self._save_message(user_id, "user",      text)
            self._save_message(user_id, "assistant", response)
            self._increment_user_messages(user_id)

            # 7. Обновляем счётчик памяти и сохраняем
            memory = self.user_memory.increment(memory)
            self.user_memory.save(user_id, memory)

            # 8. Асинхронное обновление портрета каждые N сообщений (v2.4)
            if self.user_memory.should_update(memory):
                asyncio.create_task(
                    self._update_memory_async(user_id, memory)
                )

            # 9. Предупреждение о бюджете
            warning = cost_manager.get_cost_warning()
            reply   = response
            if warning:
                reply += f"\n\n{warning}"

            # FIX: Markdown parse_mode crashes when Claude response has unescaped * _ `
            # Try with Markdown first, log + fall back to plain text on parse error
            try:
                await update.message.reply_text(reply, parse_mode="Markdown")
            except Exception as md_error:
                logger.debug(f"Markdown parse failed (falling back to plain text): {md_error}")
                await update.message.reply_text(reply)

        except Exception as e:
            print(f"❌ Message error: {e}")
            import traceback; traceback.print_exc()
            await update.message.reply_text(
                f"⚠️ Произошла ошибка. Попробуй ещё раз.\n({str(e)[:80]})"
            )

    # ── Memory update (background task) ──────────────────────────────────────

    async def _update_memory_async(self, user_id: int, current_memory: dict) -> None:
        """
        Background task: run Haiku to extract new portrait facts from
        recent conversation, then merge + save back to Supabase.
        Called via asyncio.create_task() — never blocks the response.
        """
        try:
            history = self._load_history(user_id, limit=10)
            if not history:
                return
            updated_raw = self.claude.extract_memory_update(history, current_memory)
            merged      = self.user_memory.apply_update(current_memory, updated_raw)
            self.user_memory.save(user_id, merged)
            print(f"✅ Memory updated for user {user_id} "
                  f"(msg #{current_memory['conversations']['total_messages']})")
        except Exception as e:
            print(f"⚠️ Async memory update error (user {user_id}): {e}")

    # ── Фото (анализ графиков с визуальными аннотациями) ─────────────────────

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo uploads — ICT/SMC chart analysis with visual annotations."""
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        self._ensure_user_exists(user_id, username)

        # Проверяем бюджет на Vision API
        if not cost_manager.can_use_vision():
            mode = cost_manager.get_mode()
            if mode == BotMode.OFFLINE:
                await update.message.reply_text(
                    "🔴 Дневной лимит исчерпан — анализ графиков недоступен.\n"
                    "Попробуй завтра или задай вопрос текстом!"
                )
            else:
                await update.message.reply_text(
                    "🟡 Лимит анализов графиков исчерпан.\n"
                    "Попробуй через несколько минут или задай вопрос текстом."
                )
            return

        await update.message.chat.send_action("upload_photo")
        caption = update.message.caption or ""

        try:
            # 0. Загружаем портрет ученика (v2.4)
            memory = self.user_memory.load(user_id)

            # 1. Скачиваем фото (берём максимальное качество)
            photo = update.message.photo[-1]
            file  = await context.bot.get_file(photo.file_id)

            image_bytes_io = io.BytesIO()
            await file.download_to_memory(image_bytes_io)
            image_bytes = image_bytes_io.getvalue()

            await update.message.reply_text("🔍 Анализирую ICT/SMC структуру...")

            # 2. Анализ через ChartAnnotator (Claude Vision)
            ctx: dict = {}
            if caption:
                ctx["instrument"] = caption
            # Передаём уровень ученика чтобы адаптировать глубину анализа
            user_level = memory.get("learning", {}).get("level", "Intermediate")
            ctx["student_level"] = user_level
            result = self.chart_annotator.analyze_chart(image_bytes, context=ctx)

            if not result.get("success"):
                await update.message.reply_text(
                    f"❌ Не удалось проанализировать: {result.get('error', 'неизвестная ошибка')}"
                )
                return

            drawing_instructions = result.get("drawing_instructions", {})
            analysis_text        = result.get("analysis_text", "")

            # 3. Рисуем аннотации на графике (ChartDrawer)
            annotated_bytes = None
            has_drawings = any([
                drawing_instructions.get("fvg_zones"),
                drawing_instructions.get("sr_levels"),
                drawing_instructions.get("bos_markers"),
                drawing_instructions.get("order_blocks"),
                drawing_instructions.get("liquidity_sweeps"),
            ])

            if has_drawings:
                try:
                    drawer = ChartDrawer(image_bytes)
                    annotated_bytes = drawer.draw(drawing_instructions)
                except Exception as draw_err:
                    print(f"⚠️ Drawing error (non-fatal): {draw_err}")

            # 4. Считаем количество элементов для заголовка
            n_fvg  = len(drawing_instructions.get("fvg_zones",       []))
            n_sr   = len(drawing_instructions.get("sr_levels",        []))
            n_bos  = len(drawing_instructions.get("bos_markers",      []))
            n_ob   = len(drawing_instructions.get("order_blocks",     []))
            n_liq  = len(drawing_instructions.get("liquidity_sweeps", []))

            # Plain-text header (no Markdown — avoids parse errors with dynamic content)
            header = "📊 Анализ графика"
            if any([n_fvg, n_sr, n_bos, n_ob, n_liq]):
                parts = []
                if n_fvg: parts.append(f"FVG×{n_fvg}")
                if n_ob:  parts.append(f"OB×{n_ob}")
                if n_sr:  parts.append(f"S/R×{n_sr}")
                if n_bos: parts.append(f"BOS×{n_bos}")
                if n_liq: parts.append(f"Liq×{n_liq}")
                header += f" | {' '.join(parts)}"

            reply_text = f"{header}\n\n{analysis_text}"

            # Предупреждение о бюджете
            warning = cost_manager.get_cost_warning()
            if warning:
                reply_text += f"\n\n{warning}"

            # 5. Отправляем: аннотированное изображение (если есть) + текст
            # Telegram caption limit = 1024 chars; no parse_mode to avoid
            # Markdown parse errors with dynamic Claude content
            safe_caption = reply_text[:1020]
            if annotated_bytes:
                try:
                    await update.message.reply_photo(
                        photo   = InputFile(io.BytesIO(annotated_bytes), filename="analysis.jpg"),
                        caption = safe_caption,
                    )
                except Exception as send_err:
                    print(f"⚠️ reply_photo failed ({send_err}), sending text only")
                    await update.message.reply_text(safe_caption)
            else:
                # Нет рисунков — шлём только текст
                await update.message.reply_text(reply_text)

            # 6. Сохраняем в БД
            self._save_message(user_id, "user",      f"[Chart] {caption or 'no caption'}")
            self._save_message(user_id, "assistant", reply_text[:500])
            self._increment_user_messages(user_id)

            # 7. Обновляем счётчик памяти (v2.4)
            memory = self.user_memory.increment(memory)
            self.user_memory.save(user_id, memory)
            if self.user_memory.should_update(memory):
                asyncio.create_task(self._update_memory_async(user_id, memory))

        except Exception as e:
            print(f"❌ Photo error: {e}")
            import traceback; traceback.print_exc()
            await update.message.reply_text(
                f"⚠️ Ошибка при анализе графика: {str(e)[:120]}"
            )

    # ── Работа с БД ───────────────────────────────────────────────────────────

    def _ensure_user_exists(self, telegram_id: int, username: str) -> None:
        """Create user if not exists."""
        try:
            res = self.supabase.table("bot_users").select("id").eq(
                "telegram_id", telegram_id
            ).execute()
            if not res.data:
                self.supabase.table("bot_users").insert({
                    "telegram_id": telegram_id,
                    "username":    username,
                    "level":       "Intermediate"
                }).execute()
        except Exception as e:
            print(f"❌ User create error: {e}")

    def _get_user_level(self, user_id: int) -> str:
        """Get user learning level from DB."""
        try:
            res = self.supabase.table("bot_users").select("level").eq(
                "telegram_id", user_id
            ).execute()
            if res.data:
                return res.data[0].get("level", "Intermediate")
        except Exception:
            pass
        return "Intermediate"

    def _load_history(self, user_id: int, limit: int = 20) -> list:
        """Load recent conversation history."""
        try:
            res = self.supabase.table("conversations").select(
                "role, content"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).limit(limit).execute()
            return list(reversed(res.data or []))
        except Exception as e:
            print(f"⚠️ History error: {e}")
            return []

    def _save_message(self, user_id: int, role: str, content: str) -> None:
        """Save message to conversations table."""
        try:
            self.supabase.table("conversations").insert({
                "user_id": user_id,
                "role":    role,
                "content": content
            }).execute()
        except Exception as e:
            print(f"❌ Save message error: {e}")

    def _increment_user_messages(self, user_id: int) -> None:
        """Increment user message counter — single atomic SQL UPDATE (no SELECT needed)."""
        try:
            self.supabase.rpc(
                "increment_messages",
                {"uid": user_id},
            ).execute()
        except Exception:
            # Fallback: classic select → update if RPC not available
            try:
                res = self.supabase.table("bot_users").select(
                    "messages_count"
                ).eq("telegram_id", user_id).execute()
                if res.data:
                    current = res.data[0].get("messages_count") or 0
                    self.supabase.table("bot_users").update({
                        "messages_count": current + 1
                    }).eq("telegram_id", user_id).execute()
            except Exception as e:
                print(f"⚠️ Stats update error: {e}")
