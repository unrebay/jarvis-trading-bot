"""
generate_lesson_images.py — Генерирует учебные диаграммы ICT/SMC концепций
и загружает их в Supabase Storage (bucket: lesson-images).

Запуск: python -m src.ingestion.generate_lesson_images

v2 — 20 концепций (было 8):
  Beginner:     Market Structure, BOS/CHoCH, Candlesticks, Trend, Support/Resistance,
                Liquidity, Risk Management
  Intermediate: FVG, Order Block, Premium/Discount, Inducement, MSS,
                Breaker Block, Liquidity Sweep, Displacement, BPR
  Advanced:     AMD, OTE, ICT Killzones, Judas Swing, TGIF
"""

import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BUCKET = "lesson-images"

# ── Dark theme ─────────────────────────────────────────────────────────────────
BG     = "#131722"
GRID   = "#2a2e39"
TEXT   = "#d1d4dc"
GREEN  = "#26a69a"
RED    = "#ef5350"
BLUE   = "#2196F3"
ORANGE = "#FF9800"
PURPLE = "#9C27B0"
YELLOW = "#FFD700"
GRAY   = "#787b86"


def _base_fig(title: str, w=10, h=6):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.set_title(title, color=TEXT, fontsize=14, fontweight="bold", pad=12)
    ax.grid(color=GRID, linestyle="--", linewidth=0.5, alpha=0.5)
    return fig, ax


def _candle(ax, x, o, h, l, c, w=0.4):
    color = GREEN if c >= o else RED
    ax.plot([x, x], [l, h], color=color, linewidth=1.5)
    ax.add_patch(mpatches.FancyBboxPatch(
        (x - w/2, min(o, c)), w, abs(c - o) + 1e-6,
        boxstyle="square,pad=0", facecolor=color, edgecolor=color, linewidth=0
    ))


def _label(ax, x, y, text, color=TEXT, fontsize=9, ha="left", va="center"):
    ax.text(x, y, text, color=color, fontsize=fontsize, ha=ha, va=va,
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=BG, edgecolor=GRID, alpha=0.85))


