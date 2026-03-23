"""
chart_generator.py — Live candlestick chart generation (v1.0)

Fetches OHLCV data from Yahoo Finance (yfinance) and renders a
dark-theme candlestick chart (mplfinance) as JPEG bytes.

These image bytes can then be:
  - Sent directly to Telegram as a photo (/chart command)
  - Passed to ChartAnnotator for ICT/SMC annotation overlay
  - Attached to TradingView alert notifications

Supported timeframes: 1m, 5m, 15m, 1h, 4h, 1d, 1w
Supported symbols: BTC, ETH, NQ, ES, EURUSD, GOLD, any Yahoo Finance ticker
"""

import io
from typing import Optional

import pandas as pd


# ── Symbol normalization map ───────────────────────────────────────────────────

SYMBOL_MAP: dict[str, str] = {
    # Crypto
    "BTC":      "BTC-USD",
    "BTCUSDT":  "BTC-USD",
    "BTCUSD":   "BTC-USD",
    "BITCOIN":  "BTC-USD",
    "ETH":      "ETH-USD",
    "ETHUSDT":  "ETH-USD",
    "SOL":      "SOL-USD",
    "SOLUSDT":  "SOL-USD",
    "BNB":      "BNB-USD",
    "XRP":      "XRP-USD",
    "DOGE":     "DOGE-USD",
    # Forex
    "EURUSD":   "EURUSD=X",
    "EUR/USD":  "EURUSD=X",
    "GBPUSD":   "GBPUSD=X",
    "GBP/USD":  "GBPUSD=X",
    "USDJPY":   "USDJPY=X",
    "USD/JPY":  "USDJPY=X",
    "GBPJPY":   "GBPJPY=X",
    "AUDUSD":   "AUDUSD=X",
    "USDCAD":   "USDCAD=X",
    "NZDUSD":   "NZDUSD=X",
    # Indices / Futures
    "NQ":       "NQ=F",
    "NQ100":    "NQ=F",
    "MNQ":      "NQ=F",
    "ES":       "ES=F",
    "SP500":    "ES=F",
    "SPX":      "^GSPC",
    "YM":       "YM=F",
    "RTY":      "RTY=F",
    "DXY":      "DX-Y.NYB",
    "USDX":     "DX-Y.NYB",
    # Commodities
    "GOLD":     "GC=F",
    "XAUUSD":   "GC=F",
    "OIL":      "CL=F",
    "CRUDE":    "CL=F",
    "SILVER":   "SI=F",
    "XAGUSD":   "SI=F",
}

# ── Timeframe config: (yf_interval, yf_period, resample_rule, display_candles) ─

TF_CONFIG: dict[str, tuple] = {
    "1m":  ("1m",   "1d",   None,  200),
    "5m":  ("5m",   "5d",   None,  160),
    "15m": ("15m",  "5d",   None,  130),
    "1h":  ("1h",   "30d",  None,  120),
    "4h":  ("1h",   "60d",  "4h",  100),   # yf has no 4h; resample 1h→4h
    "1d":  ("1d",   "1y",   None,  150),
    "1w":  ("1wk",  "5y",   None,  100),
}

VALID_TIMEFRAMES = list(TF_CONFIG.keys())


