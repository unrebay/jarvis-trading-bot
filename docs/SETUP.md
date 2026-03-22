# 🚀 Инструкция по установке JARVIS Trading Bot

## 📋 Требования к системе

### Обязательные:
- Python 3.10 или выше
- pip или poetry (менеджер пакетов)
- Git
- Terminal/CLI доступ

### Опциональные (для полного функционала):
- Node.js 18+ (для Discord ingestion)
- Docker & Docker Compose (для контейнеризации)
- PostgreSQL 14+ (для локального Supabase)

### Учетные записи:
- [Telegram BotFather](https://t.me/botfather) (для создания бота)
- [Anthropic Console](https://console.anthropic.com/) (Claude API)
- [Supabase Account](https://supabase.com/) (Vector database)
- [Notion](https://notion.so/) (опционально, для синхронизации)
- [Discord Developer Portal](https://discord.com/developers) (опционально)

## 🔑 Получение API Ключей

### 1. Telegram Bot Token

```
Шаги:
1. Откройте Telegram и найдите @BotFather
2. Отправьте /start
3. Отправьте /newbot
4. Введите название бота (напр. "JARVIS Trading Bot")
5. Введите username бота (напр. "jarvis_trading_bot")
6. BotFather вернет token
7. Сохраните token → .env переменная TELEGRAM_BOT_TOKEN

Пример token: 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
```

### 2. Claude API Key

```
Шаги:
1. Перейдите на https://console.anthropic.com/
2. Создайте аккаунт или войдите
3. Нажмите "Create New API Key"
4. Скопируйте ключ
5. Сохраните → .env переменная CLAUDE_API_KEY

Формат: sk-ant-[base64-encoded-key]
```

### 3. Supabase Project

```
Шаги:
1. Перейдите на https://supabase.com/
2. Создайте новый проект
3. Выберите регион (ближайший к вам)
4. Подождите инициализацию (~2 минуты)
5. Скопируйте credentials:
   - SUPABASE_URL (Project URL)
   - SUPABASE_API_KEY (anon key)
   - SUPABASE_DB_PASSWORD (database password)

Расположение в Dashboard:
Settings → API → Project URL и API keys
```

### 4. Notion API (опционально)

```
Шаги:
1. Перейдите на https://www.notion.so/my-integrations
2. Нажмите "Create new integration"
3. Заполните детали:
   - Name: "JARVIS Trading Bot"
   - User capability: Select user
4. Скопируйте Internal Integration Token
5. Сохраните → .env переменная NOTION_API_KEY
6. Откройте вашу Notion Database
7. Откройте Share → Select a connection → выберите созданный integration
8. Скопируйте Database ID из URL
9. Сохраните → .env переменная NOTION_DATABASE_ID

Пример URL: https://notion.so/workspace/[DATABASE_ID]?v=...
DATABASE_ID = часть после "/workspace/"
```

## 💻 Установка локально (macOS/Linux)

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/yourusername/jarvis-trading-bot.git
cd jarvis-trading-bot
```

### Шаг 2: Создание виртуального окружения

```bash
# Создаем venv
python3 -m venv venv

# Активируем (macOS/Linux)
source venv/bin/activate

# Или на Windows:
# venv\Scripts\activate
```

После активации вы должны увидеть `(venv)` в начале терминала.

### Шаг 3: Установка зависимостей

```bash
# Обновляем pip
pip install --upgrade pip

# Устанавливаем требуемые пакеты
pip install -r requirements.txt

# Проверяем установку
pip list | grep telegram  # должен быть python-telegram-bot
```

### Шаг 4: Конфигурирование переменных окружения

```bash
# Копируем шаблон
cp config/.env.example .env

# Открываем для редактирования (выберите свой редактор)
nano .env          # или vim, code, etc.
# или
code .env          # Visual Studio Code
```

**Заполните обязательные переменные:**

```env
# Обязательные (без них бот не запустится)
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
CLAUDE_API_KEY=ваш_ключ_здесь
SUPABASE_URL=ваш_url_здесь
SUPABASE_API_KEY=ваш_api_ключ_здесь

# Опциональные (для дополнительных функций)
NOTION_API_KEY=...
DISCORD_TOKEN=...
```

### Шаг 5: Инициализация базы знаний

```bash
# Компилируем markdown файлы в knowledge_base.json
python scripts/load_rag_base.py

# Проверяем, что файл создан
ls -lh knowledge_base.json

# Должно быть несколько килобайт (в зависимости от документов)
```

### Шаг 6: Инициализация Supabase

```bash
# Создаем необходимые таблицы в Supabase
python scripts/vector_db_setup.py --init

# Загружаем знания в векторную БД
python scripts/vector_db_setup.py --load-knowledge

# Проверяем здоровье системы
python scripts/health_check.py
```

### Шаг 7: Запуск бота

```bash
# Запускаем основного бота
python jarvis_bot.py

# Вы должны увидеть в консоли:
# [INFO] Bot started successfully
# [INFO] Listening for messages...

# Для остановки: Ctrl+C
```

### Шаг 8: Тестирование

```bash
# В другом терминале активируйте venv и проверьте бота
source venv/bin/activate

# Откройте Telegram и напишите боту:
# /start
# /help
# Что такое price action в ICT?

# Бот должен ответить с основанием на базе знаний
```

## 🐳 Установка с Docker

### Требования:
- Docker (>=20.10)
- Docker Compose (>=1.29)

### Шаги:

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourusername/jarvis-trading-bot.git
cd jarvis-trading-bot

# 2. Копируем .env
cp config/.env.example .env

# 3. Заполняем .env с реальными значениями
nano .env

# 4. Собираем Docker образ
docker build -t jarvis-bot:latest .

# 5. Запускаем контейнер
docker run -d \
  --name jarvis \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
  -e CLAUDE_API_KEY=$CLAUDE_API_KEY \
  -e SUPABASE_URL=$SUPABASE_URL \
  -e SUPABASE_API_KEY=$SUPABASE_API_KEY \
  jarvis-bot:latest

# 6. Проверяем логи
docker logs -f jarvis

# 7. Для остановки
docker stop jarvis
docker rm jarvis
```

### Docker Compose (рекомендуется):

Создайте `docker-compose.yml`:

```yaml
version: '3.8'

services:
  jarvis-bot:
    build: .
    container_name: jarvis-trading-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./cache:/app/cache
      - ./knowledge_raw:/app/knowledge_raw
    environment:
      - ENVIRONMENT=production
    networks:
      - jarvis-network

networks:
  jarvis-network:
    driver: bridge
```

Запуск:

```bash
docker-compose up -d
docker-compose logs -f jarvis-bot
```

## 🚢 Развертывание на Railway

### Требования:
- Railway Account (https://railway.app/)
- GitHub репозиторий
- Railway CLI (опционально)

### Шаги:

#### 1. Подготовка GitHub

```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
```

#### 2. Подключение к Railway

```
1. Откройте https://railway.app/
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub"
4. Авторизуйте GitHub
5. Выберите ваш репозиторий
6. Railway автоматически обнаружит:
   - Dockerfile
   - Procfile
   - requirements.txt
7. Нажмите "Deploy"
```

#### 3. Конфигурирование переменных

```
В Railway Dashboard:
1. Откройте ваш проект
2. Перейдите в "Variables"
3. Добавьте переменные из .env:
   - TELEGRAM_BOT_TOKEN
   - CLAUDE_API_KEY
   - SUPABASE_URL
   - SUPABASE_API_KEY
   - и все остальные из .env.example
4. Нажмите "Deploy"
```

#### 4. Проверка развертывания

```
1. Откройте Railway Dashboard
2. Смотрите Logs вкладку
3. Должны увидеть "Bot started successfully"
4. Тестируйте бота в Telegram
```

## 🔄 Обновление системы

### Обновление зависимостей

```bash
# Активируем venv
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Обновляем пакеты
pip install -r requirements.txt --upgrade

# Сохраняем обновления (опционально)
pip freeze > requirements.txt
```

### Обновление знаний

```bash
# Для добавления новых markdown файлов в knowledge_raw/:
python scripts/load_rag_base.py

# Для синхронизации в Notion:
python scripts/migrate_to_notion.py

# Для синхронизации из Discord:
python scripts/sync_discord_data.py
```

### Обновление с GitHub

```bash
# Получаем последние изменения
git pull origin main

# Переустанавливаем зависимости (если изменился requirements.txt)
pip install -r requirements.txt

# Перезагружаем бота
# На локальной машине: Ctrl+C и python jarvis_bot.py
# На Railway: автоматический redeploy
```

## 🔍 Проверка и тестирование

### Health Check

```bash
python scripts/health_check.py
```

Должен вывести что-то типа:

```
✅ Telegram API: OK
✅ Claude API: OK
✅ Supabase: OK
✅ Knowledge Base: 50 documents
✅ Cache: OK
✅ System: HEALTHY
```

### Тестирование RAG

```bash
python -c "
from scripts.load_rag_base import load_knowledge_base

kb = load_knowledge_base()
results = kb.search('price action ICT')
for doc in results:
    print(f'- {doc[\"title\"]}: {doc[\"score\"]:.2f}')
"
```

### Тестирование Claude

```bash
python -c "
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))
response = client.messages.create(
    model='claude-3-sonnet-20240229',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print(response.content[0].text)
"
```

## ❌ Решение проблем

### Проблема: "ModuleNotFoundError: No module named 'telegram'"

```bash
# Решение: переустановить зависимости
pip install -r requirements.txt --force-reinstall
```

### Проблема: "TELEGRAM_BOT_TOKEN not found"

```bash
# Проверяем, что .env создан и заполнен
ls -la .env
cat .env | grep TELEGRAM_BOT_TOKEN

# Если .env не существует:
cp config/.env.example .env
# И заполните вручную
```

### Проблема: "Connection to Supabase failed"

```bash
# Проверяем credentials
python -c "
import os
print(f'URL: {os.getenv(\"SUPABASE_URL\")}')
print(f'Key: {os.getenv(\"SUPABASE_API_KEY\")[:20]}...')
"

# Проверяем сетевое соединение
curl $SUPABASE_URL
```

### Проблема: "Rate limit exceeded from Claude API"

```
1. Проверяем текущий лимит в Console.anthropic.com
2. Снижаем CLAUDE_MAX_TOKENS в .env
3. Добавляем задержку между запросами
4. Контактируем Anthropic support
```

### Проблема: "Bot не отвечает в Telegram"

```bash
# Проверяем, что бот запущен
ps aux | grep jarvis_bot.py

# Смотрим логи
tail -f logs/jarvis.log

# Проверяем token
curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"

# Если token некорректен - обновляем в .env и рестартуем
```

## 📚 Дополнительная информация

### Структура логов

```
logs/
├── jarvis.log          # Основной лог
├── errors.log          # Только ошибки
├── api_calls.log       # Вызовы API
└── analytics.log       # Статистика
```

### Переменные окружения для разных окружений

```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# Staging
ENVIRONMENT=staging
LOG_LEVEL=INFO
DEBUG=false

# Production
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=false
```

### Полезные команды

```bash
# Просмотр активных процессов
ps aux | grep python

# Просмотр использования памяти
top

# Просмотр дискового пространства
df -h

# Проверка порта (если используется)
lsof -i :8000

# Очистка кэша
python scripts/cleanup.py

# Остановка всех контейнеров
docker stop $(docker ps -q)
```

## ✅ Финальный checklist

- [ ] Клонирован репозиторий
- [ ] Создано виртуальное окружение
- [ ] Установлены зависимости
- [ ] Получены все API ключи
- [ ] Создан и заполнен .env файл
- [ ] Загружена база знаний
- [ ] Инициализирована Supabase
- [ ] Health check показывает ✅
- [ ] Бот запустился без ошибок
- [ ] Тестовое сообщение в Telegram получило ответ
- [ ] Логи показывают нормальную работу

После всего этого ваша система полностью готова к работе! 🎉

---

**Last Updated:** March 2026
**Version:** 1.0.0
