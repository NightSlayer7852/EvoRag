from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClassificationLabel(str, Enum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    DUPLICATE = "DUPLICATE"
    CONTRADICTION = "CONTRADICTION"
    OBSOLETE = "OBSOLETE"


class ClassificationResult(BaseModel):
    """
    Structured container capturing classification outcome and database actions taken
    for an asynchronous web search self-update operation.
    """
    web_result_id: str
    matched_chunk_id: Optional[str] = None
    label: ClassificationLabel
    reasoning: str
    action_taken: str
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
