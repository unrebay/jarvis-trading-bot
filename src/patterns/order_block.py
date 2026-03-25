"""
order_block.py — Order Block detector

Определение (ICT):
  Бычий OB:   последняя медвежья свеча перед импульсным движением вверх
              (цена уходит выше high[OB] — пробой структуры вверх)
  Медвежий OB: последняя бычья свеча перед импульсным движением вниз
              (цена уходит ниже low[OB] — пробой структуры вниз)

Критерии импульса:
  - Следующие N свечей закрываются в направлении движения
  - Размах движения > impulse_atr_mult * ATR

Сила OB = (размах импульса / ATR) нормализованный.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List


def detect_order_block(
    df: pd.DataFrame,
    impulse_candles: int = 3,
    impulse_atr_mult: float = 1.5,
    atr_period: int = 14,
    max_lookback: int = 200,
) -> List[dict]:
    """
    Найти Order Block'и на OHLCV DataFrame.

    Args:
        df:               DataFrame с колонками open, high, low, close, volume
        impulse_candles:  Сколько свечей после OB должны подтвердить импульс
        impulse_atr_mult: Минимальный размах импульса в ATR
        atr_period:       Период ATR
        max_lookback:     Смотрим не дальше этих свечей назад

    Returns:
        Список словарей:
        {
          "type":        "ob_bull" | "ob_bear",
          "idx":         int,    # индекс свечи-OB в DataFrame
          "high":        float,  # high свечи OB
          "low":         float,  # low свечи OB
          "open":        float,
          "close":       float,
          "strength":    float,  # размах импульса / ATR
          "mitigated":   bool,   # True если OB уже был протестирован (цена зашла в зону)
        }
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame должен содержать колонки: {required}")

    atr = _calc_atr(df, atr_period)
    signals: List[dict] = []
    n = len(df)
    start = max(0, n - max_lookback)

    for i in range(start, n - impulse_candles):
        candle_body = df["close"].iloc[i] - df["open"].iloc[i]
        current_atr = atr.iloc[i] if atr.iloc[i] > 0 else 1.0

        # ── Бычий OB (медвежья свеча перед движением вверх) ──────────────────
        if candle_body < 0:  # медвежья свеча
            impulse_high = df["high"].iloc[i + 1 : i + 1 + impulse_candles].max()
            impulse_range = impulse_high - df["high"].iloc[i]

            if impulse_range >= impulse_atr_mult * current_atr:
                mitigated = _is_ob_mitigated_bull(df, i, df["low"].iloc[i], df["high"].iloc[i])
                signals.append({
                    "type":      "ob_bull",
                    "idx":       i,
                    "high":      round(df["high"].iloc[i],  8),
                    "low":       round(df["low"].iloc[i],   8),
                    "open":      round(df["open"].iloc[i],  8),
                    "close":     round(df["close"].iloc[i], 8),
                    "strength":  round(impulse_range / current_atr, 4),
                    "mitigated": mitigated,
                })

        # ── Медвежий OB (бычья свеча перед движением вниз) ───────────────────
        elif candle_body > 0:  # бычья свеча
            impulse_low   = df["low"].iloc[i + 1 : i + 1 + impulse_candles].min()
            impulse_range = df["low"].iloc[i] - impulse_low

            if impulse_range >= impulse_atr_mult * current_atr:
                mitigated = _is_ob_mitigated_bear(df, i, df["low"].iloc[i], df["high"].iloc[i])
                signals.append({
                    "type":      "ob_bear",
                    "idx":       i,
                    "high":      round(df["high"].iloc[i],  8),
                    "low":       round(df["low"].iloc[i],   8),
                    "open":      round(df["open"].iloc[i],  8),
                    "close":     round(df["close"].iloc[i], 8),
                    "strength":  round(impulse_range / current_atr, 4),
                    "mitigated": mitigated,
                })

    return signals


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _is_ob_mitigated_bull(
    df: pd.DataFrame, formed_at: int, ob_low: float, ob_high: float
) -> bool:
    """Зашла ли цена в зону бычьего OB (low..high) после его формирования."""
    future = df.iloc[formed_at + 1 :]
    return bool((future["low"] <= ob_high).any())


def _is_ob_mitigated_bear(
    df: pd.DataFrame, formed_at: int, ob_low: float, ob_high: float
) -> bool:
    """Зашла ли цена в зону медвежьего OB после его формирования."""
    future = df.iloc[formed_at + 1 :]
    return bool((future["high"] >= ob_low).any())
