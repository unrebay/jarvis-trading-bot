"""
telegram_handler.py — Обработка Telegram сообщений (v2.2)

Исправлено:
- Баг #1: неправильные параметры ask_mentor() → правильные (user_message, knowledge_context)
- Баг #2: двойная инициализация Anthropic → принимает ClaudeClient напрямую
- Баг #3: сломанный _update_user_stats() → простой select+update
- Новое: интеграция CostManager (FULL/LITE/OFFLINE режимы)
- Новое: /status команда — показывает бюджет и режим
"""

import os
from telegram import Update
from telegram.ext import ContextTypes
from supabase import Client

from .rag_search import RAGSearch
from .claude_client import ClaudeClient
from .image_handler import ImageHandler
from .cost_manager import cost_manager, BotMode


class TelegramHandler:
    def __init__(self, claude_client: ClaudeClient, supabase: Client, rag: RAGSearch):
        # Принимаем ClaudeClient напрямую (не сырой Anthropic)
        self.claude   = claude_client
        self.supabase = supabase
        self.rag      = rag

        # ImageHandler использует тот же ClaudeClient
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
            "✅ Объяснить концепции (FVG, POI, MSS, BOS...)\n"
            "✅ Разобрать стратегии и entry models\n"
            "✅ Проанализировать твой график (отправь фото)\n\n"
            "Просто напиши вопрос или отправь скриншот графика!\n"
            "/help — список команд  |  /status — состояние бота"
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📖 КОМАНДЫ:\n\n"
            "/start   — начать диалог\n"
            "/help    — эта справка\n"
            "/status  — бюджет и режим работы бота\n\n"
            "🎓 УРОВНИ ОБУЧЕНИЯ (отвечаю под твой уровень):\n"
            "• Beginner — основы (инструменты, терминология)\n"
            "• Intermediate — принципы (структура, ликвидность, POI)\n"
            "• Advanced — мульти-ТФ, entry models\n"
            "• Professional — institutional flow, psychology\n\n"
            "💡 Просто напиши вопрос по трейдингу или отправь фото графика!"
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

    # ── Фото (анализ графиков) ─────────────────────────────────────────────────

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo uploads — trading chart analysis."""
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
                    "🟡 Лимит анализов графиков на час исчерпан.\n"
                    "Попробуй через несколько минут или задай вопрос текстом."
                )
            return

        await update.message.chat.send_action("typing")

        try:
            # Скачиваем фото (берём максимальное качество)
            photo    = update.message.photo[-1]
            file     = await context.bot.get_file(photo.file_id)
            file_path = f"/tmp/chart_{photo.file_id}.jpg"
            await file.download_to_drive(file_path)

            caption = update.message.caption or ""
            await update.message.reply_text("🔍 Анализирую график...")

            result = self.image_handler.process_image_upload(
                file_path,
                context={"title": caption or "Trading Chart", "description": caption}
            )

            if result.get("success"):
                analysis = result.get("analysis", {})
                patterns = analysis.get("detected_patterns", [])
                levels   = analysis.get("key_levels", [])
                points   = analysis.get("learning_points", [])[:3]

                lines = [f"📊 **Анализ графика:**\n"]
                lines.append(f"**Тип:** {analysis.get('analysis_type', 'N/A')}  "
                             f"**Уверенность:** {analysis.get('confidence', 0):.0%}\n")

                if patterns:
                    lines.append("**Паттерны:**")
                    lines += [f"• {p}" for p in patterns]

                if levels:
                    lines.append("\n**Ключевые уровни:**")
                    lines += [f"• {l.get('type','').upper()}: {l.get('level','N/A')}" for l in levels]

                if points:
                    lines.append("\n**Выводы:**")
                    lines += [f"• {p}" for p in points]

                response_text = "\n".join(lines)

                self._save_message(user_id, "user",      f"[Chart] {caption}")
                self._save_message(user_id, "assistant", response_text)
                self._increment_user_messages(user_id)

                warning = cost_manager.get_cost_warning()
                if warning:
                    response_text += f"\n\n{warning}"

                await update.message.reply_text(response_text, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    f"❌ Не удалось проанализировать: {result.get('error', 'неизвестная ошибка')}"
                )

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
