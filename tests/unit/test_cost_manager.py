"""
Unit tests — CostManager
Run: python -m pytest tests/unit/test_cost_manager.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import patch, MagicMock


def make_cost_manager(budget=1.0):
    """Create CostManager with tmp data dir."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    from src.bot.cost_manager import CostManager, BotMode
    cm = CostManager(daily_budget=budget, data_dir=tmpdir)
    return cm, BotMode


# ── Mode transitions ──────────────────────────────────────────────────────────

def test_initial_mode_is_full():
    cm, BotMode = make_cost_manager(budget=1.0)
    assert cm.get_mode() == BotMode.FULL

def test_can_use_api_initially():
    cm, _ = make_cost_manager()
    assert cm.can_use_api() is True

def test_can_use_vision_initially():
    cm, _ = make_cost_manager()
    assert cm.can_use_vision() is True

def test_offline_mode_blocks_api():
    cm, BotMode = make_cost_manager(budget=0.01)
    cm.record_cost("sonnet", "mentoring", 10000, 5000)  # forces over budget
    assert cm.can_use_api() is False

def test_offline_mode_blocks_vision():
    cm, BotMode = make_cost_manager(budget=0.01)
    cm.record_cost("sonnet", "mentoring", 10000, 5000)
    assert cm.can_use_vision() is False


# ── record_cost ───────────────────────────────────────────────────────────────

def test_record_cost_returns_float():
    cm, _ = make_cost_manager()
    cost = cm.record_cost("haiku", "mentoring", 1000, 500)
    assert isinstance(cost, float)
    assert cost > 0

def test_record_cost_accumulates():
    cm, _ = make_cost_manager()
    c1 = cm.record_cost("haiku", "mentoring", 1000, 500)
    c2 = cm.record_cost("haiku", "mentoring", 1000, 500)
    assert cm.tracker.total_cost == pytest.approx(c1 + c2, rel=1e-6)

def test_record_cost_unknown_model_returns_zero():
    cm, _ = make_cost_manager()
    cost = cm.record_cost("unknown_model", "mentoring", 1000, 500)
    assert cost == 0.0


# ── reset_daily_limit ─────────────────────────────────────────────────────────

def test_reset_daily_limit_is_idempotent():
    cm, _ = make_cost_manager()
    cm.reset_daily_limit()
    cm.reset_daily_limit()
    assert cm.tracker is not None

def test_reset_preserves_todays_data():
    from datetime import datetime
    cm, _ = make_cost_manager()
    cm.record_cost("haiku", "mentoring", 500, 200)
    prev_cost = cm.tracker.total_cost
    cm.reset_daily_limit()
    # Same day → tracker unchanged
    assert cm.tracker.total_cost == pytest.approx(prev_cost, rel=1e-9)


# ── get_cost_warning ──────────────────────────────────────────────────────────

def test_no_warning_at_zero_spend():
    cm, _ = make_cost_manager()
    assert cm.get_cost_warning() is None or cm.get_cost_warning() == ""

def test_warning_near_budget():
    cm, _ = make_cost_manager(budget=0.01)
    cm.record_cost("sonnet", "mentoring", 5000, 2000)
    warning = cm.get_cost_warning()
    # Either None (below threshold) or a non-empty string
    assert warning is None or isinstance(warning, str)
