# JARVIS Diagnostic Report — 2026-03-25

**Исполнитель:** Claude @ Cowork
**Охват:** весь репозиторий, Supabase KB, Railway deployment, архитектура

---

## 🔴 КРИТИЧНО (блокируют работу)

### 1. Production отстаёт на 7 коммитов — imac ≠ main

`main` (production на Railway) **не содержит** этих изменений из `imac`:

| Коммит | Что включает |
|---|---|
| `e2cf9b1` | `scripts/download_discord_media.py` — новый скрипт |
| `c25e552` | fix: SUPABASE_KEY alias (видео-ingest ломался) |
| `5e65711` | **mentor.md v2** (132 строки), Discord monitor, KB enrich |
| `0c571cd` | **fix: PTB 21.x** (python-telegram-bot) |
| `81a9acb` | **fix: httpx==0.27.2** (supabase конфликт) |
| `304fe5e` | fix: ci.yml fetch-depth |
| `a3b1eda` | бэкап KB + этот план |

**Последствие:** Railway использует старый `requirements.txt` (PTB 20.7 вместо 21.x) и старый `mentor.md`. Потенциально бот работает на нестабильной версии зависимостей.

**Действие: смержить `imac` → `main` → Railway задеплоится автоматически.**

---

### 2. `/chart` не работает — yfinance заблокирован на Railway

**Диагноз:** Yahoo Finance активно блокирует запросы с datacenter IP (AWS/GCP/Railway — известная проблема yfinance). Пользователь получает: `❌ Ошибка загрузки данных: ...` или тайм-аут.

**Код работает правильно** — архитектура `ChartGenerator → ChartAnnotator → ChartDrawer` построена грамотно. Проблема только в источнике данных.

**Варианты фикса (по сложности):**

| Вариант | Сложность | Надёжность | Цена |
|---|---|---|---|
| **A. Binance WebSocket API** (крипто) | Средняя | ✅ Надёжная | Бесплатно |
| **B. Twelve Data** (форекс/индексы) | Низкая | ✅ Надёжная | Бесплатно 800 req/day |
| **C. yfinance + proxy** (User-Agent spoof) | Низкая | ⚠️ Ненадёжная | Бесплатно |
| **D. TradingView screenshot** через Chrome | Высокая | ✅ Идеально | Бесплатно |

**Рекомендация:** Вариант B (Twelve Data) для форекс/индексы + вариант A (Binance) для крипто. Оба API бесплатны и работают с Railway.

---

## 🟡 ВАЖНО (ухудшают опыт)

### 3. `/profile` не существует, хотя user_memory реализован

`user_memory.py` полностью рабочий — хранит в Supabase: имя, опыт, уровень, темп обучения, слабые места, историю разговоров. Но **нет команды для просмотра**. Ученик не знает что бот его помнит.

**Добавить:** `/profile` → выводит что JARVIS знает о пользователе + кнопка сброса.

---

### 4. Curriculum в lesson_manager устарел — не использует 200 docs KB

`CURRICULUM` в `lesson_manager.py` содержит ~20 тем. KB имеет 200 документов в 18 секциях. Когда пользователь делает `/lesson FVG`, бот ищет тему через RAG в KB — это работает. Но **список тем в `/lesson` не отражает богатство KB**.

**Текущий список (скудный):**
```
Beginner: Market Structure, Support/Resistance, BOS, CHoCH, Liquidity, Risk Management
Intermediate: FVG, Order Block, Breaker Block, POI, Premium/Discount...
Advanced: Entry Model, AMD, ICT Killzones, Mitigation Block...
```

**KB содержит но не в curriculum:**
- Gold Mechanics (10 docs) — нет в curriculum
- Backtest (7 docs) — нет
- Psychology/Discipline (15 docs) — нет
- Sessions (6 docs) — нет
- TDA/Entry Models (27 docs) — частично
- Advanced Market Analysis (4 docs) — нет

---

### 5. handle_photo: нет feedback пользователю при низком качестве анализа

Когда ученик отправляет фото, бот отвечает:
`"🔍 Анализирую ICT/SMC структуру..."`
→ возвращает аннотированный график.

Но если Haiku не уверен в паттернах (confidence < 0.5), нет предупреждения. Пользователь не понимает что анализ может быть неточным.