class ChartGenerator:
    """Generates dark-theme candlestick charts from live Yahoo Finance data."""

    def generate(self, symbol: str, timeframe: str = "4h") -> dict:
        """
        Fetch OHLCV data and render chart.

        Returns:
            {"success": True,  "image": bytes, "info": {...}}
            {"success": False, "error": "..."}
        """
        import yfinance as yf
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        sym_upper = symbol.upper().strip()
        tf_lower  = timeframe.lower().strip()

        if tf_lower not in TF_CONFIG:
            valid = ", ".join(VALID_TIMEFRAMES)
            return {"success": False, "error": f"Неизвестный таймфрейм '{timeframe}'. Доступны: {valid}"}

        yf_symbol = SYMBOL_MAP.get(sym_upper, sym_upper)
        yf_interval, yf_period, resample_rule, n_candles = TF_CONFIG[tf_lower]

        try:
            df = yf.download(
                yf_symbol,
                period=yf_period,
                interval=yf_interval,
                progress=False,
                auto_adjust=True,
            )
        except Exception as e:
            return {"success": False, "error": f"Ошибка загрузки данных: {e}"}

        if df is None or df.empty:
            return {
                "success": False,
                "error":   f"Нет данных для '{sym_upper}'. Проверь тикер (например: BTCUSDT, EURUSD, NQ)."
            }

        # Flatten MultiIndex columns (yfinance may return them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # Keep only OHLCV
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna()

        # Resample if needed (1h → 4h)
        if resample_rule:
            df = df.resample(resample_rule).agg({
                "Open":   "first",
                "High":   "max",
                "Low":    "min",
                "Close":  "last",
                "Volume": "sum",
            }).dropna()

        df = df.tail(n_candles)

        if len(df) < 10:
            return {"success": False, "error": "Недостаточно данных для построения графика."}

        # Price metadata
        last_price  = float(df["Close"].iloc[-1])
        open_price  = float(df["Open"].iloc[0])
        change_pct  = ((last_price - open_price) / open_price) * 100
        high        = float(df["High"].max())
        low         = float(df["Low"].min())

        try:
            image_bytes = self._render(df, sym_upper, tf_lower, last_price, change_pct)
        except Exception as e:
            return {"success": False, "error": f"Ошибка рендеринга: {e}"}

        return {
            "success": True,
            "image":   image_bytes,
            "info": {
                "symbol":     sym_upper,
                "yf_symbol":  yf_symbol,
                "timeframe":  tf_lower,
                "candles":    len(df),
                "last_price": last_price,
                "change_pct": round(change_pct, 2),
                "high":       high,
                "low":        low,
            },
        }

    def _render(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        last_price: float,
        change_pct: float,
    ) -> bytes:
        """Render TradingView-like dark candlestick chart. Returns JPEG bytes."""
        import mplfinance as mpf
        import matplotlib.pyplot as plt

        # TradingView dark color scheme
        mc = mpf.make_marketcolors(
            up     = "#26a69a",   # teal-green
            down   = "#ef5350",   # red
            edge   = "inherit",
            wick   = "inherit",
            volume = {"up": "#26a69a66", "down": "#ef535066"},
        )
        style = mpf.make_mpf_style(
            marketcolors  = mc,
            base_mpf_style = "nightclouds",
            facecolor      = "#131722",
            edgecolor      = "#2a2e39",
            figcolor       = "#131722",
            gridcolor      = "#2a2e39",
            gridstyle      = "--",
            gridaxis       = "both",
            y_on_right     = True,
            rc = {
                "font.size":   8,
                "text.color":  "#d1d4dc",
                "axes.labelcolor": "#d1d4dc",
                "xtick.color": "#d1d4dc",
                "ytick.color": "#d1d4dc",
            },
        )

        change_sign = "+" if change_pct >= 0 else ""
        title = f"{symbol}  ·  {timeframe.upper()}     {last_price:,.4f}  ({change_sign}{change_pct:.2f}%)"

        buf = io.BytesIO()
        fig, axes = mpf.plot(
            df,
            type       = "candle",
            style      = style,
            volume     = True,
            figsize    = (12, 7),
            tight_layout = True,
            returnfig  = True,
        )
        # Set title on the price axis (axes[0])
        axes[0].set_title(title, color="#d1d4dc", fontsize=10, pad=6, loc="left")

        fig.savefig(
            buf,
            format     = "jpeg",
            dpi        = 130,
            bbox_inches = "tight",
            facecolor  = "#131722",
            edgecolor  = "none",
        )
        plt.close(fig)
        buf.seek(0)
        return buf.read()
