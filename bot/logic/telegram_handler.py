"""
telegram_handler.py — Обработка Telegram сообщений

Функции:
- handle_message(update, context) → None
- handle_start(update, context) → None
- handle_help(update, context) → None
"""

import os
from telegram import Update
from telegram.ext import ContextTypes
from anthropic import Anthropic
from supabase import Client

from .rag_search import RAGSearch
from .claude_client import ClaudeClient


class TelegramHandler:
    def __init__(self, claude_client: Anthropic, supabase: Client, rag: RAGSearch):
        self.claude = claude_client
        self.supabase = supabase
        self.rag = rag
        self.cost_router = ClaudeClient(claude_client)

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load mentor.md system prompt."""
        try:
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, "system", "prompts", "mentor.md")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  System prompt not loaded: {e}")
            return "You are JARVIS, an AI trading mentor teaching ICT/SMC methodology."

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Anonymous"

        # Create/update user in DB
        self._ensure_user_exists(user_id, username)

        welcome_text = """
🤖 Привет! Я JARVIS — твой AI-ментор по трейдингу ICT/SMC методологии.

Я могу помочь тебе:
✅ Объяснить концепции (FVG, POI, MSS, и т.д.)
✅ Разобраться в стратегиях (entry models, risk management)
✅ Ответить на вопросы о торговле

Просто напиши мне сообщение и начнём обучение! 📚

/help — полный список команд
        """
        await update.message.reply_text(welcome_text)

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = """
📖 ДОСТУПНЫЕ КОМАНДЫ:

/start — Начать диалог
/help — Показать эту справку
/level — Установить свой уровень (Beginner, Intermediate, Advanced, Professional, Master)
/history — Показать историю последних сообщений
/search [query] — Поиск в знаниях

🎓 УРОВНИ ОБУЧЕНИЯ:
• Beginner — Основы (инструменты, терминология)
• Intermediate — Принципы (структура, ликвидность, POI)
• Advanced — Продвинутые концепции (multi-TF, entry models)
• Professional — Профессиональная торговля (institutional flow)
• Master — Экспертиза (стратегии, психология, управление капиталом)

Просто напиши вопрос — я дам ответ на твоём уровне! 💡
        """
        await update.message.reply_text(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular user messages."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Anonymous"
        text = update.message.text

        # Ensure user exists
        self._ensure_user_exists(user_id, username)

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            # 1. Load conversation history
            history = self._load_history(user_id, limit=20)

            # 2. Search knowledge base
            search_results = self.rag.search(text, top_k=3)
            context_str = self.rag.format_context(search_results)

            # 3. Build prompt
            user_message = f"{text}\n\n{context_str}"

            # 4. Get response from Claude
            response = self.cost_router.ask_mentor(
                text=user_message,
                context=self.system_prompt,
                history=history
            )

            # 5. Save to DB
            self._save_message(user_id, "user", text)
            self._save_message(user_id, "assistant", response)
            self._update_user_stats(user_id)

            # 6. Send response
            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            print(f"❌ Message handling error: {e}")
            await update.message.reply_text(f"⚠️ Произошла ошибка: {str(e)[:100]}")

    # ── Database operations ────────────────────────────────────────────────────────

    def _ensure_user_exists(self, telegram_id: int, username: str) -> None:
        """Create user if doesn't exist."""
        try:
            res = self.supabase.table("bot_users").select("id").eq(
                "telegram_id", telegram_id
            ).execute()

            if not res.data:
                self.supabase.table("bot_users").insert({
                    "telegram_id": telegram_id,
                    "username": username,
                    "level": "Intermediate"
                }).execute()
        except Exception as e:
            print(f"❌ User creation error: {e}")

    def _load_history(self, user_id: int, limit: int = 20) -> list:
        """Load recent conversation history."""
        try:
            res = self.supabase.table("conversations").select(
                "role, content, created_at"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).limit(limit).execute()

            # Reverse to get chronological order
            return list(reversed(res.data or []))
        except Exception as e:
            print(f"⚠️ History load error: {e}")
            return []

    def _save_message(self, user_id: int, role: str, content: str) -> None:
        """Save message to conversations table."""
        try:
            self.supabase.table("conversations").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()
        except Exception as e:
            print(f"❌ Message save error: {e}")

    def _update_user_stats(self, user_id: int) -> None:
        """Update user message count."""
        try:
            self.supabase.table("bot_users").update({
                "messages_count": self.supabase.rpc(
                    "increment", {"row_id": user_id, "col": "messages_count", "val": 1}
                ).execute()
            }).eq("telegram_id", user_id).execute()
        except Exception as e:
            print(f"⚠️ Stats update error: {e}")
