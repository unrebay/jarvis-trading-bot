"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education
Голос Джарвиса, стиль: рассудительный, решительный, профессиональный

v2.1 — Modular architecture (RAG + Telegram Handler + Cost Routing)
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from anthropic import Anthropic
from supabase import create_client, Client

# Import modules
from bot.logic.rag_search import RAGSearch
from bot.logic.telegram_handler import TelegramHandler
from bot.logic.claude_client import ClaudeClient

# ──────────────────────────────────────────────────────────────────────────────
# Инициализация
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CLAUDE_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_ANON_KEY")

# Initialize clients
claude_client   = Anthropic(api_key=CLAUDE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize modules
rag = RAGSearch(supabase)
handler = TelegramHandler(claude_client, supabase, rag)

# ──────────────────────────────────────────────────────────────────────────────
# Telegram Bot Application
# ──────────────────────────────────────────────────────────────────────────────

class JarvisBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Register command and message handlers."""
        self.application.add_handler(CommandHandler("start",  handler.handle_start))
        self.application.add_handler(CommandHandler("help",   handler.handle_help))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message)
        )

    def run(self):
        """Start bot polling."""
        print("🤖 JARVIS Bot v2.1 starting (modular architecture)...")
        print("   ├─ RAG: Supabase semantic search")
        print("   ├─ Claude: Cost router (Haiku default)")
        print("   ├─ Supabase: Message history + user profiles")
        print("   └─ Telegram: Event handling")
        self.application.run_polling()


if __name__ == "__main__":
    bot = JarvisBot()
    bot.run()
