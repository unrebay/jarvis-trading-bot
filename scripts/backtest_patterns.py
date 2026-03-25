"""
backtest_patterns.py — Бэктест ICT/SMC паттернов на исторических данных

Использование:
    python3 scripts/backtest_patterns.py
    python3 scripts/backtest_patterns.py --symbol BTC-USD --interval 4h --period 180d
    python3 scripts/backtest_patterns.py --symbol EURUSD=X --interval 1h --period 90d

Для каждого паттерна считает:
    - Сколько раз встретился
    - Win rate (цена дошла до тейка раньше стопа)
    - Средний RR реализованный
    - Средняя сила сигнала победителей vs проигравших

Торговая логика симуляции:
    FVG:
        Вход:    ретест зоны FVG (цена возвращается к mid)
        Стоп:    за пределы зоны (ниже low для bull, выше high для bear)
        Тейк:    1.5× расстояние до стопа в направлении тренда

    Order Block:
        Вход:    ретест OB (цена возвращается в зону high/low)
        Стоп:    50% тела OB + 0.5×ATR
        Тейк:    2× расстояние до стопа

    BOS/CHoCH:
        Вход:    закрытие свечи пробоя + 0
        Стоп:    swing перед пробоем
        Тейк:    1:2 RR от стопа

    Liquidity Sweep:
        Вход:    свеча reversal_idx
        Стоп:    extreme sweep
        Тейк:    1:2 RR
"""

import argparse
import sys
import os
import ssl

# ── macOS SSL fix ─────────────────────────────────────────────────────────────
# Python venv on macOS often lacks system certificates → SSL errors with yfinance.
# This patches the default context to match system certs before any network call.
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    # certifi not installed — fall back to unverified context (dev only)
    ssl._create_default_https_context = ssl._create_unverified_context

from dataclasses import dataclass, field
from typing import List

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.patterns import (
    detect_fvg,
    detect_order_block,
    detect_bos,
    detect_choch,
    detect_liquidity_sweep,
)


# ── Structs ───────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    pattern_type: str
    entry_idx:    int
    entry_price:  float
    stop:         float
    take:         float
    direction:    int    # +1 long, -1 short
    signal_strength: float = 0.0

    # Filled in after simulation
    result:       str   = "open"   # "win" | "loss" | "open"
    exit_idx:     int   = -1
    exit_price:   float = 0.0
    realized_rr:  float = 0.0


@dataclass
class BacktestResult:
    symbol:       str
    interval:     str
    period:       str
    total_candles: int
    trades:       List[Trade] = field(default_factory=list)

    def stats(self) -> dict:
        closed = [t for t in self.trades if t.result != "open"]
        wins   = [t for t in closed if t.result == "win"]
        losses = [t for t in closed if t.result == "loss"]

        if not closed:
            return {"total": 0, "win_rate": 0, "avg_rr": 0}

        rr_values    = [t.realized_rr for t in closed]
        win_strength = [t.signal_strength for t in wins]   if wins   else [0]
        los_strength = [t.signal_strength for t in losses] if losses else [0]

        return {
            "total":         len(closed),
            "wins":          len(wins),
            "losses":        len(losses),
            "win_rate":      round(len(wins) / len(closed) * 100, 1),
            "avg_rr":        round(np.mean(rr_values), 3),
            "best_rr":       round(max(rr_values), 3),
            "worst_rr":      round(min(rr_values), 3),
            "avg_str_win":   round(np.mean(win_strength), 3),
            "avg_str_loss":  round(np.mean(los_strength), 3),
            "expectancy":    round(
                (len(wins)/len(closed)) * np.mean([t.realized_rr for t in wins] or [0])
                - (len(losses)/len(closed)) * abs(np.mean([t.realized_rr for t in losses] or [0])),
                3
            ),
        }


# ── Simulation helpers ────────────────────────────────────────────────────────

def _simulate_trade(df: pd.DataFrame, trade: Trade) -> Trade:
    """
    Walk forward from entry_idx and check if SL or TP is hit first.
    Updates trade.result, exit_idx, exit_price, realized_rr in place.
    """
    sl = trade.stop
    tp = trade.take
    direction = trade.direction

    for j in range(trade.entry_idx + 1, len(df)):
        high = df["high"].iloc[j]
        low  = df["low"].iloc[j]

        if direction == 1:   # long
            if low <= sl:
                trade.result      = "loss"
                trade.exit_idx    = j
                trade.exit_price  = sl
                trade.realized_rr = -1.0
                return trade
            if high >= tp:
                trade.result      = "win"
                trade.exit_idx    = j
                trade.exit_price  = tp
                risk   = trade.entry_price - sl
                reward = tp - trade.entry_price
                trade.realized_rr = round(reward / risk, 3) if risk > 0 else 0
                return trade

        else:  # short
            if high >= sl:
                trade.result      = "loss"
                trade.exit_idx    = j
                trade.exit_price  = sl
                trade.realized_rr = -1.0
                return trade
            if low <= tp:
                trade.result      = "win"
                trade.exit_idx    = j
                trade.exit_price  = tp
                risk   = sl - trade.entry_price
                reward = trade.entry_price - tp
                trade.realized_rr = round(reward / risk, 3) if risk > 0 else 0
                return trade

    trade.result = "open"
    return trade


