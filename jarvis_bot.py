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

# Load knowledge base
KNOWLEDGE_BASE = {}
def load_knowledge_base():
    """Загружает базу знаний из JSON"""
    global KNOWLEDGE_BASE
    try:
        with open("knowledge_base.json", "r", encoding="utf-8") as f:
            KNOWLEDGE_BASE = json.load(f)
            print(f"✅ База знаний загружена: {KNOWLEDGE_BASE.get('total_documents', 0)} документов")
    except FileNotFoundError:
        print("⚠️  knowledge_base.json не найден. Используем базовый режим.")
        KNOWLEDGE_BASE = {"sources": {"discord": [], "txt": [], "notion": []}, "total_documents": 0}

# Функция поиска релевантных материалов
def search_knowledge_base(query: str, limit: int = 3) -> str:
    """Ищет релевантные материалы из базы знаний по ключевым словам"""
    if not KNOWLEDGE_BASE.get("sources"):
        return ""

    query_lower = query.lower()
    keywords = query_lower.split()
    results = []

    # Ищем в txt файлах (теория)
    for doc in KNOWLEDGE_BASE["sources"].get("txt", []):
        filename = doc.get("filename", "").lower()
        topic = doc.get("topic", "").lower()

        # Проверяем совпадение ключевых слов с названием файла
        if any(keyword in filename or keyword in topic for keyword in keywords):
            results.append({
                "source": "теория",
                "filename": doc.get("filename", ""),
                "score": sum(1 for k in keywords if k in filename or k in topic)
            })

    # Ищем в Discord материалах
    for doc in KNOWLEDGE_BASE["sources"].get("discord", []):
        channel = doc.get("channel", "").lower()

        # Проверяем совпадение с названием канала
        if any(keyword in channel for keyword in keywords):
            results.append({
                "source": "Discord",
                "filename": doc.get("channel", ""),
                "score": sum(1 for k in keywords if k in channel)
            })

    # Сортируем по релевантности и берём топ
    results.sort(key=lambda x: x["score"], reverse=True)

    if not results:
        return ""

    # Форматируем результаты
    context = "\n*Релевантные материалы из базы знаний:*\n"
    for i, result in enumerate(results[:limit], 1):
        context += f"• {result['filename']} ({result['source']})\n"

    return context

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

ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM (КРИТИЧНО!):
ЗАПРЕЩЕНО абсолютно:
- НЕ используй # или ## или ### или любые хеши вообще
- НЕ используй --- или ___ или === (разделители)
- НЕ используй > (цитирование)
- НЕ используй ``` (блоки кода)
- НЕ используй markdown-стиль форматирование

ИСПОЛЬЗУЙ ТОЛЬКО ЭТО:
- *жирный текст* - ДЛЯ ЗАГОЛОВКОВ И КЛЮЧЕВЫХ КОНЦЕПЦИЙ
- __подчеркивание__ - ДЛЯ ОСОБО ВАЖНОЙ ИНФОРМАЦИИ
- • список - ПУЛИ для списков (символ •, не -)
- `код` - только для технических терминов в одну строку
- Пустые строки между парагра́фами для читаемости

СТРУКТУРА ОТВЕТА:
*Заголовок темы*

Основной текст объяснения. Будь четким и практичным.

• Пункт 1
• Пункт 2
• Пункт 3

*Практический пример:*
Конкретный пример как это применить в торговле.

Помни: НИКАКИХ #, ##, ###, ---, >, ``` СИМВОЛОВ!

Помни: Твоя цель — сделать ученика лучше в торговле.
"""


class JarvisBot:
    def __init__(self):
        load_knowledge_base()  # Загружаем базу знаний при старте
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

        # Ищем релевантные материалы из базы знаний
        knowledge_context = search_knowledge_base(user_text)

        # Составляем системный prompt с контекстом
        system_message = f"""{JARVIS_SYSTEM_PROMPT}

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{knowledge_context if knowledge_context else "Прямой ответ без дополнительных материалов."}

Текущий уровень ученика: {user['level']}"""

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