def _save(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════════
# BEGINNER DIAGRAMS
# ══════════════════════════════════════════════════════════════════════════════

def draw_market_structure() -> bytes:
    fig, ax = _base_fig("Market Structure — HH · HL · LH · LL")
    bull = [100, 95, 108, 102, 116, 109, 124, 117, 130]
    xs   = list(range(len(bull)))
    ax.plot(xs, bull, color=GREEN, linewidth=2)
    pts = [
        (0, 100, "Low",  GREEN, -3), (1, 95,  "LL",   RED,   -3),
        (2, 108, "HH",   GREEN,  2), (3, 102, "HL",   GREEN, -3),
        (4, 116, "HH",   GREEN,  2), (5, 109, "HL",   GREEN, -3),
        (6, 124, "HH",   GREEN,  2), (7, 117, "HL",   GREEN, -3),
        (8, 130, "HH",   GREEN,  2),
    ]
    for x, y, lbl, col, off in pts:
        ax.scatter(x, y, color=col, zorder=5, s=50)
        _label(ax, x + 0.1, y + off, lbl, color=col, fontsize=9)
    for bx, by in [(2, 108), (4, 116), (6, 124)]:
        ax.plot([bx-2, bx+2], [by-8, by-8], color=BLUE, linewidth=1, linestyle="--", alpha=0.7)
    _label(ax, 3, 113, "--- BOS (Break of Structure)", color=BLUE, fontsize=8)
    _label(ax, 3, 110, "Каждый BOS = продолжение тренда", color=TEXT, fontsize=8)
    ax.set_xlim(-0.5, 10); ax.set_ylim(88, 138); ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_bos_choch() -> bytes:
    fig, ax = _base_fig("BOS & CHoCH — Пробой структуры и смена характера")
    pts = [(0,100),(1,110),(2,106),(3,118),(4,112),(5,122),(6,115),(7,125),(8,108),(9,114),(10,103)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=TEXT, linewidth=1.5, alpha=0.6)
    for x, y, lbl in [(3,118,"HH"),(5,122,"HH"),(7,125,"HH")]:
        ax.scatter(x, y, color=GREEN, zorder=5, s=50)
        _label(ax, x+0.1, y+1, lbl, color=GREEN)
    for x, y, lbl in [(2,106,"HL"),(4,112,"HL"),(6,115,"HL")]:
        ax.scatter(x, y, color=GREEN, zorder=5, s=40)
        _label(ax, x+0.1, y-2, lbl, color=GREEN)
    ax.plot([1,4],[110,110], color=BLUE, linewidth=1.2, linestyle="--")
    _label(ax, 4.1, 110, "BOS ▲", color=BLUE, fontsize=8)
    ax.plot([3,6],[118,118], color=BLUE, linewidth=1.2, linestyle="--")
    _label(ax, 6.1, 118, "BOS ▲", color=BLUE, fontsize=8)
    ax.plot([6,9],[115,115], color=ORANGE, linewidth=1.8, linestyle="--")
    _label(ax, 8.2, 115.5, "CHoCH ▼\n(разворот!)", color=ORANGE, fontsize=9)
    ax.scatter(8,108,color=RED,zorder=5,s=60); ax.scatter(10,103,color=RED,zorder=5,s=60)
    _label(ax, 8.1, 107, "LH", color=RED); _label(ax, 10.1, 102, "LL", color=RED)
    ax.set_xlim(-0.5, 11.5); ax.set_ylim(96, 132); ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_candlesticks() -> bytes:
    fig, ax = _base_fig("Candlestick Basics — Анатомия свечей")
    candles = [
        (1, 100, 115, 98,  112, "Bullish\n(бычья)"),
        (3, 112, 114, 100, 102, "Bearish\n(медвежья)"),
        (5, 106, 118, 104, 110, "Long upper\nwick (тень)"),
        (7, 108, 110, 96,  102, "Long lower\nwick (тень)"),
        (9, 104, 112, 102, 108, "Doji\n(неопределённость)"),
    ]
    for x, o, h, l, c, lbl in candles:
        _candle(ax, x, o, h, l, c)
        _label(ax, x - 0.3, l - 4, lbl, color=TEXT, fontsize=7.5, ha="center")
    # Anatomy arrows for first candle
    ax.annotate("", xy=(1, 115), xytext=(1, 112), arrowprops=dict(arrowstyle="<->", color=YELLOW, lw=1.2))
    _label(ax, 1.5, 113.5, "Upper wick", color=YELLOW, fontsize=7.5)
    ax.annotate("", xy=(1, 112), xytext=(1, 100), arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.2))
    _label(ax, 1.5, 106, "Body\n(тело)", color=GREEN, fontsize=7.5)
    ax.annotate("", xy=(1, 100), xytext=(1, 98), arrowprops=dict(arrowstyle="<->", color=YELLOW, lw=1.2))
    _label(ax, 1.5, 99, "Lower wick", color=YELLOW, fontsize=7.5)
    ax.set_xlim(0, 11); ax.set_ylim(88, 126); ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_trend() -> bytes:
    fig, ax = _base_fig("Trend — Восходящий · Нисходящий · Боковой")
    # Uptrend
    up_x = [0,1,2,3,4,5,6]
    up_y = [100,105,103,110,108,116,114]
    ax.plot(up_x, up_y, color=GREEN, linewidth=2)
    ax.add_patch(mpatches.FancyBboxPatch((0, 98), 6, 2, boxstyle="square,pad=0", facecolor=GREEN, alpha=0.08))
    _label(ax, 2.5, 95, "UPTREND\n(восходящий)", color=GREEN, fontsize=10, ha="center")
    # Downtrend
    dn_x = [8,9,10,11,12,13,14]
    dn_y = [116,111,113,107,109,103,105]
    ax.plot(dn_x, dn_y, color=RED, linewidth=2)
    _label(ax, 10.5, 97, "DOWNTREND\n(нисходящий)", color=RED, fontsize=10, ha="center")
    # Sideways
    sw_x = [16,17,18,19,20,21,22]
    sw_y = [108,112,106,110,107,113,108]
    ax.plot(sw_x, sw_y, color=YELLOW, linewidth=2)
    ax.axhline(y=114, xmin=16/24, xmax=23/24, color=YELLOW, linestyle="--", alpha=0.5)
    ax.axhline(y=104, xmin=16/24, xmax=23/24, color=YELLOW, linestyle="--", alpha=0.5)
    _label(ax, 18.5, 97, "SIDEWAYS\n(флэт)", color=YELLOW, fontsize=10, ha="center")
    ax.set_xlim(-1, 23); ax.set_ylim(90, 124); ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_support_resistance() -> bytes:
    fig, ax = _base_fig("Support & Resistance — Поддержка и Сопротивление")
    data = [100,106,103,110,107,115,110,115,108,116,111,118,113,110,112,108,111,114,110,116]
    ax.plot(data, color=TEXT, linewidth=1.5)
    ax.axhline(y=115, color=RED,   linewidth=1.8, linestyle="--")
    ax.axhline(y=108, color=GREEN, linewidth=1.8, linestyle="--")
    _label(ax, 0.2, 116, "RESISTANCE (сопротивление) — продавцы здесь", color=RED, fontsize=9)
    _label(ax, 0.2, 106.5, "SUPPORT (поддержка) — покупатели здесь", color=GREEN, fontsize=9)
    # Breakout arrow
    ax.annotate("", xy=(18, 117), xytext=(18, 115),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2))
    _label(ax, 18.2, 116, "Пробой!\nResistance → Support", color=ORANGE, fontsize=8)
    ax.set_xlim(-0.5, 21); ax.set_ylim(100, 124); ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_liquidity() -> bytes:
    fig, ax = _base_fig("Ликвидность — BSL & SSL")
    data = [100,108,103,112,106,115,109,116,108,119,111,120,105,118,113]
    ax.plot(data, color=TEXT, linewidth=1.5)
    for sh in [1,3,5,7,9,11]: ax.scatter(sh, data[sh], color=RED, s=40, zorder=5)
    ax.axhline(y=120, color=RED,   linewidth=1, linestyle=":", alpha=0.7)
    _label(ax, 0.1, 121, "BSL — Buy Side Liquidity (стопы шортистов)", color=RED, fontsize=9)
    for sl in [2,4,6,8,10]: ax.scatter(sl, data[sl], color=GREEN, s=40, zorder=5)
    ax.axhline(y=103, color=GREEN, linewidth=1, linestyle=":", alpha=0.7)
    _label(ax, 0.1, 101.5, "SSL — Sell Side Liquidity (стопы лонгистов)", color=GREEN, fontsize=9)
    ax.annotate("", xy=(11,120.5), xytext=(11,111),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2))
    _label(ax, 11.3, 116, "Sweep!\nЗабирают ликвидность\nперед разворотом", color=ORANGE, fontsize=8)
    ax.set_xlim(-0.5,15); ax.set_ylim(98,126); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_risk_management() -> bytes:
    fig, ax = _base_fig("Risk Management — Управление рисками")
    ax.set_xlim(0, 10); ax.set_ylim(80, 140)
    # Trade example: entry, SL, TP
    entry = 110; sl = 105; tp1 = 120; tp2 = 130
    ax.axhline(y=entry, color=YELLOW, linewidth=2, linestyle="-")
    ax.axhline(y=sl,    color=RED,    linewidth=1.5, linestyle="--")
    ax.axhline(y=tp1,   color=GREEN,  linewidth=1.5, linestyle="--")
    ax.axhline(y=tp2,   color=GREEN,  linewidth=2,   linestyle="-")
    ax.add_patch(mpatches.FancyBboxPatch((0, sl), 10, entry-sl,
        boxstyle="square,pad=0", facecolor=RED, alpha=0.1))
    ax.add_patch(mpatches.FancyBboxPatch((0, entry), 10, tp2-entry,
        boxstyle="square,pad=0", facecolor=GREEN, alpha=0.1))
    _label(ax, 0.2, entry+0.5, f"ENTRY: {entry}", color=YELLOW, fontsize=10)
    _label(ax, 0.2, sl-1.5,    f"SL: {sl}  (-{entry-sl} pts = -1R)", color=RED, fontsize=9)
    _label(ax, 0.2, tp1+0.5,   f"TP1: {tp1}  (+{tp1-entry} pts = +2R)", color=GREEN, fontsize=9)
    _label(ax, 0.2, tp2+0.5,   f"TP2: {tp2}  (+{tp2-entry} pts = +4R)", color=GREEN, fontsize=10)
    risk = entry - sl; reward = tp2 - entry
    _label(ax, 5, 87, f"RR = {reward/risk:.1f}:1   |   Risk = 1%   |   Потенциал = {reward/risk:.0f}%",
           color=TEXT, fontsize=9, ha="center")
    ax.set_xticks([]); ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