def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df["high"]
    low   = df["low"]
    close = df["close"].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


# ── Pattern → Trade converters ────────────────────────────────────────────────

def _fvg_to_trades(df: pd.DataFrame, signals: list) -> List[Trade]:
    trades = []
    atr = _calc_atr(df)

    for sig in signals:
        if sig["filled"]:
            continue  # уже пересечён — не торгуем

        mid       = sig["mid"]
        zone_size = sig["high"] - sig["low"]
        direction = 1 if sig["type"] == "fvg_bull" else -1

        # Ищем ретест зоны после формирования
        for j in range(sig["end_idx"] + 1, min(sig["end_idx"] + 50, len(df))):
            low_j  = df["low"].iloc[j]
            high_j = df["high"].iloc[j]

            if direction == 1 and low_j <= sig["high"] and df["close"].iloc[j] > sig["low"]:
                entry = df["close"].iloc[j]
                sl    = sig["low"] - atr.iloc[j] * 0.3
                tp    = entry + (entry - sl) * 1.5
                t = Trade("fvg_bull", j, entry, sl, tp, 1, sig["strength"])
                trades.append(_simulate_trade(df, t))
                break

            elif direction == -1 and high_j >= sig["low"] and df["close"].iloc[j] < sig["high"]:
                entry = df["close"].iloc[j]
                sl    = sig["high"] + atr.iloc[j] * 0.3
                tp    = entry - (sl - entry) * 1.5
                t = Trade("fvg_bear", j, entry, sl, tp, -1, sig["strength"])
                trades.append(_simulate_trade(df, t))
                break

    return trades


def _ob_to_trades(df: pd.DataFrame, signals: list) -> List[Trade]:
    trades = []
    atr = _calc_atr(df)

    for sig in signals:
        if sig["mitigated"]:
            continue

        direction = 1 if sig["type"] == "ob_bull" else -1

        for j in range(sig["idx"] + 3, min(sig["idx"] + 60, len(df))):
            low_j  = df["low"].iloc[j]
            high_j = df["high"].iloc[j]

            if direction == 1 and low_j <= sig["high"] and df["close"].iloc[j] > sig["low"]:
                entry = df["close"].iloc[j]
                sl    = sig["low"] - atr.iloc[j] * 0.5
                tp    = entry + (entry - sl) * 2.0
                t = Trade("ob_bull", j, entry, sl, tp, 1, sig["strength"])
                trades.append(_simulate_trade(df, t))
                break

            elif direction == -1 and high_j >= sig["low"] and df["close"].iloc[j] < sig["high"]:
                entry = df["close"].iloc[j]
                sl    = sig["high"] + atr.iloc[j] * 0.5
                tp    = entry - (sl - entry) * 2.0
                t = Trade("ob_bear", j, entry, sl, tp, -1, sig["strength"])
                trades.append(_simulate_trade(df, t))
                break

    return trades


def _structure_to_trades(df: pd.DataFrame, signals: list) -> List[Trade]:
    trades = []
    atr = _calc_atr(df)

    for sig in signals:
        i = sig["idx"]
        if i >= len(df) - 1:
            continue

        direction = 1 if "bull" in sig["type"] else -1
        entry     = df["close"].iloc[i]
        a         = atr.iloc[i] if atr.iloc[i] > 0 else entry * 0.001
        sl        = entry - direction * a * 2.0
        tp        = entry + direction * a * 4.0

        t = Trade(sig["type"], i, entry, sl, tp, direction, sig["strength"])
        trades.append(_simulate_trade(df, t))

    return trades


def _sweep_to_trades(df: pd.DataFrame, signals: list) -> List[Trade]:
    trades = []
    atr = _calc_atr(df)

    for sig in signals:
        rev_idx = sig["reversal_idx"]
        if rev_idx >= len(df) - 1:
            continue

        direction = 1 if sig["type"] == "sweep_bull" else -1
        entry     = df["close"].iloc[rev_idx]
        sl        = sig["extreme"]
        risk      = abs(entry - sl)
        if risk <= 0:
            continue
        tp = entry + direction * risk * 2.0

        t = Trade(sig["type"], rev_idx, entry, sl, tp, direction, sig["strength"])
        trades.append(_simulate_trade(df, t))

    return trades


