"""
JARVIS - Trading Education Bot
Professional AI teacher for trading education
Голос Джарвиса, стиль: рассудительный, решительный, профессиональный

v2.0 — Supabase persistent storage + conversation history
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from anthropic import Anthropic
from supabase import create_client, Client

# ──────────────────────────────────────────────────────────────────────────────
# Инициализация
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

TELEGRAM_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN")
CLAUDE_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_ANON_KEY")

claude_client   = Anthropic(api_key=CLAUDE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# База знаний (локальный JSON — пока не перенесли в Supabase векторы)
# ──────────────────────────────────────────────────────────────────────────────

KNOWLEDGE_BASE = {}

def load_knowledge_base():
    global KNOWLEDGE_BASE
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "knowledge_base.json")
        with open(path, "r", encoding="utf-8") as f:
            KNOWLEDGE_BASE = json.load(f)
            print(f"✅ База знаний загружена: {KNOWLEDGE_BASE.get('total_documents', 0)} документов")
    except FileNotFoundError:
        print("⚠️  knowledge_base.json не найден. Базовый режим.")
        KNOWLEDGE_BASE = {"sources": {}, "total_documents": 0}


def search_knowledge_base(query: str, limit: int = 3) -> str:
    if not KNOWLEDGE_BASE.get("sources"):
        return ""

    query_lower = query.lower()
    keywords = [w for w in query_lower.split() if len(w) > 2]
    if not keywords:
        return ""

    results = []
    for doc in KNOWLEDGE_BASE["sources"].get("markdown", []):
        content  = doc.get("content", "").lower()
        title    = doc.get("title", "").lower()
        headings = " ".join(doc.get("headings", [])).lower()
        topic    = doc.get("topic", "").lower()

        score = 0
        for kw in keywords:
            score += title.count(kw) * 5
            score += headings.count(kw) * 3
            score += topic.count(kw) * 4
            score += content.count(kw)

        if score > 0:
            snippet = _extract_snippet(doc.get("content", ""), keywords)
            results.append({
                "title":    doc.get("title", doc.get("filename", "")),
                "section":  doc.get("section", ""),
                "score":    score,
                "snippet":  snippet,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:limit]
    if not top:
        return ""

    ctx = "\n--- МАТЕРИАЛЫ ИЗ БАЗЫ ЗНАНИЙ DT КУРСА ---\n"
    for r in top:
        ctx += f"\n📚 *{r['title']}* [{r['section']}]\n{r['snippet']}\n"
    ctx += "\n--- КОНЕЦ МАТЕРИАЛОВ ---\n"
    return ctx


def _extract_snippet(content: str, keywords: list, max_length: int = 600) -> str:
    lines = content.split("\n")
    best_score, best_start = 0, 0
    window = 5
    for i in range(len(lines)):
        chunk = " ".join(lines[i:i+window]).lower()
        score = sum(chunk.count(kw) for kw in keywords)
        if score > best_score:
            best_score, best_start = score, i

    start   = max(0, best_start - 1)
    end     = min(len(lines), best_start + window + 2)
    snippet = "\n".join(lines[start:end]).strip()
    if len(snippet) > max_length:
        snippet = snippet[:max_length] + "..."
    return snippet or content[:max_length]

# ──────────────────────────────────────────────────────────────────────────────
# Supabase helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_or_create_user(telegram_id: int, username: str = None) -> dict:
    """Возвращает пользователя из БД, создаёт если не существует."""
    res = supabase.table("bot_users")\
        .select("*")\
        .eq("telegram_id", telegram_id)\
        .execute()

    if res.data:
        return res.data[0]

    new_user = {
        "telegram_id":    telegram_id,
        "username":       username,
        "level":          "Intermediate",
        "messages_count": 0,
    }
    ins = supabase.table("bot_users").insert(new_user).execute()
    return ins.data[0]


def increment_messages(telegram_id: int, current_count: int):
    supabase.table("bot_users")\
        .update({"messages_count": current_count + 1})\
        .eq("telegram_id", telegram_id)\
        .execute()


def set_user_level(telegram_id: int, level: str):
    supabase.table("bot_users")\
        .update({"level": level})\
        .eq("telegram_id", telegram_id)\
        .execute()


def save_message(telegram_id: int, role: str, content: str):
    supabase.table("conversations").insert({
        "user_id": telegram_id,
        "role":    role,
        "content": content,
    }).execute()


def get_history(telegram_id: int, limit: int = 10) -> list[dict]:
    """Возвращает последние N сообщений (пары user/assistant) для контекста Claude."""
    res = supabase.table("conversations")\
        .select("role, content")\
        .eq("user_id", telegram_id)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()

    # Разворачиваем — supabase вернул в порядке убывания
    return list(reversed(res.data)) if res.data else []

# ──────────────────────────────────────────────────────────────────────────────
# JARVIS System Prompt
# ──────────────────────────────────────────────────────────────────────────────

JARVIS_SYSTEM_PROMPT = """Ты — ДЖАРВИС, профессиональный преподаватель торговли и инвестиций.

ХАРАКТЕР И СТИЛЬ:
- Рассудительный: аналитический, методичный, всё взвешиваешь
- Решительный: ясные, конкретные рекомендации, без размытостей
- Профессиональный: используешь торговые термины, объясняешь их
- Полезный: фокусируешься на практическом применении знаний

ЯЗЫК:
- Русский основной язык
- Английские термины с переводом в скобках: "восходящий тренд (uptrend)"

