"""
Unit tests — UserMemory (no Supabase calls)
Run: python -m pytest tests/unit/test_user_memory.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import copy
import pytest
from unittest.mock import MagicMock


def make_memory():
    from src.bot.user_memory import UserMemory, DEFAULT_MEMORY
    supabase = MagicMock()
    supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    um = UserMemory(supabase)
    return um, DEFAULT_MEMORY


# ── DEFAULT_MEMORY structure ──────────────────────────────────────────────────

def test_default_memory_has_required_keys():
    _, DEFAULT_MEMORY = make_memory()
    assert "profile" in DEFAULT_MEMORY
    assert "learning" in DEFAULT_MEMORY
    assert "conversations" in DEFAULT_MEMORY
    assert "personality" in DEFAULT_MEMORY

def test_default_learning_level_is_intermediate():
    _, DEFAULT_MEMORY = make_memory()
    assert DEFAULT_MEMORY["learning"]["level"] == "Intermediate"

def test_default_topics_known_is_list():
    _, DEFAULT_MEMORY = make_memory()
    assert isinstance(DEFAULT_MEMORY["learning"]["topics_known"], list)


# ── increment ─────────────────────────────────────────────────────────────────

def test_increment_increases_message_count():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    before = mem["conversations"].get("total_messages", 0)
    mem = um.increment(mem)
    assert mem["conversations"].get("total_messages", 0) == before + 1

def test_increment_returns_dict():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    result = um.increment(mem)
    assert isinstance(result, dict)


# ── should_update ─────────────────────────────────────────────────────────────

def test_should_update_false_at_1_message():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    mem["conversations"]["total_messages"] = 1
    assert um.should_update(mem) is False

def test_should_update_true_at_multiple_of_5():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    mem["conversations"]["total_messages"] = 5
    assert um.should_update(mem) is True

def test_should_update_true_at_10():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    mem["conversations"]["total_messages"] = 10
    assert um.should_update(mem) is True


# ── apply_update ──────────────────────────────────────────────────────────────

def test_apply_update_merges_profile_name():
    um, DEFAULT_MEMORY = make_memory()
    current = copy.deepcopy(DEFAULT_MEMORY)
    updated = {"profile": {"name": "Андрей"}}
    result = um.apply_update(current, updated)
    assert result["profile"]["name"] == "Андрей"

def test_apply_update_preserves_existing_keys():
    um, DEFAULT_MEMORY = make_memory()
    current = copy.deepcopy(DEFAULT_MEMORY)
    current["profile"]["name"] = "Existing"
    current["conversations"]["total_messages"] = 42
    updated = {"profile": {"name": "New"}}
    result = um.apply_update(current, updated)
    # total_messages should be preserved
    assert result["conversations"]["total_messages"] == 42


# ── format_as_context ─────────────────────────────────────────────────────────

def test_format_as_context_empty_memory_returns_none_or_str():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    result = um.format_as_context(mem)
    assert result is None or isinstance(result, str)

def test_format_as_context_with_name():
    um, DEFAULT_MEMORY = make_memory()
    mem = copy.deepcopy(DEFAULT_MEMORY)
    mem["profile"]["name"] = "Андрей"
    mem["learning"]["level"] = "Advanced"
    result = um.format_as_context(mem)
    if result:
        assert "Андрей" in result or "Advanced" in result


# ── load fallback ─────────────────────────────────────────────────────────────

def test_load_returns_default_when_no_data():
    um, DEFAULT_MEMORY = make_memory()
    result = um.load(999999)
    assert "profile" in result
    assert "learning" in result
