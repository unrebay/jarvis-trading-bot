"""
user_memory.py — Persistent student portrait / memory system (v1.0)

Each Telegram user has ONE memory row in Supabase (user_memory table).
Memory is a structured JSON "portrait" that accumulates across ALL sessions.

Structure:
  profile      — who they are (name, experience, trading style, instruments)
  personality  — how they communicate (language, tone, traits)
  learning     — what they know/struggle with, current focus
  conversations — running summary + stats

Update strategy (cost-efficient):
  - Memory is LOADED before every message → injected as context into Claude
  - Memory is UPDATED every MEMORY_UPDATE_INTERVAL messages via Haiku
  - Update happens async (fire-and-forget) after response is already sent

The portrait is passed to ask_mentor() so JARVIS can greet by name,
remember past topics, adapt language, avoid re-explaining known concepts, etc.
"""

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from supabase import Client


# How often (every N user messages) to run Haiku memory extraction
MEMORY_UPDATE_INTERVAL = 5


# ─── Default empty portrait ───────────────────────────────────────────────────

DEFAULT_MEMORY: dict = {
    "profile": {
        "name": None,           # как представился ("Андрей", "Andy"...)
        "experience": None,     # опыт торговли ("2 года", "новичок"...)
        "style": None,          # стиль: swing / scalp / day / position
        "pairs": [],            # инструменты: ["EURUSD", "BTC", "NQ"]
        "timeframes": [],       # таймфреймы: ["H4", "D1"]
        "goals": None,          # цель обучения
        "broker": None,         # брокер/биржа
    },
    "personality": {
        "language": "ru",       # язык общения
        "tone": "unknown",      # "formal" / "informal" / "mixed"
        "traits": [],           # ["прямой", "аналитический", "нетерпеливый"...]
    },
    "learning": {
        "level": "Intermediate",
        "topics_known":       [],   # темы, которые ученик уже знает
        "topics_struggling":  [],   # темы, где путается / переспрашивает
        "current_focus":      None, # что сейчас изучает
        "questions_asked":    0,
    },
    "conversations": {
        "summary":        "",   # краткое резюме всех разговоров (2-4 предложения)
        "last_updated":   None,
        "total_messages": 0,
    },
}


# ─── UserMemory class ──────────────────────────────────────────────────────────

