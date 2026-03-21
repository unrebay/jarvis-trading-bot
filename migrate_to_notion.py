#!/usr/bin/env python3
"""
Миграция контента из txt файлов в Notion
Использует Notion API для создания структуры курса DT Trading
"""

import os
import json
from notion_client import Client

# Настройки
NOTION_API_KEY = "NOTION_TOKEN_REMOVED"
NOTION_PAGE_ID = "32a76cda92398031b1d7e241886ee996"  # ID из ссылки

# Путь к материалам
MATERIALS_PATH = "/Users/andy/personal/Trading/trading-theory"

# Инициализация Notion клиента
notion = Client(auth=NOTION_API_KEY)

# Структура курса
COURSE_STRUCTURE = {
    "BEGINNERS": {
        "description": "Основные концепции для начинающих",
        "topics": {
            "first-steps": "First Steps",
            "terminology": "Terminology",
            "instruments": "Instruments",
        }
    },
    "PRINCIPLES": {
        "description": "Основные принципы торговли по курсу DT",
        "topics": {
            "structure-and-liquidity": "Structure and Liquidity",
            "block-types": "Block Types",
            "inefficiency-types": "Inefficiency Types",
            "order-flow-analysis": "Order Flow Analysis",
            "tda-and-entry-models": "TDA and Entry Models",
        }
    },
    "MARKET-MECHANICS": {
        "description": "Механика работы рынка",
        "topics": {
            "sessions": "Trading Sessions",
            "timings": "Market Timings",
            "channels": "Channels",
        }
    },
    "TRADING-PSYCHOLOGY": {
        "description": "Психология и дисциплина в торговле",
        "topics": {
            "discipline": "Discipline",
            "emotions": "Emotions",
            "technical-psychology": "Technical Psychology",
        }
    },
    "RISK-MANAGEMENT": {
        "description": "Управление рисками",
        "topics": {
            "risk-management": "Risk Management",
            "backtest": "Backtesting",
        }
    }
}

def load_txt_content(filename):
    """Загружает контент из txt файла"""
    try:
        # Ищем файл в папке trading-theory
        for root, dirs, files in os.walk(MATERIALS_PATH):
            for file in files:
                if file == f"{filename}.txt":
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        return f.read()
    except Exception as e:
        print(f"⚠️ Ошибка при чтении {filename}: {e}")
    return None

def split_long_text(text, max_length=1800):
    """Разбивает длинный текст на части"""
    if len(text) <= max_length:
        return [text]

    sentences = text.replace('.\n', '.|||').split('|||')
    parts = []
    current_part = ""

    for sentence in sentences:
        if len(current_part) + len(sentence) + 1 <= max_length:
            current_part += sentence + "\n"
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = sentence + "\n"

    if current_part:
        parts.append(current_part.strip())

    return parts if parts else [text]

def create_notion_page(parent_id, title, content, icon=None):
    """Создает страницу в Notion с красивым форматированием"""
    try:
        import re
        children = []

        if not content:
            content = "Контент будет добавлен позже."

        # Разбиваем контент на блоки
        blocks = content.split('\n\n')

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Проверяем если это ссылка на Notion (📌 *Title*)
            if block.startswith('📌'):
                # Извлекаем заголовок и ссылку
                match = re.match(r'📌 \*(.*?)\*', block)
                if match:
                    # Добавляем заголовок
                    title_text = match.group(1)[:200]  # Ограничиваем 200 символами для безопасности
                    children.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": title_text}}]
                        }
                    })
                    continue

            # Проверяем если это ссылка ([Открыть](url))
            if block.startswith('[') and '](' in block:
                # Это ссылка, добавляем как параграф
                link_text = "🔗 Открыть материал на Notion"
                url_match = re.search(r'\]\((https://[^\)]+)\)', block)
                if url_match:
                    url = url_match.group(1)
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {
                                    "content": link_text,
                                    "link": {"url": url}
                                }
                            }]
                        }
                    })
                continue

            # Обычный текст - ВСЕГДА разбиваем если больше 1800
            if len(block) > 1800:
                text_parts = split_long_text(block)
                for part in text_parts:
                    if part and len(part) <= 2000:  # Двойная проверка
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": part}}]
                            }
                        })
            else:
                # Финальная проверка перед добавлением
                if len(block) <= 2000:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": block}}]
                        }
                    })

        page = notion.pages.create(
            parent={"page_id": parent_id},
            properties={
                "title": [{"type": "text", "text": {"content": title}}]
            },
            children=children if children else None
        )

        return page['id']
    except Exception as e:
        print(f"❌ Ошибка создания страницы '{title}': {e}")
        return None

def migrate_course():
    """Главная функция миграции"""
    print(f"🚀 Начинаю миграцию контента в Notion...")
    print(f"📍 Base Page ID: {NOTION_PAGE_ID}\n")

    try:
        # Получаем информацию о базовой странице
        base_page = notion.pages.retrieve(NOTION_PAGE_ID)
        print(f"✅ Подключение к Notion успешно!\n")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("Проверьте API ключ и Page ID")
        return

    # Создаем разделы курса
    for section_name, section_info in COURSE_STRUCTURE.items():
        print(f"\n📚 Создаю раздел: {section_name}")
        print(f"   Описание: {section_info['description']}")

        # Создаем страницу раздела
        section_page_id = create_notion_page(
            NOTION_PAGE_ID,
            section_name,
            section_info['description'],
            icon="📚"
        )

        if not section_page_id:
            continue

        print(f"   ✅ Раздел создан (ID: {section_page_id})\n")

        # Создаем страницы для каждой темы в разделе
        for file_key, topic_name in section_info['topics'].items():
            print(f"   📄 Создаю тему: {topic_name}")

            # Загружаем контент
            content = load_txt_content(file_key)

            if content:
                topic_page_id = create_notion_page(
                    section_page_id,
                    topic_name,
                    content
                )
                if topic_page_id:
                    print(f"      ✅ Тема создана с контентом\n")
                else:
                    print(f"      ⚠️ Тема создана без контента\n")
            else:
                # Создаем пустую страницу если контента нет
                topic_page_id = create_notion_page(
                    section_page_id,
                    topic_name,
                    "Контент будет добавлен позже."
                )
                print(f"      ⚠️ Контент не найден для {file_key}\n")

    print("\n" + "="*50)
    print("✅ МИГРАЦИЯ ЗАВЕРШЕНА!")
    print("="*50)
    print(f"\nОткройте свой Notion по ссылке:")
    print(f"https://www.notion.so/unrebay/DT-trading-32a76cda92398031b1d7e241886ee996")
    print(f"\nВсе разделы и темы созданы и заполнены контентом.")

if __name__ == "__main__":
    migrate_course()
