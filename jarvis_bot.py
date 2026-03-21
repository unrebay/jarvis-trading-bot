"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education
Голос Джарвиса, стиль: рассудительный, решительный, профессиональный
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from anthropic import Anthropic

# Load environment
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize Claude client
claude_client = Anthropic()

# User states
USER_DATA = {}

# JARVIS System Prompt
JARVIS_SYSTEM_PROMPT = """Ты — ДЖАРВИС, профессиональный преподаватель торговли и инвестиций.

ХАРАКТЕР И СТИЛЬ:
- Рассудительный: аналитический, методичный, всё взвешиваешь
- Решительный: ясные, конкретные рекомендации, без размытостей
- Профессиональный: используешь торговые термины, объясняешь их
- Полезный: фокусируешься на практическом применении знаний
- Помощник: помогаешь становиться лучше в торговле

ЯЗЫК:
- Русский основной язык
- Английские термины с переводом в скобках: "восходящий тренд (uptrend)"
- Четкие объяснения, структурированные ответы

СИСТЕМА ОБУЧЕНИЯ (5 УРОВНЕЙ):
1. Beginner (Новичок): Основы, без сложностей, с примерами
2. Elementary (Начинающий): Базовые стратегии, простые анализы
3. Intermediate (Средний): Продвинутые паттерны, управление рисками
4. Advanced (Продвинутый): Комплексные стратегии, психология
5. Professional (Профессионал): Экспертные техники, системное мышление

Помни: Твоя цель — сделать ученика лучше в торговле.
"""


class JarvisBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("level", self.set_level_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "level": "Intermediate",
                "conversations": [],
                "created_at": datetime.now().isoformat(),
                "stats": {"messages_count": 0}
            }

        welcome_message = """🎩 *JARVIS - Профессиональный учитель торговли*

Здравствуйте, сэр. Я JARVIS, ваш персональный преподаватель торговли и инвестиций.

*Мои возможности:*
✦ Объяснение торговых стратегий (5 уровней сложности)
✦ Анализ графиков и паттернов
✦ Помощь в развитии торговой психологии

*Команды:*
/level - выбрать уровень обучения
/help - справка
/stats - ваш прогресс

Прошу начнём. О чём бы вы хотели узнать?"""

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """*Справка по JARVIS*

*Команды:*
/level - выбрать уровень (Beginner до Professional)
/stats - показать прогресс
/help - эта справка

Просто пишите вопросы - я отвечу в соответствии с вашим уровнем!"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_text = update.message.text

        if user_id not in USER_DATA:
            USER_DATA[user_id] = {
                "level": "Intermediate",
                "conversations": [],
                "created_at": datetime.now().isoformat(),
                "stats": {"messages_count": 0}
            }

        user = USER_DATA[user_id]
        user["stats"]["messages_count"] += 1

        system_message = f"{JARVIS_SYSTEM_PROMPT}\n\nТекущий уровень ученика: {user['level']}"
        messages = [{"role": "user", "content": user_text}]

        try:
            response = claude_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_message,
                messages=messages
            )

            assistant_response = response.content[0].text
            user["conversations"].append({"user": user_text, "assistant": assistant_response, "timestamp": datetime.now().isoformat()})

            await update.message.reply_text(assistant_response, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

    async def set_level_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        levels = ["Beginner", "Elementary", "Intermediate", "Advanced", "Professional"]

        if not context.args:
            level_text = "Выберите уровень:\n"
            for level in levels:
                level_text += f"• {level}\n"
            await update.message.reply_text(level_text)
            return

        requested_level = context.args[0].capitalize()
        if requested_level in levels:
            if user_id not in USER_DATA:
                USER_DATA[user_id] = {"level": requested_level, "conversations": [], "created_at": datetime.now().isoformat(), "stats": {"messages_count": 0}}
            else:
                USER_DATA[user_id]["level"] = requested_level
            await update.message.reply_text(f"✓ Уровень установлен: *{requested_level}*", parse_mode="Markdown")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in USER_DATA:
            await update.message.reply_text("Нет данных. Начните с /start")
            return

        user = USER_DATA[user_id]
        stats_text = f"""📊 *Ваша статистика*

Уровень: *{user['level']}*
Всего сообщений: {user['stats']['messages_count']}
Дней обучения: {(datetime.now() - datetime.fromisoformat(user['created_at'])).days}

Продолжайте учиться! 💪"""

        await update.message.reply_text(stats_text, parse_mode="Markdown")

    def run(self):
        print("🤖 JARVIS Bot starting...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = JarvisBot()
    bot.run()
