"""
generate_lesson_images.py — Генерирует учебные диаграммы ICT/SMC концепций
и загружает их в Supabase Storage (bucket: lesson-images).

Запуск: python -m src.ingestion.generate_lesson_images

Создаёт диаграммы для:
  FVG, Order Block, BOS/CHoCH, Liquidity, Market Structure,
  Premium/Discount, Inducement, AMD/Power of Three
"""

import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL          = os.getenv("SUPABASE_URL")
# Ingestion scripts need service_role key to bypass Storage RLS.
# Anon key only has SELECT on lesson-images bucket.
SUPABASE_SERVICE_KEY  = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")   # last-resort fallback (will 403)
)
BUCKET = "lesson-images"

# ── Dark theme ─────────────────────────────────────────────────────────────────
BG       = "#131722"
GRID     = "#2a2e39"
TEXT     = "#d1d4dc"
GREEN    = "#26a69a"
RED      = "#ef5350"
BLUE     = "#2196F3"
ORANGE   = "#FF9800"
PURPLE   = "#9C27B0"
YELLOW   = "#FFD700"


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


# ── Diagram generators ─────────────────────────────────────────────────────────

def draw_fvg() -> bytes:
    fig, ax = _base_fig("FVG — Fair Value Gap (Имбалланс)")
    candles = [
        (1, 100, 108, 98,  106),   # bullish
        (2, 107, 120, 106, 118),   # strong bullish impulse
        (3, 117, 122, 112, 119),   # continuation
    ]
    for x, o, h, l, c in candles:
        _candle(ax, x, o, h, l, c)

    # FVG zone: between wick of candle 1 (108) and wick of candle 3 (112)
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.6, 108), 2.8, 4, boxstyle="square,pad=0",
        facecolor=GREEN, edgecolor=GREEN, alpha=0.2, linewidth=0
    ))
    ax.plot([0.6, 3.4], [108, 108], color=GREEN, linewidth=1.2, linestyle="--")
    ax.plot([0.6, 3.4], [112, 112], color=GREEN, linewidth=1.2, linestyle="--")

    _label(ax, 3.5, 110, "  FVG\n(Bullish)", color=GREEN, fontsize=10)
    _label(ax, 0.9, 106.5, "Candle 1\nhigh: 108", color=TEXT, fontsize=8)
    _label(ax, 2.7, 110.5, "Candle 3\nlow: 112", color=TEXT, fontsize=8)

    # Arrow showing price will return to FVG
    ax.annotate("", xy=(3.0, 110), xytext=(3.0, 122),
                arrowprops=dict(arrowstyle="->", color=YELLOW, lw=1.5))
    _label(ax, 3.05, 119, "Цена вернётся\nзаполнить FVG", color=YELLOW, fontsize=8)

    ax.set_xlim(0.2, 5)
    ax.set_ylim(94, 128)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_order_block() -> bytes:
    fig, ax = _base_fig("Order Block (OB) — Блок ордеров")

    # Bearish move, then last bullish candle before drop = bearish OB
    candles = [
        (1, 118, 122, 116, 120),
        (2, 120, 124, 119, 122),   # last bullish → bearish OB
        (3, 121, 122, 112, 113),   # sharp drop
        (4, 113, 115, 108, 110),
        (5, 110, 111, 104, 106),
    ]
    for x, o, h, l, c in candles:
        _candle(ax, x, o, h, l, c)

    # OB zone = body of candle 2 (bullish, 120-122)
    ax.add_patch(mpatches.FancyBboxPatch(
        (1.6, 119), 3.8, 5, boxstyle="square,pad=0",
        facecolor=RED, edgecolor=RED, alpha=0.18, linewidth=0
    ))
    ax.plot([1.6, 5.4], [119, 119], color=RED, linewidth=1.2, linestyle="--")
    ax.plot([1.6, 5.4], [124, 124], color=RED, linewidth=1.2, linestyle="--")
    _label(ax, 5.5, 121.5, "Bearish OB\n(зона возврата)", color=RED, fontsize=10)

    # Arrow showing price will return to OB
    ax.annotate("", xy=(5.0, 121), xytext=(5.0, 106),
                arrowprops=dict(arrowstyle="->", color=YELLOW, lw=1.5))
    _label(ax, 4.8, 108, "Цена вернётся\nк OB для шорта", color=YELLOW, fontsize=8, ha="right")

    ax.set_xlim(0.2, 7.5)
    ax.set_ylim(100, 130)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_bos_choch() -> bytes:
    fig, ax = _base_fig("BOS & CHoCH — Структура рынка")

    # Uptrend: HH HL HH HL then CHoCH
    points = [
        (0,  100), (1, 110), (2, 106), (3, 118),   # HH
        (4,  112), (5, 122), (6, 115),              # HL then HH
        (7,  125), (8, 108),                         # potential CHoCH
        (9,  114), (10, 103),                        # new LL
    ]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(xs, ys, color=TEXT, linewidth=1.5, alpha=0.6)

    # Mark HH, HL
    labels_up = [(3, 118, "HH"), (5, 122, "HH"), (7, 125, "HH")]
    labels_hl = [(2, 106, "HL"), (4, 112, "HL"), (6, 115, "HL")]
    for x, y, lbl in labels_up:
        ax.scatter(x, y, color=GREEN, zorder=5, s=50)
        _label(ax, x+0.1, y+1, lbl, color=GREEN, fontsize=9)
    for x, y, lbl in labels_hl:
        ax.scatter(x, y, color=GREEN, zorder=5, s=40)
        _label(ax, x+0.1, y-2, lbl, color=GREEN, fontsize=9)

    # BOS lines
    ax.plot([1, 4], [110, 110], color=BLUE, linewidth=1.2, linestyle="--")
    _label(ax, 4.1, 110, "BOS ▲", color=BLUE, fontsize=8)
    ax.plot([3, 6], [118, 118], color=BLUE, linewidth=1.2, linestyle="--")
    _label(ax, 6.1, 118, "BOS ▲", color=BLUE, fontsize=8)

    # CHoCH — price breaks below HL (115) for the first time
    ax.plot([6, 9], [115, 115], color=ORANGE, linewidth=1.8, linestyle="--")
    _label(ax, 8.5, 115.5, "CHoCH ▼\n(разворот!)", color=ORANGE, fontsize=9)
    ax.scatter(8, 108, color=RED, zorder=5, s=60)
    ax.scatter(10, 103, color=RED, zorder=5, s=60)
    _label(ax, 8.1, 107, "LH", color=RED, fontsize=9)
    _label(ax, 10.1, 102, "LL", color=RED, fontsize=9)

    ax.set_xlim(-0.5, 11.5)
    ax.set_ylim(96, 132)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_liquidity() -> bytes:
    fig, ax = _base_fig("Ликвидность — BSL & SSL")

    # Price action with swing highs/lows and sweeps
    data = [100, 108, 103, 112, 106, 115, 109, 116, 108, 119, 111, 120, 105, 118, 113]
    xs = list(range(len(data)))
    ax.plot(xs, data, color=TEXT, linewidth=1.5)

    # BSL zone (above swing highs)
    swing_highs = [1, 3, 5, 7, 9, 11]
    for sh in swing_highs:
        ax.scatter(sh, data[sh], color=RED, s=40, zorder=5)
    ax.axhline(y=120, color=RED, linewidth=1, linestyle=":", alpha=0.7)
    _label(ax, 0.1, 121, "BSL — Buy Side Liquidity\n(стоп-лоссы шортистов выше)", color=RED, fontsize=9)

    # SSL zone (below swing lows)
    swing_lows = [2, 4, 6, 8, 10]
    for sl in swing_lows:
        ax.scatter(sl, data[sl], color=GREEN, s=40, zorder=5)
    ax.axhline(y=103, color=GREEN, linewidth=1, linestyle=":", alpha=0.7)
    _label(ax, 0.1, 101.5, "SSL — Sell Side Liquidity\n(стоп-лоссы лонгистов ниже)", color=GREEN, fontsize=9)

    # Sweep arrow at end (price sweeps BSL then reverses)
    ax.annotate("", xy=(11, 120.5), xytext=(11, 111),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2))
    _label(ax, 11.3, 116, "Sweep!\nЗабирают ликвидность\nперед разворотом", color=ORANGE, fontsize=8)

    ax.set_xlim(-0.5, 15)
    ax.set_ylim(98, 126)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_market_structure() -> bytes:
    fig, ax = _base_fig("Market Structure — Структура рынка")

    # Bullish trend
    bull_data = [100, 95, 108, 102, 116, 109, 124, 117, 130]
    bull_xs   = list(range(len(bull_data)))
    ax.plot(bull_xs, bull_data, color=GREEN, linewidth=2, label="Bullish trend")

    labels = [
        (0, 100, "Low", GREEN, "below"), (1, 95, "LL→SL", RED, "below"),
        (2, 108, "HH", GREEN, "above"), (3, 102, "HL", GREEN, "below"),
        (4, 116, "HH", GREEN, "above"), (5, 109, "HL", GREEN, "below"),
        (6, 124, "HH", GREEN, "above"), (7, 117, "HL", GREEN, "below"),
        (8, 130, "HH", GREEN, "above"),
    ]
    for x, y, lbl, col, pos in labels:
        offset = 2 if pos == "above" else -3
        ax.scatter(x, y, color=col, zorder=5, s=50)
        _label(ax, x+0.05, y+offset, lbl, color=col, fontsize=9)

    # BOS lines
    for bx, by in [(2, 108), (4, 116), (6, 124)]:
        prev_hh = by - 8
        ax.plot([bx-2, bx+2], [prev_hh, prev_hh], color=BLUE, linewidth=1, linestyle="--", alpha=0.7)

    _label(ax, 3.5, 115, "--- BOS (Break of Structure)", color=BLUE, fontsize=8)
    _label(ax, 3.5, 112, "Каждый BOS = продолжение тренда", color=TEXT, fontsize=8)

    ax.set_xlim(-0.5, 10)
    ax.set_ylim(90, 136)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_premium_discount() -> bytes:
    fig, ax = _base_fig("Premium / Discount — Зоны ценности")

    ax.set_xlim(0, 10)
    ax.set_ylim(90, 160)

    # Swing range
    swing_low, swing_high = 100, 150
    mid = (swing_low + swing_high) / 2  # 125 = equilibrium

    # Zones
    ax.add_patch(mpatches.FancyBboxPatch((0, swing_high*0.75), 10, swing_high - swing_high*0.75,
        boxstyle="square,pad=0", facecolor=RED, alpha=0.12))
    ax.add_patch(mpatches.FancyBboxPatch((0, mid), 10, swing_high*0.75 - mid,
        boxstyle="square,pad=0", facecolor=RED, alpha=0.06))
    ax.add_patch(mpatches.FancyBboxPatch((0, swing_low*1.25 - swing_low), 10, mid - (swing_low*1.25 - swing_low),
        boxstyle="square,pad=0", facecolor=GREEN, alpha=0.06))
    ax.add_patch(mpatches.FancyBboxPatch((0, swing_low), 10, swing_low*0.25,
        boxstyle="square,pad=0", facecolor=GREEN, alpha=0.12))

    ax.axhline(y=swing_high, color=RED, linewidth=1.5, linestyle="-")
    ax.axhline(y=mid,        color=YELLOW, linewidth=2,   linestyle="--")
    ax.axhline(y=swing_low,  color=GREEN, linewidth=1.5, linestyle="-")
    ax.axhline(y=swing_high*0.75, color=RED, linewidth=1, linestyle=":", alpha=0.6)
    ax.axhline(y=swing_low+swing_low*0.25, color=GREEN, linewidth=1, linestyle=":", alpha=0.6)

    _label(ax, 0.2, 152, "Swing High", color=RED, fontsize=10)
    _label(ax, 0.2, 147, "PREMIUM зона — продавать/шортить", color=RED, fontsize=9)
    _label(ax, 0.2, 137, "75% — начало Premium", color=RED, fontsize=8)
    _label(ax, 0.2, 125.5, "EQUILIBRIUM (50%) — нейтральная зона", color=YELLOW, fontsize=9)
    _label(ax, 0.2, 113, "25% — начало Discount", color=GREEN, fontsize=8)
    _label(ax, 0.2, 105, "DISCOUNT зона — покупать/лонговать", color=GREEN, fontsize=9)
    _label(ax, 0.2, 99, "Swing Low", color=GREEN, fontsize=10)

    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_inducement() -> bytes:
    fig, ax = _base_fig("Inducement (IDM) — Ложная приманка")

    data = [100, 112, 108, 116, 113, 117, 111, 119, 113, 122]
    xs = list(range(len(data)))
    ax.plot(xs, data, color=TEXT, linewidth=1.5)

    # IDM at position 6 (value=111) — looks like HL but is a trap
    ax.scatter(6, 111, color=ORANGE, s=100, zorder=6, marker="v")
    _label(ax, 6.2, 111, "IDM!\n(ложное HL — приманка\nдля шортистов)", color=ORANGE, fontsize=9)

    # Real HL
    ax.scatter(8, 113, color=GREEN, s=80, zorder=5)
    _label(ax, 8.2, 113, "Реальное HL\n(после сбора IDM)", color=GREEN, fontsize=9)

    # Arrow showing the sweep of IDM
    ax.annotate("", xy=(6, 111), xytext=(6, 116),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.5))
    _label(ax, 3.5, 108, "Цена пробивает IDM, забирает\nстоп-лоссы, затем продолжает рост", color=TEXT, fontsize=9)

    ax.set_xlim(-0.5, 11)
    ax.set_ylim(96, 128)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


