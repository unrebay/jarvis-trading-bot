"""
fvg.py — Fair Value Gap detector

Определение:
  Бычий FVG:   low[i] > high[i-2]  — разрыв между свечой i-2 и i (свеча i-1 импульс вверх)
  Медвежий FVG: high[i] < low[i-2] — разрыв между свечой i-2 и i (свеча i-1 импульс вниз)

Сила FVG = размер разрыва / ATR(14) — нормализованный показатель значимости.
Filled = True, если цена вернулась в зону разрыва после его образования.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List


def detect_fvg(
    df: pd.DataFrame,
    min_strength: float = 0.1,
    atr_period: int = 14,
) -> List[dict]:
    """
    Найти все Fair Value Gap на OHLCV DataFrame.

    Args:
        df:           DataFrame с колонками open, high, low, close, volume
                      (индекс — DatetimeIndex или целые числа)
        min_strength: Минимальный размер FVG относительно ATR (0.1 = 10% ATR)
        atr_period:   Период для расчёта ATR

    Returns:
        Список словарей формата:
        {
          "type":      "fvg_bull" | "fvg_bear",
          "start_idx": int,    # индекс свечи i-2
          "end_idx":   int,    # индекс свечи i
          "high":      float,  # верхняя граница зоны
          "low":       float,  # нижняя граница зоны
          "mid":       float,  # середина зоны (50% уровень)
          "strength":  float,  # размер / ATR
          "filled":    bool,   # True если цена зашла в зону позже
        }
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame должен содержать колонки: {required}")

    # ATR для нормализации силы
    atr = _calc_atr(df, atr_period)

    signals: List[dict] = []
    n = len(df)

    for i in range(2, n):
        h_prev2 = df["high"].iloc[i - 2]
        l_prev2 = df["low"].iloc[i - 2]
        l_curr  = df["low"].iloc[i]
        h_curr  = df["high"].iloc[i]

        current_atr = atr.iloc[i] if atr.iloc[i] > 0 else 1.0

        # ── Бычий FVG ────────────────────────────────────────────────────────
        if l_curr > h_prev2:
            gap_size = l_curr - h_prev2
            strength = gap_size / current_atr

            if strength >= min_strength:
                filled = _is_fvg_filled_bull(df, i, h_prev2, l_curr)
                signals.append({
                    "type":      "fvg_bull",
                    "start_idx": i - 2,
                    "end_idx":   i,
                    "high":      round(l_curr,  8),
                    "low":       round(h_prev2, 8),
                    "mid":       round((l_curr + h_prev2) / 2, 8),
                    "strength":  round(strength, 4),
                    "filled":    filled,
                })

        # ── Медвежий FVG ──────────────────────────────────────────────────────
        elif h_curr < l_prev2:
            gap_size = l_prev2 - h_curr
            strength = gap_size / current_atr

            if strength >= min_strength:
                filled = _is_fvg_filled_bear(df, i, h_curr, l_prev2)
                signals.append({
                    "type":      "fvg_bear",
                    "start_idx": i - 2,
                    "end_idx":   i,
                    "high":      round(l_prev2, 8),
                    "low":       round(h_curr,  8),
                    "mid":       round((l_prev2 + h_curr) / 2, 8),
                    "strength":  round(strength, 4),
                    "filled":    filled,
                })

    return signals


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """True Range → ATR(period)."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - close).abs(),
        (low  - close).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(period, min_periods=1).mean()


def _is_fvg_filled_bull(
    df: pd.DataFrame, formed_at: int, fvg_low: float, fvg_high: float
) -> bool:
    """Вернулась ли цена в бычий FVG после его образования."""
    future = df.iloc[formed_at + 1 :]
    return bool((future["low"] <= fvg_high).any())


def _is_fvg_filled_bear(
    df: pd.DataFrame, formed_at: int, fvg_low: float, fvg_high: float
) -> bool:
    """Вернулась ли цена в медвежий FVG после его образования."""
    future = df.iloc[formed_at + 1 :]
    return bool((future["high"] >= fvg_low).any())
