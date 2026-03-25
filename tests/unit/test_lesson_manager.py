"""
Unit tests — LessonManager
Run: python -m pytest tests/unit/test_lesson_manager.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest
from unittest.mock import MagicMock, patch


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_lesson_manager():
    from src.bot.lesson_manager import LessonManager, CURRICULUM, ALL_TOPICS
    claude = MagicMock()
    rag    = MagicMock()
    rag.search.return_value = []
    return LessonManager(claude, rag), CURRICULUM, ALL_TOPICS


# ── CURRICULUM structure ──────────────────────────────────────────────────────

def test_curriculum_has_all_levels():
    _, CURRICULUM, _ = make_lesson_manager()
    assert set(CURRICULUM.keys()) == {"Beginner", "Intermediate", "Advanced", "Professional"}

def test_curriculum_beginner_not_empty():
    _, CURRICULUM, _ = make_lesson_manager()
    assert len(CURRICULUM["Beginner"]) >= 5

def test_curriculum_intermediate_has_fvg():
    _, CURRICULUM, _ = make_lesson_manager()
    assert "FVG" in CURRICULUM["Intermediate"]

def test_curriculum_advanced_has_gold():
    _, CURRICULUM, _ = make_lesson_manager()
    assert "Gold Mechanics" in CURRICULUM["Advanced"]

def test_curriculum_professional_has_backtest():
    _, CURRICULUM, _ = make_lesson_manager()
    assert "Backtest" in CURRICULUM["Professional"]

def test_all_topics_flat_list_not_empty():
    _, _, ALL_TOPICS = make_lesson_manager()
    assert len(ALL_TOPICS) >= 20

def test_no_duplicate_topics():
    _, _, ALL_TOPICS = make_lesson_manager()
    assert len(ALL_TOPICS) == len(set(ALL_TOPICS)), "Duplicate topics found in curriculum"


# ── get_curriculum_text ───────────────────────────────────────────────────────

def test_get_curriculum_text_returns_string():
    lm, _, _ = make_lesson_manager()
    text = lm.get_curriculum_text("Intermediate")
    assert isinstance(text, str)
    assert len(text) > 0

def test_get_curriculum_text_unknown_level_fallback():
    lm, _, _ = make_lesson_manager()
    text = lm.get_curriculum_text("Unknown")
    assert isinstance(text, str)


# ── get_topics_list ───────────────────────────────────────────────────────────

def test_get_topics_list_returns_string():
    lm, _, _ = make_lesson_manager()
    result = lm.get_topics_list()
    assert isinstance(result, str)
    assert "FVG" in result
    assert "Beginner" in result


# ── get_next_topic ────────────────────────────────────────────────────────────

def test_get_next_topic_returns_first_unknown():
    lm, CURRICULUM, _ = make_lesson_manager()
    known = CURRICULUM["Beginner"][:2]
    next_t = lm.get_next_topic("Beginner", known)
    assert next_t not in known

def test_get_next_topic_all_known_returns_none_or_str():
    lm, CURRICULUM, _ = make_lesson_manager()
    all_known = CURRICULUM["Beginner"]
    result = lm.get_next_topic("Beginner", all_known)
    # Either None (all done) or moves to next level
    assert result is None or isinstance(result, str)


# ── format_progress ───────────────────────────────────────────────────────────

def test_format_progress_empty_memory():
    lm, _, _ = make_lesson_manager()
    memory = {
        "learning": {"level": "Beginner", "topics_known": [], "topics_struggling": []},
        "conversations": {"total_messages": 0},
    }
    result = lm.format_progress(memory)
    assert isinstance(result, str)
    assert len(result) > 0

def test_format_progress_with_data():
    lm, _, _ = make_lesson_manager()
    memory = {
        "learning": {
            "level": "Intermediate",
            "topics_known": ["FVG", "Order Block", "BOS"],
            "topics_struggling": ["Multi-Timeframe Analysis"],
        },
        "conversations": {"total_messages": 42},
    }
    result = lm.format_progress(memory)
    assert "Intermediate" in result or "42" in result
