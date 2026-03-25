"""
rag_search.py — Семантический поиск по knowledge base (Supabase)

Функции:
- semantic_search(query, level) → List[Doc]  — pgvector similarity search
- keyword_search(query, level)  → List[Doc]  — full-text search (ilike)
- search(query, level)          → List[Doc]  — semantic first, keyword fallback

Уровни (иерархия):
  Beginner → Elementary → Intermediate → Advanced → Professional

Поиск возвращает документы уровня ≤ текущего уровня ученика.
"""

import os
from typing import List, Optional
from supabase import Client

# Иерархия уровней — индекс = «вес»
LEVEL_ORDER = ["Beginner", "Elementary", "Intermediate", "Advanced", "Professional"]


def _levels_up_to(level: str) -> List[str]:
    """Return all levels from Beginner up to (and including) the given level."""
    try:
        idx = LEVEL_ORDER.index(level)
    except ValueError:
        idx = 2  # Default: Intermediate
    return LEVEL_ORDER[: idx + 1]


class RAGSearch:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.embedding_enabled = bool(os.getenv("OPENAI_API_KEY"))
        self._openai = None  # lazy-loaded

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _get_openai(self):
        """Lazy-load OpenAI client."""
        if self._openai is None:
            try:
                from openai import OpenAI
                self._openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                self._openai = None
        return self._openai

    def _embed(self, text: str) -> Optional[List[float]]:
        """Generate embedding for query text. Returns None on failure."""
        client = self._get_openai()
        if not client:
            return None
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],  # stay well within 8191-token limit
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  Embedding error: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────────
    # Public search methods
    # ──────────────────────────────────────────────────────────────────────

    def semantic_search(
        self, query: str, top_k: int = 4, level: str = "Intermediate"
    ) -> List[dict]:
        """
        pgvector similarity search filtered by user level.

        Calls Supabase RPC `match_knowledge_documents(query_embedding, match_count,
        filter)` — must exist in DB (see migration).

        Falls back to keyword_search if embedding fails or RPC unavailable.
        """
        if not self.embedding_enabled:
            return self.keyword_search(query, top_k, level)

        vector = self._embed(query)
        if not vector:
            return self.keyword_search(query, top_k, level)

        allowed_levels = _levels_up_to(level)

        try:
            response = self.supabase.rpc(
                "match_knowledge_documents",
                {
                    "query_embedding":  vector,
                    "match_count":      top_k,
                    "match_threshold":  0.3,          # lowered from 0.7 — more results
                    "filter_levels":    allowed_levels,
                },
            ).execute()
            results = response.data or []
            if results:
                return results
        except Exception as e:
            print(f"⚠️  pgvector RPC error (falling back to keyword): {e}")

        return self.keyword_search(query, top_k, level)

    def keyword_search(
        self, query: str, top_k: int = 4, level: str = "Intermediate"
    ) -> List[dict]:
        """
        Full-text ilike search filtered by user level.

        Uses difficulty_level IN (allowed levels) so beginners don't get
        professional content they can't use yet.
        """
        allowed_levels = _levels_up_to(level)
        try:
            response = (
                self.supabase.table("knowledge_documents")
                .select("id, title, content, section, topic, difficulty_level, metadata")
                .ilike("content", f"%{query}%")
                .in_("difficulty_level", allowed_levels)
                .limit(top_k)
                .execute()
            )
            results = response.data or []
            if results:
                return results

            # If no level-filtered results, try without level filter as fallback
            response2 = (
                self.supabase.table("knowledge_documents")
                .select("id, title, content, section, topic, difficulty_level, metadata")
                .ilike("content", f"%{query}%")
                .limit(top_k)
                .execute()
            )
            return response2.data or []

        except Exception as e:
            print(f"❌ Keyword search error: {e}")
            return []

    def search(
        self, query: str, top_k: int = 4, level: str = "Intermediate"
    ) -> List[dict]:
        """
        Unified search — semantic first (if OpenAI key present), keyword fallback.

        Args:
            query:  User query text
            top_k:  Number of results to return
            level:  User's current learning level (filters results)

        Returns:
            List of matching knowledge_documents rows
        """
        if self.embedding_enabled:
            results = self.semantic_search(query, top_k, level)
            if results:
                return results

        return self.keyword_search(query, top_k, level)

    # ──────────────────────────────────────────────────────────────────────
    # Formatting
    # ──────────────────────────────────────────────────────────────────────

    def format_context(self, docs: List[dict], max_chars: int = 400) -> str:
        """
        Format search results into a context block for Claude's system prompt.

        Args:
            docs:       List of documents from search()
            max_chars:  Max chars to include per document snippet

        Returns:
            Formatted multi-line string ready to inject into system context
        """
        if not docs:
            return ""

        context_parts = ["📚 Релевантные материалы из базы знаний:\n"]
        for i, doc in enumerate(docs, 1):
            title   = doc.get("title", "Untitled")
            content = doc.get("content", "")[:max_chars]
            section = doc.get("section", "")
            dlevel  = doc.get("difficulty_level", "")

            level_badge = f" [{dlevel}]" if dlevel else ""
            section_str = f" • {section}" if section else ""

            context_parts.append(f"\n[{i}] {title}{level_badge}{section_str}")
            context_parts.append(f"    {content}...")

        return "\n".join(context_parts)
