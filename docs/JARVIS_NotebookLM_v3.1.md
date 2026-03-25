# JARVIS Trading Bot — Полный технический отчёт v3.1
> Документ для загрузки в NotebookLM. Единый источник знаний о проекте.
> Дата: 2026-03-25 | Версия: 3.1 | Бот: @setandforg3t_bot

---

## 1. Обзор проекта

JARVIS — AI-ментор по ICT/SMC трейдингу, реализованный как Telegram-бот. Бот обучает трейдингу по методологии Inner Circle Trader (ICT) и Smart Money Concepts (SMC) с нуля до профессионального уровня. Основная идея: персонализированное обучение с учётом уровня ученика, живые графики с ICT-аннотацией, учебные диаграммы и тесты.

### Ключевые характеристики

Бот работает в режиме polling на VPS (Ubuntu), использует Claude API от Anthropic как интеллект ментора, pgvector в Supabase для семантического поиска по базе знаний, OpenAI для генерации эмбеддингов, и yfinance для получения live-данных графиков.

Текущая версия 3.1 включает полный стек: чат с ментором, учебную программу из 51 темы, живые аннотированные графики, статические образовательные диаграммы, персистентную память ученика, квизы и систему уровней.

---

## 2. Инфраструктура

### Компоненты системы

**Bot Runtime** — VPS на Ubuntu, постоянный процесс в режиме polling. Бот запускается через systemd-сервис, автоматически перезапускается при падении.

**База данных** — Supabase (PostgreSQL, регион eu-central-1). Используется pgvector-расширение для семантического поиска по базе знаний, HNSW-индекс (m=16, ef_construction=64).

**CI/CD** — GitHub Actions. Push в ветку main → автоматический SSH-деплой на VPS за ~30 секунд.

**AI-ментор** — Anthropic Claude. Haiku используется для обычных сообщений и обновления памяти пользователя. Sonnet используется для анализа графиков (vision).

**Embeddings** — OpenAI text-embedding-3-small. Модель размерностью 1536. Используется для генерации векторов документов базы знаний и векторов запросов при поиске.

**Telegram** — бот @setandforg3t_bot. Интерфейс взаимодействия с учеником.

**Discord** — источник чартов и учебных материалов (скачивание на iMac).

**Notion** — опциональный источник контента (планируется интеграция).

### Устройства разработки

iMac — основная машина разработки (ветка imac), запуск ingestion-скриптов, работа с базой данных.
MacBook — быстрые фиксы в дороге (ветка macbook).
VPS — production-сервер, путь /opt/jarvis, ветка main.

---

## 3. Ветки Git и рабочий процесс

### Ветки

**main** — production. Только финальный, проверенный код. Push в main запускает автодеплой на VPS через GitHub Actions. Никогда не коммитить напрямую в main без прохождения через imac.

**imac** — основная ветка разработки. Все новые фичи, работы с базой данных, ingestion-скрипты разрабатываются здесь. После тестирования мержится в main.

**macbook** — ветка для MacBook. Мелкие срочные правки когда нет доступа к iMac. Синхронизируется с main автоматически.

### GitHub Actions workflows

**deploy.yml** — SSH-деплой на VPS при пуше в main. Git pull → pip install → systemctl restart jarvis.

**ci.yml** — проверка синтаксиса Python при пуше в imac или macbook. Защита от деплоя с синтаксическими ошибками.

**sync-macbook.yml** — синхронизация main → macbook и main → imac после каждого пуша в main. Обеспечивает актуальность всех веток.

### Стандартный деплой

```bash
git add -p && git commit -m "feat: описание"
git push origin imac          # CI проверяет синтаксис
git checkout main
git merge imac --no-edit
git push origin main          # автодеплой на VPS (~30 сек)
```

---

## 4. Структура кода

### src/bot/ — основные модули

**main.py** — точка входа. Инициализирует все клиенты, регистрирует хэндлеры команд, настраивает Telegram-меню. Версия 3.1.

