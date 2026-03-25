"""
reminders.py — Ежедневные напоминания об обучении (v1.0)

Запускается раз в сутки через PTB JobQueue (9:00 UTC).
Находит пользователей, неактивных > 22 часов, и отправляет
персонализированное напоминание продолжить учёбу.

Логика:
  1. Получить всех пользователей из bot_users
  2. Для каждого — найти дату последнего сообщения в conversations
  3. Если > INACTIVE_HOURS — собрать персональное сообщение и отправить
  4. 403/400 (бот заблокирован / чат не найден) — пропустить тихо
"""

import random
from datetime import datetime, timezone, timedelta
from supabase import Client

from .user_memory import UserMemory
from .lesson_manager import CURRICULUM


# ── Шаблоны напоминаний (ротируются случайно) ─────────────────────────────────

REMINDER_TEMPLATES = [
    (
        "📚 Привет! Давно не виделись.\n\n"
        "Следующая тема по программе: *{next_topic}*\n"
        "Уровень: {level} · XP: {xp}\n\n"
        "→ /lesson {next_topic}"
    ),
    (
        "🎯 Маленькое напоминание!\n\n"
        "Ты на уровне *{level}* и набрал *{xp} XP*.\n"
        "Продолжи с темы: *{next_topic}*\n\n"
        "→ /lesson {next_topic}"
    ),
    (
        "🔥 Рынок не ждёт!\n\n"
        "Твоя следующая тема: *{next_topic}*\n"
        "Уровень {level} · {xp} XP накоплено\n\n"
        "→ /lesson {next_topic}"
    ),
    (
        "💡 Лучшие трейдеры учатся каждый день.\n\n"
        "Продолжи с темы *{next_topic}* ({level})\n\n"
        "→ /lesson {next_topic}"
    ),
    (
        "⚡ Готов к новому уроку?\n\n"
        "*{next_topic}* — следующая тема программы {level}\n"
        "Уже {xp} XP — так держать!\n\n"
        "→ /lesson {next_topic}"
    ),
    (
        "📈 Привет! Не забывай про обучение.\n\n"
        "Осталось изучить: *{next_topic}*\n"
        "Твой прогресс: {level} · {xp} XP\n\n"
        "→ /lesson {next_topic}"
    ),
]

# Запасной шаблон — когда нет информации о следующей теме
REMINDER_GENERIC = (
    "📚 Привет! Давно не виделись.\n\n"
    "Зайди к JARVIS и продолжи изучение ICT/SMC!\n\n"
    "→ /lesson — следующий урок\n"
    "→ /progress — твой прогресс"
)


# ── DailyReminder ──────────────────────────────────────────────────────────────

class DailyReminder:
    """
    Sends daily learning nudges to users who haven't been active for a while.

    Usage (called from PTB JobQueue callback):
        reminder = DailyReminder(supabase, user_memory)
        await reminder.send_reminders(context.bot)
    """

    # Remind users inactive for at least this many hours
    INACTIVE_HOURS: int = 22

    def __init__(self, supabase: Client, user_memory: UserMemory) -> None:
        self.supabase     = supabase
        self.user_memory  = user_memory

    # ── Public API ─────────────────────────────────────────────────────────────

    async def send_reminders(self, bot) -> int:
        """
        Main entry point — scans all users, sends reminders to inactive ones.
        Returns the number of messages successfully sent.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.INACTIVE_HOURS)

        try:
            users_res = self.supabase.table("bot_users").select(
                "telegram_id, level"
            ).execute()
            users = users_res.data or []
        except Exception as e:
            print(f"⚠️  Reminders: failed to load users: {e}")
            return 0

        sent = 0
        skipped = 0

        for user in users:
            telegram_id = user.get("telegram_id")
            if not telegram_id:
                continue

            try:
                active = self._was_active_after(telegram_id, cutoff)
                if active:
                    skipped += 1
                    continue

                text = self._build_message(
                    telegram_id,
                    user.get("level", "Beginner"),
                )

                await bot.send_message(
                    chat_id    = telegram_id,
                    text       = text,
                    parse_mode = "Markdown",
                )
                sent += 1

            except Exception as e:
                err = str(e)
                # 403 = bot blocked by user, 400 = chat not found — not an error
                if any(code in err for code in ("403", "400", "Forbidden", "chat not found")):
                    continue
                print(f"⚠️  Reminder error (user {telegram_id}): {e}")

        print(f"📬 Daily reminders: {sent} sent, {skipped} active (skipped), total {len(users)}")
        return sent

    # ── Private helpers ────────────────────────────────────────────────────────

    def _was_active_after(self, telegram_id: int, cutoff: datetime) -> bool:
        """
        Return True if the user sent any message after `cutoff`.
        Queries the conversations table for their latest message timestamp.
        Returns True (treat as active) on query errors to avoid spam.
        """
        try:
            res = self.supabase.table("conversations").select(
                "created_at"
            ).eq(
                "user_id", telegram_id
            ).order(
                "created_at", desc=True
            ).limit(1).execute()

            data = res.data or []
            if not data:
                # No messages at all — new user, don't bother
                return True

            last_str = data[0]["created_at"]
            last_dt  = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
            return last_dt >= cutoff

        except Exception as e:
            print(f"⚠️  Reminder: activity check failed for {telegram_id}: {e}")
            return True  # Safer: treat as active on error

    def _build_message(self, telegram_id: int, level: str) -> str:
        """
        Build a personalized reminder message.
        Uses user_memory to find next unread topic + XP.
        Falls back to generic message on any error.
        """
        try:
            memory   = self.user_memory.load(telegram_id)
            learning = memory.get("learning", {})
            xp       = learning.get("xp", 0)
            known    = learning.get("topics_known", [])

            # Find first unread topic in current level's curriculum
            next_topic = self._find_next_topic(level, known)

            if next_topic:
                template = random.choice(REMINDER_TEMPLATES)
                return template.format(
                    next_topic = next_topic,
                    level      = level,
                    xp         = xp,
                )
        except Exception as e:
            print(f"⚠️  Reminder: message build error for {telegram_id}: {e}")

        return REMINDER_GENERIC

    @staticmethod
    def _find_next_topic(level: str, known_topics: list) -> str | None:
        """Return first curriculum topic not yet studied at given level."""
        curriculum  = CURRICULUM.get(level, CURRICULUM.get("Beginner", []))
        known_lower = [k.lower() for k in known_topics]
        for topic in curriculum:
            already = any(
                topic.lower() in k or k in topic.lower()
                for k in known_lower
            )
            if not already:
                return topic
        return None
