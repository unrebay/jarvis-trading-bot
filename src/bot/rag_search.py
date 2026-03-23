"""
rag_search.py — Семантический поиск по knowledge base (Supabase)

Функции:
- semantic_search(query) → List[Doc]  — поиск по embeddings
- keyword_search(query) → List[Doc]   — full-text search (GIN trigram)
"""

import os
from typing import List, Optional
from supabase import Client


class RAGSearch:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.embedding_enabled = bool(os.getenv("OPENAI_API_KEY"))

    def semantic_search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Семантический поиск по embeddings.

        Args:
            query: User query text
            top_k: Number of results to return

        Returns:
            List of documents with similarity scores
        """
        if not self.embedding_enabled:
            # Fallback to keyword search
            return self.keyword_search(query, top_k)

        try:
            # Вызываем Supabase функцию match_knowledge_documents()
            # Примечание: embeddings генерируются на стороне бота (будущая фаза)
            # Сейчас используем keyword search как fallback
            return self.keyword_search(query, top_k)

        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return self.keyword_search(query, top_k)

    def keyword_search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Full-text search по контенту (GIN trigram index).

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of matching documents
        """
        try:
            # Используем встроенный поиск Supabase
            # GIN индекс на content и title
            response = self.supabase.table("knowledge_documents").select(
                "id, title, content, section, topic, metadata"
            ).ilike("content", f"%{query}%").limit(top_k).execute()

            return response.data or []

        except Exception as e:
            print(f"❌ Keyword search error: {e}")
            return []

    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Unified search — tries semantic first, falls back to keyword.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of documents
        """
        # Try semantic search if embeddings are available
        if self.embedding_enabled:
            results = self.semantic_search(query, top_k)
            if results:
                return results

        # Fallback to keyword search
        return self.keyword_search(query, top_k)

    def format_context(self, docs: List[dict]) -> str:
        """
        Format search results into context string for Claude.

        Args:
            docs: List of documents from search

        Returns:
            Formatted context string
        """
        if not docs:
            return ""

        context_parts = ["📚 Релевантные материалы:\n"]
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "Untitled")
            content = doc.get("content", "")[:300]  # First 300 chars
            section = doc.get("section", "unknown")

            context_parts.append(f"\n[{i}] {title} (раздел: {section})")
            context_parts.append(f"    {content}...")

        return "\n".join(context_parts)
