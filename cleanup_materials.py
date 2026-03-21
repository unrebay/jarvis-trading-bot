#!/usr/bin/env python3
"""
Очистка и переформатирование txt файлов из Discord экспортов
Убирает мусор (реакции, разделители, видео) и оставляет только полезный контент
"""

import os
import re
from pathlib import Path

MATERIALS_PATH = "/Users/andy/personal/Trading/trading-theory"

def clean_discord_content(content):
    """Очищает контент от Discord мусора и переформатирует его красиво"""
    lines = content.split('\n')
    cleaned_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        # Пропускаем разделители
        if line.startswith('='):
            continue

        # Пропускаем информацию о гильдии/канале
        if line.startswith('Guild:') or line.startswith('Channel:'):
            continue

        # Пропускаем даты и авторов ([02.11.2025 16:37] education.dt)
        if re.match(r'^\[\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\]', line):
            continue

        # Пропускаем {Embed}, {Reactions}, {Attachments}
        if line.strip().startswith('{') and line.strip().endswith('}'):
            skip_next = True
            continue

        # Пропускаем реакции эмодзи (❤️ (11) 🤝 ✅ (5))
        if re.match(r'^[❤️🤝✅🥉💚🎉👍💪]*\s*\(\d+\)', line):
            continue

        # Пропускаем Discord ссылки на видео и изображения
        if 'cdn.discordapp.com' in line or 'discordapp.net' in line:
            continue

        # Пропускаем "Exported X message(s)"
        if 'Exported' in line and 'message' in line:
            continue

        # Обрабатываем Notion ссылки - форматируем как "📌 [Название](ссылка)"
        if line.strip().startswith('[') and '](https://silk-seahorse' in line:
            # Извлекаем название и ссылку
            match = re.match(r'\[(.*?)\]\((https://silk-seahorse[^\)]+)\)', line.strip())
            if match:
                title = match.group(1)
                url = match.group(2)
                cleaned_lines.append('')  # Пустая строка перед заголовком
                cleaned_lines.append(f'📌 *{title}*')
                cleaned_lines.append(f'[Открыть в Notion]({url})')
                continue

        # Оставляем обычный контент (описания Notion и остальное)
        if line.strip():  # Только если не пустая строка
            cleaned_lines.append(line.strip())
        else:
            # Сохраняем пустые строки для читаемости (но не более одной подряд)
            if cleaned_lines and cleaned_lines[-1] != '':
                cleaned_lines.append('')

    # Финальная очистка - убираем множественные пустые строки
    result = []
    prev_empty = False
    for line in cleaned_lines:
        if line == '':
            if not prev_empty:
                result.append(line)
                prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return '\n'.join(result).strip()

def process_txt_files(materials_path):
    """Обрабатывает все txt файлы в папке"""
    materials_path = Path(materials_path)

    if not materials_path.exists():
        print(f"❌ Папка не найдена: {materials_path}")
        return

    txt_files = list(materials_path.glob('*.txt'))

    if not txt_files:
        print(f"⚠️ Txt файлы не найдены в {materials_path}")
        return

    print(f"🧹 Начинаю очистку {len(txt_files)} файлов...\n")

    for file_path in sorted(txt_files):
        print(f"📄 Обрабатываю: {file_path.name}")

        try:
            # Читаем оригинальный файл
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Очищаем контент
            cleaned_content = clean_discord_content(original_content)

            # Сохраняем обратно
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            # Показываем статистику
            original_lines = len(original_content.split('\n'))
            cleaned_lines = len(cleaned_content.split('\n'))
            reduction = ((original_lines - cleaned_lines) / original_lines * 100) if original_lines > 0 else 0

            print(f"   ✅ Очищено: {original_lines} → {cleaned_lines} строк (-{reduction:.0f}%)\n")

        except Exception as e:
            print(f"   ❌ Ошибка: {e}\n")

    print("=" * 60)
    print("✅ ВСЕ ФАЙЛЫ ОЧИЩЕНЫ!")
    print("=" * 60)
    print("\nТеперь запусти миграцию снова:")
    print("python3 migrate_to_notion.py")

if __name__ == "__main__":
    process_txt_files(MATERIALS_PATH)