**telegram_handler.py** — обработчик всех команд и сообщений. Содержит handle_start, handle_lesson, handle_quiz, handle_levelup, handle_chart, handle_example, handle_photo, handle_message. Rate limiting: 1 запрос / 3 секунды на пользователя.

**claude_client.py** — клиент для Anthropic API. Единый экземпляр на весь процесс. Поддерживает caching для снижения стоимости. Haiku для чата, Sonnet для vision.

**rag_search.py** — семантический поиск по базе знаний. Полная реализация с pgvector + keyword fallback. Level-aware фильтрация.

**lesson_manager.py** — учебная программа из 51 темы. Управление XP, уровнями, бейджами. Метод get_lesson_image() для получения образовательных диаграмм.

**user_memory.py** — персистентный портрет ученика в Supabase. JSONB-документ обновляется каждые 5 сообщений через Haiku.

**cost_manager.py** — управление дневным бюджетом API ($1.00/день). Три режима: FULL → LITE → OFFLINE.

**chart_generator.py** — генерация живых свечных графиков через yfinance + mplfinance. Тёмная тема (#131722).

**chart_annotator.py** — аннотация графиков через Claude Vision (Sonnet). Поддерживает focus_concept для таргетированного анализа.

**image_handler.py** — обработка входящих изображений от пользователей.

### src/ingestion/ — скрипты наполнения данных

**add_structured_content.py** — добавляет структурированные документы в knowledge_documents. 18 новых разделов по индикаторам, моделям и торговым системам по уровням.

**re_embed_missing.py** — генерирует text-embedding-3-small для документов без вектора. Использовался для заполнения 94 пропущенных эмбеддингов.

**generate_lesson_images.py** — генерирует 8 образовательных matplotlib-диаграмм (ICT/SMC), загружает в Supabase Storage bucket "lesson-images", вставляет записи в таблицу lesson_images.

### system/prompts/

**mentor.md** — системный промпт JARVIS-ментора. Определяет личность, стиль общения, правила гейм-ификации, правило первого сообщения (приветствие + первый урок).

---

## 5. База данных Supabase

### Таблицы

**knowledge_documents** — база знаний, 238 документов. Поля: id, title, content, section, topic, difficulty_level, embedding vector(1536), metadata JSONB. HNSW-индекс на поле embedding.

**bot_users** — пользователи Telegram. Поля: user_id, username, level, xp, created_at, last_active.

**user_memory** — персистентный портрет ученика. Поля: user_id, memory JSONB (имя, опыт, стиль, темы, уровень, бейджи, XP), updated_at.

**conversations** — история диалогов. Последние 20 сообщений на пользователя.

**user_watchlist** — вотч-лист тикеров пользователя.

**quiz_results** — результаты финальных тестов уровня. Поля: user_id, topic, level, score, total, created_at.

**lesson_requests** — лог выданных уроков и квизов. Поля: user_id, topic, level, action (lesson/quiz), created_at.

**lesson_images** — маппинг концепции → изображение. Поля: id, topic, image_url, caption, level, concept_type, source, created_at.

### Supabase Storage

Bucket: lesson-images. Публичный доступ на чтение. Лимит файла 5MB. Только изображения (image/*). Политика: public SELECT, service_role INSERT.

Путь файлов: concepts/{concept}.png. Примеры: concepts/fvg.png, concepts/order_block.png.

RPC-функция match_knowledge_documents принимает query_embedding vector, match_count integer, filter jsonb (с полем difficulty_levels). Возвращает документы отсортированные по косинусному сходству.

---

## 6. RAG-поиск (Retrieval-Augmented Generation)

### Принцип работы

При каждом сообщении пользователя:
1. Определяется текущий уровень пользователя из Supabase.
2. Запрос векторизуется через OpenAI text-embedding-3-small.
3. pgvector ищет top-4 наиболее похожих документа из knowledge_documents.
4. Фильтр: difficulty_level IN (все уровни ≤ текущего пользователя).
5. Найденные документы форматируются и инжектируются в системный промпт Claude.

### Level-aware фильтрация

Иерархия уровней: Beginner → Elementary → Intermediate → Advanced → Professional.

Функция _levels_up_to("Intermediate") возвращает ["Beginner", "Elementary", "Intermediate"]. Это значит ученик уровня Intermediate видит только контент предназначенный для его уровня и ниже, но не видит Advanced и Professional материалы.

### Fallback механизм

Если OpenAI API недоступен или эмбеддинг не удалось создать — используется keyword_search через ilike по полю content. Если ilike не даёт результатов с фильтром по уровню — поиск повторяется без фильтра уровня.

---

## 7. Учебная программа

### Уровни и переходы

Beginner → Elementary → Intermediate → Advanced → Professional.

Переход на следующий уровень: завершить 80% тем текущего уровня → пройти /levelup тест (5 вопросов) → получить 80%+ правильных ответов → +500 XP + новый уровень.

### XP-система

/lesson — +50 XP за каждый полученный урок.
/quiz — +100 XP за пройденный квиз.
/levelup — +500 XP за переход на новый уровень.
Бейджи выдаются за достижения (первый квиз, 10 уроков, переход уровня и т.д.).

### Команды бота

/start — приветствие и первый урок.
/help — список всех команд.
/lesson — следующий урок по программе (или /lesson FVG для конкретной темы).
/quiz ТЕМА — тест по теме в формате Telegram QUIZ poll (автопроверка ответа).
/levelup — финальный тест для перехода на следующий уровень.
/progress — текущий прогресс, XP, пройденные темы.
/profile — что JARVIS помнит о пользователе.
/chart SYMBOL TF — живой график с ICT/SMC аннотацией.
/chart SYMBOL TF CONCEPT — график с фокусом на конкретной концепции.
/example CONCEPT — статическая образовательная диаграмма концепции.
/watch add SYMBOL TF — добавить тикер в вотч-лист.
/status — бюджет API и текущий режим бота.

---

## 8. Образовательные диаграммы (v3.1)

### Что генерирует generate_lesson_images.py

Скрипт создаёт 8 matplotlib-диаграмм в торговом тёмном стиле (фон #131722, сетка #2a2e39, текст #d1d4dc):

**FVG (Fair Value Gap)** — уровень Beginner. Три бычьих свечи, зелёная зона имбалланса между high первой и low третьей свечи, стрелка "цена вернётся заполнить FVG".

**Order Block** — уровень Beginner. Медвежье движение с последней бычьей свечой перед падением = Bearish OB, красная зона, стрелка "цена вернётся к OB для шорта".

**BOS и CHoCH** — уровень Beginner. Восходящий тренд с метками HH/HL, синие линии BOS, оранжевая линия CHoCH, красные LH/LL после смены структуры.

**Liquidity (BSL/SSL)** — уровень Intermediate. Свинг-хаи красными точками (BSL зона), свинг-лоу зелёными точками (SSL зона), оранжевая стрелка Sweep.

**Market Structure** — уровень Beginner. Бычий тренд с метками Low/HH/HL, пунктирные линии BOS.

**Premium/Discount** — уровень Intermediate. Диапазон свинга с зонами: Premium (выше 75%), Discount (ниже 25%), Equilibrium (50%), жёлтая линия мидпойнта.

**Inducement (IDM)** — уровень Advanced. Ложное HL отмечено оранжевым треугольником вниз, стрелка показывает sweep IDM, зелёная точка реального HL после сбора ликвидности.

**AMD (Accumulation, Manipulation, Distribution)** — уровень Intermediate. Три фазы с цветными зонами, ценовой путь показывает Judas Swing вниз и настоящее движение вверх.

### Интеграция в бот

При команде /example FVG — сначала проверяется таблица lesson_images (topic или concept_type ILIKE запрос), если найдено — reply_photo с URL из Supabase Storage. Если не найдено — генерируется live EURUSD 4h график с focus_concept="FVG".

При команде /lesson — после текста урока автоматически вызывается get_lesson_image(), если для темы есть диаграмма — прикрепляется к ответу.

При команде /chart SYMBOL TF CONCEPT — focus_concept передаётся в ChartAnnotator, который добавляет в prompt Claude Vision инструкцию "FOCUS: student wants to learn about {concept}. Identify ALL instances...".

---

## 9. Переменные окружения

TELEGRAM_BOT_TOKEN — токен бота Telegram.
ANTHROPIC_API_KEY — ключ Claude API.
SUPABASE_URL — https://ivifpljgzsmstirlrjar.supabase.co
SUPABASE_ANON_KEY — публичный anon-ключ Supabase.
OPENAI_API_KEY — ключ OpenAI для генерации эмбеддингов.
DISCORD_TOKEN — токен Discord (только на iMac, для скачивания медиа).
VPS_HOST — GitHub Secret, IP-адрес VPS.
VPS_USER — GitHub Secret, SSH-пользователь на VPS.
VPS_SSH_KEY — GitHub Secret, приватный SSH-ключ для деплоя.

Файл .env находится в корне проекта (~/jarvis-trading-bot/.env) и на VPS (/opt/jarvis/.env). Не коммитится в Git (в .gitignore).

---

## 10. История версий

### v3.1 (2026-03-25) — Educational Images

Добавлен скрипт generate_lesson_images.py. Генерирует 8 ICT/SMC диаграмм через matplotlib, загружает PNG в Supabase Storage bucket "lesson-images", вставляет записи в таблицу lesson_images. Диаграммы: FVG, Order Block, BOS/CHoCH, Liquidity, Market Structure, Premium/Discount, Inducement, AMD.

### v3.0 (2026-03-25) — /example command + lesson_images

Добавлена команда /example [CONCEPT]. Создана таблица lesson_images и Storage bucket. Добавлен метод get_lesson_image() в LessonManager. ChartAnnotator получил поддержку focus_concept. Версия main.py обновлена до v3.0.

### v2.7 (2026-03-24) — Level-aware RAG + DB logging

Полная переработка rag_search.py: pgvector semantic search (match_knowledge_documents RPC) + keyword fallback. Level filter: _levels_up_to() → difficulty_level IN (allowed_levels). Добавлен openai>=1.0.0 в requirements.txt. Функции _save_lesson_request() и _save_quiz_result() подключены к handlers. Таблицы quiz_results и lesson_requests используются.

### v2.6 (2026-03-24) — Branch cleanup + Rate limiting

Rate limiting 3 секунды на пользователя в TelegramHandler. Очистка веток репозитория: удалены production, feature/*, macbook-clean. Оставлены main, imac, macbook. Workflow sync-macbook.yml исправлен (ссылался на удалённую ветку macbook-clean). PATHS.md переписан как единый источник правды. 12 устаревших .md файлов перемещены в docs/archive/.

### v2.5 (2026-03-23) — Live Charts + Education System

ChartGenerator: live OHLCV через yfinance + mplfinance, тёмная тема. Команда /chart SYMBOL TF. LessonManager: 51 тема, XP, уровни, бейджи. Команды /lesson /quiz /progress /levelup /profile. /quiz использует нативные Telegram QUIZ polls. /watch вотч-лист + TradingView webhook.

### v2.4 (2026-03-22) — Persistent Student Memory

UserMemory: JSONB-портрет ученика в Supabase. Загружается перед каждым сообщением, инжектируется в контекст Claude. Обновляется каждые 5 сообщений через Haiku асинхронно. JARVIS помнит имя, опыт, стиль, темы между сессиями.

### v2.3 (2026-03-21) — Visual Chart Analysis

ChartAnnotator + ChartDrawer. Анализ присланных пользователем фото графиков через Claude Sonnet Vision. Команда /analyze.

### v2.2 (2026-03-20) — Architecture Fix

Single ClaudeClient на весь процесс. CostManager с дневным бюджетом. Исправлены баги: неправильные параметры ask_mentor(), двойная инициализация Anthropic, сломанный _update_user_stats().

---

## 11. Известные технические решения

### Почему VPS, а не Railway

Railway использовался ранее, но оказался нестабильным для long-running Telegram polling процессов. Текущий деплой на VPS через GitHub Actions SSH более надёжен и контролируем.

### Почему Haiku для чата, Sonnet только для vision

Haiku значительно дешевле при сравнимом качестве для образовательного чата. Sonnet используется только там где нужна vision-способность (анализ графиков, аннотации). CostManager следит за дневным бюджетом $1.00.

### Почему pgvector + keyword fallback

pgvector требует OpenAI API для векторизации запроса в реальном времени. При недоступности API семантический поиск невозможен. Keyword fallback через ilike гарантирует что бот работает даже без OpenAI ключа.

### Почему level-aware RAG

Документы в knowledge_documents имеют поле difficulty_level. Начинающий ученик не должен получать Advanced материалы в контексте, т.к. это сбивает с толку. Фильтр _levels_up_to() обеспечивает что ментор отвечает материалами соответствующего уровня.

---

## 12. Типичные операции обслуживания

### Добавить новый контент в базу знаний

Отредактировать add_structured_content.py или создать новый ingestion-скрипт. Запустить python -m src.ingestion.add_structured_content на iMac. Запустить python -m src.ingestion.re_embed_missing для генерации эмбеддингов новых документов.

### Обновить образовательные диаграммы

Отредактировать функции draw_* в generate_lesson_images.py. Запустить python -m src.ingestion.generate_lesson_images на iMac (upsert по полю topic).

### Деплой изменений

```bash
cd ~/jarvis-trading-bot
git pull origin imac
# ... внести изменения ...
git add src/bot/telegram_handler.py
git commit -m "fix: описание"
git push origin imac
git checkout main && git merge imac --no-edit && git push origin main
```

### Проверить статус бота на VPS

```bash
ssh user@VPS_IP "systemctl status jarvis"
ssh user@VPS_IP "journalctl -u jarvis -n 50"
```

---

## 13. Зависимости (requirements.txt)

python-telegram-bot — Telegram Bot API SDK.
anthropic — Claude API клиент.
supabase — Supabase Python клиент.
openai>=1.0.0 — OpenAI клиент для embeddings.
yfinance — получение OHLCV данных финансовых инструментов.
mplfinance — свечные графики через matplotlib.
matplotlib — base графика и генерация образовательных диаграмм.
numpy — матричные вычисления.
Pillow — обработка изображений.
python-dotenv — загрузка .env файла.
httpx — async HTTP клиент.

---

## 14. Структура директорий

```
jarvis-trading-bot/
├── src/
│   ├── bot/
│   │   ├── main.py              # Точка входа v3.1
│   │   ├── telegram_handler.py  # Все команды и хэндлеры
│   │   ├── claude_client.py     # Anthropic API клиент
│   │   ├── rag_search.py        # pgvector + keyword search
│   │   ├── lesson_manager.py    # Учебная программа
│   │   ├── user_memory.py       # Портрет ученика
│   │   ├── cost_manager.py      # Бюджет API
│   │   ├── chart_generator.py   # Live charts (yfinance)
│   │   ├── chart_annotator.py   # ICT аннотации (Sonnet)
│   │   ├── chart_drawer.py      # Pillow рисование
│   │   └── image_handler.py     # Входящие фото
│   └── ingestion/
│       ├── add_structured_content.py
│       ├── re_embed_missing.py
│       └── generate_lesson_images.py
├── system/prompts/
│   └── mentor.md                # Системный промпт
├── supabase/migrations/         # SQL миграции
├── .github/workflows/
│   ├── deploy.yml               # SSH деплой на VPS
│   ├── ci.yml                   # Проверка синтаксиса
│   └── sync-macbook.yml         # Синхронизация веток
├── docs/
│   ├── JARVIS_NotebookLM_v3.1.md  # Этот файл
│   └── archive/                    # Устаревшие доки
├── tests/unit/
├── PATHS.md                     # Architecture reference v3.1
├── requirements.txt
└── .env                         # Не в Git
```

---

*Документ сгенерирован 2026-03-25. При обновлении проекта обновлять этот файл и PATHS.md.*
