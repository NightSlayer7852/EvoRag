from typing import TypedDict, Optional, List, Dict, Any
from app.schemas.web_result_schema import WebSearchResult
from app.schemas.answer_schema import AnswerResult
from app.schemas.classification_schema import ClassificationResult


class EvoRAGState(TypedDict):
    """
    TypedDict representing shared state flowing through the EvoRAG LangGraph nodes.
    """
    query: str
    retrieval_result: Optional[Dict[str, Any]]
    web_results: Optional[List[WebSearchResult]]
    answer_result: Optional[AnswerResult]
    classification_results: Optional[List[ClassificationResult]]
