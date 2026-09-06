from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field


class AnswerResult(BaseModel):
    """
    Structured Pydantic model representing final answer synthesis output.
    Returned to backend/frontend and used by frontend SourceBadge component.
    """
    answer: str
    used_rag: bool = False
    used_web: bool = False
    rag_chunk_ids: List[str] = Field(default_factory=list)
    web_result_ids: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
