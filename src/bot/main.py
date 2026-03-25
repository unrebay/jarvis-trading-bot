"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education (ICT/SMC)

v3.2 — Daily learning reminders:
- DailyReminder: finds users inactive > 22h and sends personalized nudges
- PTB JobQueue: runs every day at 09:00 UTC (run_daily)
- Personalized: shows next topic, level, XP from user_memory
- 6 rotating message templates to avoid repetition
- Graceful 403/400 handling (blocked bots)

v3.1 — Educational images + /stats admin dashboard:
- generate_lesson_images.py: 21 ICT/SMC matplotlib diagrams (dark theme #131722)
- Uploaded to Supabase Storage bucket "lesson-images"
- /example [CONCEPT] → returns static diagram from lesson_images table
- /stats → admin analytics (users, lessons, quizzes, top topics)
- mentor.md: bot no longer says "не могу создавать картинки"

v3.0 — /example command + focus_concept in chart annotation:
- handle_example: fetches lesson_images table → reply_photo
- get_lesson_image() in LessonManager — topic/concept_type ILIKE lookup

v2.7 — RAG level-aware semantic search:
- RAGSearch full rewrite: pgvector (match_knowledge_documents RPC) + keyword fallback
- Level filter: _levels_up_to(level) → difficulty_level IN (allowed_levels)
- quiz_results and lesson_requests tables wired into handlers

v2.5 — Live charts + Education system:
- ChartGenerator: live OHLCV charts via yfinance + mplfinance (dark theme)
- LessonManager: /lesson /quiz /progress structured ICT/SMC curriculum
- /quiz → native Telegram QUIZ polls (auto-checks answer + explanation)
- /watch → user watchlist + TradingView webhook alert integration

v2.4 — Persistent student memory (UserMemory, Supabase, every 5 msgs)
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

claude: ClaudeClient = ClaudeClient(enable_caching=True)
supabase: Client     = create_client(SUPABASE_URL, SUPABASE_KEY)

rag     = RAGSearch(supabase)
handler = TelegramHandler(claude, supabase, rag)

# ──────────────────────────────────────────────────────────────────────────────
# JobQueue callback — daily reminder (09:00 UTC every day)
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
        # Wrapped in try/except: if APScheduler is missing or JobQueue is None,
        # bot starts normally — reminders just won't fire (non-fatal degradation).
        try:
            if self.application.job_queue is not None:
                self.application.job_queue.run_daily(
                    _daily_reminder_job,
                    time = dt_time(hour=9, minute=0, tzinfo=timezone.utc),
                    name = "daily_reminders",
                )
                print("   ✅ DailyReminder registered (09:00 UTC)")
            else:
                print("   ⚠️  JobQueue not available — reminders disabled (install APScheduler)")
        except Exception as e:
            print(f"   ⚠️  DailyReminder setup failed (non-fatal): {e}")

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
