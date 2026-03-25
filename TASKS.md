# Tasks — JARVIS Trading Bot

## Active

- [ ] **Починить pgvector RPC** - `match_knowledge_documents` возвращает 404, семантический поиск не работает (только keyword fallback)
  - Проверить что функция существует в Supabase, пересоздать если нет
  - Проверить что pgvector extension включён

- [ ] **Защитный слой при деплое** - новые фичи не должны ронять бота целиком
  - Обернуть JobQueue init в try/except (если APScheduler не установлен — логируем, продолжаем без напоминаний)
  - Добавить smoke-test в CI: реально импортировать src.bot.main и проверить что не падает
  - Добавить health-check endpoint для мониторинга

- [ ] **Написать детекторы ICT/SMC паттернов** - модуль `src/patterns/`
  - `detect_fvg(df)` — Fair Value Gap на OHLCV данных
  - `detect_order_block(df)` — бычий/медвежий Order Block
  - `detect_bos(df)` — Break of Structure
  - `detect_liquidity_sweep(df)` — sweep внешней ликвидности
  - Каждая функция: принимает pandas DataFrame, возвращает список сигналов с координатами и силой
  - Unit-тесты на исторических данных

- [ ] **Расширить базу знаний до 500+ документов**
  - Добавить структурированные примеры сетапов для каждого концепта (вход, стоп, цель)
  - Добавить Q&A пары для файн-тюнинга
  - Форматировать как structured training data

- [ ] **Freqtrade стратегия** - `freqtrade_strategy/JarvisICT.py`
  - Использовать детекторы из `src/patterns/` как условия входа
  - Backtesting через freqtrade Hyperopt
  - Документация по настройке и запуску

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

- [x] ~~Ежедневные напоминания (DailyReminder, JobQueue 09:00 UTC)~~ (2026-03-25)
- [x] ~~21 диаграмма ICT/SMC в Supabase Storage~~ (2026-03-25)
- [x] ~~`/example` команда + auto-image в handle_message~~ (2026-03-25)
- [x] ~~`/stats` admin команда~~ (2026-03-25)
- [x] ~~RAG с фильтрацией по уровню (pgvector + keyword fallback)~~ (2026-03-25)
- [x] ~~Починить падение бота (PTB job-queue extra в requirements.txt)~~ (2026-03-25)
