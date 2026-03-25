# Tasks — JARVIS Trading Bot

## Active

- [ ] **Запустить бэктест паттернов на реальных данных** - `python3 scripts/backtest_patterns.py`
  - BTC-USD 4h 180d (основной тест)
  - Проверить win rate каждого паттерна, отсечь неэффективные
  - Результаты → задокументировать в docs/

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
- [x] ~~Починить pgvector semantic search (параметры + регистр уровней)~~ (2026-03-25)
- [x] ~~CI smoke test из requirements.txt~~ (2026-03-25)
- [x] ~~Safe JobQueue init (try/except, non-fatal)~~ (2026-03-25)
- [x] ~~Ежедневные напоминания (DailyReminder, JobQueue 09:00 UTC)~~ (2026-03-25)
- [x] ~~21 диаграмма ICT/SMC в Supabase Storage~~ (2026-03-25)
- [x] ~~`/example` команда + auto-image в handle_message~~ (2026-03-25)
- [x] ~~`/stats` admin команда~~ (2026-03-25)
- [x] ~~RAG с фильтрацией по уровню (pgvector + keyword fallback)~~ (2026-03-25)
- [x] ~~Починить падение бота (PTB job-queue extra в requirements.txt)~~ (2026-03-25)