# ── Main backtest ─────────────────────────────────────────────────────────────

def run_backtest(symbol: str, interval: str, period: str) -> BacktestResult:
    try:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            print(f"❌ Нет данных для {symbol}")
            sys.exit(1)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    except ImportError:
        print("❌ yfinance не установлен: pip install yfinance")
        sys.exit(1)

    df = df.reset_index(drop=True)
    result = BacktestResult(symbol=symbol, interval=interval, period=period, total_candles=len(df))

    print(f"\n📊 {symbol} · {interval} · {period} → {len(df)} свечей")
    print("─" * 60)

    # Запускаем детекторы
    fvg_sigs    = detect_fvg(df)
    ob_sigs     = detect_order_block(df)
    bos_sigs    = detect_bos(df)
    choch_sigs  = detect_choch(df)
    sweep_sigs  = detect_liquidity_sweep(df)

    print(f"Паттернов найдено: FVG={len(fvg_sigs)}, OB={len(ob_sigs)}, "
          f"BOS={len(bos_sigs)}, CHoCH={len(choch_sigs)}, Sweep={len(sweep_sigs)}")

    # Симулируем сделки
    result.trades += _fvg_to_trades(df, fvg_sigs)
    result.trades += _ob_to_trades(df, ob_sigs)
    result.trades += _structure_to_trades(df, bos_sigs)
    result.trades += _structure_to_trades(df, choch_sigs)
    result.trades += _sweep_to_trades(df, sweep_sigs)

    return result


def print_report(result: BacktestResult) -> None:
    """Печатает читаемый отчёт по паттернам."""
    all_types = sorted(set(t.pattern_type for t in result.trades))

    print(f"\n{'═'*60}")
    print(f"  BACKTEST REPORT — {result.symbol} {result.interval} ({result.period})")
    print(f"  Всего свечей: {result.total_candles}")
    print(f"{'═'*60}\n")

    total_wins = 0
    total_closed = 0

    for ptype in all_types:
        group = [t for t in result.trades if t.pattern_type == ptype]
        closed = [t for t in group if t.result != "open"]
        wins   = [t for t in closed if t.result == "win"]

        if not closed:
            print(f"  {ptype:<20} нет завершённых сделок")
            continue

        wr = len(wins) / len(closed) * 100
        avg_rr = np.mean([t.realized_rr for t in closed])
        expectancy = (len(wins)/len(closed)) * np.mean([t.realized_rr for t in wins] or [0]) \
                   - (len([t for t in closed if t.result=="loss"])/len(closed))

        bar_len   = 20
        bar_filled = int(wr / 100 * bar_len)
        bar = "█" * bar_filled + "░" * (bar_len - bar_filled)

        print(f"  {ptype:<20} [{bar}] {wr:5.1f}%  "
              f"({len(wins)}/{len(closed)})  "
              f"avg RR={avg_rr:+.2f}  "
              f"E={expectancy:+.2f}")

        total_wins   += len(wins)
        total_closed += len(closed)

    if total_closed:
        overall_wr = total_wins / total_closed * 100
        print(f"\n{'─'*60}")
        print(f"  ИТОГО: {total_wins}/{total_closed} сделок  Win rate: {overall_wr:.1f}%")
        print(f"{'─'*60}")

    # Топ-3 сделки
    top = sorted([t for t in result.trades if t.result == "win"],
                 key=lambda t: t.realized_rr, reverse=True)[:3]
    if top:
        print("\n  Лучшие сделки:")
        for t in top:
            print(f"    {t.pattern_type:<20} свеча #{t.entry_idx:4d}  "
                  f"RR={t.realized_rr:+.2f}  сила={t.signal_strength:.3f}")

    # Паттерны с плохим win rate — предупреждение
    print()
    for ptype in all_types:
        group  = [t for t in result.trades if t.pattern_type == ptype]
        closed = [t for t in group if t.result != "open"]
        if len(closed) >= 5:
            wr = sum(1 for t in closed if t.result == "win") / len(closed) * 100
            if wr < 40:
                print(f"  ⚠️  {ptype}: win rate {wr:.0f}% < 40% — не рекомендуется для freqtrade")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Бэктест ICT/SMC паттернов")
    parser.add_argument("--symbol",   default="BTC-USD",  help="Тикер (yfinance)")
    parser.add_argument("--interval", default="4h",       help="Таймфрейм: 1h 4h 1d")
    parser.add_argument("--period",   default="180d",     help="Период: 30d 90d 180d 1y")
    args = parser.parse_args()

    result = run_backtest(args.symbol, args.interval, args.period)
    print_report(result)


if __name__ == "__main__":
    main()
