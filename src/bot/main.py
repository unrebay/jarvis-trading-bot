"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education (ICT/SMC)

v3.2 — Daily learning reminders:
- DailyReminder: finds users inactive > 22h and sends personalized nudges
- PTB JobQueue: runs every day at 09:00 UTC (run_daily)
- Personalized: shows next topic, level, XP from user_memory
- 6 rotating message templates to avoid repetition
- Graceful 403/400 handling (blocked bots)

v2.5 — Live charts + Education system:
- ChartGenerator: live OHLCV charts via yfinance + mplfinance (dark theme)
- /chart SYMBOL TF → generates live chart + ICT/SMC annotation
- LessonManager: /lesson /quiz /progress structured ICT/SMC curriculum
- /quiz → native Telegram QUIZ polls (auto-checks answer + explanation)
- /watch → user watchlist + TradingView webhook alert integration
- send_alert_chart() → proactive annotated chart when TV alert fires

v2.4 — Persistent student memory:
- UserMemory: per-user portrait stored in Supabase (user_memory table)
- Loaded before every message → JARVIS remembers name, experience, style
- Updated every 5 messages via Haiku (async, after response sent)

v2.3 — Visual chart analysis (ChartAnnotator + ChartDrawer)
v2.2 — Fixed architecture (single ClaudeClient, CostManager)
"""

import os
from datetime import time as dt_time, timezone
from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters
)
from supabase import create_client, Client

from .rag_search import RAGSearch
from .telegram_handler import TelegramHandler
from .claude_client import ClaudeClient
from .reminders import DailyReminder

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
# JobQueue callback — daily reminder (called at 09:00 UTC every day)
# ──────────────────────────────────────────────────────────────────────────────

async def _daily_reminder_job(context) -> None:
    """PTB JobQueue callback: send daily learning nudges to inactive users."""
    reminder = DailyReminder(supabase, handler.user_memory)
    sent = await reminder.send_reminders(context.bot)
    print(f"📬 Daily reminder job finished: {sent} messages sent")


# ──────────────────────────────────────────────────────────────────────────────
# Telegram Application
# ──────────────────────────────────────────────────────────────────────────────

class JarvisBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command and message handlers."""
        # ── Daily reminders (v3.2) ──
        self.application.job_queue.run_daily(
            _daily_reminder_job,
            time = dt_time(hour=9, minute=0, tzinfo=timezone.utc),
            name = "daily_reminders",
        )

        # ── Core ──
        self.application.add_handler(CommandHandler("start",    handler.handle_start))
        self.application.add_handler(CommandHandler("help",     handler.handle_help))
        self.application.add_handler(CommandHandler("status",   handler.handle_status))

        # ── Charts ──
        self.application.add_handler(CommandHandler("chart",    handler.handle_chart))

        # ── Education ──
        self.application.add_handler(CommandHandler("lesson",   handler.handle_lesson))
        self.application.add_handler(CommandHandler("quiz",     handler.handle_quiz))
        self.application.add_handler(CommandHandler("progress", handler.handle_progress))
        self.application.add_handler(CommandHandler("levelup",  handler.handle_levelup))
        self.application.add_handler(CommandHandler("profile",  handler.handle_profile))
        self.application.add_handler(CommandHandler("example",  handler.handle_example))
        self.application.add_handler(CommandHandler("stats",    handler.handle_stats))

        # ── Watchlist ──
        self.application.add_handler(CommandHandler("watch",    handler.handle_watch))

        # ── Photo analysis ──
        self.application.add_handler(
            MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/analyze'), handler.handle_photo)
        )
        self.application.add_handler(
            MessageHandler(filters.PHOTO, handler.handle_photo)
        )

        # ── Free text ──
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message)
        )

        # ── Register commands in Telegram menu ──
        self.application.post_init = self._set_bot_commands

    async def _set_bot_commands(self, application):
        """Register commands so they appear in the Telegram '/' menu."""
        commands = [
            BotCommand("start",    "👋 Начать / перезапустить бота"),
            BotCommand("help",     "📖 Список всех команд"),
            BotCommand("lesson",   "🎓 Следующий урок по программе"),
            BotCommand("quiz",     "❓ Тест по теме — /quiz FVG"),
            BotCommand("levelup",  "⬆️ Сдать тест для перехода на след. уровень"),
            BotCommand("progress", "📊 Мой прогресс и XP"),
            BotCommand("profile",  "👤 Мой профиль (что JARVIS помнит)"),
            BotCommand("example",  "🖼 Учебная диаграмма — /example FVG"),
            BotCommand("chart",    "📈 Чарт с анализом — /chart BTCUSDT 4h"),
            BotCommand("watch",    "👁 Watchlist — /watch add BTCUSDT 4h"),
            BotCommand("status",   "💰 Бюджет и режим бота"),
        ]
        await application.bot.set_my_commands(commands)

    def run(self):
        """Start bot polling."""
        print("🤖 JARVIS Bot v3.2 starting...")
        print("   ├─ Claude:     Sonnet (vision/chart), Haiku (chat/memory)")
        print("   ├─ RAG:        pgvector semantic search (238 docs, level-aware)")
        print("   ├─ Lessons:    LessonManager 51 topics (/lesson /quiz /levelup)")
        print("   ├─ Images:     21 ICT/SMC diagrams in Supabase Storage (/example)")
        print("   ├─ Charts:     live yfinance + ChartAnnotator Sonnet (/chart)")
        print("   ├─ Memory:     UserMemory portrait (Supabase, updates every 5 msgs)")
        print("   ├─ Reminders:  DailyReminder 09:00 UTC (inactive users, v3.2)")
        print("   ├─ Watch:      user_watchlist + TradingView webhook /alert")
        print("   ├─ Budget:     CostManager ($1.00/day, FULL→LITE→OFFLINE)")
        print("   └─ Telegram:   polling mode + full command menu")
        self.application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    bot = JarvisBot()
    bot.run()
