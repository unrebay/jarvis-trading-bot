"""
Chart Annotator Module - Specialized chart analysis and annotation

Handles:
- Chart image analysis (patterns, levels, structures)
- Geometric annotation generation
- ICT pattern detection (Judas Swings, BOS, etc.)
- Key level identification and strength assessment
- Confluence analysis
- JSON annotation output
"""

import json
import base64
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from io import BytesIO

from PIL import Image

from .claude_client import ClaudeClient


@dataclass
class KeyLevel:
    """Key support/resistance level"""
    level: float
    type: str  # "support" or "resistance"
    strength: str  # "strong", "medium", "weak"
    test_count: int = 0
    factors: List[str] = None
    confidence: float = 0.8


@dataclass
class DetectedPattern:
    """Detected trading pattern"""
    pattern_name: str
    pattern_id: str
    confidence: float
    description: str
    location: Dict[str, Any]  # start candle, end candle, price levels
    entry_setup: Optional[Dict[str, Any]] = None
    significance: str = "medium"  # high, medium, low


@dataclass
class GeometricAnnotation:
    """Geometric annotation on chart"""
    id: str
    type: str  # point, rectangle, line, arrow, circle
    coordinates: List[List[float]]
    label: str
    color: str
    description: str = ""


class ChartAnnotator:
    """
    Specialized chart analysis and annotation

    Workflow:
    1. Receive chart image and context
    2. Extract chart info (instrument, timeframe, price range)
    3. Detect patterns (Judas Swing, BOS, structure)
    4. Identify key levels (support, resistance, liquidity)
    5. Analyze confluence (multiple reasons at same level)
    6. Generate geometric annotations
    7. Output structured annotation JSON
    """

    def __init__(self, claude_client: ClaudeClient):
        """
        Initialize chart annotator

        Args:
            claude_client: ClaudeClient instance
        """
        self.claude = claude_client

    def analyze_chart(
        self,
        image_data: bytes,
        context: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Analyze chart and generate annotations

        Args:
            image_data: Chart image bytes
            context: Context (instrument, timeframe, etc)

        Returns:
            Dict with patterns, levels, and annotations
        """
        context = context or {}

        # Get chart info
        chart_info = self._extract_chart_info(context)

        # Analyze with vision
        analysis = self._analyze_patterns_and_levels(image_data, chart_info)
        if not analysis.get("success"):
            return analysis

        patterns = analysis["patterns"]
        levels = analysis["levels"]

        # Generate geometric annotations
        annotations = self._generate_annotations(patterns, levels, chart_info)

        # Analyze confluence
        confluence = self._analyze_confluence(levels)

        return {
            "success": True,
            "chart_info": chart_info,
            "patterns": patterns,
            "key_levels": levels,
            "annotations": annotations,
            "confluence": confluence,
            "annotation_json": self._build_annotation_json(
                chart_info, patterns, levels, annotations, confluence
            )
        }

    def _extract_chart_info(self, context: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract chart metadata from context

        Args:
            context: Context dict

        Returns:
            Chart info
        """
        return {
            "instrument": context.get("instrument", "Unknown"),
            "timeframe": context.get("timeframe", "Unknown"),
            "date_range": context.get("date_range", "Unknown"),
            "price_range": context.get("price_range", [0, 0]),
            "session": context.get("session", "Unknown")
        }

    def _analyze_patterns_and_levels(
        self,
        image_data: bytes,
        chart_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze chart for patterns and levels

        Args:
            image_data: Chart image bytes
            chart_info: Chart metadata

        Returns:
            Dict with patterns and levels
        """
        try:
            # Encode image
            image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

            # Build prompt
            prompt = self._build_analysis_prompt(chart_info)

            # Call Claude
            response = self.claude.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse response
            response_text = response.content[0].text

            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response_text[json_start:json_end])
                else:
                    data = {}
            except json.JSONDecodeError:
                data = {}

            # Parse patterns
            patterns = []
            for p in data.get("patterns_detected", []):
                patterns.append(DetectedPattern(
                    pattern_name=p.get("pattern_name", "Unknown"),
                    pattern_id=p.get("pattern_id", "unknown"),
                    confidence=p.get("confidence", 0.0),
                    description=p.get("description", ""),
                    location=p.get("location", {}),
                    entry_setup=p.get("entry_setup"),
                    significance=p.get("significance", "medium")
                ))

            # Parse levels
            levels = []
            for level_data in data.get("key_levels", []):
                levels.append(KeyLevel(
                    level=level_data.get("level", 0.0),
                    type=level_data.get("type", "unknown"),
                    strength=level_data.get("strength", "medium"),
                    test_count=level_data.get("test_count", 0),
                    factors=level_data.get("factors", []),
                    confidence=level_data.get("confidence", 0.7)
                ))

            return {
                "success": True,
                "patterns": patterns,
                "levels": levels,
                "raw_response": response_text
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Pattern/level analysis failed: {str(e)}"
            }

    def _build_analysis_prompt(self, chart_info: Dict[str, Any]) -> str:
        """
        Build analysis prompt for Claude

        Args:
            chart_info: Chart metadata

        Returns:
            Prompt text
        """
        return f"""Analyze this trading chart in detail. Return structured JSON with:

Chart Context:
- Instrument: {chart_info.get('instrument')}
- Timeframe: {chart_info.get('timeframe')}
- Price Range: {chart_info.get('price_range')}

Look for these ICT patterns:
1. Judas Swing (liquidity sweep + reversal)
2. Break of Structure (strong directional break)
3. Market Structure (HH/HL or LL/LH)
4. Liquidity Grabs
5. Volume Confirmation

Return JSON:
{{
  "patterns_detected": [
    {{
      "pattern_name": "Judas Swing",
      "pattern_id": "pattern_judas_swing",
      "confidence": 0.92,
      "description": "Clear Judas swing with liquidity grab below support",
      "location": {{
        "start_candle": 10,
        "end_candle": 22,
        "swing_low": 1.0825,
        "reversal_high": 1.0950
      }},
      "significance": "high",
      "entry_setup": {{
        "trigger": "Retest of broken support at 1.0850",
        "risk_level": 1.0825,
        "target": 1.1050,
        "risk_reward": 3.0
      }}
    }}
  ],
  "key_levels": [
    {{
      "level": 1.0850,
      "type": "support",
      "strength": "strong",
      "test_count": 3,
      "factors": ["multiple_tests", "volume_confirmation", "previous_support"],
      "confidence": 0.95,
      "description": "Strong support held 3x with volume"
    }}
  ]
}}"""

    def _generate_annotations(
        self,
        patterns: List[DetectedPattern],
        levels: List[KeyLevel],
        chart_info: Dict[str, Any]
    ) -> List[GeometricAnnotation]:
        """
        Generate geometric annotations

        Args:
            patterns: Detected patterns
            levels: Key levels
            chart_info: Chart metadata

        Returns:
            List of annotations
        """
        annotations = []
        ann_id = 0

        # Add level annotations
        for level in levels:
            color = "#FF0000" if level.type == "resistance" else "#00FF00"
            ann_id += 1
            annotations.append(GeometricAnnotation(
                id=f"ann_{ann_id}",
                type="horizontal_line",
                coordinates=[[0, level.level], [1000, level.level]],
                label=f"{level.type.title()} {level.level}",
                color=color,
                description=f"{level.strength.title()} {level.type}, tested {level.test_count}x"
            ))

        # Add pattern annotations
        for pattern in patterns:
            if pattern.pattern_id == "pattern_judas_swing":
                ann_id += 1
                # Mark the liquidity grab
                annotations.append(GeometricAnnotation(
                    id=f"ann_{ann_id}",
                    type="rectangle",
                    coordinates=[
                        [pattern.location.get("start_candle", 0), pattern.location.get("swing_low", 0)],
                        [pattern.location.get("end_candle", 0), pattern.location.get("swing_low", 0)]
                    ],
                    label="Judas Swing",
                    color="#FF00FF",
                    description=f"Pattern confidence: {pattern.confidence:.0%}"
                ))

        return annotations

    def _analyze_confluence(self, levels: List[KeyLevel]) -> Dict[str, Any]:
        """
        Analyze confluence at key levels

        Args:
            levels: Key levels

        Returns:
            Confluence analysis
        """
        confluence_zones = []

        for level in levels:
            if level.strength == "strong":
                confluence_zones.append({
                    "level": level.level,
                    "type": level.type,
                    "strength": level.strength,
                    "factors": level.factors,
                    "confluence_score": len(level.factors or []) / 5 * 100,
                    "trading_probability": 0.80 + (len(level.factors or []) * 0.05)
                })

        return {
            "strong_confluence_zones": confluence_zones,
            "best_level": max(
                confluence_zones,
                key=lambda x: x["trading_probability"]
            ) if confluence_zones else None
        }

    def _build_annotation_json(
        self,
        chart_info: Dict[str, Any],
        patterns: List[DetectedPattern],
        levels: List[KeyLevel],
        annotations: List[GeometricAnnotation],
        confluence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build final annotation JSON structure

        Args:
            chart_info: Chart metadata
            patterns: Detected patterns
            levels: Key levels
            annotations: Geometric annotations
            confluence: Confluence analysis

        Returns:
            Complete annotation JSON
        """
        return {
            "image_id": "image_unknown",
            "chart_info": chart_info,
            "patterns_detected": [
                {
                    "pattern_name": p.pattern_name,
                    "pattern_id": p.pattern_id,
                    "confidence": p.confidence,
                    "description": p.description,
                    "location": p.location,
                    "significance": p.significance,
                    "entry_setup": p.entry_setup
                }
                for p in patterns
            ],
            "key_levels": [
                {
                    "level": l.level,
                    "type": l.type,
                    "strength": l.strength,
                    "test_count": l.test_count,
                    "factors": l.factors or [],
                    "confidence": l.confidence
                }
                for l in levels
            ],
            "geometric_annotations": [
                {
                    "id": a.id,
                    "type": a.type,
                    "coordinates": a.coordinates,
                    "label": a.label,
                    "color": a.color,
                    "description": a.description
                }
                for a in annotations
            ],
            "confluence": confluence,
            "annotations_summary": {
                "total_patterns": len(patterns),
                "total_levels": len(levels),
                "total_annotations": len(annotations),
                "analysis_completeness": "high" if len(patterns) + len(levels) > 3 else "medium",
                "generated_at": datetime.now().isoformat()
            }
        }