СИСТЕМА ОБУЧЕНИЯ (5 УРОВНЕЙ):
1. Beginner (Новичок): Основы, без сложностей, с примерами
2. Elementary (Начинающий): Базовые стратегии, простые анализы
3. Intermediate (Средний): Продвинутые паттерны, управление рисками
4. Advanced (Продвинутый): Комплексные стратегии, психология
5. Professional (Профессионал): Экспертные техники, системное мышление

ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
ЗАПРЕЩЕНО:
- НЕ используй # ## ### (хеши)
- НЕ используй --- ___ === (разделители)
- НЕ используй > (цитирование)
- НЕ используй ``` (блоки кода)

ИСПОЛЬЗУЙ ТОЛЬКО:
- *жирный текст* — для заголовков и ключевых концепций
- __подчеркивание__ — для особо важной информации
- • список — пули для списков (символ •, не -)
- `код` — только для технических терминов в одну строку
- Пустые строки между параграфами

РАБОТА С БАЗОЙ ЗНАНИЙ:
Если в контексте есть материалы из курса DT — используй их как первоисточник.
Объясняй своими словами, но основывайся на этих материалах.
Если вопрос выходит за рамки материалов — отвечай как профессиональный ICT/SMC трейдер.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Telegram Bot handlers
# ──────────────────────────────────────────────────────────────────────────────

class JarvisBot:
    def __init__(self):
        load_knowledge_base()
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start",  self.start_command))
        self.application.add_handler(CommandHandler("help",   self.help_command))
        self.application.add_handler(CommandHandler("level",  self.set_level_command))
        self.application.add_handler(CommandHandler("stats",  self.stats_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    # ── /start ────────────────────────────────────────────────────────────────

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user     = update.effective_user
        db_user  = get_or_create_user(user.id, user.username)

        welcome = """🎩 *JARVIS — Профессиональный учитель торговли*

Здравствуйте, сэр. Я JARVIS, ваш персональный преподаватель торговли.

*Возможности:*
✦ Объяснение торговых стратегий (5 уровней сложности)
✦ Анализ паттернов ICT / Smart Money
✦ Помощь в развитии торговой психологии

*Команды:*
/level — выбрать уровень обучения
/stats — ваш прогресс
/help  — справка

Прошу начнём. О чём бы вы хотели узнать?"""

        await update.message.reply_text(welcome, parse_mode="Markdown")

    # ── /help ─────────────────────────────────────────────────────────────────

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Справка по JARVIS*\n\n"
            "/level — выбрать уровень (Beginner → Professional)\n"
            "/stats — показать прогресс\n"
            "/help  — эта справка\n\n"
            "Просто пишите вопросы — я отвечу по вашему уровню!",
            parse_mode="Markdown"
        )

    # ── /level ────────────────────────────────────────────────────────────────

    async def set_level_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        levels = ["Beginner", "Elementary", "Intermediate", "Advanced", "Professional"]
        user   = update.effective_user

        if not context.args:
            text = "*Выберите уровень:*\n\n"
            text += "\n".join(f"• {l}" for l in levels)
            text += "\n\nПример: /level Intermediate"
            await update.message.reply_text(text, parse_mode="Markdown")
            return

        requested = context.args[0].capitalize()
        if requested in levels:
            get_or_create_user(user.id, user.username)
            set_user_level(user.id, requested)
            await update.message.reply_text(
                f"✓ Уровень установлен: *{requested}*", parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"Уровень «{requested}» не найден. Доступны: {', '.join(levels)}"
            )

    # ── /stats ────────────────────────────────────────────────────────────────

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user    = update.effective_user
        db_user = get_or_create_user(user.id, user.username)

        created = datetime.fromisoformat(db_user["created_at"].replace("Z", "+00:00"))
        days    = (datetime.now(created.tzinfo) - created).days

        await update.message.reply_text(
            f"📊 *Ваша статистика*\n\n"
            f"Уровень: *{db_user['level']}*\n"
            f"Всего сообщений: {db_user['messages_count']}\n"
            f"Дней обучения: {days}\n\n"
            f"Продолжайте учиться! 💪",
            parse_mode="Markdown"
        )

    # ── Основной обработчик сообщений ─────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user      = update.effective_user
        user_text = update.message.text

        # Получаем / создаём пользователя в Supabase
        db_user = get_or_create_user(user.id, user.username)
        increment_messages(user.id, db_user["messages_count"])

        # RAG поиск по локальной базе знаний
        knowledge_context = search_knowledge_base(user_text)

        if knowledge_context:
            kb_section = (
                "\nВАЖНО: Ниже — реальные материалы из курса DT Trading. "
                "Используй их как основу ответа.\n"
                + knowledge_context
            )
        else:
            kb_section = "\nОтвечай на основе общих знаний о Smart Money / ICT концепте."

        system_message = (
            f"{JARVIS_SYSTEM_PROMPT}{kb_section}\n\n"
            f"Текущий уровень ученика: {db_user['level']}"
        )

        # Загружаем историю из Supabase (последние 10 сообщений = 5 пар)
        history  = get_history(user.id, limit=10)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": user_text})

        try:
            response = claude_client.messages.create(
                model      = "claude-haiku-4-5-20251001",
                max_tokens = 1024,
                system     = system_message,
                messages   = messages,
            )
            assistant_response = response.content[0].text

            # Сохраняем оба сообщения в Supabase
            save_message(user.id, "user",      user_text)
            save_message(user.id, "assistant", assistant_response)

            await update.message.reply_text(assistant_response, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

    # ── Запуск ────────────────────────────────────────────────────────────────

    def run(self):
        print("🤖 JARVIS Bot v2.0 starting (Supabase mode)...")
        self.application.run_polling()


if __name__ == "__main__":
    bot = JarvisBot()
    bot.run()
