import logging
from typing import Optional, List
from fastapi import BackgroundTasks
from langgraph.graph import StateGraph, START, END

from app.graphs.state import EvoRAGState
from app.pipelines.rag_retrieval import retrieve_and_assess
from app.pipelines.web_search import search_web
from app.pipelines.answer_generator import generate_answer
from app.pipelines.classifier_pipeline import classify_and_update
from app.schemas.answer_schema import AnswerResult
from app.schemas.web_result_schema import WebSearchResult

logger = logging.getLogger("evorag.graph")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


# Node 1: RAG Retrieval & Staleness Assessment
def rag_retrieval_node(state: EvoRAGState) -> dict:
    logger.info(f"[Graph] Executing RAG Retrieval Node for query: '{state['query']}'")
    retrieval_res = retrieve_and_assess(state["query"])
    return {"retrieval_result": retrieval_res}


# Conditional Edge Router: Determine if Web Search is required
def should_search_web(state: EvoRAGState) -> str:
    retrieval_res = state.get("retrieval_result") or {}
    needs_search = retrieval_res.get("needs_web_search", False)
    if needs_search:
        logger.info("[Graph] RAG confidence low or stale context -> Routing to 'web_search_node'")
        return "web_search_node"
    logger.info("[Graph] RAG confidence high & fresh -> Routing directly to 'answer_node'")
    return "answer_node"


# Node 2: Triggered Web Search
def web_search_node(state: EvoRAGState) -> dict:
    logger.info(f"[Graph] Executing Web Search Node for query: '{state['query']}'")
    results = search_web(state["query"])
    return {"web_results": results}


# Node 3: Answer Generation
def answer_node(state: EvoRAGState) -> dict:
    logger.info("[Graph] Executing Answer Generation Node")
    answer_res = generate_answer(
        query=state["query"],
        retrieval_result=state.get("retrieval_result") or {},
        web_results=state.get("web_results")
    )
    return {"answer_result": answer_res}


# Build and compile the EvoRAG LangGraph StateGraph
def build_evorag_graph():
    workflow = StateGraph(EvoRAGState)

    # Add Nodes
    workflow.add_node("rag_retrieval_node", rag_retrieval_node)
    workflow.add_node("web_search_node", web_search_node)
    workflow.add_node("answer_node", answer_node)

    # Add Edges
    workflow.add_edge(START, "rag_retrieval_node")

    # Add Conditional Edge from Retrieval
    workflow.add_conditional_edges(
        "rag_retrieval_node",
        should_search_web,
        {
            "web_search_node": "web_search_node",
            "answer_node": "answer_node"
        }
    )

    workflow.add_edge("web_search_node", "answer_node")
    workflow.add_edge("answer_node", END)

    return workflow.compile()


# Compiled LangGraph application instance
evorag_app = build_evorag_graph()


def async_classify_web_results(web_results: List[WebSearchResult]) -> None:
    """
    Background worker task to classify web search results and update vector database memory.
    Runs asynchronously without delaying answer response delivery.
    """
    logger.info(f"[AsyncClassifier] Starting background classification for {len(web_results)} web results...")
    for idx, web_item in enumerate(web_results, 1):
        res = classify_and_update(web_item)
        logger.info(
            f"[AsyncClassifier] [{idx}/{len(web_results)}] Classified '{res.web_result_id}': "
            f"Label={res.label.value} | Action={res.action_taken}"
        )


def run_evorag_pipeline(
    query: str,
    background_tasks: Optional[BackgroundTasks] = None
) -> AnswerResult:
    """
    Executes full EvoRAG workflow pipeline for input query:
    1. Runs LangGraph state machine (Retrieval -> Conditional Web Search -> Answer Generation).
    2. Schedules async self-updating background tasks if web search was triggered.
    3. Returns AnswerResult immediately.

    Args:
        query (str): Input query string.
        background_tasks (BackgroundTasks, optional): FastAPI background task manager.

    Returns:
        AnswerResult: Final synthesized answer result object.
    """
    initial_state: EvoRAGState = {
        "query": query,
        "retrieval_result": None,
        "web_results": None,
        "answer_result": None,
        "classification_results": None
    }

    # Execute compiled graph state machine
    final_state = evorag_app.invoke(initial_state)
    answer_res: AnswerResult = final_state.get("answer_result")
    web_results: Optional[List[WebSearchResult]] = final_state.get("web_results")

    # Schedule or run self-updating classification step
    if web_results:
        if background_tasks is not None:
            logger.info("[EvoRAG] Scheduling async web results classification in FastAPI BackgroundTasks.")
            background_tasks.add_task(async_classify_web_results, web_results)
        else:
            logger.info("[EvoRAG] Standalone execution detected: Running classification inline for test verification.")
            async_classify_web_results(web_results)

    return answer_res
