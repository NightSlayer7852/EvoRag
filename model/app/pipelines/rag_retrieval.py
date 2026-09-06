import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.config import (
    CONFIDENCE_THRESHOLD,
    MAX_AGE_DAYS,
    RECENCY_KEYWORDS,
)
from app.schemas.chunk_metadata_schema import ChunkMetadata, RetrievedChunk, ChunkStatus
from app.services.qdrant_service import QdrantService
from app.utils.embeddings import embed_text

# Global service instance
qdrant_service = QdrantService()


def assess_confidence(chunks: List[RetrievedChunk]) -> float:
    """
    Computes normalized confidence score from similarity scores of retrieved chunks.
    Combines top result score (60% weight) and top-K average score (40% weight).
    """
    if not chunks:
        return 0.0

    scores = [c.score for c in chunks]
    top_score = scores[0]
    avg_score = sum(scores) / len(scores)

    confidence = 0.6 * top_score + 0.4 * avg_score
    # Clamp score to [0.0, 1.0] interval
    return max(0.0, min(1.0, float(confidence)))


def check_staleness(query: str, top_chunk: RetrievedChunk = None) -> bool:
    """
    Evaluates staleness based on chunk age and query recency intent.

    Args:
        query (str): User query string.
        top_chunk (RetrievedChunk, optional): Top matching active chunk.

    Returns:
        bool: True if chunk is older than MAX_AGE_DAYS or query asks for real-time information.
    """
    query_lower = query.lower()

    # 1. Recency keyword check
    for keyword in RECENCY_KEYWORDS:
        if keyword in query_lower:
            return True

    # 2. Chunk update timestamp check
    if top_chunk and top_chunk.metadata.updated_at:
        updated_at = top_chunk.metadata.updated_at
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = None

        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = (now - updated_at).days
            if age_days > MAX_AGE_DAYS:
                return True

    return False


def retrieve_and_assess(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Executes EvoRAG retrieval step:
    1. Embeds query text.
    2. Searches active vector chunks in Qdrant.
    3. Calculates retrieval confidence score.
    4. Evaluates staleness (age vs max_age_days and recency keywords).
    5. Determines whether web search fallback is required.

    Args:
        query (str): Input query string.
        top_k (int): Number of top matches to retrieve.

    Returns:
        Dict[str, Any]: Dictionary containing retrieved_chunks, confidence_score, is_stale, needs_web_search.
    """
    query_embedding = embed_text(query)
    retrieved_chunks = qdrant_service.search(query_embedding, top_k=top_k, status_filter="active")

    confidence_score = assess_confidence(retrieved_chunks)
    top_chunk = retrieved_chunks[0] if retrieved_chunks else None
    is_stale = check_staleness(query, top_chunk)

    needs_web_search = (confidence_score < CONFIDENCE_THRESHOLD) or is_stale

    return {
        "retrieved_chunks": retrieved_chunks,
        "confidence_score": round(confidence_score, 4),
        "is_stale": is_stale,
        "needs_web_search": needs_web_search
    }


if __name__ == "__main__":
    print("=== EvoRAG RAG Retrieval Pipeline Manual Verification ===")

    # Initialize Qdrant service and seed sample chunks for manual testing
    qdrant_service.connect()
    
    sample_chunks = [
        ChunkMetadata(
            content="EvoRAG is an evolving Retrieval-Augmented Generation system created in 2026.",
            source="docs/architecture.md",
            status=ChunkStatus.ACTIVE,
            version=1
        ),
        ChunkMetadata(
            content="Legacy RAG systems rely on static vector storage without self-updating memory.",
            source="docs/background.pdf",
            status=ChunkStatus.ACTIVE,
            version=1
        )
    ]

    for chunk in sample_chunks:
        emb = embed_text(chunk.content)
        qdrant_service.upsert_chunk(chunk, emb)

    print("[Test Seed] Seeded 2 sample active chunks into Qdrant.")

    # Load test queries from eval/test_cases.json if available
    eval_file = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "test_cases.json")
    queries_to_test = ["What is EvoRAG?", "What is the latest update today for AI?"]

    if os.path.exists(eval_file):
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                cases = json.load(f)
                queries_to_test = [c.get("query") for c in cases if c.get("query")]
        except Exception as e:
            print(f"[Warning] Could not load eval/test_cases.json: {e}")

    for test_query in queries_to_test:
        print(f"\n--- Testing Query: '{test_query}' ---")
        result = retrieve_and_assess(test_query)
        print(f"Confidence Score: {result['confidence_score']}")
        print(f"Is Stale:         {result['is_stale']}")
        print(f"Needs Web Search: {result['needs_web_search']}")
        print(f"Retrieved Chunks Count: {len(result['retrieved_chunks'])}")
        for idx, chunk in enumerate(result['retrieved_chunks'], 1):
            print(f"  [{idx}] Score: {chunk.score:.4f} | Source: {chunk.metadata.source} | Text: '{chunk.metadata.content}'")
