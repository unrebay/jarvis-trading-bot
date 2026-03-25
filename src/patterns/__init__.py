"""
src/patterns — ICT/SMC pattern detectors

Чистые функции на pandas/numpy. Принимают OHLCV DataFrame, возвращают
список сигналов со структурированными данными для freqtrade и бэктеста.

Детекторы:
  fvg.py          — Fair Value Gap (бычий / медвежий)
  order_block.py  — Order Block (последняя свеча перед импульсом)
  structure.py    — BOS и CHoCH (Break of Structure, Change of Character)
  liquidity.py    — Liquidity Sweep (снятие внешней ликвидности)

Общий формат сигнала:
  {
    "type":       str,   # "fvg_bull", "ob_bear", "bos_bull", ...
    "start_idx":  int,   # индекс начала паттерна в DataFrame
    "end_idx":    int,   # индекс конца (включительно)
    "high":       float, # верхняя граница зоны
    "low":        float, # нижняя граница зоны
    "strength":   float, # 0.0–1.0 (чем больше — тем значимее)
    "filled":     bool,  # зона уже закрыта ценой (True = недействительна)
  }
"""

from .fvg         import detect_fvg
from .order_block import detect_order_block
from .structure   import detect_bos, detect_choch
from .liquidity   import detect_liquidity_sweep

__all__ = [
    "detect_fvg",
    "detect_order_block",
    "detect_bos",
    "detect_choch",
    "detect_liquidity_sweep",
]
