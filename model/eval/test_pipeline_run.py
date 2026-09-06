import json
import os
import sys

# Ensure model directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graphs.evorag_graph import run_evorag_pipeline


def main():
    print("==========================================================")
    print("=== EvoRAG Full Pipeline End-to-End Verification Run ===")
    print("==========================================================")

    eval_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    queries_to_test = [
        "What is EvoRAG?",
        "What is the latest update today for AI technology in 2026?"
    ]

    if os.path.exists(eval_file):
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                cases = json.load(f)
                loaded_queries = [c.get("query") for c in cases if c.get("query")]
                if loaded_queries:
                    queries_to_test = loaded_queries
        except Exception as e:
            print(f"[Warning] Could not read test_cases.json: {e}")

    for idx, query in enumerate(queries_to_test, 1):
        print(f"\n==========================================================")
        print(f"[{idx}/{len(queries_to_test)}] RUNNING PIPELINE FOR QUERY: '{query}'")
        print("==========================================================")

        # Run pipeline inline without background_tasks parameter
        result = run_evorag_pipeline(query)

        print("\n--- FINAL PIPELINE OUTPUT (AnswerResult) ---")
        print(f"Answer:           {result.answer}")
        print(f"Used RAG:         {result.used_rag} (Cited Chunk IDs: {result.rag_chunk_ids})")
        print(f"Used Web:         {result.used_web} (Cited Web IDs:   {result.web_result_ids})")
        print(f"Confidence Score: {result.confidence_score}")
        print(f"Generated At:     {result.generated_at}")
        print("==========================================================")


if __name__ == "__main__":
    main()
