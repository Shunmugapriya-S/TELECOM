import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.retriever import TelecomRAGRetriever
from rag_engine.context_engineering import ContextEngineer
from rag_engine.ai_agents.LLM import TelecomLLMClient


def run_llm_pipeline_test():
    os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    os.environ.setdefault("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

    retriever = TelecomRAGRetriever()
    print("\n=== INDEXING ===")
    retriever.index_documents()

    query = "internet not working after recharge"
    print(f"\n=== QUERY: {query} ===")

    results = retriever.retrieve(query, top_k=5)
    print(f"Retrieved chunks: {len(results)}")

    engineer = ContextEngineer(max_context_chars=4000, max_chunks=5, min_score=0.0)
    ranked = engineer.rank_context(results, query)
    print(f"Ranked chunks: {len(ranked)}")

    sections = engineer.build_requirement_aware_context(results, query)
    print("\n=== REQUIREMENT BLOCKS ===")
    for key, values in sections.items():
        if values:
            print(f"\n[{key}]")
            for v in values[:2]:
                print("-", v[:250])

    llm = TelecomLLMClient()
    context_text = "\n".join(r["chunk"]["text"] for r in results if r.get("chunk", {}).get("text"))
    answer = llm.generate_response(
        "You are a telecom support assistant. Use the retrieved facts, customer history, complaint history, temporal context, and required actions.",
        query,
        context_text,
    )

    print("\n=== FINAL GEMINI ANSWER ===")
    print(answer)


if __name__ == "__main__":
    run_llm_pipeline_test()
