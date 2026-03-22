# Merge Plan — MacBook feature/v2-architecture → main

> Статус: ОЖИДАЕТ СОГЛАСОВАНИЯ
> Дата: 2026-03-22
> Бэкап: jarvis-trading-bot-BACKUP-2026-03-22 (20MB, полная копия)
> Анализ: полный просмотр всех файлов MacBook ветки

---

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (нужно исправить ДО merge)

### 1. `.env` закоммичен в git!
MacBook случайно запушил реальный `.env` с токенами в ветку.
**Файл виден всем на GitHub прямо сейчас.**
**Действие:** Удалить из истории git + сменить токены если они утекли.

### 2. `requirements.txt` — не хватает `supabase`
`jarvis_bot.py` v2 делает `from supabase import create_client` — но в requirements.txt этого пакета нет!
Бот упадёт при старте с `ModuleNotFoundError`.
**Действие:** Добавить `supabase>=2.0.0` в requirements.txt.

### 3. Хардкоженный путь в `claude_client.py`
```python
open("/sessions/brave-exciting-pascal/mnt/outputs/system/prompts/mentor.md")
```
Это путь к MacBook-сессии. На VPS и iMac файл не найдёт.
**Действие:** Изменить на относительный путь `"system/prompts/mentor.md"` + fallback промпт уже есть.

### 4. `jarvis.service` запускает несуществующий файл
```
ExecStart=/opt/jarvis/venv/bin/python3 /opt/jarvis/bot/main.py
```
У нас нет `bot/main.py` — бот живёт в `jarvis_bot.py` (корень).
**Действие:** Исправить на `/opt/jarvis/jarvis_bot.py` или создать `bot/main.py` как точку входа.

### 5. Submodule-артефакт
В ветке есть `jarvis-trading-bot` как git submodule (указывает сам на себя). Не нужен, нужно убрать.

---

## 📋 ЧТО БЕРЁМ С MACBOOK (файл за файлом)

### ✅ Новые файлы (конфликтов нет — просто добавить)

| Файл | Путь в репо | Правки перед merge |
|------|------------|-------------------|
| `claude_client.py` | `bot/logic/claude_client.py` | Исправить путь к mentor.md → `system/prompts/mentor.md` |
| `__init__.py` | `bot/logic/__init__.py` | Без правок |
| `deploy.sh` | `deploy/deploy.sh` | Без правок |
| `Makefile` | `deploy/Makefile` | Без правок |
| `jarvis.service` | `deploy/jarvis.service` | Исправить `bot/main.py` → `jarvis_bot.py` |
| `mentor.md` | `system/prompts/mentor.md` | Без правок — отличный промпт |
| `SETUP.md` | `docs/SETUP.md` | Без правок |
| `ARCHITECTURE.md` | `docs/MACBOOK-ARCHITECTURE.md` | Сохранить, не перезаписывать наш architecture.md |
| `schema.sql` | `supabase/schema.sql` | Без правок — для справки |
| `.env.example` | `.env.example` | Без правок — более полный чем старый |

### ⚔️ Конфликтные файлы (наша версия vs MacBook)

| Файл | Победитель | Причина |
|------|-----------|---------|
| `jarvis_bot.py` | ✅ MacBook v2 | Supabase + история диалогов = лучше |
| `.gitignore` | ✅ MacBook | Более полный (добавляет `.env`, `env/`, `logs/`) |
| `requirements.txt` | 🔀 Merge | MacBook: `anthropic==0.49.0` (апгрейд). Мы: старая версия. Объединить + добавить `supabase` |

### ❌ НЕ БЕРЁМ с MacBook

| Файл/Папка | Причина |
|-----------|---------|
| `schemas/` (в корне) | Наш `system/schemas/` полнее — 8 схем vs 4 у MacBook |
| `jarvis-trading-bot` (submodule) | Артефакт, не нужен |
| `.env` | Безопасность — не трогать |
| `docs/ARCHITECTURE.md` | Сохраним как отдельный файл чтобы не перезаписать наш `architecture.md` |

### ✅ НАШИ ФАЙЛЫ (MacBook не создавал — полностью сохранить)

| Что | Где |
|-----|-----|
| 63 .md файла | `knowledge/raw/**` |
| 8 JSON схем | `system/schemas/` |
| 3 skills | `system/skills/` |
| Ingestion state | `system/progress/discord_ingestion_state.json` |
| Документация | `docs/architecture.md`, `docs/action-plan.md`, `docs/full-context-prompt.md`, `docs/extensions-evaluation.md` |
| Operations | `operations/*.md` |
| Пустые dirs | `knowledge/lessons/`, `knowledge/rules/` и т.д., `strategies/`, `media/` |

---

## ⚠️ НЕСООТВЕТСТВИЕ SUPABASE ТАБЛИЦ

MacBook создал таблицы (в прошлой сессии): `bot_users`, `conversations`, `knowledge_documents`
`jarvis_bot.py` v2 ожидает: `bot_users`, `conversations` — **совпадает** ✅

Но `schema.sql` от MacBook определяет: `users` (не `bot_users`) — **несовпадение**
`schema.sql` — это "задуманная" схема, уже устаревшая. Реально работает то что в Supabase.
**Действие:** `schema.sql` оставляем как историческую справку, не применяем.

---

## 📦 ИТОГОВЫЙ requirements.txt после merge

```
python-telegram-bot==20.7
python-dotenv==1.0.0
anthropic==0.49.0
supabase>=2.0.0
```

---

## 🔒 ЧТО НУЖНО СДЕЛАТЬ ТЕБЕ (вручную)

1. **Сменить токены** если `.env` лежал открытым:
   - Telegram: @BotFather → `/revoke`
   - Anthropic: console.anthropic.com → API Keys → Revoke & create new
   - Supabase: settings → API → Rotate anon key

2. **Удалить `.env` из git-истории** (я скажу точные команды)

---

## 📥 ПОРЯДОК ВЫПОЛНЕНИЯ MERGE (я делаю после твоего OK)

1. Исправить `claude_client.py` (путь к mentor.md)
2. Исправить `jarvis.service` (путь к main файлу)
3. Скопировать все новые файлы из MacBook ветки
4. Обновить `jarvis_bot.py` → v2 с MacBook
5. Обновить `.gitignore` → версия MacBook
6. Обновить `requirements.txt` → merge + add supabase
7. Сохранить `.env.example` → полная версия MacBook

**Бэкап сделан. Ничего не трогаю до твоего подтверждения.**
