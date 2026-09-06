import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.config import (
    CLASSIFICATION_MATCH_FLOOR,
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_MODEL_NAME,
)
from app.schemas.chunk_metadata_schema import ChunkMetadata, ChunkStatus
from app.schemas.classification_schema import ClassificationResult, ClassificationLabel
from app.schemas.web_result_schema import WebSearchResult
from app.services.qdrant_service import QdrantService
from app.utils.embeddings import embed_text
from app.pipelines.rag_retrieval import retrieve_and_assess
from app.pipelines.web_search import search_web

# Setup module logger
logger = logging.getLogger("evorag.classifier")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

qdrant_service = QdrantService()


def build_classification_prompt(
    web_result: WebSearchResult,
    matched_chunk: ChunkMetadata
) -> str:
    """
    Constructs an LLM prompt to classify the relationship between new web content
    and an existing vector database chunk.
    """
    prompt = (
        "=== EVORAG KNOWLEDGE MEMORY CLASSIFIER ===\n\n"
        f"NEW WEB CONTENT:\n"
        f"- Content: {web_result.content}\n"
        f"- Source URL: {web_result.source_url}\n"
        f"- Fetched At: {web_result.fetched_at}\n\n"
        f"MATCHED EXISTING KNOWLEDGE CHUNK:\n"
        f"- Chunk ID: {matched_chunk.chunk_id}\n"
        f"- Content: {matched_chunk.content}\n"
        f"- Version: {matched_chunk.version}\n"
        f"- Last Updated: {matched_chunk.updated_at}\n\n"
        "=== CLASSIFICATION LABELS ===\n"
        "- NEW: The web content presents a distinct, novel topic or entity not captured by the existing chunk.\n"
        "- UPDATE: The web content covers the same topic/entity, but refines, updates, or adds newer facts to the existing chunk.\n"
        "- DUPLICATE: The web content states essentially the same facts as the existing chunk without new information.\n"
        "- CONTRADICTION: The web content directly conflicts with the existing chunk on the same topic, with no clear indication of which is newer or correct.\n"
        "- OBSOLETE: The web content renders the existing chunk completely false, closed, or invalidated.\n\n"
        "=== INSTRUCTIONS ===\n"
        "Select exactly one label from: [NEW, UPDATE, DUPLICATE, CONTRADICTION, OBSOLETE].\n"
        "Provide a short reasoning explaining your classification decision.\n"
        "Respond EXCLUSIVELY in valid JSON format matching this schema:\n"
        "{\n"
        '  "label": "<NEW|UPDATE|DUPLICATE|CONTRADICTION|OBSOLETE>",\n'
        '  "reasoning": "<short reasoning text>"\n'
        "}\n"
    )
    return prompt


def execute_mock_classification(
    web_result: WebSearchResult,
    matched_chunk: ChunkMetadata
) -> Dict[str, str]:
    """
    Fallback deterministic classification rule engine used when no LLM API key is configured.
    """
    web_text = web_result.content.lower()
    chunk_text = matched_chunk.content.lower()

    if "closed" in web_text or "obsolete" in web_text or "discontinued" in web_text:
        return {
            "label": "OBSOLETE",
            "reasoning": "[MOCK CLASSIFIER] Web content indicates existing item has been closed or obsoleted."
        }
    elif "conflict" in web_text or "contradict" in web_text or "differs from" in web_text:
        return {
            "label": "CONTRADICTION",
            "reasoning": "[MOCK CLASSIFIER] Web content contradicts existing knowledge chunk facts."
        }
    elif web_text == chunk_text or len(set(web_text.split()).intersection(set(chunk_text.split()))) > 15:
        return {
            "label": "DUPLICATE",
            "reasoning": "[MOCK CLASSIFIER] Web content contains identical information to existing chunk."
        }
    else:
        return {
            "label": "UPDATE",
            "reasoning": "[MOCK CLASSIFIER] Web content updates or adds new context to existing topic."
        }


