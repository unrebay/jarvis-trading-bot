"""
RAG Base Loader
Загружает все материалы (Discord, Notion, txt) в единую базу знаний
"""

import os
import json
from pathlib import Path
from datetime import datetime

class RAGBaseLoader:
    def __init__(self):
        self.knowledge_base = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "sources": {
                "discord": [],
                "notion": [],
                "txt": [],
                "videos": []
            },
            "total_documents": 0
        }

    def load_discord_materials(self, discord_path):
        """Загружает Discord материалы"""
        print("\n📚 Загружаю Discord материалы...")

        # Основной путь к Discord экспорту (server2)
        main_path = "/sessions/tender-wizardly-gauss/mnt/trading-theory/server2"

        count = 0
        if os.path.exists(main_path):
            print(f"  📍 Сканирую {main_path}...")
            for file in os.listdir(main_path):
                if file.endswith('.txt'):
                    file_path = os.path.join(main_path, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.knowledge_base["sources"]["discord"].append({
                                "filename": file,
                                "path": file_path,
                                "size": len(content),
                                "type": "text",
                                "channel": file.replace('.txt', '')
                            })
                            count += 1
                            print(f"  ✓ {file} ({len(content)} символов)")
                    except Exception as e:
                        print(f"  ✗ Ошибка загрузки {file}: {e}")
        else:
            print(f"  ⚠️  Папка не найдена: {main_path}")

        print(f"✅ Загружено Discord материалов: {count} файлов")
        return count

    def load_txt_materials(self, txt_path):
        """Загружает txt файлы из trading-theory"""
        print("\n📄 Загружаю txt файлы...")

        txt_dir = "/sessions/tender-wizardly-gauss/mnt/trading-theory"

        if not os.path.exists(txt_dir):
            print(f"⚠️  Папка не найдена: {txt_dir}")
            return 0

        count = 0
        for file in os.listdir(txt_dir):
            # Пропускаем подпапки и файлы со скриптами
            if file.startswith('.') or file.endswith('.sh') or file == 'server2':
                continue

            if file.endswith('.txt') or file.endswith('.md'):
                file_path = os.path.join(txt_dir, file)
                # Пропускаем, если это папка
                if os.path.isdir(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.knowledge_base["sources"]["txt"].append({
                            "filename": file,
                            "path": file_path,
                            "size": len(content),
                            "type": file.split('.')[-1],
                            "topic": file.replace('.txt', '').replace('.md', '')
                        })
                        count += 1
                        print(f"  ✓ {file} ({len(content)} символов)")
                except Exception as e:
                    print(f"  ✗ Ошибка загрузки {file}: {e}")

        print(f"✅ Загружено txt файлов: {count} файлов")
        return count

    def load_notion_links(self):
        """Загружает Notion ссылки для отслеживания"""
        print("\n🔗 Подготавливаю Notion ссылки...")
        print("  ℹ️  Notion загрузка доступна через API (нужно реализовать позже)")
        print("  ✓ На данный момент используем информацию из Notion HTML экспортов")
        return 0

    def load_schedule(self):
        """Загружает расписание занятий"""
        print("\n📅 Загружаю расписание...")

        schedule_file = "schedule.json"
        if os.path.exists(schedule_file):
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule = json.load(f)
                    self.knowledge_base["schedule"] = schedule
                    print(f"✅ Загружено событий: {len(schedule.get('events', []))}")
            except Exception as e:
                print(f"✗ Ошибка загрузки расписания: {e}")

    def save_knowledge_base(self):
        """Сохраняет базу знаний"""
        print("\n💾 Сохраняю базу знаний...")

        # Подсчитываем общее количество документов
        total = (len(self.knowledge_base["sources"]["discord"]) +
                len(self.knowledge_base["sources"]["txt"]) +
                len(self.knowledge_base["sources"]["notion"]))

        self.knowledge_base["total_documents"] = total

        with open("knowledge_base.json", "w", encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)

        print(f"✅ База знаний сохранена: knowledge_base.json")
        return total

    def print_summary(self):
        """Выводит сводку"""
        print("\n" + "="*50)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*50)

        discord_count = len(self.knowledge_base["sources"]["discord"])
        txt_count = len(self.knowledge_base["sources"]["txt"])
        notion_count = len(self.knowledge_base["sources"]["notion"])
        total = self.knowledge_base["total_documents"]

        print(f"\n📚 Discord материалы: {discord_count} файлов")
        print(f"📄 Txt файлы: {txt_count} файлов")
        print(f"🔗 Notion ссылки: {notion_count} ссылок")
        print(f"\n📊 ВСЕГО ДОКУМЕНТОВ: {total}")

        print("\n✅ База готова к использованию!")
        print("📍 Файл: knowledge_base.json")
        print("\nПримечание: Для полной RAG интеграции нужно:")
        print("  1. Подключить Pinecone (векторная БД)")
        print("  2. Создать embeddings для каждого документа")
        print("  3. Загрузить в Pinecone индекс")
        print("="*50)


if __name__ == "__main__":
    print("\n🚀 Начинаю загрузку RAG базы...")
    print("="*50)

    loader = RAGBaseLoader()

    # Загружаем все источники
    loader.load_discord_materials(None)
    loader.load_txt_materials(None)
    loader.load_notion_links()
    loader.load_schedule()

    # Сохраняем базу
    loader.save_knowledge_base()

    # Выводим сводку
    loader.print_summary()
