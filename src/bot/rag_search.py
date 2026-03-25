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

# Иерархия уровней — индекс = «вес» (lowercase, matches DB constraint)
LEVEL_ORDER = ["beginner", "elementary", "intermediate", "advanced", "professional"]


def _levels_up_to(level: str) -> List[str]:
    """Return all levels from beginner up to (and including) the given level.

    Accepts both Title Case ("Intermediate") and lowercase ("intermediate") input.
    Returns lowercase values matching DB difficulty_level constraint.
    """
    try:
        idx = LEVEL_ORDER.index(level.lower())
    except ValueError:
        idx = 2  # Default: intermediate
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

    @staticmethod
    def _extract_search_term(query: str) -> str:
        """
        Extract the most searchable term from a natural-language query.

        Strategy (in priority order):
        1. ALL-CAPS acronyms with optional CamelCase suffix: BOS, FVG, CHoCH, AMD
        2. English Title Case multi-word phrases: "Order Block", "Silver Bullet"
        3. Single English Title Case words > 3 chars
        4. Quoted strings
        5. Longest non-stopword Russian word
        6. First 40 chars as last resort
        """
        import re

        # 2. English Title Case phrase (2 words): "Order Block", "Silver Bullet", "Kill Zone"
        en_phrases = re.findall(
            r'\b([A-Z][a-z]{2,}\s[A-Z][a-z]{2,})\b', query
        )
        en_phrases = [p for p in en_phrases if all(ord(c) < 128 for c in p)]

        # 1. ALL-CAPS / CamelCase acronyms (BOS, FVG, CHoCH, IPDA, etc.)
        acronyms = re.findall(r'\b[A-Z]{2,}(?:[a-z]+[A-Z]*)?\b', query)
        if acronyms:
            long_acronyms = [a for a in acronyms if len(a) > 3]
            if long_acronyms:
                return long_acronyms[-1]
            # Short acronym (2-3 chars): prefer it if it's the subject of the query
            # (appears as "ACRONYM (" or "( ACRONYM )") — i.e. parenthetical notation
            for acr in acronyms:
                if re.search(rf'\b{re.escape(acr)}\s*[\(\—]', query) or \
                   re.search(rf'[\(,]\s*{re.escape(acr)}\s*[\),]', query):
                    return acr
            # Otherwise only use short acronym if no Title Case phrase found
            if not en_phrases:
                return acronyms[-1]

        if en_phrases:
            return en_phrases[0]

        # 3. Single English Title Case word > 3 chars (Premium, Discount, Fibonacci…)
        en_words = re.findall(r'\b([A-Z][a-z]{3,})\b', query)
        en_words = [w for w in en_words if all(ord(c) < 128 for c in w)]
        if en_words:
            return en_words[0]

        # 4. Quoted strings
        quoted = re.findall(r'["\u00ab\u00bb](.*?)["\u00ab\u00bb]', query)
        if quoted:
            return quoted[0]

        # 5. Longest meaningful Russian word (skip stopwords)
        RU_STOPWORDS = {
            'что', 'такое', 'как', 'это', 'для', 'при', 'между', 'чём',
            'чем', 'разница', 'отличие', 'опиши', 'объясни', 'является',
            'нужно', 'можно', 'нельзя', 'какой', 'какие', 'почему',
            'торговать', 'определить', 'определяется', 'используется',
            'работать', 'считать', 'рисковать',
        }
        words = [w for w in re.split(r'\W+', query.lower())
                 if len(w) > 4 and w not in RU_STOPWORDS]
        if words:
            return max(words, key=len)

        return query[:40]

    def keyword_search(
        self, query: str, top_k: int = 4, level: str = "Intermediate"
    ) -> List[dict]:
        """
        Full-text ilike search filtered by user level.

        Extracts the most specific term from the query (ICT acronyms, key words)
        rather than searching for the entire question string.
        """
        search_term = self._extract_search_term(query)
        allowed_levels = _levels_up_to(level)

        try:
            # Pass 1: level-filtered search for the key term
            response = (
                self.supabase.table("knowledge_documents")
                .select("id, title, content, section, topic, difficulty_level, metadata")
                .ilike("content", f"%{search_term}%")
                .in_("difficulty_level", allowed_levels)
                .limit(top_k)
                .execute()
            )
            results = response.data or []
            if results:
                return results

            # Pass 2: also search topic field
            response_topic = (
                self.supabase.table("knowledge_documents")
                .select("id, title, content, section, topic, difficulty_level, metadata")
                .ilike("topic", f"%{search_term}%")
                .in_("difficulty_level", allowed_levels)
                .limit(top_k)
                .execute()
            )
            results = response_topic.data or []
            if results:
                return results

            # Pass 3: no level filter — cast wider net
            response2 = (
                self.supabase.table("knowledge_documents")
                .select("id, title, content, section, topic, difficulty_level, metadata")
                .ilike("content", f"%{search_term}%")
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
