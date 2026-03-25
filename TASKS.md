# Tasks — JARVIS Trading Bot

> **Активная ветка для новых фич: `develop`**
> `main` = только стабильный образовательный бот, не трогать

---

## ✅ Фаза 1 — Качество базы знаний (ЗАВЕРШЕНО 2026-03-25)

**Результат: 95% покрытие, 30/30 вопросов ≥ 60%, все 11 модулей зелёные**
Отчёт: `docs/kb_audit.md`

- [x] Аудит KB: 30 ключевых ICT вопросов (`scripts/audit_kb.py`)
- [x] Удалены 10 дублей (220 → 210 документов)
- [x] Расширены тонкие документы (stb_bts, supply demand, inducement, Lunch, IFVG, VI, RB)
- [x] Добавлены новые документы: Kill Zone, Gold sessions, Psychology
- [x] RAG fix: smart `_extract_search_term()` — вместо полного запроса как ilike
- [x] pgvector fix: убрана дублирующая функция + filter_levels как pg array literal
- [x] Lowercase LEVEL_ORDER — совместим с DB constraint

---

## 🔴 Фаза 2 — TradingView интеграция (ТЕКУЩИЙ ПРИОРИТЕТ)

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
