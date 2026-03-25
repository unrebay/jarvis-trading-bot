# JARVIS Phase 2 — План Действий (актуализирован 2026-03-25)

**Этап:** Production Optimization & Feature Expansion
**Сроки:** 2026-03-22 → 2026-04-22 (1 месяц)
**Цель:** Стабильный production бот + chart vision + user memory

---

## ✅ Что уже сделано (на 2026-03-25)

### Инфраструктура
- ✅ **Bot deployed on Railway** — работает 24/7 (`python -m src.bot.main`)
- ✅ **Supabase** — production БД с 200 документами
- ✅ **GitHub** — ветки: `main` (production), `imac`, `macbook`, `production`
- ✅ **Бэкап KB** — `kb/knowledge_base_backup_2026-03-25.json` (200 docs)

### Knowledge Base (200 документов / 18 секций)
| Секция | Docs | Секция | Docs |
|---|---|---|---|
| market-mechanics | 37 | gold-mechanics | 10 |
| tda-and-entry-models | 27 | block-types | 9 |
| structure-and-liquidity | 23 | risk-management | 8 |
| principles | 20 | psychology | 8 |
| beginners | 17 | discipline | 7 |
| backtest | 7 | sessions | 6 |
| work-with-imbalance | 4 | inefficiency-types | 4 |
| order-flow-analysis | 4 | advanced-market-analysis | 4 |
| manipulations | 3 | timings | 2 |

**Источники:** silk-seahorse (67) + markdown (60) + stream-recording (56) + прочие (17)

### Архитектура бота (`src/bot/`)
- ✅ `telegram_handler.py` — все команды + handle_photo
- ✅ `claude_client.py` — Haiku/Sonnet/Opus routing + prompt caching
- ✅ `rag_search.py` — поиск по KB через Supabase embeddings
- ✅ `cost_manager.py` — дневные лимиты ($0/offline, $1/economy, $3/normal, $10/premium)
- ✅ `user_memory.py` — per-user portrait в Supabase (user_memory table)
- ✅ `lesson_manager.py` — структурированный курс + quiz
- ✅ `chart_generator.py` — live candlestick charts (yfinance + mplfinance)
- ✅ `chart_annotator.py` — ICT/SMC аннотации через Claude Vision
- ✅ `chart_drawer.py` — рисует зоны поверх графика (Pillow)
- ✅ `image_handler.py` — анализ скриншотов от пользователей

### Команды бота
- ✅ `/start`, `/help`, `/status`
- ✅ `/chart SYMBOL TF` — генерирует live chart + ICT/SMC анализ
- ✅ `/lesson [тема]` — структурированный урок
- ✅ `/quiz` — Telegram quiz poll
- ✅ `/progress` — прогресс обучения
- ✅ `/watch` — watchlist + TradingView webhooks
- ✅ Отправка фото → автоматический анализ графика

---

## ⚠️ Известные проблемы (2026-03-25)

### Проблема 1: `/chart` не работает (тест 2026-03-24)
**Симптом:** `/chart EURUSD 4h` не рисует график
**Возможные причины:**
1. **yfinance не может получить данные с Railway** — Yahoo Finance блокирует datacentre IP
2. **matplotlib требует display** — на headless сервере нужно `matplotlib.use('Agg')` _до_ первого импорта
3. **Тайм-аут yfinance** — нет явного timeout, зависает

**Что проверить:**
```bash
# На Railway, в консоли:
python3 -c "import yfinance as yf; df = yf.download('GC=F', period='5d'); print(df.tail())"
python3 -c "import matplotlib; matplotlib.use('Agg'); import mplfinance; print('OK')"
```

**Фикс (если yfinance заблокирован):**
- Перейти на Binance API для крипто, Twelve Data / Polygon.io для форекс/индексы
- Или добавить fallback: если yfinance fail → ответить текстовым анализом

