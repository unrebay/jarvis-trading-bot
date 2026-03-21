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
        # Используем абсолютный путь для корректной работы на Railway
        base_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_base_path = os.path.join(base_dir, 'knowledge_base.json')
        with open(knowledge_base_path, "r", encoding="utf-8") as f:
            KNOWLEDGE_BASE = json.load(f)
            print(f"✅ База знаний загружена: {KNOWLEDGE_BASE.get('total_documents', 0)} документов")
    except FileNotFoundError as e:
        print(f"⚠️  knowledge_base.json не найден ({e}). Используем базовый режим.")
        KNOWLEDGE_BASE = {"sources": {"discord": [], "txt": [], "notion": []}, "total_documents": 0}

# Функция полнотекстового поиска по базе знаний
def search_knowledge_base(query: str, limit: int = 3) -> str:
    """Ищет релевантные материалы из базы знаний по содержимому (RAG)"""
    if not KNOWLEDGE_BASE.get("sources"):
        return ""

    query_lower = query.lower()
    # Разбиваем на слова, убираем короткие стоп-слова
    keywords = [w for w in query_lower.split() if len(w) > 2]
    if not keywords:
        return ""

    results = []

    # Полнотекстовый поиск по markdown-документам (основная база)
    for doc in KNOWLEDGE_BASE["sources"].get("markdown", []):
        content = doc.get("content", "").lower()
        title = doc.get("title", "").lower()
        headings = " ".join(doc.get("headings", [])).lower()
        topic = doc.get("topic", "").lower()

        # Считаем вхождения каждого ключевого слова
        score = 0
        for kw in keywords:
            # Заголовок и тема дают больший вес
            score += title.count(kw) * 5
            score += headings.count(kw) * 3
            score += topic.count(kw) * 4
            score += content.count(kw)

        if score > 0:
            # Находим релевантный фрагмент текста для контекста
            snippet = _extract_snippet(doc.get("content", ""), keywords)
            results.append({
                "title": doc.get("title", doc.get("filename", "")),
                "section": doc.get("section", ""),
                "score": score,
                "snippet": snippet,
                "full_content": doc.get("content", "")
            })

    # Сортируем по релевантности и берём топ
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:limit]

    if not top_results:
        return ""

    # Формируем контекст с фрагментами текста для Claude
    context = "\n--- МАТЕРИАЛЫ ИЗ БАЗЫ ЗНАНИЙ DT КУРСА ---\n"
    for result in top_results:
        context += f"\n📚 *{result['title']}* [{result['section']}]\n"
        context += result['snippet'] + "\n"

    context += "\n--- КОНЕЦ МАТЕРИАЛОВ ---\n"
    return context


def _extract_snippet(content: str, keywords: list, max_length: int = 600) -> str:
    """Извлекает наиболее релевантный фрагмент текста"""
    lines = content.split('\n')
    best_score = 0
    best_start = 0

    # Ищем лучший блок из 5 строк
    window = 5
    for i in range(len(lines)):
        chunk = ' '.join(lines[i:i+window]).lower()
        score = sum(chunk.count(kw) for kw in keywords)
        if score > best_score:
            best_score = score
            best_start = i

    # Берём блок вокруг лучшего места
    start = max(0, best_start - 1)
    end = min(len(lines), best_start + window + 2)
    snippet = '\n'.join(lines[start:end]).strip()

    # Обрезаем если слишком длинный
    if len(snippet) > max_length:
        snippet = snippet[:max_length] + "..."

    return snippet if snippet else content[:max_length]

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

РАБОТА С БАЗОЙ ЗНАНИЙ:
Если в контексте есть материалы из курса DT — используй их как первоисточник.
Объясняй своими словами, но основывайся на этих материалах.
Если вопрос выходит за рамки материалов — отвечай как профессиональный ICT/SMC трейдер.
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
        if knowledge_context:
            kb_section = f"""
ВАЖНО: Ниже — реальные материалы из курса DT Trading. Используй их как основу ответа, отвечай строго по этим материалам. Если материалы содержат нужную информацию — цитируй их суть, не придумывай от себя.

{knowledge_context}"""
        else:
            kb_section = "\nОтвечай на основе общих знаний о торговле в стиле Smart Money / ICT концепта."

        system_message = f"""{JARVIS_SYSTEM_PROMPT}{kb_section}

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
