"""
structure.py — BOS и CHoCH детектор

BOS (Break of Structure):
  Бычий BOS:   закрытие выше предыдущего значимого HH (Higher High)
               → тренд продолжается вверх
  Медвежий BOS: закрытие ниже предыдущего значимого LL (Lower Low)
               → тренд продолжается вниз

CHoCH (Change of Character):
  Бычий CHoCH:  рынок был в даунтренде (LL/LH), затем пробивает последний LH
                → возможная смена тренда на бычий
  Медвежий CHoCH: рынок был в аптренде (HH/HL), затем пробивает последний HL
                → возможная смена тренда на медвежий

Алгоритм:
  1. Определяем swing high/low через lookback-окно
  2. Отслеживаем текущую структуру (HH/LH или LL/HL)
  3. При пробое — фиксируем BOS или CHoCH
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List


def detect_bos(
    df: pd.DataFrame,
    swing_length: int = 5,
    atr_period: int = 14,
) -> List[dict]:
    """
    Найти Break of Structure на OHLCV DataFrame.

    Args:
        df:            DataFrame с колонками open, high, low, close
        swing_length:  Число свечей слева и справа для определения swing точки

    Returns:
        Список:
        {
          "type":      "bos_bull" | "bos_bear",
          "idx":       int,    # индекс свечи пробоя
          "level":     float,  # уровень пробоя (swing high / swing low)
          "strength":  float,  # размер пробоя / ATR
        }
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    atr = _calc_atr(df, atr_period)

    swings = _find_swings(df, swing_length)
    signals: List[dict] = []
    n = len(df)

    prev_hh: float | None = None
    prev_ll: float | None = None

    for i in range(swing_length, n):
        close = df["close"].iloc[i]
        current_atr = atr.iloc[i] if atr.iloc[i] > 0 else 1.0

        # Обновляем последние swing high/low до текущей свечи
        past_highs = [s["level"] for s in swings if s["type"] == "swing_high" and s["idx"] < i]
        past_lows  = [s["level"] for s in swings if s["type"] == "swing_low"  and s["idx"] < i]

        if not past_highs or not past_lows:
            continue

        last_hh = max(past_highs[-3:]) if past_highs else None
        last_ll = min(past_lows[-3:])  if past_lows  else None

        # Бычий BOS — пробой выше последнего HH
        if last_hh is not None and close > last_hh and prev_hh != last_hh:
            strength = (close - last_hh) / current_atr
            signals.append({
                "type":     "bos_bull",
                "idx":      i,
                "level":    round(last_hh, 8),
                "strength": round(strength, 4),
            })
            prev_hh = last_hh

        # Медвежий BOS — пробой ниже последнего LL
        if last_ll is not None and close < last_ll and prev_ll != last_ll:
            strength = (last_ll - close) / current_atr
            signals.append({
                "type":     "bos_bear",
                "idx":      i,
                "level":    round(last_ll, 8),
                "strength": round(strength, 4),
            })
            prev_ll = last_ll

    return signals


def detect_choch(
    df: pd.DataFrame,
    swing_length: int = 5,
    atr_period: int = 14,
) -> List[dict]:
    """
    Найти Change of Character (CHoCH) на OHLCV DataFrame.

    Returns:
        Список:
        {
          "type":      "choch_bull" | "choch_bear",
          "idx":       int,
          "level":     float,
          "strength":  float,
        }
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    atr = _calc_atr(df, atr_period)

    swings = _find_swings(df, swing_length)
    signals: List[dict] = []
    n = len(df)

    # Отслеживаем тренд: 1=бычий, -1=медвежий, 0=неопределён
    trend = 0
    last_hh: float | None = None
    last_hl: float | None = None
    last_ll: float | None = None
    last_lh: float | None = None

    swing_highs = [s for s in swings if s["type"] == "swing_high"]
    swing_lows  = [s for s in swings if s["type"] == "swing_low"]

    already_signalled = set()

    for i in range(swing_length * 2, n):
        close = df["close"].iloc[i]
        current_atr = atr.iloc[i] if atr.iloc[i] > 0 else 1.0

        past_highs = [s for s in swing_highs if s["idx"] < i]
        past_lows  = [s for s in swing_lows  if s["idx"] < i]

        if len(past_highs) < 2 or len(past_lows) < 2:
            continue

        recent_highs = [s["level"] for s in past_highs[-4:]]
        recent_lows  = [s["level"] for s in past_lows[-4:]]

        # Определяем текущий тренд
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh = recent_highs[-1] > recent_highs[-2]
            hl = recent_lows[-1]  > recent_lows[-2]
            lh = recent_highs[-1] < recent_highs[-2]
            ll = recent_lows[-1]  < recent_lows[-2]

            if hh and hl:
                trend = 1   # аптренд
            elif lh and ll:
                trend = -1  # даунтренд

        # CHoCH бычий: даунтренд, пробиваем последний LH
        if trend == -1 and past_highs:
            lh_level = past_highs[-1]["level"]
            key = ("choch_bull", past_highs[-1]["idx"])
            if close > lh_level and key not in already_signalled:
                strength = (close - lh_level) / current_atr
                signals.append({
                    "type":     "choch_bull",
                    "idx":      i,
                    "level":    round(lh_level, 8),
                    "strength": round(strength, 4),
                })
                already_signalled.add(key)
                trend = 0  # сброс — ждём подтверждения

        # CHoCH медвежий: аптренд, пробиваем последний HL
        elif trend == 1 and past_lows:
            hl_level = past_lows[-1]["level"]
            key = ("choch_bear", past_lows[-1]["idx"])
            if close < hl_level and key not in already_signalled:
                strength = (hl_level - close) / current_atr
                signals.append({
                    "type":     "choch_bear",
                    "idx":      i,
                    "level":    round(hl_level, 8),
                    "strength": round(strength, 4),
                })
                already_signalled.add(key)
                trend = 0

    return signals


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_swings(df: pd.DataFrame, length: int) -> List[dict]:
    """
    Найти swing high и swing low.
    Swing high: high[i] — максимум среди ±length свечей вокруг него.
    """
    swings = []
    n = len(df)

    for i in range(length, n - length):
        # Swing high
        window_h = df["high"].iloc[i - length : i + length + 1]
        if df["high"].iloc[i] == window_h.max():
            swings.append({"type": "swing_high", "idx": i, "level": df["high"].iloc[i]})

        # Swing low
        window_l = df["low"].iloc[i - length : i + length + 1]
        if df["low"].iloc[i] == window_l.min():
            swings.append({"type": "swing_low", "idx": i, "level": df["low"].iloc[i]})

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
