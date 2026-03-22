# 🏗️ Архитектура JARVIS Trading Bot

## Содержание

1. [Обзор системы](#обзор-системы)
2. [Компоненты](#компоненты)
3. [Поток данных](#поток-данных)
4. [Технологический стек](#технологический-стек)
5. [Паттерны проектирования](#паттерны-проектирования)
6. [Интеграции](#интеграции)

## Обзор системы

JARVIS — это многоуровневая система с четкым разделением ответственности:

```
┌─────────────────────────────────────────────────┐
│          Presentation Layer (UI)                 │
│  ┌──────────────┬──────────────┬──────────────┐ │
│  │   Telegram   │   Discord    │  Web API     │ │
│  │    Bot       │  Ingestion   │  (future)    │ │
│  └──────┬───────┴──────┬───────┴──────────────┘ │
└─────────┼──────────────┼──────────────────────────┘
          │              │
          └──────┬───────┘
                 │
┌────────────────▼──────────────────────────────────┐
│       Application Layer (Logic)                    │
│  ┌────────────────────────────────────────────┐  │
│  │  Message Router & Request Processor        │  │
│  │  (jarvis_bot.py - main entry point)        │  │
│  └────────┬──────────┬──────────┬────────────┘  │
└───────────┼──────────┼──────────┼────────────────┘
            │          │          │
   ┌────────▼──┐ ┌────▼────┐ ┌──▼──────────┐
   │ RAG Engine│ │ Claude  │ │ Context Mgr │
   │ (Search)  │ │ AI API  │ │ (Sessions)  │
   └────┬──────┘ └────┬────┘ └──┬──────────┘
        │             │         │
┌───────┴─────────────┼─────────┴────────────────┐
│   Data Layer (Storage & Processing)             │
│  ┌──────────────┬──────────────┬────────────┐  │
│  │  Supabase    │  Knowledge   │   Cache    │  │
│  │ (Vectors)    │  Base (JSON) │  (Memory)  │  │
│  └──────────────┴──────────────┴────────────┘  │
└──────────────────────────────────────────────────┘
```

## Компоненты

### 1. Presentation Layer

#### Telegram Bot (`jarvis_bot.py`)
- **Назначение:** Основной интерфейс взаимодействия с пользователями
- **Компоненты:**
  - `TelegramBotHandler` — обработка сообщений
  - `MessageParser` — парсинг команд
  - `ResponseFormatter` — форматирование ответов
- **Протокол:** Telegram Bot API (polling/webhook)
- **Масштабируемость:** Поддерживает thousands simultaneous users

#### Discord Ingestion
- **Назначение:** Сбор образовательного контента из Discord
- **Функции:**
  - Скачивание сообщений из указанных каналов
  - Извлечение ссылок и файлов
  - Автоматическое добавление в knowledge_raw/

#### Web API (Future)
- REST API для интеграции с веб-приложениями
- GraphQL для сложных запросов
- WebSocket для real-time обновлений

### 2. Application Layer

#### Message Router & Processor (`jarvis_bot.py`)

```python
class MessageProcessor:
    def process(message: str) -> Response:
        1. Парсинг и валидация
        2. Маршрутизация (команда vs вопрос)
        3. Выполнение логики
        4. Генерация ответа

    def route(command: str) -> Handler:
        # /help -> help_handler()
        # /ask [query] -> ask_handler(query)
        # /search [term] -> search_handler(term)
```

#### RAG Engine
- **Компоненты:**
  - `KnowledgeBase` — загрузка и управление документами
  - `VectorStore` — работа с Supabase
  - `Retriever` — семантический поиск
  - `RankingEngine` — ранжирование результатов

```python
class RAGEngine:
    def search(query: str, top_k: int = 5) -> List[Document]:
        # 1. Кодирование запроса в вектор
        # 2. Поиск в Supabase (cosine similarity)
        # 3. Ранжирование и фильтрация
        # 4. Возврат результатов с оценкой релевантности
```

#### Claude AI Integration
- **Модель:** Claude 3 Sonnet (или Opus для критичных задач)
- **Функции:**
  - Генерация текста
  - Анализ данных
  - Перефразирование
  - Ответы на вопросы

```python
class ClaudeAI:
    def generate(prompt: str, context: str) -> str:
        # 1. Конструирование полного промпта с контекстом
        # 2. Вызов Claude API
        # 3. Обработка стриминга/батча
        # 4. Парсинг ответа
```

#### Context Manager
- Управление сессиями пользователей
- Сохранение истории диалога
- Контроль памяти контекста

### 3. Data Layer

#### Supabase (PostgreSQL + pgvector)
- **Таблицы:**
  - `knowledge_vectors` — эмбединги документов
  - `user_sessions` — история диалогов
  - `search_queries` — логирование поисков
  - `analytics` — статистика использования

- **Функции:**
  - Vector similarity search
  - Full-text search
  - Session management

#### Knowledge Base JSON
- **Структура:**
```json
{
  "documents": [
    {
      "id": "ict-price-action-001",
      "category": "ict-concepts",
      "title": "Price Action в ICT",
      "content": "...",
      "keywords": ["price", "action", "ict"],
      "embedding": [0.123, 0.456, ...],
      "metadata": {
        "created_at": "2026-03-22",
        "source": "knowledge_raw/ict-concepts/price-action.md"
      }
    }
  ]
}
```

#### Cache Layer
- **Типы кэша:**
  - Query cache (результаты поиска)
  - Response cache (сгенерированные ответы)
  - Session cache (данные юзера)

- **TTL:** 1 час для обычных данных, 24 часа для знаний

## Поток данных

### Основной User Flow

```
1. USER INPUT
   └─> Telegram сообщение

2. TELEGRAM API
   └─> Webhook/Polling получает сообщение

3. MESSAGE PROCESSOR
   └─> Парсинг и валидация
   └─> Определение типа: команда vs вопрос

4. REQUEST ROUTING
   ├─ Если команда (/help, /search):
   │  └─> Выполнение специфичного обработчика
   │
   └─ Если вопрос:
      └─> RAG Pipeline

5. RAG PIPELINE
   ├─ Кодирование запроса в вектор
   ├─ Поиск в Supabase (top-k retrieval)
   ├─ Ранжирование результатов
   └─> Контекст документов

6. CONTEXT CONSTRUCTION
   └─> System prompt
   └─> User question
   └─> Retrieved documents
   └─> Chat history

7. CLAUDE API CALL
   └─> Отправка промпта
   └─> Получение стриминг-ответа
   └─> Форматирование

8. RESPONSE FORMATTING
   └─> Обрезка по length limit
   └─> Добавление источников
   └─> Эмодзи и форматирование

9. TELEGRAM SEND
   └─> Отправка сообщения юзеру

10. LOGGING & ANALYTICS
    └─> Сохранение в DB
    └─> Обновление статистики
```

### Knowledge Update Flow

```
1. MARKDOWN EDIT
   └─> knowledge_raw/[category]/[file].md

2. LOAD RAG BASE SCRIPT
   └─> scripts/load_rag_base.py
   └─> Чтение all markdown файлов
   └─> Генерация embeddings (Supabase)
   └─> Создание knowledge_base.json

3. COMPILATION
   └─> Parsing markdown
   └─> Chunking больших документов
   └─> Metadata extraction

4. EMBEDDING GENERATION
   └─> Отправка chunks в Supabase
   └─> pgvector кодирует в 1536-dim vectors
   └─> Сохранение с индексом

5. CACHE INVALIDATION
   └─> Очистка query cache
   └─> Обновление в памяти

6. NOTION SYNC (опционально)
   └─> python scripts/migrate_to_notion.py
   └─> Загрузка в Notion Database

7. GIT COMMIT
   └─> git add knowledge_raw/ knowledge_base.json
   └─> git commit
   └─> git push

8. CI/CD TRIGGER
   └─> GitHub Actions запускает тесты
   └─> Deploy на Railway
```

## Технологический стек

### Backend
- **Language:** Python 3.10+
- **Framework:** Custom (lightweight, no Django/Flask)
- **Async:** asyncio + aiohttp для параллелизма
- **API Clients:** python-telegram-bot, anthropic, supabase

### Database
- **Vector DB:** Supabase (PostgreSQL + pgvector)
- **Vector Dimension:** 1536 (OpenAI embedding size)
- **Cache:** File-based (memory for local dev)

### AI/ML
- **LLM:** Claude 3 Sonnet (Anthropic)
- **Embeddings:** Supabase embeddings (via pgvector)
- **RAG:** Custom implementation

### Deployment
- **Containerization:** Docker
- **Platform:** Railway
- **CI/CD:** GitHub Actions
- **Monitoring:** Custom health checks

### External Services
- **Telegram:** Bot API
- **Claude:** Anthropic API
- **Supabase:** PostgreSQL + pgvector
- **Notion:** API для синхронизации
- **Discord:** Bot API (для ingestion)

## Паттерны проектирования

### 1. Repository Pattern
```python
class KnowledgeRepository:
    def get_by_category(category: str) -> List[Document]
    def search(query: str) -> List[Document]
    def save(document: Document) -> None
```

### 2. Service Layer Pattern
```python
class RAGService:
    def search_and_rank(query: str) -> List[Document]

class ClaudeService:
    def generate_response(prompt: str) -> str
```

### 3. Adapter Pattern
```python
class TelegramAdapter:
    def receive_message() -> Message
    def send_message(text: str) -> None

class DiscordAdapter:
    def receive_data() -> Data
    def send_notification() -> None
```

### 4. Strategy Pattern
```python
class ResponseStrategy:
    class SummaryStrategy: # Краткий ответ
    class DetailedStrategy: # Подробный ответ
    class SourcesOnlyStrategy: # Только источники
```

### 5. Observer Pattern
```python
# Event-driven обновления
class EventBus:
    on_knowledge_updated()
    on_user_message_received()
    on_api_error()
```

## Интеграции

### Telegram ↔ JARVIS
```
User Message
    ↓
Telegram Bot API
    ↓
jarvis_bot.py (webhook/polling)
    ↓
Message Processing
    ↓
RAG + Claude
    ↓
Response
    ↓
Telegram API
    ↓
User receives message
```

### Knowledge Update ↔ Supabase
```
Markdown Files (knowledge_raw/)
    ↓
load_rag_base.py
    ↓
Parse & Chunk
    ↓
Generate Embeddings
    ↓
Supabase pgvector
    ↓
Vector Index Ready
```

### Notion ↔ JARVIS
```
knowledge_base.json
    ↓
migrate_to_notion.py
    ↓
Notion API
    ↓
Create/Update Pages
    ↓
Notion Database
```

### Discord ↔ JARVIS
```
Discord Channels
    ↓
sync_discord_data.py (scheduled)
    ↓
Download Messages/Files
    ↓
Parse Content
    ↓
knowledge_raw/
    ↓
Trigger load_rag_base.py
```

## Error Handling Strategy

```python
class ErrorHandler:
    def handle_api_error(error: APIError):
        1. Log with context
        2. Retry with exponential backoff
        3. Fallback to cached response
        4. Alert if critical

    def handle_rag_error(error: RAGError):
        1. Log query and error
        2. Return "Unable to find answer"
        3. Suggest related topics

    def handle_claude_error(error: ClaudeError):
        1. Check rate limits
        2. Retry with smaller context
        3. Use fallback response
        4. Alert admins
```

## Performance Considerations

### Latency Targets
- Message receipt to response: < 5 seconds (p95)
- RAG search: < 1 second
- Claude API call: < 3 seconds
- Embedding generation: < 100ms per chunk

### Scalability
- **User concurrency:** 1000+ simultaneous
- **Knowledge base:** 10,000+ documents
- **Queries/minute:** 1000+ qpm
- **Vector dimension:** 1536 (optimal for pgvector)

### Optimization Strategies
1. **Caching:** Query results, embeddings, responses
2. **Batching:** Multiple user requests
3. **Vector indexing:** IVFFlat + HNSW in Supabase
4. **Async operations:** Non-blocking I/O
5. **Connection pooling:** Database connections

---

**Last Updated:** March 2026
**Architecture Version:** 1.0.0
