# Tasks — JARVIS Trading Bot

> **Активная ветка для новых фич: `develop`**
> `main` = только стабильный образовательный бот, не трогать

---

## 🔴 Фаза 1 — Качество базы знаний (ТЕКУЩИЙ ПРИОРИТЕТ)

> Пока KB не проверена на правильность ответов — торговую часть не трогаем.

- [ ] **Аудит KB: прогнать 30 ключевых ICT вопросов**
  - Записать ответы бота, отметить правильные / неправильные
  - Цель: 90%+ правильных ответов на базовые концепции курса
  - Скрипт: `scripts/audit_kb.py`

- [ ] **Устранить дубли тем** (160+ тем → ~80 качественных)
  - market-structure (beginner/intermediate/advanced/Структура рынка → 1 тема)
  - liquidity, FVG, order-flow, inducement — аналогично
  - Скрипт: `scripts/deduplicate_kb.py`

- [ ] **Заполнить тонкие документы** (10 штук < 600 симв.)
  - stb_bts (337 симв.), Indices Mechanics homework (303 симв.)
  - supply demand zone, inducement beginner, gap

- [ ] **Стандартизировать имена тем** (English only, snake_case)
  - Убрать кириллические названия тем
  - Привести к формату: `fair_value_gap`, `order_block`, `bos_choch`

- [ ] **Загрузить материалы курса которых не хватает**
  - channels.txt, channels2.txt — не представлены в KB
  - Проверить полное покрытие всех 20 модулей курса

---

## 🟡 Фаза 2 — TradingView интеграция (после Фазы 1)

- [ ] **Pine Script: перенести 5 детекторов**
  - FVG, Order Block, BOS, CHoCH, Liquidity Sweep
  - + HTF trend filter (SMA200 daily)
  - + Session filter (London 08:00-10:00, NY 13:30-15:30 UTC)
  - Визуально сверить с нашим Python бэктестом на XAUUSD

- [ ] **Webhook сервер на VPS**
  - FastAPI `POST /webhook/tradingview`
  - Схема JSON: symbol, pattern, price, strength, session, direction
  - Запись в Supabase таблицу `trading_signals`
  - Telegram уведомление: "📊 FVG Bull · XAUUSD · 2850.5 · London"

---

## 🟡 Фаза 3 — Бэктесты XAUUSD (после Фазы 2)

- [ ] **500+ сделок на XAUUSD**
  - Разные периоды: 1y, 2y
  - Разные таймфреймы: 1d, 4h, 1h
  - С сессионным фильтром и без — сравнить результаты
  - Зафиксировать параметры при WR > 50% стабильно

- [ ] **Сравнить: Python симуляция vs freqtrade backtesting**
  - Установить freqtrade, прогнать те же данные
  - Разница > 10% → найти причину

---

## 🟡 Фаза 4 — Demo счёт (после Фазы 3)

- [ ] **freqtrade dry-run на Bybit, актив XAUUSDT**
  - Минимум 3 недели наблюдения
  - Логировать каждый вход: почему бот открыл?
  - Сравнивать с ручным ICT-анализом

---

## ⏳ Waiting On

- [ ] **Push develop ветки** — сделать `git push -u origin develop` с локальной машины
- [ ] **Купить TradingView Pro** — нужен для webhook алертов
- [ ] **Проверить что images работают в боте**
  - `/example FVG`, `/example Order Block` → должны присылать картинки

---

## 💡 Someday

- [ ] Webhook режим вместо polling (надёжнее на VPS)
- [ ] Fine-tune модель на Q&A парах из curriculum
- [ ] Улучшить онбординг `/start` — интерактивный первый урок
- [ ] Нотификации о рыночных событиях через watchlist
- [ ] Фаза 5: живой счёт с минимальным объёмом (только после Фазы 4)

---

## ✅ Done

- [x] ~~develop ветка создана локально~~ (2026-03-25)
- [x] ~~Multi-asset бэктест: Gold/EURUSD/NQ/ES 1d 365d — docs/backtest-results.md~~ (2026-03-25)
- [x] ~~Fix yfinance TypeError + --multi флаг + сводная таблица~~ (2026-03-25)
- [x] ~~Детекторы паттернов src/patterns/ (FVG, OB, BOS, CHoCH, LiqSweep)~~ (2026-03-25)
- [x] ~~Бэктест скрипт scripts/backtest_patterns.py~~ (2026-03-25)
- [x] ~~Починить pgvector semantic search (параметры + регистр уровней)~~ (2026-03-25)
- [x] ~~CI smoke test из requirements.txt~~ (2026-03-25)
- [x] ~~Safe JobQueue init (try/except, non-fatal)~~ (2026-03-25)
- [x] ~~Ежедневные напоминания (DailyReminder, JobQueue 09:00 UTC)~~ (2026-03-25)
- [x] ~~21 диаграмма ICT/SMC в Supabase Storage~~ (2026-03-25)
- [x] ~~`/example` команда + auto-image~~ (2026-03-25)
- [x] ~~RAG с фильтрацией по уровню (pgvector + keyword fallback)~~ (2026-03-25)
- [x] ~~Починить падение бота (PTB job-queue extra)~~ (2026-03-25)
