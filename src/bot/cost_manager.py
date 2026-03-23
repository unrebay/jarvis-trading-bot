"""
Cost Manager - Track API costs and enforce budget limits

Prevents daily budget overruns with:
- Daily cost tracking
- Budget alerts
- Fallback mode activation
- Request throttling
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class BotMode(Enum):
    """Operating modes"""
    FULL = "full"  # All features enabled
    LITE = "lite"  # Vision disabled, local fallback
    OFFLINE = "offline"  # No API calls, cached responses only


@dataclass
class CostTracker:
    """Track daily costs"""
    date: str  # YYYY-MM-DD
    total_cost: float  # USD
    by_model: Dict[str, float]  # Model → cost
    by_feature: Dict[str, float]  # Feature → cost
    request_count: int
    vision_calls: int
    last_updated: str


class CostManager:
    """
    Manage API costs with budget enforcement

    Budget thresholds:
    - $0.00-0.50: Full mode
    - $0.50-0.80: Lite mode (vision disabled for non-critical)
    - $0.80+: Offline mode (cached responses only)
    """

    def __init__(self, daily_budget: float = 1.00, data_dir: str = "data/costs"):
        """
        Initialize cost manager

        Args:
            daily_budget: Daily budget in USD (default $1.00)
            data_dir: Directory to store cost tracking data
        """
        self.daily_budget = daily_budget
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.today = datetime.now().strftime("%Y-%m-%d")
        self.tracker = self._load_today_tracker()

    def _load_today_tracker(self) -> CostTracker:
        """Load or create today's cost tracker"""
        tracker_file = self.data_dir / f"{self.today}.json"

        if tracker_file.exists():
            with open(tracker_file) as f:
                data = json.load(f)
                return CostTracker(**data)

        return CostTracker(
            date=self.today,
            total_cost=0.0,
            by_model={},
            by_feature={},
            request_count=0,
            vision_calls=0,
            last_updated=datetime.now().isoformat(),
        )

    def _save_tracker(self) -> None:
        """Save tracker to disk"""
        tracker_file = self.data_dir / f"{self.today}.json"
        with open(tracker_file, "w") as f:
            json.dump(asdict(self.tracker), f, indent=2)

    def get_mode(self) -> BotMode:
        """Get current operating mode based on budget"""
        remaining = self.daily_budget - self.tracker.total_cost
        spending_percent = (self.tracker.total_cost / self.daily_budget) * 100

        if spending_percent >= 80:
            return BotMode.OFFLINE
        elif spending_percent >= 50:
            return BotMode.LITE
        else:
            return BotMode.FULL

    def can_use_vision(self) -> bool:
        """Check if vision analysis is allowed"""
        return self.get_mode() in (BotMode.FULL, BotMode.LITE)

    def can_use_api(self) -> bool:
        """Check if any API calls are allowed"""
        return self.get_mode() != BotMode.OFFLINE

    def record_cost(
        self,
        model: str,
        feature: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Record API call cost

        Args:
            model: Model used (haiku, sonnet, opus)
            feature: Feature type (mentoring, search, vision, analysis)
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        # Pricing (as of March 2026)
        pricing = {
            "haiku": {"input": 0.80 / 1_000_000, "output": 0.40 / 1_000_000},
            "sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
            "opus": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
        }

        if model not in pricing:
            return 0.0

        model_pricing = pricing[model]
        cost = (
            input_tokens * model_pricing["input"]
            + output_tokens * model_pricing["output"]
        )

        # Update tracker
        self.tracker.total_cost += cost
        self.tracker.by_model[model] = self.tracker.by_model.get(model, 0.0) + cost
        self.tracker.by_feature[feature] = (
            self.tracker.by_feature.get(feature, 0.0) + cost
        )
        self.tracker.request_count += 1
        self.tracker.last_updated = datetime.now().isoformat()

        if model == "opus":
            self.tracker.vision_calls += 1

        self._save_tracker()

        return cost

    def get_daily_summary(self) -> str:
        """Get human-readable daily summary"""
        remaining = self.daily_budget - self.tracker.total_cost
        spending_percent = (self.tracker.total_cost / self.daily_budget) * 100
        mode = self.get_mode()

        summary = f"""
📊 DAILY COST SUMMARY ({self.today})
{'=' * 50}

Budget: ${self.daily_budget:.2f}/day
Spent: ${self.tracker.total_cost:.4f}
Remaining: ${remaining:.4f}
Usage: {spending_percent:.1f}%

Mode: {mode.value.upper()}

By Model:
"""
        for model, cost in self.tracker.by_model.items():
            summary += f"  • {model}: ${cost:.4f}\n"

        summary += f"\nBy Feature:\n"
        for feature, cost in self.tracker.by_feature.items():
            summary += f"  • {feature}: ${cost:.4f}\n"

        summary += f"\nRequests: {self.tracker.request_count}\n"
        summary += f"Vision calls: {self.tracker.vision_calls}\n"

        return summary

    def get_cost_warning(self) -> Optional[str]:
        """Get warning if approaching budget limit"""
        spending_percent = (self.tracker.total_cost / self.daily_budget) * 100

        if spending_percent >= 90:
            return f"⚠️ CRITICAL: {spending_percent:.0f}% of daily budget spent!"
        elif spending_percent >= 75:
            return f"⚠️ WARNING: {spending_percent:.0f}% of daily budget spent. Switching to LITE mode."
        elif spending_percent >= 50:
            return f"⚠️ CAUTION: {spending_percent:.0f}% of daily budget spent. Vision calls limited."

        return None

    def reset_daily_limit(self) -> None:
        """Reset at midnight (manual call)"""
        now = datetime.now().strftime("%Y-%m-%d")
        if now != self.today:
            self.today = now
            self.tracker = CostTracker(
                date=self.today,
                total_cost=0.0,
                by_model={},
                by_feature={},
                request_count=0,
                vision_calls=0,
                last_updated=datetime.now().isoformat(),
            )
            self._save_tracker()


class RequestThrottler:
    """Throttle API requests to prevent accidental overspending"""

    def __init__(self, max_vision_calls_per_hour: int = 10):
        """
        Initialize throttler

        Args:
            max_vision_calls_per_hour: Max vision calls allowed per hour
        """
        self.max_vision_calls_per_hour = max_vision_calls_per_hour
        self.vision_call_times = []

    def can_make_vision_call(self) -> bool:
        """Check if vision call is allowed"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # Remove old calls outside 1-hour window
        self.vision_call_times = [
            t for t in self.vision_call_times if t > one_hour_ago
        ]

        # Check if under limit
        if len(self.vision_call_times) >= self.max_vision_calls_per_hour:
            return False

        return True

    def record_vision_call(self) -> None:
        """Record a vision call"""
        self.vision_call_times.append(datetime.now())

    def get_throttle_wait_time(self) -> Optional[int]:
        """Get seconds to wait before next vision call (if throttled)"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        self.vision_call_times = [
            t for t in self.vision_call_times if t > one_hour_ago
        ]

        if len(self.vision_call_times) >= self.max_vision_calls_per_hour:
            # Return seconds until oldest call exits the window
            oldest = self.vision_call_times[0]
            wait_until = oldest + timedelta(hours=1)
            wait_seconds = int((wait_until - now).total_seconds())
            return wait_seconds

        return None


# Global instances
cost_manager = CostManager(daily_budget=1.00)  # $1.00/day default
request_throttler = RequestThrottler(max_vision_calls_per_hour=10)
