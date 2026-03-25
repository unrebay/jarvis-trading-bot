# JARVIS — Отчёт завершения Фазы 1
**Дата:** 2026-03-26
**Git tag:** `v1.0-phase1`
**Ветка:** `develop`

---

## Итоговые результаты аудита

| Проверка | Результат | Порог | Статус |
|---|---|---|---|
| KB Audit (30 вопросов) | **95%** | ≥80% | ✅ |
| Model Audit (10 вопросов) | **80%** | ≥80% | ✅ |
| Бот на VPS | `active (running)` | — | ✅ |
| pgvector semantic search | исправлен | — | ✅ |

---

## Что было сделано за сессию

### 🔧 Исправления RAG системы

**Проблема 1: keyword_search возвращал 0% для всех вопросов**
Причина: поиск использовал полный русский вопрос как ilike-паттерн ("Что такое BOS?") — никогда не совпадал с документами.
Решение: `_extract_search_term()` — умная экстракция термина из вопроса:
- ALL-CAPS акронимы: BOS, FVG, CHoCH, AMD, IFVG
- Title Case фразы: "Order Block", "Kill Zone", "Silver Bullet"
- Одиночные английские слова: Premium, Fibonacci
- Русские смысловые слова (без стоп-слов)

**Проблема 2: pgvector RPC ошибка `invalid input syntax for type integer`**
Причина 1: две перегруженные функции `match_knowledge_documents` — старая `(vector, float8, int, text)` и новая `(vector, float8, int, text[])`.
Решение: `DROP FUNCTION` для старой версии.
Причина 2: `supabase-py 2.x` некорректно сериализует Python list для `text[]` параметра.
Решение: передаём как PostgreSQL array literal: `"{beginner,intermediate}"`.

**Проблема 3: LEVEL_ORDER Title Case vs DB lowercase**
Причина: `LEVEL_ORDER = ["Intermediate"]` vs DB хранит `"intermediate"`.
Решение: LEVEL_ORDER теперь lowercase + `.lower()` нормализация входных данных.

**Проблема 4: /opt/jarvis/supabase/ директория теняет Python пакет**
Причина: Supabase CLI создаёт папку `supabase/` в проекте — Python находит её раньше реального пакета.
Решение: всегда запускать через venv (`source venv/bin/activate`).

---

### 📚 Улучшения базы знаний

**Новые документы добавлены в Supabase:**
- `kill_zone` — Kill Zone (London/NY/Asian), времена, пример XAUUSD
- `gold_sessions` — торговля Gold по сессиям, XAUUSD, Silver Bullet
- `trading_psychology` — работа с убытками, эмоции, FOMO, Revenge Trading

**Расширены тонкие документы:**
- IFVG: добавлены "inverted", "перевёрнут" для поиска
- Volume Imbalance: добавлен "имбаланс" (было только "дисбаланс")
- Rejection Block: добавлены "wick", "хвост", "отказ"
- stb_bts, supply demand zone, inducement, Lunch session

**Удалено дублей:** 10 документов (220 → ~213)

---

### 🧪 Инфраструктура аудита

**`scripts/audit_kb.py`** — 30 ICT/SMC вопросов × keyword scoring:
- Проверяет что RAG находит правильные документы
- 11 модулей: Structure, Liquidity, FVG/Blocks, Order Flow, TDA, Sessions, Risk, Psychology, Advanced
- `--export` сохраняет `docs/kb_audit.md`
- Результат: **95%**, все 11 модулей ≥60%

**`scripts/audit_model.py`** — 10 вопросов × полный пайплайн:
- Тестирует: вопрос → RAG → Claude Haiku → keyword scoring ответа
- Использует реальный системный промпт (`system/prompts/mentor.md`)
- OR-логика ключевых слов: `"хай|high|максимум"` — принимает любой вариант
- `--export` сохраняет `docs/model_audit.md`
- Результат: **80%**, 9/10 вопросов ≥60%

---

### 🔀 Git / Deploy

**Коммиты за сессию:**
```
ec6a491  feat(audit): add model quality audit (RAG + Claude Haiku, 80% score)
6fb6f62  docs(tasks): mark Phase 1 complete, Phase 2 active
ba716c9  fix(rag): filter_levels as pg array literal + kb_audit.md
515862a  fix(rag): normalize difficulty_level to lowercase
6fee9a0  fix(rag): smart keyword extraction + drop duplicate pgvector fn
fed001a  feat(audit): KB audit script + TASKS roadmap
```

**Тег:** `v1.0-phase1`
**VPS:** синхронизирован, `systemctl restart jarvis-bot` выполнен

---

## Текущая архитектура RAG

```
Вопрос пользователя
       │
       ▼
semantic_search()  ←── pgvector + OPENAI embeddings
  ├─ _embed(query)              → 1536-dim vector
  ├─ RPC match_knowledge_documents(vector, threshold=0.3, levels="{beginner,...}")
  └─ если 0 результатов → fallback:
       │
       ▼
keyword_search()   ←── 3-pass ilike
  ├─ Pass 1: _extract_search_term() + level filter
  ├─ Pass 2: topic field + level filter
  └─ Pass 3: content field, no level filter
       │
       ▼
format_context()   → Claude system prompt context
       │
       ▼
Claude Haiku → ответ пользователю
```

---

## Следующий шаг — Фаза 2

**Требуется:** TradingView Pro (для webhook алертов)

**Порядок работ:**
1. Pine Script: FVG + OB + BOS детекторы с HTF filter и Session filter
2. FastAPI webhook сервер на VPS (`POST /webhook/tradingview`)
3. Supabase таблица `trading_signals`
4. TradingView Alert → webhook → Telegram уведомление
5. End-to-end тест

**Приоритетный актив:** XAUUSD (Gold) — лучшие бэктест результаты, хорошо реагирует на ICT паттерны.
