"""Knowledge Base Engine — ChromaDB-backed expert knowledge for AI audits.

Stores expert articles as vector embeddings (OpenAI text-embedding-3-small).
Used invisibly during audits to enrich AI prompts with specialist knowledge.
"""
from __future__ import annotations

import logging
import os
import textwrap
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────

COLLECTION_NAME = "expert_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 1500  # chars per chunk (roughly 375 tokens)
CHUNK_OVERLAP = 200


def _get_chroma_client():
    """Return a persistent ChromaDB client."""
    import chromadb

    persist_dir = getattr(settings, "CHROMA_DB_DIR", None)
    if not persist_dir:
        persist_dir = os.path.join(settings.BASE_DIR, "chroma_db")

    return chromadb.PersistentClient(path=persist_dir)


def _get_openai_ef():
    """Return OpenAI embedding function for ChromaDB."""
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    return OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name=EMBEDDING_MODEL,
    )


def get_collection():
    """Get or create the expert_knowledge ChromaDB collection."""
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_openai_ef(),
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def embed_article(article_id: int) -> int:
    """Embed an ExpertArticle into ChromaDB. Returns chunk count."""
    from .models import ExpertArticle

    article = ExpertArticle.objects.get(id=article_id)
    collection = get_collection()

    # Remove existing chunks for this article
    remove_article(article_id)

    # Chunk the content
    chunks = _chunk_text(article.content)
    if not chunks:
        return 0

    # Prepare data for ChromaDB
    ids = [f"article_{article_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "article_id": str(article_id),
            "title": article.title[:200],
            "category": article.category,
            "source_url": article.source_url or "",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    # Update article record
    article.chunk_count = len(chunks)
    article.embedded_at = timezone.now()
    article.save(update_fields=["chunk_count", "embedded_at"])

    logger.info("Embedded article %d (%s) → %d chunks", article_id, article.title, len(chunks))
    return len(chunks)


def remove_article(article_id: int) -> None:
    """Remove all chunks for an article from ChromaDB."""
    collection = get_collection()
    try:
        existing = collection.get(where={"article_id": str(article_id)})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def query_knowledge_base(
    query: str,
    categories: list[str] | None = None,
    n_results: int = 5,
) -> str:
    """Semantic search for expert knowledge relevant to a query.

    Returns formatted text ready to inject into AI prompts.
    """
    try:
        collection = get_collection()
        if collection.count() == 0:
            return ""

        where_filter = None
        if categories:
            where_filter = {"category": {"$in": categories}}

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
            where=where_filter,
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        # Format results for prompt injection
        knowledge_parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            title = meta.get("title", "")
            source = meta.get("source_url", "")
            header = f"[{title}]"
            if source:
                header += f" (fonte: {source})"
            knowledge_parts.append(f"{header}\n{doc}")

        return "\n\n---\n\n".join(knowledge_parts)

    except Exception as e:
        logger.warning("Knowledge base query failed: %s", e)
        return ""


def get_stats() -> dict[str, Any]:
    """Return knowledge base statistics."""
    from .models import ExpertArticle

    try:
        collection = get_collection()
        total_chunks = collection.count()
    except Exception:
        total_chunks = 0

    return {
        "total_articles": ExpertArticle.objects.filter(is_active=True).count(),
        "embedded_articles": ExpertArticle.objects.filter(
            is_active=True, embedded_at__isnull=False,
        ).count(),
        "total_chunks": total_chunks,
    }