class UserMemory:
    """
    Manages persistent user memory in Supabase (user_memory table).

    Usage in telegram_handler:
        memory = self.user_memory.load(user_id)
        context_str = self.user_memory.format_as_context(memory)
        # ... send response ...
        memory = self.user_memory.increment(memory)
        self.user_memory.save(user_id, memory)
        if self.user_memory.should_update(memory):
            asyncio.create_task(self._update_memory_async(user_id, memory))
    """

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ── Load / Save ────────────────────────────────────────────────────────────

    def load(self, telegram_id: int) -> dict:
        """
        Load user memory from Supabase.
        Returns a deep-copy of DEFAULT_MEMORY if user has no memory yet.
        """
        try:
            res = self.supabase.table("user_memory").select("memory").eq(
                "telegram_id", telegram_id
            ).execute()
            if res.data and res.data[0].get("memory"):
                # Merge with defaults so new fields are always present
                return self._merge_with_defaults(res.data[0]["memory"])
        except Exception as e:
            print(f"⚠️ Memory load error (user {telegram_id}): {e}")
        return deepcopy(DEFAULT_MEMORY)

    def save(self, telegram_id: int, memory: dict) -> None:
        """Upsert memory to Supabase."""
        try:
            memory["conversations"]["last_updated"] = (
                datetime.now(timezone.utc).isoformat()
            )
            self.supabase.table("user_memory").upsert(
                {"telegram_id": telegram_id, "memory": memory},
                on_conflict="telegram_id",
            ).execute()
        except Exception as e:
            print(f"⚠️ Memory save error (user {telegram_id}): {e}")

    # ── Counter ────────────────────────────────────────────────────────────────

    def increment(self, memory: dict) -> dict:
        """Increment message counters. Returns modified memory (in-place)."""
        memory["conversations"]["total_messages"] = (
            memory["conversations"].get("total_messages", 0) + 1
        )
        memory["learning"]["questions_asked"] = (
            memory["learning"].get("questions_asked", 0) + 1
        )
        return memory

    def should_update(self, memory: dict) -> bool:
        """True every MEMORY_UPDATE_INTERVAL messages."""
        total = memory["conversations"].get("total_messages", 0)
        return total > 0 and (total % MEMORY_UPDATE_INTERVAL == 0)

    # ── Context formatting ─────────────────────────────────────────────────────

    def format_as_context(self, memory: dict) -> Optional[str]:
        """
        Format memory as a compact context string for injection into Claude.
        Returns None if memory is essentially empty (new user).
        """
        parts = []

        profile      = memory.get("profile", {})
        personality  = memory.get("personality", {})
        learning     = memory.get("learning", {})
        conversations = memory.get("conversations", {})

        # ── Profile ──
        if profile.get("name"):
            parts.append(f"Имя ученика: {profile['name']}")
        if profile.get("experience"):
            parts.append(f"Опыт торговли: {profile['experience']}")
        if profile.get("style"):
            parts.append(f"Стиль: {profile['style']}")
        if profile.get("pairs"):
            parts.append(f"Торгует: {', '.join(profile['pairs'][:6])}")
        if profile.get("timeframes"):
            parts.append(f"Таймфреймы: {', '.join(profile['timeframes'])}")
        if profile.get("goals"):
            parts.append(f"Цель: {profile['goals']}")
        if profile.get("broker"):
            parts.append(f"Брокер/биржа: {profile['broker']}")

        # ── Learning ──
        level = learning.get("level", "Intermediate")
        parts.append(f"Уровень: {level}")

        if learning.get("topics_known"):
            known = ", ".join(learning["topics_known"][:10])
            parts.append(f"Уже знает: {known}")
        if learning.get("topics_struggling"):
            struggling = ", ".join(learning["topics_struggling"][:6])
            parts.append(f"Трудности: {struggling}")
        if learning.get("current_focus"):
            parts.append(f"Текущая тема: {learning['current_focus']}")

        # ── Personality ──
        tone = personality.get("tone", "unknown")
        if tone != "unknown":
            parts.append(f"Стиль общения: {tone}")
        if personality.get("traits"):
            parts.append(f"Черты: {', '.join(personality['traits'][:4])}")

        total = conversations.get("total_messages", 0)
        if total:
            parts.append(f"Всего сообщений: {total}")

        # ── Summary ──
        summary = conversations.get("summary", "").strip()
        if summary:
            parts.append(f"\nСводка предыдущих разговоров:\n{summary}")

        # Return None for brand-new users with no data
        meaningful = [p for p in parts if not p.startswith("Уровень")]
        if not meaningful and not summary:
            return None

        header = "=== ПОРТРЕТ УЧЕНИКА (помни это в каждом ответе) ==="
        footer = "====================================================="
        return header + "\n" + "\n".join(parts) + "\n" + footer

    # ── Apply Claude-extracted update ─────────────────────────────────────────

    def apply_update(self, current: dict, updated: dict) -> dict:
        """
        Merge Haiku-extracted update into current memory.
        Lists are merged (deduped), strings/scalars are overwritten only
        when the new value is non-empty.
        """
        result = deepcopy(current)
        for section in ("profile", "personality", "learning", "conversations"):
            curr_sec = result.get(section, {})
            upd_sec  = updated.get(section, {})
            for key, new_val in upd_sec.items():
                if isinstance(new_val, list):
                    # Merge lists, deduplicate, preserve order
                    existing = curr_sec.get(key) or []
                    merged   = existing.copy()
                    for item in new_val:
                        if item and item not in merged:
                            merged.append(item)
                    curr_sec[key] = merged
                elif isinstance(new_val, str):
                    if new_val.strip():  # overwrite only if non-empty string
                        curr_sec[key] = new_val
                elif new_val is not None:
                    curr_sec[key] = new_val
            result[section] = curr_sec
        return result

    # ── Internal ───────────────────────────────────────────────────────────────

    def _merge_with_defaults(self, stored: dict) -> dict:
        """Ensure all default keys exist (forward-compat with new fields)."""
        result = deepcopy(DEFAULT_MEMORY)
        for section, defaults in DEFAULT_MEMORY.items():
            if section in stored:
                if isinstance(defaults, dict):
                    result[section] = {**defaults, **stored[section]}
                else:
                    result[section] = stored[section]
        return result
