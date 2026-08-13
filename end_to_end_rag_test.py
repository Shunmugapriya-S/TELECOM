import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.retriever import TelecomRAGRetriever
from rag_engine.context_engineering import ContextEngineer


def run_end_to_end_test():
    retriever = TelecomRAGRetriever()
    retriever.index_documents()

    queries = [
        "internet not working after recharge",
        "billing issue and duplicate charge",
        "network signal dropped after recent plan change",
        "customer angry about unresolved complaint and refund"
    ]

    engineer = ContextEngineer(max_context_chars=4000, max_chunks=5, min_score=0.0)

    for query in queries:
        print(f"\n=== QUERY: {query} ===")
        results = retriever.retrieve(query, top_k=5)
        ranked = engineer.rank_context(results, query)
        summary = engineer.build_context_summary(results)
        history = engineer.merge_customer_and_complaint_history(results)

        print("\nRANKED REQUIREMENT BLOCKS:")
        sections = engineer.build_requirement_aware_context(results, query)
        for key, values in sections.items():
            if values:
                print(f"\n• {key}")
                for v in values:
                    print("  -", v[:220])

        print("\nTEMPORAL / HISTORY SUMMARY:")
        print(history)
        print("\nTOP CONTEXT SUMMARY:")
        print(summary)

        print("\nPROMPT PREVIEW:")
        prompt = engineer.build_prompt(
            system_prompt="You are a telecom support assistant. Use retrieved information, customer history, and action rules to answer accurately.",
            user_query=query,
            search_results=results,
        )
        print(prompt[:1500])


if __name__ == "__main__":
    run_end_to_end_test()
