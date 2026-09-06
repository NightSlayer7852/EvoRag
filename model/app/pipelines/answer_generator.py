import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

from app.config import (
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_MODEL_NAME,
)
from app.schemas.answer_schema import AnswerResult
from app.schemas.web_result_schema import WebSearchResult
from app.pipelines.rag_retrieval import retrieve_and_assess
from app.pipelines.web_search import search_web

# Setup module logger
logger = logging.getLogger("evorag.answer_generator")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def build_prompt(
    query: str,
    rag_chunks: List[Any],
    web_results: Optional[List[WebSearchResult]] = None
) -> str:
    """
    Constructs a structured prompt for the LLM clearly separating internal RAG memory
    from dynamic web information.
    """
    prompt = f"USER QUERY: {query}\n\n"

    # 1. Internal RAG Knowledge Section
    prompt += "=== INTERNAL KNOWLEDGE (may be outdated) ===\n"
    if rag_chunks:
        for idx, chunk in enumerate(rag_chunks, 1):
            meta = getattr(chunk, "metadata", chunk)
            chunk_id = getattr(meta, "chunk_id", f"chunk_{idx}")
            updated_at = getattr(meta, "updated_at", "Unknown Date")
            content = getattr(meta, "content", str(chunk))
            prompt += f"[Chunk ID: {chunk_id} | Last Updated: {updated_at}]\n{content}\n\n"
    else:
        prompt += "No internal knowledge retrieved.\n\n"

    # 2. Fresh Web Information Section
    if web_results:
        prompt += "=== FRESH WEB INFORMATION ===\n"
        for result in web_results:
            result_id = getattr(result, "result_id", "web_item")
            source_url = getattr(result, "source_url", "")
            fetched_at = getattr(result, "fetched_at", "Recently")
            content = getattr(result, "content", "")
            prompt += f"[Result ID: {result_id} | Source: {source_url} | Fetched: {fetched_at}]\n{content}\n\n"

    # 3. LLM Instructions & JSON Response Format
    prompt += (
        "=== INSTRUCTIONS ===\n"
        "1. Synthesize a clear, accurate, and concise answer to the user's query.\n"
        "2. If FRESH WEB INFORMATION contradicts or updates INTERNAL KNOWLEDGE, prefer the FRESH WEB INFORMATION "
        "and briefly note any discrepancy.\n"
        "3. Cite which specific Chunk IDs and Result IDs were actually relied upon to answer the query.\n"
        "4. Respond EXCLUSIVELY in valid JSON format matching this schema:\n"
        "{\n"
        '  "answer": "<your synthesized answer text>",\n'
        '  "used_chunk_ids": ["<chunk_id_1>", ...],\n'
        '  "used_result_ids": ["<result_id_1>", ...]\n'
        "}\n"
    )

    return prompt


def execute_mock_llm_generation(
    query: str,
    rag_chunks: List[Any],
    web_results: Optional[List[WebSearchResult]],
    confidence_score: float
) -> AnswerResult:
    """
    Fallback mock answer generator used when no LLM API key is configured.
    Generates a structured answer referencing available RAG and Web IDs.
    """
    logger.info(f"[AnswerGenerator] Using Mock LLM Generator for query: '{query}'")

    used_chunk_ids = []
    used_result_ids = []

    rag_summary_parts = []
    if rag_chunks:
        for c in rag_chunks:
            meta = getattr(c, "metadata", c)
            c_id = getattr(meta, "chunk_id", None)
            if c_id:
                used_chunk_ids.append(c_id)
            rag_summary_parts.append(getattr(meta, "content", ""))

    web_summary_parts = []
    if web_results:
        for w in web_results:
            r_id = getattr(w, "result_id", None)
            if r_id:
                used_result_ids.append(r_id)
            web_summary_parts.append(getattr(w, "content", ""))

    answer_text = f"[MOCK ANSWER] Synthesized response for '{query}'."
    if web_results:
        answer_text += f" Integrated fresh web search details ({len(web_results)} results)."
        if rag_chunks:
            answer_text += " Updated existing internal knowledge base facts with fresh web findings."
    elif rag_chunks:
        answer_text += f" Based on internal knowledge base ({len(rag_chunks)} retrieved active chunks)."
    else:
        answer_text += " No relevant internal or external knowledge was found."

    return AnswerResult(
        answer=answer_text,
        used_rag=len(used_chunk_ids) > 0,
        used_web=len(used_result_ids) > 0,
        rag_chunk_ids=used_chunk_ids,
        web_result_ids=used_result_ids,
        confidence_score=confidence_score
    )