def classify_and_update(web_result: WebSearchResult) -> ClassificationResult:
    """
    Asynchronously classifies fetched web search result against existing vector chunks in Qdrant,
    and executes appropriate database self-updating actions.

    Args:
        web_result (WebSearchResult): Search result item to classify.

    Returns:
        ClassificationResult: Record of classification decision and database actions executed.
    """
    try:
        # 1. Embed web result content
        web_embedding = embed_text(web_result.content)

        # 2. Search Qdrant for top 3 matching active chunks
        retrieved = qdrant_service.search(web_embedding, top_k=3, status_filter="active")

        # 3. Check similarity match floor
        if not retrieved or retrieved[0].score < CLASSIFICATION_MATCH_FLOOR:
            # Below match floor threshold -> Treat as NEW
            new_chunk = ChunkMetadata(
                content=web_result.content,
                source=web_result.source_url,
                status=ChunkStatus.ACTIVE,
                version=1
            )
            qdrant_service.upsert_chunk(new_chunk, web_embedding)

            return ClassificationResult(
                web_result_id=web_result.result_id,
                matched_chunk_id=None,
                label=ClassificationLabel.NEW,
                reasoning="Top similarity match below floor threshold; treated as novel knowledge.",
                action_taken=f"Upserted new active chunk '{new_chunk.chunk_id}' into vector DB."
            )

        # 4. Top similarity match exists above floor
        top_match = retrieved[0]
        matched_metadata = top_match.metadata
        matched_id = matched_metadata.chunk_id

        # Determine label & reasoning using LLM or mock classifier
        label_str = "NEW"
        reasoning = ""

        if not LLM_API_KEY:
            res_dict = execute_mock_classification(web_result, matched_metadata)
            label_str = res_dict["label"]
            reasoning = res_dict["reasoning"]
        else:
            prompt_text = build_classification_prompt(web_result, matched_metadata)
            try:
                provider = LLM_PROVIDER.lower()
                response_text = ""

                if provider == "groq":
                    from langchain_groq import ChatGroq
                    llm = ChatGroq(
                        groq_api_key=LLM_API_KEY,
                        model_name=LLM_MODEL_NAME,
                        temperature=0.0
                    )
                    res = llm.invoke(prompt_text)
                    response_text = res.content if hasattr(res, "content") else str(res)

                elif provider == "openai":
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        openai_api_key=LLM_API_KEY,
                        model_name=LLM_MODEL_NAME,
                        temperature=0.0
                    )
                    res = llm.invoke(prompt_text)
                    response_text = res.content if hasattr(res, "content") else str(res)

                else:
                    res_dict = execute_mock_classification(web_result, matched_metadata)
                    label_str = res_dict["label"]
                    reasoning = res_dict["reasoning"]
                    response_text = ""

                if response_text:
                    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                    json_str = match.group(1) if match else response_text.strip()
                    parsed = json.loads(json_str)
                    label_str = parsed.get("label", "UPDATE").upper()
                    reasoning = parsed.get("reasoning", "LLM classified relationship.")

            except Exception as e:
                logger.error(f"[Classifier] LLM classification call error: {e}. Falling back to mock engine.")
                res_dict = execute_mock_classification(web_result, matched_metadata)
                label_str = res_dict["label"]
                reasoning = res_dict["reasoning"]

        # Validate label enum
        try:
            label_enum = ClassificationLabel(label_str)
        except ValueError:
            label_enum = ClassificationLabel.UPDATE

        action_taken = ""

        # 5. Execute corresponding Database Action based on label
        if label_enum == ClassificationLabel.NEW:
            new_chunk = ChunkMetadata(
                content=web_result.content,
                source=web_result.source_url,
                status=ChunkStatus.ACTIVE,
                version=1
            )
            qdrant_service.upsert_chunk(new_chunk, web_embedding)
            action_taken = f"Inserted new active chunk '{new_chunk.chunk_id}' into vector DB."

        elif label_enum == ClassificationLabel.UPDATE:
            new_chunk = ChunkMetadata(
                content=web_result.content,
                source=web_result.source_url,
                status=ChunkStatus.ACTIVE,
                version=matched_metadata.version + 1,
                supersedes=matched_id
            )
            # Upsert new version chunk as active
            qdrant_service.upsert_chunk(new_chunk, web_embedding)
            # Mark matched chunk as superseded
            qdrant_service.update_status(matched_id, new_status="superseded", superseded_by=new_chunk.chunk_id)
            action_taken = (
                f"Inserted updated version {new_chunk.version} chunk '{new_chunk.chunk_id}' as active "
                f"and marked old chunk '{matched_id}' as superseded."
            )

        elif label_enum == ClassificationLabel.DUPLICATE:
            # Refresh updated_at timestamp without re-embedding
            now_iso = datetime.now(timezone.utc).isoformat()
            qdrant_service.update_payload(matched_id, {"updated_at": now_iso})
            action_taken = f"Refreshed updated_at timestamp for duplicate chunk '{matched_id}'."

        elif label_enum == ClassificationLabel.CONTRADICTION:
            new_chunk = ChunkMetadata(
                content=web_result.content,
                source=web_result.source_url,
                status=ChunkStatus.ACTIVE,
                version=1,
                conflicts_with=[matched_id]
            )
            qdrant_service.upsert_chunk(new_chunk, web_embedding)

            # Update matched chunk's conflicts_with list
            existing_conflicts = matched_metadata.conflicts_with or []
            if new_chunk.chunk_id not in existing_conflicts:
                updated_conflicts = existing_conflicts + [new_chunk.chunk_id]
                qdrant_service.update_payload(matched_id, {"conflicts_with": updated_conflicts})

            action_taken = (
                f"Inserted conflicting active chunk '{new_chunk.chunk_id}' and updated "
                f"mutual conflict tagging with chunk '{matched_id}'."
            )

        elif label_enum == ClassificationLabel.OBSOLETE:
            # Mark matched chunk as obsolete without storing obsolete event text
            qdrant_service.update_status(matched_id, new_status="obsolete")
            action_taken = f"Marked existing chunk '{matched_id}' as obsolete in vector DB."

        return ClassificationResult(
            web_result_id=web_result.result_id,
            matched_chunk_id=matched_id,
            label=label_enum,
            reasoning=reasoning,
            action_taken=action_taken
        )

    except Exception as exc:
        logger.error(f"[Classifier] Failed classifying web result '{web_result.result_id}': {exc}")
        return ClassificationResult(
            web_result_id=web_result.result_id,
            matched_chunk_id=None,
            label=ClassificationLabel.NEW,
            reasoning=f"Pipeline exception encountered: {exc}",
            action_taken="Error encountered during classification; no DB state modified."
        )


