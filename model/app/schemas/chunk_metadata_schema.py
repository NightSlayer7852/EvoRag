from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class ChunkStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    OBSOLETE = "obsolete"


class ChunkMetadata(BaseModel):
    """
    Metadata model stored alongside vector embeddings in Qdrant payload.
    Supports chunk lineage, versioning, staleness tracking, and status transitions.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    source: str
    status: ChunkStatus = ChunkStatus.ACTIVE
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    tags: Optional[List[str]] = None


class RetrievedChunk(BaseModel):
    """
    Lightweight model representing a search result chunk along with vector similarity score.
    """
    metadata: ChunkMetadata
    score: float
