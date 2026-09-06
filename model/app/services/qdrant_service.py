from datetime import datetime, timezone
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
)
from app.schemas.chunk_metadata_schema import ChunkMetadata, RetrievedChunk, ChunkStatus


class QdrantService:
    """
    Service wrapping Qdrant Vector DB operations for EvoRAG active-tier chunks.
    Manages vector storage, status-filtered retrieval, and dynamic payload updates.
    """

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = QDRANT_COLLECTION_NAME

    def connect(self) -> QdrantClient:
        """
        Initializes connection to Qdrant instance.
        Attempts connecting using QDRANT_URL or QDRANT_HOST/PORT.
        Falls back to in-memory mode (':memory:') if live instance is unreachable.
        """
        if self.client is not None:
            return self.client

        try:
            if QDRANT_URL:
                self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            else:
                self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            # Test connectivity
            self.client.get_collections()
            print("[QdrantService] Connected to external Qdrant instance.")
        except Exception as e:
            print(f"[QdrantService] Warning: Could not connect to host Qdrant ({e}). Falling back to in-memory Qdrant.")
            self.client = QdrantClient(location=":memory:")

        return self.client

    def create_collection_if_not_exists(self, collection_name: Optional[str] = None, vector_size: int = 384) -> None:
        """
        Ensures target vector collection exists in Qdrant with Cosine distance metric.
        
        Args:
            collection_name (str, optional): Target collection name. Defaults to config value.
            vector_size (int): Dimension of vector embeddings (default 384).
        """
        self.connect()
        target_collection = collection_name or self.collection_name
        collections = [c.name for c in self.client.get_collections().collections]
        
        if target_collection not in collections:
            self.client.create_collection(
                collection_name=target_collection,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )
            print(f"[QdrantService] Created collection '{target_collection}' with vector size {vector_size}.")

    def upsert_chunk(self, chunk: ChunkMetadata, embedding: List[float], collection_name: Optional[str] = None) -> None:
        """
        Inserts or updates a vector point in Qdrant along with ChunkMetadata stored as point payload.

        Args:
            chunk (ChunkMetadata): Metadata object representing the text chunk.
            embedding (List[float]): Vector embedding corresponding to the chunk content.
            collection_name (str, optional): Target collection.
        """
        self.connect()
        target_collection = collection_name or self.collection_name
        self.create_collection_if_not_exists(target_collection, vector_size=len(embedding))

        payload = chunk.model_dump(mode="json")
        point = qmodels.PointStruct(
            id=chunk.chunk_id,
            vector=embedding,
            payload=payload
        )
        self.client.upsert(collection_name=target_collection, points=[point])

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        status_filter: str = "active",
        collection_name: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Executes vector similarity search in Qdrant filtered by metadata payload status.

        Args:
            query_embedding (List[float]): Embedding of user query.
            top_k (int): Number of top matches to return.
            status_filter (str): Payload status filter (default: "active").
            collection_name (str, optional): Target collection.

        Returns:
            List[RetrievedChunk]: Matching chunks sorted descending by similarity score.
        """
        self.connect()
        target_collection = collection_name or self.collection_name

        query_filter = None
        if status_filter:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="status",
                        match=qmodels.MatchValue(value=status_filter)
                    )
                ]
            )

        try:
            results = self.client.search(
                collection_name=target_collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter
            )
        except Exception:
            # Collection might not exist yet
            return []

        retrieved_chunks = []
        for hit in results:
            payload = hit.payload or {}
            metadata = ChunkMetadata(**payload)
            retrieved_chunks.append(RetrievedChunk(metadata=metadata, score=float(hit.score)))

        return retrieved_chunks

    def update_status(
        self,
        chunk_id: str,
        new_status: str,
        superseded_by: Optional[str] = None,
        collection_name: Optional[str] = None
    ) -> None:
        """
        Updates metadata status fields of a specific chunk in-place in Qdrant without re-embedding.

        Args:
            chunk_id (str): UUID string of target chunk.
            new_status (str): Target status ("active", "superseded", "obsolete").
            superseded_by (str, optional): Chunk ID that replaces this chunk.
            collection_name (str, optional): Target collection.
        """
        self.connect()
        target_collection = collection_name or self.collection_name

        now_iso = datetime.now(timezone.utc).isoformat()
        payload_updates = {
            "status": new_status,
            "updated_at": now_iso
        }
        if superseded_by is not None:
            payload_updates["superseded_by"] = superseded_by

        self.client.set_payload(
            collection_name=target_collection,
            payload=payload_updates,
            points=[chunk_id]
        )

    def get_by_id(self, chunk_id: str, collection_name: Optional[str] = None) -> Optional[RetrievedChunk]:
        """
        Fetches a single chunk point by its UUID chunk_id.

        Args:
            chunk_id (str): Target chunk ID.
            collection_name (str, optional): Target collection.

        Returns:
            Optional[RetrievedChunk]: Retrieved chunk or None if not found.
        """
        self.connect()
        target_collection = collection_name or self.collection_name

        try:
            records = self.client.retrieve(
                collection_name=target_collection,
                ids=[chunk_id]
            )
            if not records:
                return None
            point = records[0]
            metadata = ChunkMetadata(**(point.payload or {}))
            return RetrievedChunk(metadata=metadata, score=1.0)
        except Exception:
            return None
