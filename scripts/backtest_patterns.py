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
        # NOTE: не используем sig["filled"] — он рассчитан по всему датасету
        # (lookahead bias). Симулируем поиск ретеста честно, свеча за свечой.

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
        # NOTE: не используем sig["mitigated"] — lookahead bias

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

# ICT/SMC curriculum assets and recommended intervals
MULTI_ASSETS = [
    # (symbol,     interval, period,  label)
    ("BTC-USD",   "1d",     "365d",  "Bitcoin"),
    ("GC=F",      "1d",     "365d",  "Gold (XAU)"),
    ("EURUSD=X",  "1d",     "365d",  "EUR/USD"),
    ("NQ=F",      "1d",     "365d",  "Nasdaq (NQ)"),
    ("ES=F",      "1d",     "365d",  "S&P 500 (ES)"),
]


def _download_df(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """
    Robust yfinance downloader.
    - Tries multi_level_index=False (yfinance >= 0.2.37) for flat columns.
    - Falls back to legacy download + MultiIndex flatten.
    - Raises ValueError if empty / None returned.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("❌ yfinance не установлен: pip install yfinance")
        sys.exit(1)

    # Note: yfinance intraday limits — 4h/1h max 60 days, 1d up to years
    df = None
    try:
        # Preferred: flat columns, no MultiIndex confusion
        df = yf.download(
            symbol, period=period, interval=interval,
            progress=False, auto_adjust=True, multi_level_index=False,
        )
    except TypeError:
        # Older yfinance doesn't know multi_level_index
        df = yf.download(
            symbol, period=period, interval=interval,
            progress=False, auto_adjust=True,
        )

    if df is None or (hasattr(df, "empty") and df.empty):
        raise ValueError(f"Нет данных для {symbol} ({interval} {period})")

    # Flatten MultiIndex columns → plain lowercase strings
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0).str.lower()
    else:
        df.columns = [str(c).lower() for c in df.columns]

    # Keep only OHLCV
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df.reset_index(drop=True)


def run_backtest(symbol: str, interval: str, period: str) -> BacktestResult:
    try:
        df = _download_df(symbol, interval, period)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

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
    parser.add_argument("--interval", default="1d",       help="Таймфрейм: 1h 4h 1d")
    parser.add_argument("--period",   default="365d",     help="Период: 30d 90d 180d 1y 2y")
    parser.add_argument("--multi",    action="store_true",
                        help="Запустить бэктест по всем ICT/SMC активам (BTC, Gold, EURUSD, NQ, ES)")
    args = parser.parse_args()

    if args.multi:
        _run_multi()
    else:
        result = run_backtest(args.symbol, args.interval, args.period)
        print_report(result)


def _run_multi():
    """Batch backtest across all key ICT/SMC curriculum assets."""
    summary_rows = []

    for symbol, interval, period, label in MULTI_ASSETS:
        print(f"\n{'━'*60}")
        print(f"  {label} ({symbol})")
        print(f"{'━'*60}")
        try:
            df = _download_df(symbol, interval, period)
        except ValueError as e:
            print(f"  ❌ {e} — пропускаем")
            continue

        result = BacktestResult(symbol=symbol, interval=interval,
                                period=period, total_candles=len(df))

        print(f"  {len(df)} свечей  {interval} {period}")

        fvg_sigs   = detect_fvg(df)
        ob_sigs    = detect_order_block(df)
        bos_sigs   = detect_bos(df)
        choch_sigs = detect_choch(df)
        sweep_sigs = detect_liquidity_sweep(df)

        print(f"  Паттернов: FVG={len(fvg_sigs)} OB={len(ob_sigs)} "
              f"BOS={len(bos_sigs)} CHoCH={len(choch_sigs)} Sweep={len(sweep_sigs)}")

        result.trades += _fvg_to_trades(df, fvg_sigs)
        result.trades += _ob_to_trades(df, ob_sigs)
        result.trades += _structure_to_trades(df, bos_sigs)
        result.trades += _structure_to_trades(df, choch_sigs)
        result.trades += _sweep_to_trades(df, sweep_sigs)

        print_report(result)

        # Collect per-pattern summary for cross-asset table
        all_types = sorted(set(t.pattern_type for t in result.trades))
        for ptype in all_types:
            group  = [t for t in result.trades if t.pattern_type == ptype]
            closed = [t for t in group if t.result != "open"]
            if not closed:
                continue
            wins = [t for t in closed if t.result == "win"]
            wr   = len(wins) / len(closed) * 100
            avg_rr = np.mean([t.realized_rr for t in closed])
            summary_rows.append({
                "asset":   label,
                "pattern": ptype,
                "trades":  len(closed),
                "win_rate": round(wr, 1),
                "avg_rr":  round(avg_rr, 3),
            })

    # ── Cross-asset summary table ────────────────────────────────────────────
    if not summary_rows:
        print("\nНет данных для сводной таблицы.")
        return

    print(f"\n\n{'═'*72}")
    print("  СВОДНАЯ ТАБЛИЦА — ICT/SMC ПАТТЕРНЫ × АКТИВЫ")
    print(f"{'═'*72}")
    print(f"  {'Актив':<15} {'Паттерн':<22} {'Сделок':>7} {'Win%':>7} {'avg RR':>8}  {'✓/✗'}")
    print(f"  {'─'*15} {'─'*22} {'─'*7} {'─'*7} {'─'*8}  {'─'*5}")

    for row in summary_rows:
        ok = "✅" if row["win_rate"] >= 50 else ("⚠️ " if row["win_rate"] >= 40 else "❌")
        print(f"  {row['asset']:<15} {row['pattern']:<22} {row['trades']:>7} "
              f"{row['win_rate']:>6.1f}% {row['avg_rr']:>+8.3f}  {ok}")

    # Best patterns overall
    from collections import defaultdict
    pattern_agg: dict = defaultdict(lambda: {"wins": 0, "total": 0, "rr_sum": 0.0})
    for row in summary_rows:
        p = pattern_agg[row["pattern"]]
        wins = round(row["trades"] * row["win_rate"] / 100)
        p["wins"]   += wins
        p["total"]  += row["trades"]
        p["rr_sum"] += row["avg_rr"] * row["trades"]

    print(f"\n  {'─'*72}")
    print("  АГРЕГАТ (все активы):")
    for pname, p in sorted(pattern_agg.items(),
                           key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                           reverse=True):
        if p["total"] == 0:
            continue
        wr    = p["wins"] / p["total"] * 100
        avg_rr = p["rr_sum"] / p["total"]
        rec   = "→ использовать" if wr >= 50 else ("→ осторожно" if wr >= 40 else "→ пропустить")
        print(f"  {pname:<22} WR={wr:5.1f}%  avg RR={avg_rr:+.3f}  {rec}")

    print(f"{'═'*72}\n")


if __name__ == "__main__":
    main()