Также: ChartAnnotator использует `VISION_MODEL = "claude-haiku-4-5-20251001"` — Haiku имеет слабее vision-способности чем Sonnet. Для ICT/SMC анализа это критично: Haiku часто не различает OB от FVG.

**Рекомендация:** переключить на Sonnet для chart analysis (разница в цене ~$0.01-0.03 за анализ, но качество значительно лучше).

---

### 6. 3 известных бага (из RELEASE-v2.6-ANALYSIS.md)

| # | Файл | Строка | Severity | Описание |
|---|---|---|---|---|
| 1 | `telegram_handler.py` | ~560 | MEDIUM | Markdown fallback без logging — трудно дебажить |
| 2 | `cost_manager.py` | ~108 | LOW | Race condition (безопасно из-за GIL, но нет комментария) |
| 3 | `lesson_manager.py` | ~184 | LOW | `json.loads()` без try/except — падает при кривом JSON от Claude |

---

## 🟢 ЧТО РАБОТАЕТ ХОРОШО

| Компонент | Статус | Комментарий |
|---|---|---|
| Telegram Bot (Railway) | ✅ Live | Отвечает на сообщения |
| RAG поиск по KB | ✅ | Supabase + embeddings |
| ClaudeClient (Haiku/Sonnet/Opus) | ✅ | Роутинг + prompt caching |
| UserMemory (Supabase) | ✅ | Портрет ученика сохраняется |
| CostManager ($1/день) | ✅ | Лимиты работают |
| /lesson + /quiz | ✅ | Уроки + Telegram quiz polls |
| handle_photo | ✅ | Принимает скриншоты, анализирует |
| mentor.md (132 строк) | ✅ | Хороший промпт, ICT/SMC терминология |
| ChartAnnotator + ChartDrawer | ✅ | Код работает, только источник данных сломан |
| KB: 200 документов | ✅ | 18 секций, 11 источников, backup есть |
| CI (GitHub Actions) | ✅ | Syntax check на push в imac/macbook |

---

## 📋 ПЛАН ДЕЙСТВИЙ (приоритизировано)

### Немедленно (этот спринт):

**P0 — Мерж imac → main** (5 мин, делает Andy на iMac):
```bash
git checkout main
git merge imac --no-ff
git push origin main   # Railway задеплоится автоматически
```

**P1 — Починить `/chart`** (~2-3 часа разработки):
1. Получить API ключ Twelve Data (бесплатно, без карты)
2. Заменить `yfinance.download()` на `requests.get(twelve_data_url)`
3. Для крипто: Binance public API (без ключа)
4. Добавить timeout=10 + внятный fallback message

**P2 — Haiku → Sonnet для chart analysis** (~15 мин):
```python
# В chart_annotator.py строка 43:
VISION_MODEL = "claude-sonnet-4-6"  # было: claude-haiku-4-5-20251001
```

**P3 — Fix Bug #3 lesson_manager.py** (~10 мин):
```python
try:
    questions = json.loads(text.strip())
except json.JSONDecodeError as e:
    print(f"⚠️ Quiz JSON parse error: {e}")
    return []
```

### Следующий спринт:

**P4 — Добавить `/profile` команду** (~1 час):
- Показывает что JARVIS знает о пользователе
- Кнопки: "Сбросить память", "Изменить уровень"

**P5 — Расширить CURRICULUM** (~30 мин):
- Добавить Gold Mechanics, Backtest, Psychology, Sessions темы
- Связать топики с реальными секциями KB

**P6 — Добавить confidence warning в handle_photo** (~30 мин):
- Если все паттерны с confidence < 0.6: "Анализ неуверенный — пришли более чёткий скриншот"

**P7 — Добавить Bug #1 + #2 фиксы** (~20 мин)

---

## 📊 Итоговая оценка здоровья проекта

| Категория | Оценка | Комментарий |
|---|---|---|
| Архитектура кода | 9/10 | Чистая, модульная, хорошо структурирована |
| KB качество | 8/10 | 200 docs, некоторые секции маловаты |
| Bot функциональность | 6/10 | Chart сломан, profile нет |
| Production стабильность | 7/10 | 7 коммитов не смержены |
| Безопасность | 9/10 | .env не в гите, CostManager есть |
| Тесты | 2/10 | tests/ пустой (только папки) |
| **ИТОГО** | **7/10** | Хороший фундамент, несколько быстрых фиксов |

---

*Создан: 2026-03-25 | Следующая диагностика: после фикса /chart*