# ══════════════════════════════════════════════════════════════════════════════
# INTERMEDIATE DIAGRAMS
# ══════════════════════════════════════════════════════════════════════════════

def draw_fvg() -> bytes:
    fig, ax = _base_fig("FVG — Fair Value Gap (Имбалланс)")
    candles = [(1,100,108,98,106),(2,107,120,106,118),(3,117,122,112,119)]
    for x,o,h,l,c in candles: _candle(ax,x,o,h,l,c)
    ax.add_patch(mpatches.FancyBboxPatch((0.6,108),2.8,4,boxstyle="square,pad=0",
        facecolor=GREEN, edgecolor=GREEN, alpha=0.2, linewidth=0))
    ax.plot([0.6,3.4],[108,108],color=GREEN,linewidth=1.2,linestyle="--")
    ax.plot([0.6,3.4],[112,112],color=GREEN,linewidth=1.2,linestyle="--")
    _label(ax,3.5,110,"  FVG\n(Bullish)",color=GREEN,fontsize=10)
    _label(ax,0.9,106.5,"Candle 1\nhigh: 108",color=TEXT,fontsize=8)
    _label(ax,2.7,110.5,"Candle 3\nlow: 112",color=TEXT,fontsize=8)
    ax.annotate("",xy=(3.0,110),xytext=(3.0,122),
                arrowprops=dict(arrowstyle="->",color=YELLOW,lw=1.5))
    _label(ax,3.05,119,"Цена вернётся\nзаполнить FVG",color=YELLOW,fontsize=8)
    ax.set_xlim(0.2,5); ax.set_ylim(94,128); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_order_block() -> bytes:
    fig, ax = _base_fig("Order Block (OB) — Блок ордеров")
    candles = [(1,118,122,116,120),(2,120,124,119,122),(3,121,122,112,113),(4,113,115,108,110),(5,110,111,104,106)]
    for x,o,h,l,c in candles: _candle(ax,x,o,h,l,c)
    ax.add_patch(mpatches.FancyBboxPatch((1.6,119),3.8,5,boxstyle="square,pad=0",
        facecolor=RED, edgecolor=RED, alpha=0.18, linewidth=0))
    ax.plot([1.6,5.4],[119,119],color=RED,linewidth=1.2,linestyle="--")
    ax.plot([1.6,5.4],[124,124],color=RED,linewidth=1.2,linestyle="--")
    _label(ax,5.5,121.5,"Bearish OB\n(зона возврата)",color=RED,fontsize=10)
    ax.annotate("",xy=(5.0,121),xytext=(5.0,106),
                arrowprops=dict(arrowstyle="->",color=YELLOW,lw=1.5))
    _label(ax,4.8,108,"Цена вернётся\nк OB для шорта",color=YELLOW,fontsize=8,ha="right")
    ax.set_xlim(0.2,7.5); ax.set_ylim(100,130); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_premium_discount() -> bytes:
    fig, ax = _base_fig("Premium / Discount — Зоны ценности")
    ax.set_xlim(0,10); ax.set_ylim(90,160)
    sl, sh = 100, 150; mid = (sl+sh)/2
    ax.add_patch(mpatches.FancyBboxPatch((0,sh*0.75),10,sh-sh*0.75,boxstyle="square,pad=0",facecolor=RED,alpha=0.12))
    ax.add_patch(mpatches.FancyBboxPatch((0,mid),10,sh*0.75-mid,boxstyle="square,pad=0",facecolor=RED,alpha=0.06))
    ax.add_patch(mpatches.FancyBboxPatch((0,sl),10,mid-sl,boxstyle="square,pad=0",facecolor=GREEN,alpha=0.06))
    ax.add_patch(mpatches.FancyBboxPatch((0,sl),10,sl*0.25,boxstyle="square,pad=0",facecolor=GREEN,alpha=0.12))
    ax.axhline(y=sh,color=RED,linewidth=1.5); ax.axhline(y=mid,color=YELLOW,linewidth=2,linestyle="--")
    ax.axhline(y=sl,color=GREEN,linewidth=1.5)
    _label(ax,0.2,152,"Swing High",color=RED,fontsize=10)
    _label(ax,0.2,147,"PREMIUM — продавать/шортить",color=RED,fontsize=9)
    _label(ax,0.2,125.5,"EQUILIBRIUM (50%) — нейтральная зона",color=YELLOW,fontsize=9)
    _label(ax,0.2,105,"DISCOUNT — покупать/лонговать",color=GREEN,fontsize=9)
    _label(ax,0.2,99,"Swing Low",color=GREEN,fontsize=10)
    ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_inducement() -> bytes:
    fig, ax = _base_fig("Inducement (IDM) — Ложная приманка")
    data = [100,112,108,116,113,117,111,119,113,122]
    ax.plot(data, color=TEXT, linewidth=1.5)
    ax.scatter(6,111,color=ORANGE,s=100,zorder=6,marker="v")
    _label(ax,6.2,111,"IDM!\n(ложное HL — приманка\nдля шортистов)",color=ORANGE,fontsize=9)
    ax.scatter(8,113,color=GREEN,s=80,zorder=5)
    _label(ax,8.2,113,"Реальное HL\n(после сбора IDM)",color=GREEN,fontsize=9)
    ax.annotate("",xy=(6,111),xytext=(6,116),arrowprops=dict(arrowstyle="->",color=ORANGE,lw=1.5))
    _label(ax,3.5,108,"Цена пробивает IDM, забирает\nстопы, затем продолжает рост",color=TEXT,fontsize=9)
    ax.set_xlim(-0.5,11); ax.set_ylim(96,128); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_mss() -> bytes:
    fig, ax = _base_fig("MSS — Market Structure Shift (Смена структуры)")
    # Uptrend then MSS
    data = [100,95,108,102,116,109,122,112,118,105,112,98,105]
    ax.plot(data, color=TEXT, linewidth=1.5)
    # Uptrend labels
    ax.scatter(0,100,color=GREEN,s=50,zorder=5); _label(ax,0.1,99,"Low",color=GREEN,fontsize=8)
    ax.scatter(2,108,color=GREEN,s=50,zorder=5); _label(ax,2.1,109,"HH",color=GREEN,fontsize=8)
    ax.scatter(3,102,color=GREEN,s=50,zorder=5); _label(ax,3.1,100,"HL",color=GREEN,fontsize=8)
    ax.scatter(4,116,color=GREEN,s=50,zorder=5); _label(ax,4.1,117,"HH",color=GREEN,fontsize=8)
    ax.scatter(5,109,color=GREEN,s=50,zorder=5); _label(ax,5.1,107,"HL",color=GREEN,fontsize=8)
    ax.scatter(6,122,color=GREEN,s=50,zorder=5); _label(ax,6.1,123,"HH",color=GREEN,fontsize=8)
    # MSS line
    ax.plot([5,9],[109,109],color=ORANGE,linewidth=2,linestyle="--")
    _label(ax,8,110,"MSS ▼\nПробой HL\n= смена структуры!",color=ORANGE,fontsize=9)
    # After MSS
    ax.scatter(9,105,color=RED,s=60,zorder=5);  _label(ax,9.1,103,"LH",color=RED,fontsize=8)
    ax.scatter(11,98,color=RED,s=60,zorder=5);  _label(ax,11.1,96,"LL",color=RED,fontsize=8)
    ax.set_xlim(-0.5,13); ax.set_ylim(90,130); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_breaker_block() -> bytes:
    fig, ax = _base_fig("Breaker Block — Переломный блок")
    # Original OB → broken → becomes breaker
    candles = [
        (1, 108, 112, 106, 110),  # last bullish before drop (OB candidate)
        (2, 109, 110, 100, 102),  # sharp drop
        (3, 102, 104,  98, 100),
        (4, 100, 106,  99, 105),  # bounce
        (5, 105, 116, 104, 114),  # breaks back above OB → OB becomes Breaker
        (6, 113, 115, 108, 110),
    ]
    for x,o,h,l,c in candles: _candle(ax,x,o,h,l,c)
    # Original OB zone (now broken = Breaker)
    ax.add_patch(mpatches.FancyBboxPatch((0.6,106),5.8,4,boxstyle="square,pad=0",
        facecolor=PURPLE, edgecolor=PURPLE, alpha=0.2, linewidth=0))
    ax.plot([0.6,6.4],[106,106],color=PURPLE,linewidth=1.2,linestyle="--")
    ax.plot([0.6,6.4],[110,110],color=PURPLE,linewidth=1.2,linestyle="--")
    _label(ax,6.5,108,"BREAKER BLOCK\n(бывший OB —\nтеперь поддержка)",color=PURPLE,fontsize=9)
    _label(ax,1.5,94,"Медвежий OB не удержал\n→ стал Breaker Block",color=TEXT,fontsize=8)
    ax.set_xlim(0,9); ax.set_ylim(90,122); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_liquidity_sweep() -> bytes:
    fig, ax = _base_fig("Liquidity Sweep — Выбивание стопов")
    data = [100,105,102,108,106,110,107,112,110,114,112,120,115,112,108,110,106]
    ax.plot(data, color=TEXT, linewidth=1.5)
    # Swing highs line
    ax.axhline(y=114,color=RED,linewidth=1,linestyle=":",alpha=0.7)
    _label(ax,0.2,115,"Equal Highs\n(BSL зона — там стопы)",color=RED,fontsize=9)
    # Sweep spike
    ax.scatter(11,120,color=ORANGE,s=120,zorder=6,marker="^")
    _label(ax,11.2,120,"SWEEP!\n(выбило стопы\nвыше EQH)",color=ORANGE,fontsize=9)
    # Reversal
    ax.annotate("",xy=(15,106),xytext=(11,120),
                arrowprops=dict(arrowstyle="->",color=RED,lw=2,connectionstyle="arc3,rad=0.3"))
    _label(ax,13,112,"Разворот после\nсбора ликвидности",color=RED,fontsize=8)
    ax.set_xlim(-0.5,18); ax.set_ylim(96,126); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_displacement() -> bytes:
    fig, ax = _base_fig("Displacement — Импульсное смещение цены")
    # Slow grind up, then displacement
    slow = list(range(8))
    slow_y = [100+i*1.5+np.sin(i)*2 for i in slow]
    ax.plot(slow, slow_y, color=GRAY, linewidth=1.5, alpha=0.8)
    _label(ax, 3, 97, "Медленное\nдвижение", color=GRAY, fontsize=8, ha="center")
    # Displacement candles
    disp = [(8,110,120,109,119),(9,119,128,118,126),(10,125,130,123,128)]
    for x,o,h,l,c in disp: _candle(ax,x,o,h,l,c)
    ax.add_patch(mpatches.FancyBboxPatch((7.5,108),3.5,22,boxstyle="square,pad=0",
        facecolor=GREEN,alpha=0.08))
    _label(ax,8.8,106,"DISPLACEMENT\n(3 большие бычьи свечи\n= институциональный вход)",color=GREEN,fontsize=9)
    # FVG left behind
    ax.add_patch(mpatches.FancyBboxPatch((8.6,119),2,6,boxstyle="square,pad=0",
        facecolor=GREEN,alpha=0.2,edgecolor=GREEN,linewidth=1))
    _label(ax,11.2,122,"FVG\n(имбаланс)",color=GREEN,fontsize=8)
    ax.set_xlim(-0.5,13); ax.set_ylim(92,136); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_bpr() -> bytes:
    fig, ax = _base_fig("BPR — Balanced Price Range")
    # Two opposing FVGs that overlap = BPR
    ax.set_xlim(0,10); ax.set_ylim(95,130)
    # Bearish FVG (from drop)
    ax.add_patch(mpatches.FancyBboxPatch((0,115),10,5,boxstyle="square,pad=0",
        facecolor=RED, alpha=0.15, edgecolor=RED, linewidth=1))
    ax.plot([0,10],[115,115],color=RED,linewidth=1,linestyle="--")
    ax.plot([0,10],[120,120],color=RED,linewidth=1,linestyle="--")
    _label(ax,0.2,122,"Bearish FVG",color=RED,fontsize=9)
    # Bullish FVG (from rise)
    ax.add_patch(mpatches.FancyBboxPatch((0,112),10,5,boxstyle="square,pad=0",
        facecolor=GREEN, alpha=0.15, edgecolor=GREEN, linewidth=1))
    ax.plot([0,10],[112,112],color=GREEN,linewidth=1,linestyle="--")
    ax.plot([0,10],[117,117],color=GREEN,linewidth=1,linestyle="--")
    _label(ax,0.2,110.5,"Bullish FVG",color=GREEN,fontsize=9)
    # Overlap = BPR
    ax.add_patch(mpatches.FancyBboxPatch((0,115),10,2,boxstyle="square,pad=0",
        facecolor=YELLOW, alpha=0.3, edgecolor=YELLOW, linewidth=2))
    _label(ax,4,117,"BPR — зона перекрытия двух FVG\n(магнит для цены)",color=YELLOW,fontsize=10,ha="center")
    ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


