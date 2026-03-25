# JARVIS Bot — Architecture & Paths Reference
> Единый источник правды. Обновляй при любых изменениях структуры.
<<<<<<< HEAD
> Last updated: 2026-03-25 (v3.1)
=======
> Last updated: 2026-03-25 (v3.2)
>>>>>>> imac

---

## 🏗️ Инфраструктура

| Компонент | Сервис | Назначение |
|-----------|--------|-----------|
| **Bot runtime** | VPS (Ubuntu) | Постоянный процесс, polling mode |
| **Database** | Supabase (eu-central-1) | Postgres + pgvector RAG |
| **CI/CD** | GitHub Actions | Авто-деплой push→main→VPS |
| **AI — ментор** | Anthropic Claude | Haiku (чат) / Sonnet (vision) |
| **AI — embeddings** | OpenAI text-embedding-3-small | Семантический поиск по KB |
| **Бот** | Telegram @setandforg3t_bot | Интерфейс с учеником |
| **Данные** | Discord | Скачивание чартов и материалов |
| **Знания** | Notion | Контент (опционально) |

---

## 🌿 Ветки Git

| Ветка | Устройство | Роль |
|-------|-----------|------|
| main  | VPS | Production — только финальный код. Пуш → автодеплой |
| imac  | iMac | Основная разработка — новые фичи, embeddings, DB-работы |
| macbook | MacBook | Быстрые фиксы — мелкие правки без iMac |

Workflow:
  imac / macbook → push → CI проверяет → merge в main → автодеплой на VPS

После каждого пуша в main GitHub Actions автоматически синхронизирует imac и macbook.

---

## 📁 Структура проекта

src/bot/
  main.py              - Точка входа, регистрация хэндлеров, JobQueue
  telegram_handler.py  - Все команды (/lesson, /quiz, /levelup, /stats, ...)
  claude_client.py     - Запросы к Claude API (ментор + vision)
  rag_search.py        - Семантический поиск по KB (pgvector + keyword)
  lesson_manager.py    - Учебная программа, XP, уровни, бейджи, get_lesson_image
  user_memory.py       - Портрет ученика (JSONB в Supabase)
  cost_manager.py      - Лимиты API, дневной бюджет
  chart_generator.py   - Генерация свечных графиков (yfinance)
  chart_annotator.py   - Аннотация графиков (Pillow)
  image_handler.py     - Обработка входящих картинок
  reminders.py         - Ежедневные напоминания об обучении (v3.2, JobQueue 09:00 UTC)

src/ingestion/
  add_structured_content.py  - Добавление доков в KB (индикаторы/модели/системы)
  re_embed_missing.py        - Генерация эмбеддингов для docs без векторов
<<<<<<< HEAD
  generate_lesson_images.py  - Генерация 8 ICT/SMC диаграмм → Supabase Storage
=======
  generate_lesson_images.py  - Генерация 21 ICT/SMC диаграммы и загрузка в Supabase Storage
>>>>>>> imac

system/prompts/mentor.md   - Системный промпт JARVIS-ментора
tests/unit/                - Юнит-тесты
supabase/migrations/       - SQL миграции БД
.github/workflows/         - CI/CD

---

## 🗄️ Supabase — таблицы

| Таблица | Назначение |
|---------|-----------|
| knowledge_documents | База знаний (238 docs), embedding vector(1536), difficulty_level |
| bot_users | Пользователи Telegram, уровень, статистика |
| user_memory | JSONB-портрет каждого ученика (XP, бейджи, темы, уровень) |
| conversations | История диалогов (последние 20 сообщений на пользователя) |
| user_watchlist | Тикеры в вотч-листе |
| quiz_results | Результаты финальных тестов уровня |
| lesson_requests | Лог выданных уроков и квизов |
| lesson_images | topic → image_url (PNG в Supabase Storage) + caption, level, concept_type |

Индекс: HNSW на embedding (m=16, ef_construction=64)

Supabase Storage:
  Bucket: lesson-images (public, 5MB limit, image/*)
  Path:   concepts/{concept}.png
  Access: public read, service_role insert

---

## 🔑 Переменные окружения

| Переменная | Описание |
|-----------|---------|
| TELEGRAM_BOT_TOKEN | Токен бота |
| ANTHROPIC_API_KEY | Claude API |
| SUPABASE_URL | https://ivifpljgzsmstirlrjar.supabase.co |
| SUPABASE_ANON_KEY | Публичный anon-ключ |
| OPENAI_API_KEY | Для генерации эмбеддингов |
| DISCORD_TOKEN | Скачивание медиа из Discord (iMac) |
| VPS_HOST | GitHub Secret — IP VPS |
| VPS_USER | GitHub Secret — SSH пользователь |
| VPS_SSH_KEY | GitHub Secret — SSH приватный ключ |

---

## 💻 Пути на устройствах

| Устройство | Путь | Ветка |
|-----------|------|-------|
| iMac | ~/jarvis-trading-bot | imac |
| MacBook | ~/jarvis-trading-bot | macbook |
| VPS | /opt/jarvis | main |

---

## 🤖 Учебная программа

Уровни: Beginner → Elementary → Intermediate → Advanced → Professional
Переход: 80% тем → /levelup → 5-вопросный тест → +500 XP + новый уровень
XP: /lesson +50 | /quiz +100 | /levelup +500

---

## 🚀 Стандартный деплой

  git add -p && git commit -m "feat: ..."
  git push origin imac          # CI проверяет синтаксис
  git checkout main
  git merge imac --no-edit
  git push origin main          # автодеплой на VPS (~30 сек)

---

## 📝 Ingestion (запускать на iMac)

<<<<<<< HEAD
  python -m src.ingestion.add_structured_content    # добавить контент в KB
  python -m src.ingestion.re_embed_missing           # сгенерировать эмбеддинги
  python -m src.ingestion.generate_lesson_images     # сгенерировать/загрузить диаграммы
  python scripts/analyze_kb.py                       # анализ KB

---

## 📦 Версии

| Версия | Дата | Ключевые изменения |
|--------|------|-------------------|
| v3.1 | 2026-03-25 | generate_lesson_images.py: 8 ICT/SMC диаграмм → Supabase Storage |
| v3.0 | 2026-03-25 | /example команда, lesson_images таблица, focus_concept в ChartAnnotator |
| v2.7 | 2026-03-24 | RAG level-aware (pgvector), quiz_results/lesson_requests в БД |
| v2.6 | 2026-03-24 | Rate limiting, branch cleanup, sync-macbook.yml fix |
| v2.5 | 2026-03-23 | Live charts (yfinance), LessonManager, /quiz Telegram polls |
| v2.4 | 2026-03-22 | UserMemory — персистентный портрет ученика |
| v2.3 | 2026-03-21 | ChartAnnotator + ChartDrawer (Sonnet vision) |
| v2.2 | 2026-03-20 | Single ClaudeClient, CostManager |
=======
  python3 -m src.ingestion.add_structured_content    # добавить контент в KB
  python3 -m src.ingestion.re_embed_missing           # сгенерировать эмбеддинги
  python3 -m src.ingestion.generate_lesson_images     # загрузить 21 диаграмму в Storage
  python3 scripts/analyze_kb.py                       # анализ KB
>>>>>>> imac
