from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field


class WebSearchResult(BaseModel):
    """
    Structured container for a cleaned web search result item.
    Ready to be merged into final answer and queued for async memory updating.
    """
    result_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    content: str
    source_url: str
    title: str = "Untitled Page"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rank: int