# ══════════════════════════════════════════════════════════════════════════════
# ADVANCED DIAGRAMS
# ══════════════════════════════════════════════════════════════════════════════

def draw_amd() -> bytes:
    fig, ax = _base_fig("AMD — Accumulation · Manipulation · Distribution")
    phases = {
        "Accumulation\n(сбор позиции)": (0,3,100,108,GREEN,0.08),
        "Manipulation\n(ложный пробой)": (3,6,108,95,RED,0.1),
        "Distribution\n(движение)": (6,10,95,130,GREEN,0.12),
    }
    for label,(x1,x2,y1,y2,color,alpha) in phases.items():
        ax.add_patch(mpatches.FancyBboxPatch((x1,min(y1,y2)-2),x2-x1,abs(y2-y1)+4,
            boxstyle="square,pad=0",facecolor=color,alpha=alpha))
        _label(ax,(x1+x2)/2,(y1+y2)/2+10,label,color=color,fontsize=9,ha="center")
    path_x = [0,1,2,1.5,2.5,3,3.5,4,4.5,5,5.5,6,7,8,9,10]
    path_y = [100,104,102,106,104,108,105,100,97,95,98,95,100,110,120,130]
    ax.plot(path_x,path_y,color=TEXT,linewidth=2)
    _label(ax,3.3,92,"Judas Swing\n(ложный пробой вниз)",color=RED,fontsize=8)
    _label(ax,7.0,132,"Настоящее движение ▲",color=GREEN,fontsize=9)
    ax.set_xlim(-0.5,11); ax.set_ylim(86,142); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_ote() -> bytes:
    fig, ax = _base_fig("OTE — Optimal Trade Entry (Зона оптимального входа)")
    ax.set_xlim(0,10); ax.set_ylim(90,155)
    low, high = 100, 150
    fib_levels = {
        0.0:   (high, "1.0 — Swing High"),
        0.236: (high-(high-low)*0.236, "0.786"),
        0.5:   ((high+low)/2, "0.5 — Equilibrium"),
        0.618: (high-(high-low)*0.618, "0.618"),
        0.705: (high-(high-low)*0.705, "0.705 ← OTE START"),
        0.79:  (high-(high-low)*0.79,  "0.79  ← OTE END"),
        1.0:   (low, "0.0 — Swing Low"),
    }
    for fib,(price,label) in fib_levels.items():
        color = ORANGE if "OTE" in label else (YELLOW if "Equil" in label else GRAY)
        lw    = 2 if "OTE" in label else 1
        ax.axhline(y=price,color=color,linewidth=lw,linestyle="--",alpha=0.8)
        _label(ax,0.2,price+0.5,label,color=color,fontsize=8)
    # OTE zone highlight
    ote_low = high-(high-low)*0.79; ote_high = high-(high-low)*0.705
    ax.add_patch(mpatches.FancyBboxPatch((0,ote_low),10,ote_high-ote_low,
        boxstyle="square,pad=0",facecolor=ORANGE,alpha=0.2))
    _label(ax,4,ote_low+(ote_high-ote_low)/2,"OTE ЗОНА\n(лучшее место входа после откатa)",
           color=ORANGE,fontsize=10,ha="center")
    ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_killzones() -> bytes:
    fig, ax = _base_fig("ICT Killzones — Лучшее время для торговли (UTC)")
    ax.set_xlim(0,24); ax.set_ylim(0,5)
    sessions = [
        (0,  8,  0.5, "ASIA\n00:00–08:00\n(консолидация)", GRAY),
        (8,  13, 2.0, "LONDON\n08:00–13:00\n(основное движение)", GREEN),
        (13, 16, 2.5, "NY OPEN\n13:00–16:00\n(максимальная\nволатильность)", RED),
        (16, 20, 1.5, "NY AFTERNOON\n16:00–20:00\n(стихает)", BLUE),
        (20, 24, 0.5, "ЗАКРЫТИЕ\n20:00–00:00\n(неактивно)", GRAY),
    ]
    for x1,x2,importance,label,color in sessions:
        ax.add_patch(mpatches.FancyBboxPatch((x1,0),x2-x1,importance+0.5,
            boxstyle="square,pad=0",facecolor=color,alpha=0.2,edgecolor=color,linewidth=1))
        ax.text((x1+x2)/2, (importance+0.5)/2, label, color=color, fontsize=7.5,
                ha="center", va="center", fontfamily="monospace")
    # Kill zone highlights
    for x1,x2 in [(8,10),(13,15)]:
        ax.add_patch(mpatches.FancyBboxPatch((x1,0),x2-x1,5,
            boxstyle="square,pad=0",facecolor=YELLOW,alpha=0.07))
    _label(ax,8.2,4.6,"🎯 Kill Zone",color=YELLOW,fontsize=8)
    _label(ax,13.2,4.6,"🎯 Kill Zone",color=YELLOW,fontsize=8)
    ax.set_yticks([]); ax.set_xlabel("Время UTC", color=TEXT)
    ax.set_xticks([0,4,8,12,16,20,24])
    ax.set_xticklabels(["00:00","04:00","08:00","12:00","16:00","20:00","24:00"],color=TEXT,fontsize=8)
    return _save(fig)


