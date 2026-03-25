# Tasks — JARVIS Trading Bot

> **Активная ветка для новых фич: `develop`**
> `main` = только стабильный образовательный бот, не трогать

---

## ✅ Фаза 1 — Качество базы знаний (ЗАВЕРШЕНО 2026-03-26)

**KB Audit: 95% · Model Audit: 80% · Git tag: `v1.0-phase1`**
Отчёты: `docs/kb_audit.md` · `docs/model_audit.md`

- [x] Аудит KB: 30 вопросов, 95% покрытие (`scripts/audit_kb.py --export`)
- [x] Аудит модели: 10 вопросов, 80% качество ответов (`scripts/audit_model.py --export`)
- [x] Удалены 10 дублей (220 → ~213 документов)
- [x] Расширены тонкие документы (stb_bts, supply demand, inducement, Lunch, IFVG, VI, RB)
- [x] Добавлены новые документы: Kill Zone, Gold sessions, Psychology
- [x] RAG fix: smart `_extract_search_term()` — вместо полного запроса как ilike
- [x] RAG fix: 3-pass keyword search (content+level → topic+level → content no filter)
- [x] pgvector fix: убрана дублирующая функция + filter_levels как pg array literal
- [x] Lowercase LEVEL_ORDER — совместим с DB constraint (`beginner/intermediate/advanced`)
- [x] Очищены стейл ветки: imac, macbook, production (локально)

---

## 🔴 Фаза 2 — TradingView интеграция (ТЕКУЩИЙ ПРИОРИТЕТ)

> Требуется: TradingView Pro (для webhook алертов)

### 2.1 Pine Script детекторы (на TradingView)
- [ ] **FVG детектор** — 3 свечи, бычий/медвежий, отображение зон
- [ ] **Order Block детектор** — последняя свеча перед импульсом
- [ ] **BOS/CHoCH детектор** — слом структуры с типом (bullish/bearish)
- [ ] **HTF trend filter** — SMA200 на D1, определяет направление дня
- [ ] **Session filter** — London KZ (02:00-05:00 NY), NY KZ (07:00-10:00 NY)
- [ ] Визуальная проверка на XAUUSD — сверить с Python бэктестом

### 2.2 Webhook сервер на VPS
- [ ] **FastAPI сервер** `src/webhook/server.py`
  - `POST /webhook/tradingview` — принимает JSON от TradingView
  - Валидация secret token (чтобы не принимать чужие алерты)
  - Сохранение в Supabase таблицу `trading_signals`
- [ ] **Supabase таблица** `trading_signals`
  - Поля: id, symbol, pattern, price, direction, session, tf, created_at
- [ ] **Telegram уведомление**
  - Формат: `📊 FVG Bull · XAUUSD · $2850.5 · London KZ · H1`
  - Отправка в бот (или отдельный канал)
- [ ] **TradingView алерт** — настроить alert → webhook URL на VPS
- [ ] **Тест end-to-end**: TradingView сигнал → VPS → Supabase → Telegram

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

- [ ] **Купить TradingView Pro** — нужен для webhook алертов (Фаза 2)
- [ ] **Удалить remote ветки** — `git push origin --delete imac macbook` (с Мака)
- [ ] **VPS pull + restart** после каждого `git push origin develop`
  ```bash
  ssh root@77.110.126.107 "cd /opt/jarvis && git pull origin develop && systemctl restart jarvis-bot"
  ```

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