def generate_answer(
    query: str,
    retrieval_result: Dict[str, Any],
    web_results: Optional[List[WebSearchResult]] = None
) -> AnswerResult:
    """
    Synthesizes final answer from RAG retrieval chunks and optional web search results.

    Args:
        query (str): Original user query.
        retrieval_result (dict): Output dict from retrieve_and_assess().
        web_results (list[WebSearchResult], optional): Output list from search_web().

    Returns:
        AnswerResult: Structured result object with answer string and citation IDs.
    """
    retrieved_chunks = retrieval_result.get("retrieved_chunks", [])
    confidence_score = retrieval_result.get("confidence_score", 0.0)

    # Fallback to mock LLM generator if no API key is provided
    if not LLM_API_KEY:
        return execute_mock_llm_generation(query, retrieved_chunks, web_results, confidence_score)

    prompt_text = build_prompt(query, retrieved_chunks, web_results)

    try:
        provider = LLM_PROVIDER.lower()
        response_text = ""

        if provider == "groq":
            try:
                from langchain_groq import ChatGroq
                llm = ChatGroq(
                    groq_api_key=LLM_API_KEY,
                    model_name=LLM_MODEL_NAME,
                    temperature=0.2
                )
                res = llm.invoke(prompt_text)
                response_text = res.content if hasattr(res, "content") else str(res)
            except Exception as e:
                logger.error(f"[AnswerGenerator] Groq LLM call error: {e}")
                return execute_mock_llm_generation(query, retrieved_chunks, web_results, confidence_score)

        elif provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    openai_api_key=LLM_API_KEY,
                    model_name=LLM_MODEL_NAME,
                    temperature=0.2
                )
                res = llm.invoke(prompt_text)
                response_text = res.content if hasattr(res, "content") else str(res)
            except Exception as e:
                logger.error(f"[AnswerGenerator] OpenAI LLM call error: {e}")
                return execute_mock_llm_generation(query, retrieved_chunks, web_results, confidence_score)

        else:
            logger.warning(f"[AnswerGenerator] Unsupported provider '{provider}'. Falling back to mock LLM.")
            return execute_mock_llm_generation(query, retrieved_chunks, web_results, confidence_score)

        # Parse LLM JSON output
        parsed_json = {}
        try:
            # Extract JSON block if wrapped in markdown code blocks
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            json_str = match.group(1) if match else response_text.strip()
            parsed_json = json.loads(json_str)
        except Exception:
            logger.warning("[AnswerGenerator] Failed to parse JSON from LLM response. Using fallback text.")
            parsed_json = {"answer": response_text.strip(), "used_chunk_ids": [], "used_result_ids": []}

        answer_str = parsed_json.get("answer", response_text.strip())
        used_chunk_ids = parsed_json.get("used_chunk_ids", [])
        used_result_ids = parsed_json.get("used_result_ids", [])

        # If LLM didn't return cited IDs, infer from provided context
        if not used_chunk_ids and retrieved_chunks:
            used_chunk_ids = [
                getattr(getattr(c, "metadata", c), "chunk_id", "")
                for c in retrieved_chunks if getattr(getattr(c, "metadata", c), "chunk_id", None)
            ]

        if not used_result_ids and web_results:
            used_result_ids = [
                getattr(w, "result_id", "")
                for w in web_results if getattr(w, "result_id", None)
            ]

        return AnswerResult(
            answer=answer_str,
            used_rag=len(retrieved_chunks) > 0,
            used_web=len(web_results or []) > 0,
            rag_chunk_ids=used_chunk_ids,
            web_result_ids=used_result_ids,
            confidence_score=confidence_score
        )

    except Exception as exc:
        logger.error(f"[AnswerGenerator] Pipeline failed for query '{query}': {exc}")
        return AnswerResult(
            answer="Unable to generate an answer right now.",
            used_rag=False,
            used_web=False,
            rag_chunk_ids=[],
            web_result_ids=[],
            confidence_score=confidence_score
        )


if __name__ == "__main__":
    print("=== EvoRAG Answer Generator Pipeline Manual Verification ===")

    eval_file = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "test_cases.json")
    queries_to_test = ["What is EvoRAG?", "What is the latest update today for AI?"]

    if os.path.exists(eval_file):
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                cases = json.load(f)
                queries_to_test = [c.get("query") for c in cases if c.get("query")]
        except Exception as err:
            print(f"[Warning] Could not load eval/test_cases.json: {err}")

    for test_query in queries_to_test:
        print(f"\n--- Processing Query: '{test_query}' ---")
        
        # Step 1: Retrieval + Staleness Assessment
        retrieval_res = retrieve_and_assess(test_query)
        print(f"Retrieval Confidence: {retrieval_res['confidence_score']}")
        print(f"Needs Web Search:     {retrieval_res['needs_web_search']}")

        # Step 2: Web Search if triggered
        web_res = None
        if retrieval_res["needs_web_search"]:
            web_res = search_web(test_query)
            print(f"Web Results Fetched:  {len(web_res)}")

        # Step 3: Generate Answer
        final_answer = generate_answer(test_query, retrieval_res, web_res)
        
        print("\n--- Final Generated AnswerResult ---")
        print(f"Answer:            {final_answer.answer}")
        print(f"Used RAG:          {final_answer.used_rag} (Chunk IDs: {final_answer.rag_chunk_ids})")
        print(f"Used Web:          {final_answer.used_web} (Result IDs: {final_answer.web_result_ids})")
        print(f"Confidence Score:  {final_answer.confidence_score}")
        print(f"Generated At:      {final_answer.generated_at}")
