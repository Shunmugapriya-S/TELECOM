import os
import sys
from pathlib import Path

from types import ModuleType
if "rag_engine" not in sys.modules:
    root_dir = Path(__file__).resolve().parent
    while root_dir.parent != root_dir and not (root_dir / "requirements.txt").exists():
        root_dir = root_dir.parent
    m = ModuleType("rag_engine")
    m.__path__ = [str(root_dir)]
    sys.modules["rag_engine"] = m

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_engine.embeddings import EmbeddingsEngine
from rag_engine.vector_store import DualVectorStore

os.environ["LANGSMITH_TRACING"] = "false"
def traceable(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

@traceable(name="embedding_retrieval_test")
def run_embedding_test(query: str):
    engine = EmbeddingsEngine("all-MiniLM-L6-v2")
    query_vector = engine.encode(query, normalize_embeddings=True)

    sample_chunks = [
        {"text": "Customer reports internet not working after recharge.", "metadata": {"source": "complaint", "id": 1}},
        {"text": "Telecom billing issue due to duplicate charge on broadband plan.", "metadata": {"source": "complaint", "id": 2}},
        {"text": "Use troubleshooting steps for network outage and signal drops.", "metadata": {"source": "sop", "id": 3}},
    ]

    store = DualVectorStore(
        dimension=engine.dimension,
        model_name=engine.model_name,
        pinecone_api_key=""
    )
    store.upsert_chunks(sample_chunks, [query_vector] * len(sample_chunks))

    results = store.search(query_vector, top_k=3)

    return {
        "query": query,
        "embedding_dim": engine.dimension,
        "vector_shape": list(query_vector.shape),
        "top_results": [
            {"text": r["chunk"]["text"], "score": float(r["score"])}
            for r in results
        ],
    }

result = run_embedding_test("internet not working after recharge")
print(result)