"""
Chart Annotator Module — ICT/SMC chart analysis + drawing instructions

Workflow:
1. Receive chart image bytes + optional context
2. Send to Claude Vision with an ICT/SMC-focused prompt
3. Parse JSON response:
   - patterns_detected  (Judas Swing, BOS, CHoCH, OB, FVG …)
   - key_levels         (support / resistance / order blocks)
   - drawing_instructions → passed to ChartDrawer for visual overlay
4. Return structured result dict

Changes v2 (iMac):
- Added drawing_instructions block (normalized 0-1 coordinates)
- FVG, OB, BOS/CHoCH, S/R, liquidity sweeps
- Improved system prompt (more ICT vocabulary)
- Cleaner response parsing with safer JSON extraction
- Media type auto-detect (JPEG / PNG)
"""

import json
import base64
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from .claude_client import ClaudeClient


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class KeyLevel:
    level: float
    type: str           # "support" | "resistance" | "order_block_bull" | "order_block_bear"
    strength: str       # "strong" | "medium" | "weak"
    test_count: int = 0
    factors: List[str] = None
    confidence: float = 0.8


@dataclass
class DetectedPattern:
    pattern_name: str
    pattern_id: str
    confidence: float
    description: str
    location: Dict[str, Any]
    entry_setup: Optional[Dict[str, Any]] = None
    significance: str = "medium"   # "high" | "medium" | "low"


# ─── ChartAnnotator ──────────────────────────────────────────────────────────