def draw_amd() -> bytes:
    fig, ax = _base_fig("AMD — Accumulation · Manipulation · Distribution")

    # Three phases
    phases = {
        "Accumulation\n(сбор позиции)": (0, 3, 100, 108, GREEN, 0.08),
        "Manipulation\n(ложный пробой)": (3, 6, 108, 95, RED, 0.1),
        "Distribution\n(движение)": (6, 10, 95, 130, GREEN, 0.12),
    }
    for label, (x1, x2, y1, y2, color, alpha) in phases.items():
        ax.add_patch(mpatches.FancyBboxPatch(
            (x1, min(y1,y2)-2), x2-x1, abs(y2-y1)+4,
            boxstyle="square,pad=0", facecolor=color, alpha=alpha
        ))
        _label(ax, (x1+x2)/2, (y1+y2)/2+10, label, color=color, fontsize=9, ha="center")

    # Price path
    path_x = [0, 1, 2, 1.5, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 9, 10]
    path_y = [100, 104, 102, 106, 104, 108, 105, 100, 97, 95, 98, 95, 100, 110, 120, 130]
    ax.plot(path_x, path_y, color=TEXT, linewidth=2)

    _label(ax, 3.3, 92, "Judas Swing\n(ложный пробой вниз)", color=RED, fontsize=8)
    _label(ax, 7.0, 132, "Настоящее движение ▲", color=GREEN, fontsize=9)

    ax.set_xlim(-0.5, 11)
    ax.set_ylim(86, 142)
    ax.set_xticks([])
    ax.set_ylabel("Price", color=TEXT)
    return _save(fig)


