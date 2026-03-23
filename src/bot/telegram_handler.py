"""
telegram_handler.py — Обработка Telegram сообщений (v2.3)

Changes v2.3 (iMac):
- Photo analysis now uses ChartAnnotator + ChartDrawer
  → sends ANNOTATED IMAGE back (FVG, S/R, BOS/CHoCH drawn on chart)
  → plus text analysis with ICT/SMC vocabulary
- /analyze command added (same as sending a photo)
- ImageHandler kept for backward-compat but not used for photos

Previous fixes (v2.2):
- Баг #1: неправильные параметры ask_mentor()
- Баг #2: двойная инициализация Anthropic
- Баг #3: сломанный _update_user_stats()
- Интеграция CostManager (FULL/LITE/OFFLINE режимы)
"""

import io
import os
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from supabase import Client

from .rag_search import RAGSearch
from .claude_client import ClaudeClient
from .image_handler import ImageHandler
from .chart_annotator import ChartAnnotator
from .chart_drawer import ChartDrawer
from .cost_manager import cost_manager, BotMode


class TelegramHandler:
    def __init__(self, claude_client: ClaudeClient, supabase: Client, rag: RAGSearch):
        # Принимаем ClaudeClient напрямую (не сырой Anthropic)
        self.claude   = claude_client
        self.supabase = supabase
        self.rag      = rag

        # Chart analysis modules (v2.3)
        self.chart_annotator = ChartAnnotator(claude_client)

        # ImageHandler kept for legacy / fallback
        self.image_handler = ImageHandler(self.claude, supabase)

    # ── Команды ───────────────────────────────────────────────────────────────

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        self._ensure_user_exists(user_id, username)

        await update.message.reply_text(
            "🤖 Привет! Я JARVIS — твой AI-ментор по трейдингу ICT/SMC методологии.\n\n"
            "Я могу помочь:\n"
            "✅ Объяснить концепции (FVG, OB, POI, MSS, BOS, CHoCH...)\n"
            "✅ Разобрать стратегии и entry models\n"
            "✅ Проанализировать график с визуальными аннотациями 🖼️\n\n"
            "Просто напиши вопрос или отправь скриншот графика!\n"
            "/help — список команд  |  /status — состояние бота"
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📖 КОМАНДЫ:\n\n"
            "/start   — начать диалог\n"
            "/help    — эта справка\n"
            "/status  — бюджет и режим работы бота\n"
            "/analyze — анализ графика (отправь фото с командой)\n\n"
            "🎓 УРОВНИ ОБУЧЕНИЯ (отвечаю под твой уровень):\n"
            "• Beginner — основы (инструменты, терминология)\n"
            "• Intermediate — принципы (структура, ликвидность, POI)\n"
            "• Advanced — мульти-ТФ, entry models\n"
            "• Professional — institutional flow, psychology\n\n"
            "🖼 Для анализа графика: отправь скриншот.\n"
            "Я нарисую FVG, OB, BOS/CHoCH, S/R прямо на твоём графике!"
        )

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command — показывает текущий режим и бюджет."""
        summary = cost_manager.get_daily_summary()
        mode    = cost_manager.get_mode()

        mode_emoji = {"FULL": "🟢", "LITE": "🟡", "OFFLINE": "🔴"}.get(mode.value, "⚪")
        mode_desc  = {
            "FULL":    "все функции включены",
            "LITE":    "анализ графиков ограничен",
            "OFFLINE": "только база знаний (API лимит)"
        }.get(mode.value, "неизвестно")

        await update.message.reply_text(
            f"📊 JARVIS Status:\n\n"
            f"{mode_emoji} Режим: {mode.value} ({mode_desc})\n"
            f"💰 Потрачено сегодня: ${summary['total_cost']:.4f} / $1.00\n"
            f"📈 Запросов: {summary['request_count']}\n"
            f"🖼 Анализов графиков: {summary['vision_calls']}"
        )

    # ── Текстовые сообщения ────────────────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular user text messages."""
        user_id  = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        text     = update.message.text

        self._ensure_user_exists(user_id, username)

        # Проверка бюджета
        if not cost_manager.can_use_api():
            await update.message.reply_text(
                "⚠️ Дневной лимит API исчерпан. Попробуй завтра!\n"
                "Бюджет сбрасывается каждый день в 00:00 UTC."
            )
            return

        await update.message.chat.send_action("typing")

        try:
            # 1. История диалога
            history = self._load_history(user_id, limit=20)

            # 2. Поиск по базе знаний
            search_results = self.rag.search(text, top_k=3)
            context_str    = self.rag.format_context(search_results)

            # 3. Уровень пользователя
            user_level = self._get_user_level(user_id)

            # ─── БАГ #1 ИСПРАВЛЕН ───────────────────────────────────────────
            # Было: ask_mentor(text=..., context=..., history=...)
            # Стало: ask_mentor(user_message=..., history=..., knowledge_context=...)
            response = self.claude.ask_mentor(
                user_message      = text,
                history           = history,
                level             = user_level,
                knowledge_context = context_str if context_str else None
            )
            # ────────────────────────────────────────────────────────────────

            # 4. Сохранение в БД
            self._save_message(user_id, "user",      text)
            self._save_message(user_id, "assistant", response)
            self._increment_user_messages(user_id)

            # 5. Предупреждение о бюджете
            warning = cost_manager.get_cost_warning()

            reply = response
            if warning:
                reply += f"\n\n{warning}"

            await update.message.reply_text(reply, parse_mode="Markdown")

        except Exception as e:
            print(f"❌ Message error: {e}")
            import traceback; traceback.print_exc()
            await update.message.reply_text(
                f"⚠️ Произошла ошибка. Попробуй ещё раз.\n`{str(e)[:80]}`",
                parse_mode="Markdown"
            )

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
            # 1. Скачиваем фото (берём максимальное качество)
            photo = update.message.photo[-1]
            file  = await context.bot.get_file(photo.file_id)

            image_bytes_io = io.BytesIO()
            await file.download_to_memory(image_bytes_io)
            image_bytes = image_bytes_io.getvalue()

            await update.message.reply_text("🔍 Анализирую ICT/SMC структуру...")

            # 2. Анализ через ChartAnnotator (Claude Vision)
            ctx = {}
            if caption:
                # Пытаемся извлечь инструмент/таймфрейм из подписи
                ctx["instrument"] = caption
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

            header = "📊 *Анализ графика*"
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
            if annotated_bytes:
                await update.message.reply_photo(
                    photo   = InputFile(io.BytesIO(annotated_bytes), filename="analysis.jpg"),
                    caption = reply_text,
                    parse_mode = "Markdown",
                )
            else:
                # Нет рисунков — шлём только текст
                await update.message.reply_text(reply_text, parse_mode="Markdown")

            # 6. Сохраняем в БД
            patterns_summary = ", ".join(
                p.pattern_name for p in result.get("patterns", [])
            ) or "none"
            self._save_message(user_id, "user",      f"[Chart] {caption or 'no caption'}")
            self._save_message(user_id, "assistant", reply_text[:500])
            self._increment_user_messages(user_id)

        except Exception as e:
            print(f"❌ Photo error: {e}")
            import traceback; traceback.print_exc()
            await update.message.reply_text(
                f"⚠️ Ошибка при анализе графика: `{str(e)[:80]}`",
                parse_mode="Markdown"
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
        """Increment user message counter.
        БАГ #3 ИСПРАВЛЕН: убран сломанный RPC внутри update().
        Теперь: select → increment → update.
        """
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
