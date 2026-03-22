# JARVIS Phase 2 — План Действий

**Этап:** Production Deployment & Knowledge Expansion
**Сроки:** 2026-03-22 → 2026-04-22 (1 месяц)
**Цель:** Production bot + 100+ документов

---

## 📅 Неделя 1 (2026-03-22 → 2026-03-29)

### Задача 1: Deploy Bot на VPS ⭐ ПРИОРИТЕТ 1

**Что:** Запустить `jarvis_bot.py` на VPS и протестировать в Telegram

**Шаги:**

1. **Подготовить VPS окружение**
   ```bash
   # На iMac/MacBook:
   git push origin feature/v2-architecture  # push MacBook changes
   git merge --no-ff feature/v2-architecture # merge в main
   git push origin main
   ```

2. **На VPS:**
   ```bash
   cd /opt && git clone https://github.com/user/jarvis-trading-bot.git
   cd jarvis-trading-bot
   bash deploy/deploy.sh
   make deploy  # systemd setup
   ```

3. **Проверить статус:**
   ```bash
   systemctl status jarvis
   journalctl -u jarvis -f  # real-time logs
   ```

4. **Тест в Telegram:**
   - Отправить сообщение боту
   - Проверить response (должен быть в течение 2-3 сек)
   - Смотреть logs на предмет ошибок

**Критерии успеха:**
- ✅ Bot активен 24/7
- ✅ Отвечает на сообщения
- ✅ История сохраняется в БД
- ✅ Költség < $1/день

**Ответственный:** Andy (iMac/MacBook)

---

### Задача 2: Мониторинг & Оптимизация

**Что:** Собирать метрики и оптимизировать

**Метрики to track:**
- Среднее время ответа (target: < 2s)
- Успешные/ошибочные запросы (target: > 99%)
- Стоимость per message (target: < $0.001)
- Очереди (queue depth)

**Действия:**
1. Настроить логирование в Supabase (cost per message)
2. Наблюдать за первыми 100 сообщениями от реальных юзеров
3. Итерировать на prompts если нужно

---

### Задача 3: Установить Расширения

**GitHub MCP:**
```
Claude Desktop → Settings → Extensions → Add MCP Server
URL: https://api.githubcopilot.com/mcp
```

**Claude Memory:**
```
Claude Desktop → Settings → Features → Enable Claude Memory
```

---

## 📅 Неделя 2-3 (2026-03-30 → 2026-04-12)

### Задача 4: Расширить Knowledge Base ⭐ ПРИОРИТЕТ 2

**Цель:** 39 → 100+ документов

**Источники контента:**

1. **Discord Scraping** (~60 документов)
   - ✅ `beginners/` — 3 docs (done)
   - ✅ `principles/` — 20 docs (done)
   - ✅ `market-mechanics/` — 10 docs (done)
   - ⏳ `wyckoff/` — ?  docs (next)
   - ⏳ `advanced/` — ? docs
   - ⏳ `PSYCHO/` — ? docs
   - ⏳ `FUNDAMENTAL/` — ? docs
   - ⏳ `MARKET PROFILE/` — ? docs
   - ⏳ `DT LIBRARY/` — ? docs

2. **Notion Export** (~20 документов)
   - news-macro-analysis (8 pages lost, re-scrape)
   - video-materials-library
   - research-notes

3. **Live Trading Logs** (~10 документов)
   - Real P&L examples
   - Trade reviews
   - Case studies

**Процесс:**
1. Discord export → `knowledge_base.json`
2. `load_knowledge_to_supabase.py --reset` (skip existing)
3. Test search queries
4. Iterate on content

**Ответственный:** Andy (iMac + Chrome MCP for scraping)

---

### Задача 5: Обучение Бота на Примерах

**Что:** Fine-tune prompts на основе реальных диалогов

**Процесс:**
1. Собрать топ-10 вопросов от пользователей
2. Оценить качество ответов (1-5 stars)
3. Улучшить `mentor.md` based on feedback
4. A/B тест (половина пользователей видит v1, половина v2)

**Метрики:**
- User satisfaction (рейтинг ответов)
- Follow-up questions (если юзер спросил более чем 1 раз — значит не понял)
- Engagement time (сколько времени юзер провёл в боте)

---

## 📅 Неделя 4 (2026-04-13 → 2026-04-22)

### Задача 6: Advanced Features

**Опция 1: Level Adaptation** (среднее, нужна переподготовка)
- Определить уровень пользователя по первому вопросу
- Адаптировать ответы (для Beginner — больше деталей, для Professional — концизно)

**Опция 2: Persistent User Memory** (высоко)
- Запомнить интересы пользователя (какие стратегии, инструменты)
- Рекомендовать материалы на основе истории

**Опция 3: Trading Journal Integration** (высоко)
- Юзеры могут логировать свои сделки в боте
- Bot анализирует и даёт feedback

**Рекомендация:** Start с Opion 2 (persistent memory), это даст максимум value с минимум complexity.

---

### Задача 7: Documentation & Handoff

**Что:** Подготовить бота к масштабированию

**Документы:**
- [ ] Bot User Manual (как пользоваться)
- [ ] Admin Manual (как обновлять knowledge base)
- [ ] Technical docs (для будущих разработчиков)
- [ ] Deployment checklist

---

## 🎯 Critical Path (Minimum Viable Sequence)

```
Week 1: Deploy → Test → Monitor
    ↓
Week 2: Expand knowledge base → Quality check
    ↓
Week 3: Optimize prompts → User feedback
    ↓
Week 4: Document → Plan Phase 3
```

**Не делай:** Feature bloat, пока bot не стабилен в production.

---

## 💰 Budget Allocation

**Month 1 (March-April):**
```
Claude API (Haiku + Sonnet): $10-15
OpenAI Embeddings:           $0.10
Supabase (free tier):        $0
VPS (1-core):                $5
──────────────────────────
Total:                       ~$20-25/month
```

**Margin for scale:** 10x users = ~$200-250/month (still cheap)

---

## ⚠️ Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| VPS goes down | Low | High | Enable auto-restart + monitoring |
| Claude API rate limit | Medium | Medium | Implement queue + retry logic |
| Knowledge base is incomplete | High | Medium | Aggressive Discord scraping |
| Bot gives wrong info | Medium | High | Quality review per section |
| DB gets too large | Low | Low | Implement archiving policy |

---

## 📊 Success Metrics (End of April)

- [x] Bot deployed and stable (99%+ uptime)
- [ ] 100+ documents in knowledge base
- [ ] 500+ test messages from users
- [ ] < 1% error rate
- [ ] Avg response time < 2s
- [ ] User satisfaction > 4.0/5.0
- [ ] Monthly cost < $50

---

## 📝 Sign-off

**Plan Created:** 2026-03-22
**Next Review:** 2026-03-29 (after Week 1)
**Updated by:** Claude @ Cowork

---

## 🔗 Related Docs

- `ARCHITECTURE-FULL.md` — System overview
- `EXTENSIONS-EVALUATION.md` — Tool selection
- `MERGE-PLAN.md` — Git workflow
- `docs/JARVIS-ARCHITECTURE-v1.md` — Detailed specs