### Проблема 2: Три баги из v2.6-анализа (LOW/MEDIUM priority)
- BUG #1: Markdown fallback без логирования (telegram_handler.py:560)
- BUG #2: Race condition в cost_manager (MEDIUM — нужен комментарий)
- BUG #3: JSON parse в lesson_manager без try/except

---

## 📅 Неделя 1-2 (2026-03-25 → 2026-04-05) — ТЕКУЩИЙ ФОКУС

### Задача 1: Починить `/chart` ⭐ ПРИОРИТЕТ 1
1. Залогировать конкретную ошибку на Railway (`journalctl` / Railway logs)
2. Если yfinance заблокирован → заменить на рабочий источник данных
3. Убедиться что `matplotlib.use('Agg')` стоит в самом начале chart_generator.py
4. Добавить явный timeout (10 сек) и fallback сообщение

### Задача 2: Улучшить handle_photo
**Текущий статус:** код есть, но требует /analyze caption или просто фото → анализирует
**Что улучшить:**
- Добавить подсказку в ответе: "Пришли график с подписью инструмента для точного анализа"
- Сократить время ответа (сейчас может быть медленно — Opus model)
- Добавить в /help что можно отправить фото для анализа

### Задача 3: Исправить 3 баги из v2.6 (LOW effort, HIGH reliability)
- Файлы: `telegram_handler.py:560`, `cost_manager.py:108`, `lesson_manager.py:184`

---

## 📅 Неделя 2-3 (2026-04-05 → 2026-04-15) — СЛЕДУЮЩИЙ ФОКУС

### Задача 4: User Memory improvements
**Текущий статус:** таблица user_memory есть, базовая реализация есть
**Что добавить:**
- Команда `/profile` — показать что бот помнит о пользователе
- Персонализированные ответы на основе слабых мест (weaknesses в memory)
- Рекомендации: "Судя по твоим вопросам, стоит изучить X"

### Задача 5: Расширить KB (слабые секции)
**Timings (2 docs)** → добавить больше материала по таймингам Лондон/NY
**Manipulations (3 docs)** → типы манипуляций, stop hunts
**Advanced Market Analysis (4 docs)** → PO3, STDV, weekly profiles

---

## 📅 Неделя 4 (2026-04-15 → 2026-04-22)

### Задача 6: Обновить mentor.md по фидбеку
- Собрать топ-10 вопросов от пользователей
- Оценить качество ответов
- Итерировать на промпте

### Задача 7: Документация
- Bot User Manual (для учеников)
- Admin Manual (как обновлять KB)

---

## 🎯 Critical Path

```
Сейчас: Починить /chart → Улучшить handle_photo → Фикс 3 багов
    ↓
Апрель: User memory /profile → KB слабые секции
    ↓
Конец апреля: mentor.md v2 → Документация → Phase 3 planning
```

---

## 📊 KPI (цели на конец апреля)

| Метрика | Текущее | Цель |
|---|---|---|
| Docs в KB | 200 ✅ | 200+ |
| /chart работает | ❌ broken | ✅ |
| handle_photo | ✅ есть | ✅ стабильно |
| Avg response time | ? | < 3s |
| Error rate | ? | < 1% |
| Monthly cost | ? | < $30 |

---

## 💰 Бюджет

```
Claude API (Haiku основа, Sonnet для анализа):  $10-20/мес
Railway:                                         ~$5/мес
Supabase (free tier):                            $0
──────────────────────────────────────────────
Total:                                           ~$15-25/мес
```

---

## 🔗 Файлы

- `src/bot/` — основной код бота
- `kb/knowledge_base_backup_2026-03-25.json` — бэкап БД (200 docs)
- `system/prompts/mentor.md` — системный промпт JARVIS
- `RELEASE-v2.6-ANALYSIS.md` — детальный анализ кода и 3 найденных бага
- `ARCHITECTURE-FULL.md` — полная архитектура системы
- `supabase/` — схемы таблиц

---

*Последнее обновление: 2026-03-25 | Claude @ Cowork*