# ── Upload to Supabase ─────────────────────────────────────────────────────────

CONCEPTS = [
    ("fvg",              "FVG",              draw_fvg,              "Beginner",     "Fair Value Gap — зона имбалланса"),
    ("order_block",      "Order Block",      draw_order_block,      "Beginner",     "Order Block — блок ордеров крупного игрока"),
    ("bos_choch",        "BOS",              draw_bos_choch,        "Beginner",     "BOS и CHoCH — пробои структуры и смена характера"),
    ("liquidity",        "Liquidity",        draw_liquidity,        "Intermediate", "Ликвидность — BSL и SSL зоны"),
    ("market_structure", "Market Structure", draw_market_structure, "Beginner",     "Рыночная структура — HH, HL, LH, LL"),
    ("premium_discount", "Premium/Discount", draw_premium_discount, "Intermediate", "Premium и Discount зоны — где покупать и продавать"),
    ("inducement",       "Inducement",       draw_inducement,       "Advanced",     "Inducement — ложная приманка перед реальным движением"),
    ("amd",              "AMD",              draw_amd,              "Intermediate", "AMD — Accumulation, Manipulation, Distribution"),
]


def upload_to_supabase(image_bytes: bytes, filename: str) -> str | None:
    """Upload image to Supabase Storage, return public URL."""
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        path = f"concepts/{filename}"
        client.storage.from_(BUCKET).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        return url
    except Exception as e:
        print(f"  ⚠️  Upload error: {e}")
        return None