def draw_judas_swing() -> bytes:
    fig, ax = _base_fig("Judas Swing — Ложный пробой перед настоящим движением")
    # Price at equilibrium, fake move up, then real move down
    data_x = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14]
    data_y = [110,111,112,110,109,115,118,116,110,105,100,95,92,88,85]
    ax.plot(data_x, data_y, color=TEXT, linewidth=1.5)
    ax.axhline(y=110, color=YELLOW, linewidth=1, linestyle="--", alpha=0.6)
    _label(ax,0.2,111.5,"Equilibrium",color=YELLOW,fontsize=8)
    # Fake pump zone
    ax.add_patch(mpatches.FancyBboxPatch((4,110),3,9,boxstyle="square,pad=0",
        facecolor=RED,alpha=0.1))
    ax.scatter(6,118,color=RED,s=100,zorder=6,marker="^")
    _label(ax,6.2,119,"JUDAS SWING\n(ложный памп вверх\n= приманка для лонгов)",color=RED,fontsize=9)
    # Real move arrow
    ax.annotate("",xy=(14,85),xytext=(7,116),
                arrowprops=dict(arrowstyle="->",color=GREEN,lw=2,connectionstyle="arc3,rad=0.2"))
    _label(ax,10,96,"Настоящее\nдвижение вниз",color=GREEN,fontsize=9)
    ax.set_xlim(-0.5,16); ax.set_ylim(78,128); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


