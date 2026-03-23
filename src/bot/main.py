"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education (ICT/SMC)

v2.2 — Fixed architecture:
- Single ClaudeClient (no double Anthropic instantiation)
- Clean dependency injection chain
- CostManager guards all API calls
"""

import os
from dotenv import load_dotenv
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters
)
from supabase import create_client, Client

from .rag_search import RAGSearch
from .telegram_handler import TelegramHandler
from .claude_client import ClaudeClient

# ──────────────────────────────────────────────────────────────────────────────
# Инициализация окружения
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_ANON_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL / SUPABASE_ANON_KEY not set in .env")

# ──────────────────────────────────────────────────────────────────────────────
# Инициализация клиентов (один раз, на весь процесс)
# ──────────────────────────────────────────────────────────────────────────────

# ClaudeClient сам читает ANTHROPIC_API_KEY из .env и создаёт Anthropic() внутри
claude: ClaudeClient   = ClaudeClient(enable_caching=True)
supabase: Client       = create_client(SUPABASE_URL, SUPABASE_KEY)

# Модули
rag     = RAGSearch(supabase)
handler = TelegramHandler(claude, supabase, rag)

# ──────────────────────────────────────────────────────────────────────────────
# Telegram Application
# ──────────────────────────────────────────────────────────────────────────────

class JarvisBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command and message handlers."""
        self.application.add_handler(CommandHandler("start",   handler.handle_start))
        self.application.add_handler(CommandHandler("help",    handler.handle_help))
        self.application.add_handler(CommandHandler("status",  handler.handle_status))
        self.application.add_handler(
            MessageHandler(filters.PHOTO, handler.handle_photo)
        )
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message)
        )

    def run(self):
        """Start bot polling."""
        print("🤖 JARVIS Bot v2.2 starting...")
        print("   ├─ Claude:    ClaudeClient (Haiku default, cache ON)")
        print("   ├─ RAG:       Supabase keyword search (61 lessons)")
        print("   ├─ Budget:    CostManager ($1.00/day, FULL→LITE→OFFLINE)")
        print("   ├─ Supabase:  conversations + users")
        print("   └─ Telegram:  polling mode")
        self.application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    bot = JarvisBot()
    bot.run()