def insert_lesson_image(topic: str, image_url: str, caption: str, level: str, concept_type: str):
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
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
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env")
        sys.exit(1)
    if SUPABASE_SERVICE_KEY == os.getenv("SUPABASE_ANON_KEY"):
        print("⚠️  WARNING: Using anon key — uploads will likely 403.")
        print("   Add SUPABASE_SERVICE_ROLE_KEY to .env (Supabase → Settings → API)")
        print()

    print(f"🎨 Generating {len(CONCEPTS)} educational diagrams...\n")

    for concept_type, topic, draw_fn, level, caption in CONCEPTS:
        print(f"  📐 {topic}...", end=" ", flush=True)
        try:
            image_bytes = draw_fn()
            filename    = f"{concept_type}.png"
            url         = upload_to_supabase(image_bytes, filename)
            if url:
                insert_lesson_image(topic, url, caption, level, concept_type)
                print(f"✅  → {url.split('/')[-1]}")
            else:
                print("❌ upload failed")
        except Exception as e:
            print(f"❌ {e}")

    print(f"\n✅ Done! {len(CONCEPTS)} diagrams uploaded to Supabase Storage.")
    print(f"   Bucket: {BUCKET}")
    print(f"   Table:  lesson_images")
    print(f"\n   Bot will now send images automatically with /lesson and /example commands.")


if __name__ == "__main__":
    main()
