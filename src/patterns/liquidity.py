"""
liquidity.py — Liquidity Sweep detector

Определение (ICT):
  Ликвидность копится над swing high (стопы покупателей) и под swing low (стопы продавцов).
  Liquidity Sweep = цена резко выходит за swing уровень, затем разворачивается.

  Бычий sweep (медвежий манипуляция → разворот вверх):
    - Цена уходит ниже swing low (снимает стопы продавцов)
    - Затем закрывается ВЫШЕ этого low в течение reversal_candles свечей

  Медвежий sweep (бычий манипуляция → разворот вниз):
    - Цена уходит выше swing high (снимает стопы покупателей)
    - Затем закрывается НИЖЕ этого high в течение reversal_candles свечей

Сила = глубина выхода за уровень / ATR.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List


def detect_liquidity_sweep(
    df: pd.DataFrame,
    swing_length: int = 5,
    reversal_candles: int = 3,
    min_strength: float = 0.1,
    atr_period: int = 14,
    max_lookback: int = 300,
) -> List[dict]:
    """
    Найти Liquidity Sweep на OHLCV DataFrame.

    Args:
        df:               DataFrame с колонками open, high, low, close
        swing_length:     Окно для определения swing high/low
        reversal_candles: Максимум свечей для подтверждения разворота
        min_strength:     Минимальная глубина sweep в долях ATR
        atr_period:       Период ATR
        max_lookback:     Анализируем не дальше N свечей назад

    Returns:
        Список:
        {
          "type":       "sweep_bull" | "sweep_bear",
          "idx":        int,    # индекс свечи sweep (выход за уровень)
          "reversal_idx": int,  # индекс свечи подтверждения разворота
          "level":      float,  # swing уровень который был сметён
          "extreme":    float,  # экстремум sweep (min low / max high)
          "strength":   float,  # глубина / ATR
        }
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame должен содержать колонки: {required}")

    atr    = _calc_atr(df, atr_period)
    swings = _find_swings(df, swing_length)
    n      = len(df)
    start  = max(swing_length * 2, n - max_lookback)

    swing_highs = [s for s in swings if s["type"] == "swing_high"]
    swing_lows  = [s for s in swings if s["type"] == "swing_low"]

    signals: List[dict] = []
    used_sweeps: set = set()

    for i in range(start, n - reversal_candles):
        current_atr = atr.iloc[i] if atr.iloc[i] > 0 else 1.0

        # ── Бычий sweep: цена уходит под swing low → разворот вверх ──────────
        past_lows = [s for s in swing_lows if s["idx"] < i - swing_length]
        if past_lows:
            nearest_low = past_lows[-1]
            level = nearest_low["level"]
            low_i = df["low"].iloc[i]

            if low_i < level:
                depth   = level - low_i
                strength = depth / current_atr

                if strength >= min_strength:
                    # Ищем разворот: закрытие выше level в следующих reversal_candles свечах
                    reversal_idx = _find_reversal_up(df, i, level, reversal_candles)
                    key = ("sweep_bull", nearest_low["idx"])

                    if reversal_idx is not None and key not in used_sweeps:
                        signals.append({
                            "type":         "sweep_bull",
                            "idx":          i,
                            "reversal_idx": reversal_idx,
                            "level":        round(level, 8),
                            "extreme":      round(low_i, 8),
                            "strength":     round(strength, 4),
                        })
                        used_sweeps.add(key)

        # ── Медвежий sweep: цена уходит выше swing high → разворот вниз ───────
        past_highs = [s for s in swing_highs if s["idx"] < i - swing_length]
        if past_highs:
            nearest_high = past_highs[-1]
            level  = nearest_high["level"]
            high_i = df["high"].iloc[i]

            if high_i > level:
                depth    = high_i - level
                strength = depth / current_atr

                if strength >= min_strength:
                    reversal_idx = _find_reversal_down(df, i, level, reversal_candles)
                    key = ("sweep_bear", nearest_high["idx"])

                    if reversal_idx is not None and key not in used_sweeps:
                        signals.append({
                            "type":         "sweep_bear",
                            "idx":          i,
                            "reversal_idx": reversal_idx,
                            "level":        round(level, 8),
                            "extreme":      round(high_i, 8),
                            "strength":     round(strength, 4),
                        })
                        used_sweeps.add(key)

    return signals


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_reversal_up(
    df: pd.DataFrame, from_idx: int, level: float, max_candles: int
) -> int | None:
    """Найти индекс первой свечи, закрывшейся выше level после from_idx."""
    end = min(from_idx + max_candles + 1, len(df))
    for j in range(from_idx + 1, end):
        if df["close"].iloc[j] > level:
            return j
    return None


def _find_reversal_down(
    df: pd.DataFrame, from_idx: int, level: float, max_candles: int
) -> int | None:
    """Найти индекс первой свечи, закрывшейся ниже level после from_idx."""
    end = min(from_idx + max_candles + 1, len(df))
    for j in range(from_idx + 1, end):
        if df["close"].iloc[j] < level:
            return j
    return None


def _find_swings(df: pd.DataFrame, length: int) -> List[dict]:
    swings = []
    n = len(df)
    for i in range(length, n - length):
        window_h = df["high"].iloc[i - length : i + length + 1]
        if df["high"].iloc[i] == window_h.max():
            swings.append({"type": "swing_high", "idx": i, "level": float(df["high"].iloc[i])})
        window_l = df["low"].iloc[i - length : i + length + 1]
        if df["low"].iloc[i] == window_l.min():
            swings.append({"type": "swing_low", "idx": i, "level": float(df["low"].iloc[i])})
    return swings


def _calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high  = df["high"]
    low   = df["low"]
    close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low  - close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()
