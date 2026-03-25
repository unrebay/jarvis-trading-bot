# Tasks — JARVIS Trading Bot

## Active

- [ ] **Multi-asset бэктест** — запустить на VPS/локально, вставить результаты в docs/
  ```bash
  python3 scripts/backtest_patterns.py --multi 2>&1 | tee docs/multi_backtest_$(date +%F).txt
  ```
  - BTC-USD, Gold (GC=F), EURUSD=X, NQ=F, ES=F — все 1d 365d
  - Сводная таблица паттерн × актив выводится автоматически
  - Обновить `docs/backtest-results.md` с результатами

- [ ] **Freqtrade стратегия** - `freqtrade_strategy/JarvisICT.py`
  - Использовать детекторы из `src/patterns/` как условия входа
  - Только паттерны с win rate > 50% из бэктеста
  - Backtesting через freqtrade backtesting
  - Документация по установке freqtrade и запуску

- [ ] **Расширить базу знаний до 500+ документов**
  - Добавить структурированные примеры сетапов (вход, стоп, цель, скриншот)
  - Добавить Q&A пары для файн-тюнинга
  - Форматировать как structured training data

## Waiting On

- [ ] **Проверить что images работают в боте** - ждём подтверждения от пользователя
  - `/example FVG`, `/example Order Block` должны присылать картинки
  - auto-image при фразах "покажи пример FVG" и т.п.

## Someday

- [ ] Webhook режим вместо polling (надёжнее на VPS)
- [ ] Улучшить онбординг `/start` — интерактивный первый урок
- [ ] Нотификации о рыночных событиях через watchlist
- [ ] Fine-tune модель на Q&A парах из curriculum

## Done

- [x] ~~Детекторы паттернов src/patterns/ (FVG, OB, BOS, CHoCH, LiqSweep)~~ (2026-03-25)
- [x] ~~Бэктест скрипт scripts/backtest_patterns.py~~ (2026-03-25)
- [x] ~~Бэктест BTC-USD 4h: bos_bear 57%, sweep_bear 50% → кандидаты для freqtrade~~ (2026-03-25)
- [x] ~~Fix yfinance TypeError (multi_level_index=False + robust column flatten)~~ (2026-03-25)
- [x] ~~Добавить --multi флаг: batch по BTC/Gold/EURUSD/NQ/ES + сводная таблица~~ (2026-03-25)
- [x] ~~docs/backtest-results.md с первыми результатами и рекомендациями~~ (2026-03-25)
- [x] ~~Починить pgvector semantic search (параметры + регистр уровней)~~ (2026-03-25)
- [x] ~~CI smoke test из requirements.txt~~ (2026-03-25)
- [x] ~~Safe JobQueue init (try/except, non-fatal)~~ (2026-03-25)
- [x] ~~Ежедневные напоминания (DailyReminder, JobQueue 09:00 UTC)~~ (2026-03-25)
- [x] ~~21 диаграмма ICT/SMC в Supabase Storage~~ (2026-03-25)
- [x] ~~`/example` команда + auto-image в handle_message~~ (2026-03-25)
- [x] ~~`/stats` admin команда~~ (2026-03-25)
- [x] ~~RAG с фильтрацией по уровню (pgvector + keyword fallback)~~ (2026-03-25)
- [x] ~~Починить падение бота (PTB job-queue extra в requirements.txt)~~ (2026-03-25)
