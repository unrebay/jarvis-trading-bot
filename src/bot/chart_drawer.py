"""
Chart Drawer Module — Visual annotation engine for trading charts

Draws ICT/SMC annotations directly on chart images using PIL:
  • FVG zones        — semi-transparent rectangles (bullish=green, bearish=red)
  • S/R levels       — dashed horizontal lines with price labels
  • BOS / CHoCH      — arrows + text markers
  • Order Blocks     — outlined rectangles with OB label
  • Liquidity sweeps — small triangles at swing highs/lows
  • Overall summary  — legend in the corner

Input: raw image bytes + drawing_instructions JSON from ChartAnnotator
Output: annotated image bytes (JPEG)
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


# ─── Color Palette ────────────────────────────────────────────────────────────

COLORS = {
    # FVG
    "fvg_bull":       (0,   200,  80,  55),   # transparent green
    "fvg_bear":       (220,  60,  60,  55),   # transparent red
    "fvg_outline_bull": (0,  200,  80, 200),
    "fvg_outline_bear": (220, 60,  60, 200),

    # S/R levels
    "support":        (0,   210,  80, 220),   # bright green
    "resistance":     (220,  80,  80, 220),   # bright red
    "key_level":      (255, 200,   0, 220),   # yellow

    # BOS / CHoCH
    "bos":            (100, 160, 255, 240),   # light blue
    "choch":          (255, 140,  60, 240),   # orange

    # Order Blocks
    "ob_bull":        (0,   180, 100,  45),
    "ob_bear":        (200,  60,  60,  45),
    "ob_outline_bull": (0,  180, 100, 200),
    "ob_outline_bear": (200, 60,  60, 200),

    # Liquidity
    "liquidity":      (200, 100, 255, 220),   # purple

    # Text
    "label_bg":       (10,  10,  25, 180),
    "label_text":     (255, 255, 255, 255),

    # Legend
    "legend_bg":      (15,  15,  30, 195),
}


def _rgba(key: str) -> Tuple[int, int, int, int]:
    return COLORS.get(key, (255, 255, 255, 200))


# ─── Font loader (graceful fallback) ─────────────────────────────────────────

def _load_font(size: int = 12) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a small monospace font, fall back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


# ─── ChartDrawer ──────────────────────────────────────────────────────────────

class ChartDrawer:
    """
    Draws ICT/SMC annotations on a chart image.

    Usage::

        drawer = ChartDrawer(image_bytes)
        annotated = drawer.draw(drawing_instructions)
        # annotated is JPEG bytes

    Drawing instructions format (from ChartAnnotator)::

        {
          "fvg_zones": [
            {"x1_pct": 0.4, "x2_pct": 0.6, "y1_pct": 0.3, "y2_pct": 0.4,
             "type": "bullish", "label": "FVG"}
          ],
          "sr_levels": [
            {"y_pct": 0.45, "label": "S 2050.0", "level_type": "support"}
          ],
          "bos_markers": [
            {"x_pct": 0.55, "y_pct": 0.42, "direction": "up", "label": "BOS"}
          ],
          "order_blocks": [
            {"x1_pct": 0.3, "x2_pct": 0.5, "y1_pct": 0.5, "y2_pct": 0.6,
             "type": "bullish", "label": "OB"}
          ],
          "liquidity_sweeps": [
            {"x_pct": 0.7, "y_pct": 0.2, "label": "SSL grabbed"}
          ],
          "summary": "Bullish BOS detected. FVG formed. Potential long setup."
        }
    """

    FONT_SMALL  = 11
    FONT_MEDIUM = 13
    FONT_LARGE  = 15
    ARROW_SIZE  = 14   # px for arrow triangles
    LINE_WIDTH  = 2

    def __init__(self, image_bytes: bytes):
        """Load image, create RGBA overlay canvas."""
        self._orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        self._w, self._h = self._orig.size
        self._overlay = Image.new("RGBA", (self._w, self._h), (0, 0, 0, 0))
        self._draw = ImageDraw.Draw(self._overlay)
        self._font_s = _load_font(self.FONT_SMALL)
        self._font_m = _load_font(self.FONT_MEDIUM)
        self._font_l = _load_font(self.FONT_LARGE)

    # ─── Public API ───────────────────────────────────────────────────────────

    def draw(self, instructions: Dict[str, Any]) -> bytes:
        """
        Apply all drawing instructions and return annotated JPEG bytes.

        Args:
            instructions: Dict from ChartAnnotator with drawing primitives

        Returns:
            JPEG bytes of annotated image
        """
        # Draw in layer order (back to front)
        self._draw_fvg_zones(instructions.get("fvg_zones", []))
        self._draw_order_blocks(instructions.get("order_blocks", []))
        self._draw_sr_levels(instructions.get("sr_levels", []))
        self._draw_liquidity_sweeps(instructions.get("liquidity_sweeps", []))
        self._draw_bos_markers(instructions.get("bos_markers", []))

        # Merge overlay with original
        base_rgba = self._orig.convert("RGBA")
        merged = Image.alpha_composite(base_rgba, self._overlay)

        # Draw legend on top (uses regular RGB draw)
        result_rgb = merged.convert("RGB")
        self._draw_legend(result_rgb, instructions)

        # Return JPEG bytes
        out = io.BytesIO()
        result_rgb.save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue()

    # ─── Layer Drawers ────────────────────────────────────────────────────────

    def _draw_fvg_zones(self, zones: List[Dict]) -> None:
        """Draw Fair Value Gap rectangles."""
        for z in zones:
            x1, y1 = self._pct(z.get("x1_pct", 0), z.get("y1_pct", 0))
            x2, y2 = self._pct(z.get("x2_pct", 1), z.get("y2_pct", 0))
            zone_type = z.get("type", "bullish").lower()

            fill_key    = "fvg_bull" if zone_type == "bullish" else "fvg_bear"
            outline_key = "fvg_outline_bull" if zone_type == "bullish" else "fvg_outline_bear"

            self._draw.rectangle(
                [x1, min(y1, y2), x2, max(y1, y2)],
                fill=_rgba(fill_key),
                outline=_rgba(outline_key),
                width=1,
            )
            # Label
            label = z.get("label", "FVG")
            self._draw_label(x1 + 4, min(y1, y2) + 3, label, self._font_s)

    def _draw_order_blocks(self, blocks: List[Dict]) -> None:
        """Draw Order Block rectangles (outlined)."""
        for ob in blocks:
            x1, y1 = self._pct(ob.get("x1_pct", 0), ob.get("y1_pct", 0))
            x2, y2 = self._pct(ob.get("x2_pct", 1), ob.get("y2_pct", 0))
            ob_type = ob.get("type", "bullish").lower()

            fill_key    = "ob_bull" if ob_type == "bullish" else "ob_bear"
            outline_key = "ob_outline_bull" if ob_type == "bullish" else "ob_outline_bear"

            self._draw.rectangle(
                [x1, min(y1, y2), x2, max(y1, y2)],
                fill=_rgba(fill_key),
                outline=_rgba(outline_key),
                width=2,
            )
            label = ob.get("label", "OB")
            self._draw_label(x1 + 4, min(y1, y2) + 3, label, self._font_s)

    def _draw_sr_levels(self, levels: List[Dict]) -> None:
        """Draw horizontal dashed lines for Support/Resistance."""
        for lvl in levels:
            _, y = self._pct(0, lvl.get("y_pct", 0))
            level_type = lvl.get("level_type", "key_level").lower()
            color_key  = level_type if level_type in COLORS else "key_level"
            color      = _rgba(color_key)
            label      = lvl.get("label", "Level")

            # Dashed line across full width
            self._draw_dashed_hline(y, color, dash_len=12, gap=6)

            # Right-side label
            self._draw_label(self._w - 4, y - 8, label, self._font_s, align="right")

    def _draw_bos_markers(self, markers: List[Dict]) -> None:
        """Draw BOS / CHoCH arrows with labels."""
        for m in markers:
            x, y = self._pct(m.get("x_pct", 0.5), m.get("y_pct", 0.5))
            label     = m.get("label", "BOS")
            direction = m.get("direction", "up").lower()
            is_choch  = "choch" in label.lower() or "choc" in label.lower()
            color     = _rgba("choch" if is_choch else "bos")

            self._draw_arrow(x, y, direction, color)
            # Label below/above arrow
            offset = -(self.ARROW_SIZE + 14) if direction == "up" else (self.ARROW_SIZE + 4)
            self._draw_label(x, y + offset, label, self._font_m, center=True)

    def _draw_liquidity_sweeps(self, sweeps: List[Dict]) -> None:
        """Draw liquidity grab markers (small triangles)."""
        for s in sweeps:
            x, y  = self._pct(s.get("x_pct", 0.5), s.get("y_pct", 0.5))
            label = s.get("label", "Liq")
            color = _rgba("liquidity")

            # Small diamond marker
            size = 7
            self._draw.polygon(
                [(x, y - size), (x + size, y), (x, y + size), (x - size, y)],
                fill=color,
                outline=(200, 100, 255, 255),
            )
            self._draw_label(x + size + 3, y - 6, label, self._font_s)

    def _draw_legend(self, img_rgb: Image.Image, instructions: Dict) -> None:
        """Draw info legend in top-left corner."""
        draw = ImageDraw.Draw(img_rgb)

        # Collect legend items
        items: List[str] = []
        if instructions.get("fvg_zones"):
            items.append(f"  FVG: {len(instructions['fvg_zones'])} zone(s)")
        if instructions.get("sr_levels"):
            items.append(f"  S/R: {len(instructions['sr_levels'])} level(s)")
        if instructions.get("bos_markers"):
            items.append(f"  BOS/CHoCH: {len(instructions['bos_markers'])}")
        if instructions.get("order_blocks"):
            items.append(f"  OB: {len(instructions['order_blocks'])}")
        if instructions.get("liquidity_sweeps"):
            items.append(f"  Liq: {len(instructions['liquidity_sweeps'])}")

        # Summary text (wrap at 50 chars)
        summary = instructions.get("summary", "")
        if summary:
            words = summary.split()
            lines: List[str] = []
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 <= 50:
                    cur = (cur + " " + w).strip()
                else:
                    if cur:
                        lines.append("  " + cur)
                    cur = w
            if cur:
                lines.append("  " + cur)
            items += lines

        if not items:
            return

        font = self._font_s
        pad  = 6
        line_h = self.FONT_SMALL + 4
        box_w  = max(len(i) for i in items) * 7 + pad * 2
        box_h  = len(items) * line_h + pad * 2 + 14  # +14 for title

        x0, y0 = 10, 10
        x1, y1 = x0 + box_w, y0 + box_h

        # Background
        draw.rectangle([x0, y0, x1, y1], fill=(15, 15, 30, 195))
        draw.rectangle([x0, y0, x1, y1], outline=(80, 80, 120), width=1)

        # Title
        draw.text((x0 + pad, y0 + pad), "⬛ JARVIS Analysis", font=font,
                  fill=(180, 180, 255))

        # Items
        for i, line in enumerate(items):
            draw.text(
                (x0 + pad, y0 + pad + 14 + i * line_h),
                line, font=font, fill=(220, 220, 240),
            )

    # ─── Drawing Primitives ───────────────────────────────────────────────────

    def _pct(self, x_pct: float, y_pct: float) -> Tuple[int, int]:
        """Convert normalized (0-1) coordinates to pixel coordinates."""
        x = max(0, min(self._w - 1, int(x_pct * self._w)))
        y = max(0, min(self._h - 1, int(y_pct * self._h)))
        return x, y

    def _draw_dashed_hline(
        self,
        y: int,
        color: Tuple[int, int, int, int],
        dash_len: int = 12,
        gap: int = 6,
    ) -> None:
        """Draw a horizontal dashed line at pixel y."""
        x = 0
        on = True
        while x < self._w:
            end = min(x + (dash_len if on else gap), self._w)
            if on:
                self._draw.line([(x, y), (end, y)], fill=color, width=self.LINE_WIDTH)
            x = end
            on = not on

    def _draw_arrow(
        self,
        x: int,
        y: int,
        direction: str,
        color: Tuple[int, int, int, int],
    ) -> None:
        """Draw an upward or downward filled triangle arrow."""
        s = self.ARROW_SIZE
        if direction == "up":
            pts = [(x, y - s), (x - s, y + s // 2), (x + s, y + s // 2)]
        else:
            pts = [(x, y + s), (x - s, y - s // 2), (x + s, y - s // 2)]
        self._draw.polygon(pts, fill=color, outline=(255, 255, 255, 200))

    def _draw_label(
        self,
        x: int,
        y: int,
        text: str,
        font,
        align: str = "left",
        center: bool = False,
    ) -> None:
        """Draw a pill-shaped label with semi-transparent background."""
        if not text:
            return

        try:
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = len(text) * 7, 12

        pad = 3
        if center:
            x = x - tw // 2
        if align == "right":
            x = x - tw - pad * 2

        rx0 = x - pad
        ry0 = y - pad
        rx1 = x + tw + pad
        ry1 = y + th + pad

        self._draw.rounded_rectangle(
            [rx0, ry0, rx1, ry1],
            radius=3,
            fill=_rgba("label_bg"),
        )
        self._draw.text((x, y), text, font=font, fill=_rgba("label_text"))
