"""
Unit tests — ChartAnnotator (parsing helpers, no API calls)
Run: python -m pytest tests/unit/test_chart_annotator.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest
from unittest.mock import MagicMock


def make_annotator():
    from src.bot.chart_annotator import ChartAnnotator
    claude = MagicMock()
    return ChartAnnotator(claude)


# ── Model version ─────────────────────────────────────────────────────────────

def test_uses_sonnet_not_haiku():
    from src.bot.chart_annotator import ChartAnnotator
    assert "sonnet" in ChartAnnotator.VISION_MODEL.lower(), \
        "ChartAnnotator should use Sonnet for production quality"

def test_max_tokens_at_least_4096():
    """Sonnet upgrade should have increased max_tokens."""
    import inspect
    from src.bot.chart_annotator import ChartAnnotator
    src = inspect.getsource(ChartAnnotator._call_claude_vision)
    assert "4096" in src or "4000" in src, "max_tokens should be >= 4096 for Sonnet"


# ── _extract_json ─────────────────────────────────────────────────────────────

def test_extract_json_clean():
    from src.bot.chart_annotator import ChartAnnotator
    text = '{"market_bias": "bullish", "patterns_detected": []}'
    result = ChartAnnotator._extract_json(text)
    assert result == {"market_bias": "bullish", "patterns_detected": []}

def test_extract_json_with_preamble():
    from src.bot.chart_annotator import ChartAnnotator
    text = 'Sure! Here is my analysis: {"market_bias": "bearish"} done.'
    result = ChartAnnotator._extract_json(text)
    assert result["market_bias"] == "bearish"

def test_extract_json_invalid_returns_empty():
    from src.bot.chart_annotator import ChartAnnotator
    result = ChartAnnotator._extract_json("no json here at all")
    assert result == {}

def test_extract_json_nested():
    from src.bot.chart_annotator import ChartAnnotator
    data = {"patterns_detected": [{"pattern_name": "FVG", "confidence": 0.9}]}
    result = ChartAnnotator._extract_json(json.dumps(data))
    assert result["patterns_detected"][0]["pattern_name"] == "FVG"


# ── _parse_patterns ───────────────────────────────────────────────────────────

def test_parse_patterns_valid():
    from src.bot.chart_annotator import ChartAnnotator
    raw = [{"pattern_name": "FVG", "pattern_id": "fvg_1",
            "confidence": 0.85, "description": "Bullish FVG",
            "significance": "high"}]
    patterns = ChartAnnotator._parse_patterns(raw)
    assert len(patterns) == 1
    assert patterns[0].pattern_name == "FVG"
    assert patterns[0].confidence == 0.85

def test_parse_patterns_skips_missing_name():
    from src.bot.chart_annotator import ChartAnnotator
    raw = [{"confidence": 0.5}]  # no pattern_name
    patterns = ChartAnnotator._parse_patterns(raw)
    assert len(patterns) == 0

def test_parse_patterns_empty_list():
    from src.bot.chart_annotator import ChartAnnotator
    assert ChartAnnotator._parse_patterns([]) == []


# ── _parse_levels ─────────────────────────────────────────────────────────────

def test_parse_levels_valid():
    from src.bot.chart_annotator import ChartAnnotator
    raw = [{"level": 2050.5, "type": "support", "strength": "strong",
            "test_count": 3, "factors": ["fvg_overlap"], "confidence": 0.9}]
    levels = ChartAnnotator._parse_levels(raw)
    assert len(levels) == 1
    assert levels[0].level == 2050.5
    assert levels[0].type == "support"

def test_parse_levels_empty():
    from src.bot.chart_annotator import ChartAnnotator
    assert ChartAnnotator._parse_levels([]) == []


# ── _build_analysis_text ──────────────────────────────────────────────────────

def test_build_analysis_text_bullish():
    from src.bot.chart_annotator import ChartAnnotator
    data = {"market_bias": "bullish", "analysis_summary": "Price targets 2100."}
    text = ChartAnnotator._build_analysis_text(data, [], [])
    assert "Бычий" in text or "bullish" in text.lower()

def test_build_analysis_text_bearish():
    from src.bot.chart_annotator import ChartAnnotator
    data = {"market_bias": "bearish", "analysis_summary": "Drop expected."}
    text = ChartAnnotator._build_analysis_text(data, [], [])
    assert "Медвежий" in text or "bearish" in text.lower()

def test_build_analysis_text_no_special_chars():
    """Result must be Telegram-safe (no unescaped markdown)."""
    from src.bot.chart_annotator import ChartAnnotator
    data = {"market_bias": "bullish", "analysis_summary": "Test *with* _markdown_."}
    text = ChartAnnotator._build_analysis_text(data, [], [])
    assert "*" not in text
    assert "_" not in text


# ── Cache ─────────────────────────────────────────────────────────────────────

def test_cache_evicts_at_max():
    from src.bot.chart_annotator import ChartAnnotator
    ChartAnnotator._analysis_cache.clear()
    for i in range(ChartAnnotator._CACHE_MAX + 5):
        ChartAnnotator._analysis_cache[f"key_{i}"] = {"success": True}
    # Manually trigger eviction (next analyze_chart call would evict)
    while len(ChartAnnotator._analysis_cache) >= ChartAnnotator._CACHE_MAX:
        oldest = next(iter(ChartAnnotator._analysis_cache))
        del ChartAnnotator._analysis_cache[oldest]
    assert len(ChartAnnotator._analysis_cache) < ChartAnnotator._CACHE_MAX