if __name__ == "__main__":
    print("=== EvoRAG Async Classifier Pipeline Manual Verification ===")

    # Initialize Qdrant and seed sample active chunk
    qdrant_service.connect()

    initial_chunk = ChunkMetadata(
        content="EvoRAG 1.0 architecture uses a static retrieval window.",
        source="docs/arch_v1.md",
        status=ChunkStatus.ACTIVE,
        version=1
    )
    qdrant_service.upsert_chunk(initial_chunk, embed_text(initial_chunk.content))
    print(f"\n[Test Seed] Initialized seed active chunk '{initial_chunk.chunk_id}' (v1).")

    # Sample web results to classify against seed chunk
    test_web_results = [
        WebSearchResult(
            query="EvoRAG update",
            content="EvoRAG 2.0 refines the architecture with dynamic self-updating memory and async background compaction.",
            source_url="https://evorag.dev/v2-release",
            title="EvoRAG 2.0 Release Notes",
            rank=1
        ),
        WebSearchResult(
            query="EvoRAG obsolete note",
            content="The old static retrieval window in EvoRAG 1.0 is now obsolete and completely deprecated.",
            source_url="https://evorag.dev/deprecation",
            title="Deprecation Notice",
            rank=2
        )
    ]

    for idx, web_item in enumerate(test_web_results, 1):
        print(f"\n--- Testing Classification #{idx} ---")
        print(f"Web Content: '{web_item.content}'")

        # Verify initial chunk status before classification
        before_state = qdrant_service.get_by_id(initial_chunk.chunk_id)
        before_status = before_state.metadata.status if before_state else "None"
        print(f"Chunk '{initial_chunk.chunk_id}' status BEFORE: {before_status}")

        result = classify_and_update(web_item)

        print(f"Classification Label:  {result.label}")
        print(f"Reasoning:             {result.reasoning}")
        print(f"Action Taken:          {result.action_taken}")

        # Verify initial chunk status after classification
        after_state = qdrant_service.get_by_id(initial_chunk.chunk_id)
        after_status = after_state.metadata.status if after_state else "None"
        print(f"Chunk '{initial_chunk.chunk_id}' status AFTER:  {after_status}")
