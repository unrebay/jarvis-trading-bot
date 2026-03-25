# Backtest Results — ICT/SMC Паттерны

> Результаты запускаются командой:
> ```bash
> python3 scripts/backtest_patterns.py --multi          # все активы, 1d 365d
> python3 scripts/backtest_patterns.py --symbol BTC-USD --interval 4h --period 60d
> ```

---

## BTC-USD · 4h · 180d (первый запуск, 2026-03-25)

| Паттерн     | Win%  | W/L    | avg RR  | Expectancy |
|-------------|-------|--------|---------|------------|
| bos_bear    | 57.1% | 4/7    | +0.71   | +0.27      |
| sweep_bear  | 50.0% | 3/6    | +0.67   | +0.17      |
| bos_bull    | 33.3% | 2/6    | −0.11   | −0.44      |
| choch_bull  | 25.0% | 1/4    | −0.38   | −0.69      |
| choch_bear  | 20.0% | 1/5    | −0.62   | −0.76      |
| sweep_bull  | 0.0%  | 0/5    | −1.00   | −1.00      |

**Вывод:** Для использования в freqtrade → **только `bos_bear` + `sweep_bear`** (WR > 50%).

---

## Multi-Asset (запустить командой `--multi`)

Результаты записать сюда после запуска на реальных данных.

Активы для тестирования:
- **BTC-USD** — Bitcoin (1d, 365d)
- **GC=F** — Gold / XAU (1d, 365d)
- **EURUSD=X** — EUR/USD forex (1d, 365d)
- **NQ=F** — Nasdaq futures (1d, 365d)
- **ES=F** — S&P 500 futures (1d, 365d)

Команда:
```bash
cd /opt/jarvis
source venv/bin/activate
python3 scripts/backtest_patterns.py --multi 2>&1 | tee docs/multi_backtest_$(date +%F).txt
```

---

## Рекомендации для JarvisICT freqtrade стратегии

На основании первых результатов:

1. **Использовать:** `bos_bear`, `sweep_bear` — win rate > 50%
2. **Пропустить:** `bos_bull`, `choch_bull`, `choch_bear`, `sweep_bull` — win rate < 40%
3. **Добавить трендовый фильтр:** входить в short только если `bos_bear` подтверждён на более высоком TF
4. **Минимальная сила сигнала:** `strength > 0.3` для уменьшения ложных срабатываний

Паттерны, ожидаемые к добавлению после multi-asset теста:
- Если `bos_bear` показывает WR > 50% на 3+ активах → приоритет #1 для freqtrade
- Если `sweep_bear` устойчив на forex (EURUSD) → хороший кандидат для реального торга

---

*Обновлено: 2026-03-25*