class ChartAnnotator:
    """
    Analyze a trading chart image with Claude Vision.

    Returns both a structured analysis AND drawing instructions
    (normalized 0-1 coordinates) that ChartDrawer can render.
    """

    VISION_MODEL = "claude-opus-4-6"

    def __init__(self, claude_client: ClaudeClient):
        self.claude = claude_client

    # ─── Public ───────────────────────────────────────────────────────────────

    def analyze_chart(
        self,
        image_data: bytes,
        context: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze chart and return full result including drawing instructions.

        Args:
            image_data: raw image bytes (JPEG or PNG)
            context:    optional dict with keys instrument, timeframe, etc.

        Returns:
            {
              "success": bool,
              "chart_info": {...},
              "patterns": [DetectedPattern, ...],
              "key_levels": [KeyLevel, ...],
              "drawing_instructions": {...},   ← for ChartDrawer
              "analysis_text": "...",          ← narrative for Telegram reply
              "error": "..." (only on failure)
            }
        """
        context = context or {}
        chart_info = self._extract_chart_info(context)

        result = self._call_claude_vision(image_data, chart_info)
        if not result.get("success"):
            return result

        return {
            "success": True,
            "chart_info": chart_info,
            "patterns": result["patterns"],
            "key_levels": result["key_levels"],
            "drawing_instructions": result["drawing_instructions"],
            "analysis_text": result["analysis_text"],
            "raw_response": result.get("raw_response", ""),
        }

    # ─── Private ──────────────────────────────────────────────────────────────

    def _extract_chart_info(self, context: Dict[str, str]) -> Dict[str, Any]:
        return {
            "instrument": context.get("instrument", "Unknown"),
            "timeframe":  context.get("timeframe",  "Unknown"),
            "session":    context.get("session",    "Unknown"),
        }

    def _call_claude_vision(
        self,
        image_data: bytes,
        chart_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send image + prompt to Claude, parse structured JSON response."""
        try:
            # Detect media type
            try:
                img = Image.open(BytesIO(image_data))
                fmt = (img.format or "JPEG").upper()
                media_type = "image/png" if fmt == "PNG" else "image/jpeg"
            except Exception:
                media_type = "image/jpeg"

            image_b64 = base64.standard_b64encode(image_data).decode("utf-8")
            prompt    = self._build_prompt(chart_info)

            response = self.claude.client.messages.create(
                model=self.VISION_MODEL,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type":       "base64",
                                    "media_type": media_type,
                                    "data":       image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            raw = response.content[0].text
            data = self._extract_json(raw)

            patterns = self._parse_patterns(data.get("patterns_detected", []))
            levels   = self._parse_levels(data.get("key_levels", []))
            drawing  = data.get("drawing_instructions", {})
            analysis_text = self._build_analysis_text(data, patterns, levels)

            return {
                "success":              True,
                "patterns":             patterns,
                "key_levels":           levels,
                "drawing_instructions": drawing,
                "analysis_text":        analysis_text,
                "raw_response":         raw,
            }

        except Exception as exc:
            return {"success": False, "error": f"Vision analysis failed: {exc}"}

    # ─── Prompt Builder ───────────────────────────────────────────────────────

    def _build_prompt(self, chart_info: Dict[str, Any]) -> str:
        return f"""You are an expert ICT/SMC trading analyst. Analyze this chart image carefully.

Chart context:
- Instrument : {chart_info.get('instrument', 'Unknown')}
- Timeframe  : {chart_info.get('timeframe',  'Unknown')}
- Session    : {chart_info.get('session',    'Unknown')}

=== WHAT TO IDENTIFY ===

1. ICT / SMC PATTERNS
   • FVG (Fair Value Gaps) — imbalance zones between candles
   • Order Blocks (OB) — last up/down candle before strong move
   • BOS (Break of Structure) — higher high or lower low break
   • CHoCH (Change of Character) — first counter-trend BOS
   • Judas Swing — liquidity sweep before real move
   • Liquidity sweeps — stop-hunt above/below swing highs/lows

2. KEY LEVELS — strong S/R, POI zones, previous highs/lows

3. MARKET BIAS — overall trend direction and next likely move

=== OUTPUT FORMAT ===

Return ONLY valid JSON (no markdown, no extra text):

{{
  "patterns_detected": [
    {{
      "pattern_name": "FVG",
      "pattern_id": "fvg_1",
      "type": "bullish",
      "confidence": 0.88,
      "description": "Bullish FVG formed after strong up-move",
      "significance": "high",
      "entry_setup": {{
        "trigger": "Price retraces into FVG",
        "risk_level": 2045.0,
        "target": 2095.0,
        "risk_reward": 2.5
      }}
    }}
  ],
  "key_levels": [
    {{
      "level": 2050.0,
      "type": "support",
      "strength": "strong",
      "test_count": 3,
      "factors": ["multiple_tests", "order_block", "fvg_overlap"],
      "confidence": 0.92
    }}
  ],
  "market_bias": "bullish",
  "analysis_summary": "2-3 sentences describing the overall picture and trade idea.",
  "drawing_instructions": {{
    "fvg_zones": [
      {{
        "x1_pct": 0.55, "x2_pct": 0.75,
        "y1_pct": 0.38, "y2_pct": 0.45,
        "type": "bullish",
        "label": "FVG"
      }}
    ],
    "order_blocks": [
      {{
        "x1_pct": 0.40, "x2_pct": 0.55,
        "y1_pct": 0.50, "y2_pct": 0.58,
        "type": "bullish",
        "label": "OB"
      }}
    ],
    "sr_levels": [
      {{
        "y_pct": 0.45,
        "label": "S 2050.0",
        "level_type": "support"
      }}
    ],
    "bos_markers": [
      {{
        "x_pct": 0.62, "y_pct": 0.35,
        "direction": "up",
        "label": "BOS"
      }}
    ],
    "liquidity_sweeps": [
      {{
        "x_pct": 0.48, "y_pct": 0.22,
        "label": "BSL grabbed"
      }}
    ],
    "summary": "Bullish structure with FVG at 2050. OB confluence. Expect continuation."
  }}
}}

COORDINATE RULES:
- All _pct values are 0.0 (left/top) to 1.0 (right/bottom) of the CHART AREA (not the whole image)
- y_pct 0.0 = TOP of chart (highest price), y_pct 1.0 = BOTTOM (lowest price)
- x_pct 0.0 = leftmost candle, x_pct 1.0 = rightmost candle
- For rectangles: y1_pct is the UPPER edge (higher price), y2_pct is LOWER edge (lower price)
- Include ONLY elements you can actually see in the chart
- If a section has no elements, use an empty array []
"""

    # ─── JSON Parsing Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract first complete JSON object from Claude response text."""
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        return json.loads(text[start: i + 1])
                    except json.JSONDecodeError:
                        pass
        return {}

    @staticmethod
    def _parse_patterns(raw: List[Dict]) -> List[DetectedPattern]:
        patterns = []
        for p in raw:
            if not p.get("pattern_name"):
                continue
            patterns.append(DetectedPattern(
                pattern_name = p.get("pattern_name", "Unknown"),
                pattern_id   = p.get("pattern_id",   "unknown"),
                confidence   = float(p.get("confidence", 0.0)),
                description  = p.get("description",  ""),
                location     = p.get("location",     {}),
                entry_setup  = p.get("entry_setup"),
                significance = p.get("significance", "medium"),
            ))
        return patterns

    @staticmethod
    def _parse_levels(raw: List[Dict]) -> List[KeyLevel]:
        levels = []
        for l in raw:
            levels.append(KeyLevel(
                level      = float(l.get("level", 0.0)),
                type       = l.get("type",       "unknown"),
                strength   = l.get("strength",   "medium"),
                test_count = int(l.get("test_count", 0)),
                factors    = l.get("factors",    []),
                confidence = float(l.get("confidence", 0.7)),
            ))
        return levels

    # ─── Analysis Text Builder ────────────────────────────────────────────────

    @staticmethod
    def _build_analysis_text(
        data:     Dict[str, Any],
        patterns: List[DetectedPattern],
        levels:   List[KeyLevel],
    ) -> str:
        """Build a concise Telegram-ready analysis narrative."""
        bias    = data.get("market_bias", "").capitalize()
        summary = data.get("analysis_summary", "")

        lines = []

        if bias:
            emoji = "🟢" if bias.lower() == "bullish" else ("🔴" if bias.lower() == "bearish" else "⚪")
            lines.append(f"{emoji} *Bias:* {bias}")

        if patterns:
            lines.append("\n*Detected Patterns:*")
            for p in patterns[:5]:
                conf_bar = "▓" * int(p.confidence * 5) + "░" * (5 - int(p.confidence * 5))
                lines.append(
                    f"  • *{p.pattern_name}* [{conf_bar}] {int(p.confidence*100)}%"
                )
                if p.description:
                    lines.append(f"    _{p.description}_")
                if p.entry_setup:
                    es = p.entry_setup
                    if es.get("risk_reward"):
                        lines.append(f"    RR: {es['risk_reward']:.1f}x")

        if levels:
            strong = [l for l in levels if l.strength == "strong"]
            if strong:
                lines.append("\n*Key Levels:*")
                for l in strong[:4]:
                    emoji = "🟩" if l.type == "support" else "🟥"
                    lines.append(f"  {emoji} {l.type.upper()}: {l.level}")

        if summary:
            lines.append(f"\n💡 _{summary}_")

        return "\n".join(lines) if lines else "Analysis complete — see annotated chart."