def draw_tgif() -> bytes:
    fig, ax = _base_fig("TGIF — Thank God It's Friday Setup")
    # Thu-Fri pattern: sweep high on Thursday, reverse Friday
    days = ["Пн","Вт","Ср","Чт","Пт"]
    data = [100,103,101,106,104,108,106,112,109,116,115,120,116,114,112]
    xs   = [i*0.5 for i in range(len(data))]
    ax.plot(xs, data, color=TEXT, linewidth=1.5)
    # Thursday sweep
    ax.axvline(x=5,color=GRAY,linewidth=1,linestyle="--",alpha=0.5)
    ax.axvline(x=6,color=GRAY,linewidth=1,linestyle="--",alpha=0.5)
    _label(ax,5.1,98,"ЧТ",color=GRAY,fontsize=8)
    _label(ax,6.1,98,"ПТ",color=GRAY,fontsize=8)
    ax.scatter(11,120,color=RED,s=100,zorder=6,marker="^")
    _label(ax,11.2,121,"Sweep BSL\nв четверг!",color=RED,fontsize=9)
    # Friday reversal
    ax.annotate("",xy=(7,112),xytext=(5.5,118),
                arrowprops=dict(arrowstyle="->",color=GREEN,lw=2))
    _label(ax,6,114,"Пятница:\nразворот и\nпадение",color=GREEN,fontsize=8)
    _label(ax,1,94,"FVG часто остаётся незаполненным до пн",color=YELLOW,fontsize=8)
    ax.set_xlim(-0.5,8); ax.set_ylim(90,128); ax.set_xticks([]); ax.set_ylabel("Price",color=TEXT)
    return _save(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Concepts registry
# ══════════════════════════════════════════════════════════════════════════════

CONCEPTS = [
    # (concept_type, topic, draw_fn, level, caption)

    # ── Beginner ──────────────────────────────────────────────────────────────
    ("market_structure", "Market Structure", draw_market_structure, "Beginner",
     "Рыночная структура: HH (Higher High), HL (Higher Low), LH, LL и BOS"),
    ("bos_choch",        "BOS",              draw_bos_choch,        "Beginner",
     "BOS (Break of Structure) и CHoCH (Change of Character) — пробои и смена тренда"),
    ("candlesticks",     "Candlestick Basics", draw_candlesticks,   "Beginner",
     "Анатомия свечи: тело, верхняя и нижняя тень — основа технического анализа"),
    ("trend",            "Trend",            draw_trend,            "Beginner",
     "Три типа тренда: восходящий (бычий), нисходящий (медвежий), боковой (флэт)"),
    ("support_resistance","Support and Resistance", draw_support_resistance, "Beginner",
     "Поддержка и сопротивление: зоны где цена разворачивается"),
    ("liquidity",        "Liquidity",        draw_liquidity,        "Beginner",
     "Ликвидность: BSL (Buy Side) и SSL (Sell Side) — где стопы розничных трейдеров"),
    ("risk_management",  "Risk Management",  draw_risk_management,  "Beginner",
     "Управление рисками: SL, TP, RR ratio — без этого нет стабильного трейдинга"),

    # ── Intermediate ──────────────────────────────────────────────────────────
    ("fvg",              "FVG",              draw_fvg,              "Intermediate",
     "FVG (Fair Value Gap) — зона имбалланса между свечами, цена возвращается заполнить"),
    ("order_block",      "Order Block",      draw_order_block,      "Intermediate",
     "Order Block — последняя свеча перед импульсным движением, зона крупного игрока"),
    ("premium_discount", "Premium/Discount", draw_premium_discount, "Intermediate",
     "Premium и Discount зоны: выше 50% = дорого (шорт), ниже 50% = дёшево (лонг)"),
    ("inducement",       "Inducement",       draw_inducement,       "Intermediate",
     "Inducement (IDM) — ложная HL/LL-приманка перед реальным движением"),
    ("mss",              "MSS",              draw_mss,              "Intermediate",
     "MSS (Market Structure Shift) — пробой HL в аптренде = первый признак разворота"),
    ("breaker_block",    "Breaker Block",    draw_breaker_block,    "Intermediate",
     "Breaker Block — OB который был пробит и теперь сменил роль (поддержка ↔ сопротивление)"),
    ("liquidity_sweep",  "Liquidity Sweep",  draw_liquidity_sweep,  "Intermediate",
     "Liquidity Sweep — цена выходит за экстремум, выбивает стопы и разворачивается"),
    ("displacement",     "Displacement",     draw_displacement,     "Intermediate",
     "Displacement — резкое импульсное движение 3+ большими свечами = институциональный вход"),
    ("bpr",              "BPR",              draw_bpr,              "Intermediate",
     "BPR (Balanced Price Range) — пересечение двух FVG, сильная зона притяжения цены"),

    # ── Advanced ──────────────────────────────────────────────────────────────
    ("amd",              "AMD",              draw_amd,              "Advanced",
     "AMD (Power of Three): Accumulation → Manipulation → Distribution"),
    ("ote",              "OTE",              draw_ote,              "Advanced",
     "OTE (Optimal Trade Entry): зона 70.5–79% коррекции по Фибоначчи — лучший вход"),
    ("killzones",        "ICT Killzones",    draw_killzones,        "Advanced",
     "ICT Killzones: London 08-10 UTC и NY Open 13-15 UTC — лучшее время для входов"),
    ("judas_swing",      "Judas Swing",      draw_judas_swing,      "Advanced",
     "Judas Swing — ложное движение в начале сессии перед настоящим импульсом"),
    ("tgif",             "TGIF Setup",       draw_tgif,             "Advanced",
     "TGIF (Thank God It's Friday) — четверговый sweep + пятничный разворот"),
]


def upload_to_supabase(image_bytes: bytes, filename: str) -> str | None:
    """Upload image to Supabase Storage via direct REST API."""
    import requests
    path = f"concepts/{filename}"
    url  = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "image/png",
        "x-upsert":      "true",
    }
    try:
        resp = requests.post(url, data=image_bytes, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        print(f"  ⚠️  Upload error: {resp.status_code} {resp.text}")
        return None
    except Exception as e:
        print(f"  ⚠️  Upload error: {e}")
        return None


def insert_lesson_image(topic: str, image_url: str, caption: str, level: str, concept_type: str):
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table("lesson_images").upsert({
            "topic":        topic,
            "image_url":    image_url,
            "caption":      caption,
            "level":        level.lower(),
            "concept_type": concept_type,
            "source":       "generated",
        }, on_conflict="topic").execute()
    except Exception as e:
        print(f"  ⚠️  DB insert error: {e}")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL / SUPABASE_ANON_KEY not set in .env")
        sys.exit(1)

    print(f"🎨 Generating {len(CONCEPTS)} educational diagrams (v2)...\n")
    ok = 0
    for concept_type, topic, draw_fn, level, caption in CONCEPTS:
        print(f"  📐 {topic}...", end=" ", flush=True)
        try:
            image_bytes = draw_fn()
            filename    = f"{concept_type}.png"
            url         = upload_to_supabase(image_bytes, filename)
            if url:
                insert_lesson_image(topic, url, caption, level, concept_type)
                print(f"✅")
                ok += 1
            else:
                print("❌ upload failed")
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n{'✅' if ok == len(CONCEPTS) else '⚠️'} {ok}/{len(CONCEPTS)} диаграмм загружено.")
    print(f"   Bucket: {BUCKET}/concepts/")
    print(f"   Table:  lesson_images ({ok} rows upserted)")


if __name__ == "__main__":
    main()
