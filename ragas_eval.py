"""RAGAS Framework Evaluation Module (Ollama-Powered)

Implements standard RAGAS (Retrieval-Augmented Generation Assessment) metrics
using the local Ollama model for LLM-as-judge evaluation:

1. Faithfulness      — LLM judges if each response claim is supported by context
2. Answer Relevance  — Embedding similarity between query and response
3. Context Precision — Ratio of relevant retrieved chunks (embedding-based)
4. Context Recall    — Ground truth fact coverage by retrieved chunks
5. Composite RAGAS Score
"""

import sys
import re
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional

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


# ---- Ollama judge helper ---------------------------------------------------
def _ollama_judge(prompt: str, model: str = "gemma3:latest",
                  base_url: str = "http://localhost:11434") -> str:
    """Call Ollama to get a short LLM judgment. Returns raw text."""
    import urllib.request
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 256},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip()
    except Exception:
        return ""


def _ollama_available(base_url: str = "http://localhost:11434") -> bool:
    import urllib.request
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


class RAGASEvaluator:
    """RAGAS Framework Evaluator using Ollama LLM-as-Judge + Embeddings."""

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2",
                 ollama_model: str = "gemma3:latest"):
        self.embeddings = EmbeddingsEngine(model_name=embedding_model)
        self.ollama_model = ollama_model
        self.use_llm_judge = _ollama_available()

    def _cosine_sim(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        na, nb = np.linalg.norm(vec_a), np.linalg.norm(vec_b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (na * nb))

    # ---- 1. Faithfulness (LLM-as-Judge) ------------------------------------
    def evaluate_faithfulness(self, response: str, contexts: List[str]) -> float:
        """Uses Ollama LLM to judge whether each claim in the response is
        supported by the retrieved context. Falls back to token-overlap if
        Ollama is unavailable."""
        if not response or not contexts:
            return 0.0

        # Extract claims (sentences > 10 chars)
        claims = [s.strip() for s in re.split(r"[.\n;]", response) if len(s.strip()) > 10]
        if not claims:
            return 1.0

        context_text = "\n".join(contexts)

        if self.use_llm_judge:
            # LLM-as-Judge: ask Ollama to verify each claim
            prompt = (
                "You are a factuality judge. Given the CONTEXT and a list of CLAIMS, "
                "for each claim respond ONLY with 'SUPPORTED' or 'NOT_SUPPORTED'.\n\n"
                f"CONTEXT:\n{context_text[:3000]}\n\n"
                "CLAIMS:\n"
            )
            for i, claim in enumerate(claims[:12], 1):
                prompt += f"{i}. {claim}\n"
            prompt += "\nFor each claim number, write ONLY: <number>. SUPPORTED or <number>. NOT_SUPPORTED"

            judgment = _ollama_judge(prompt, model=self.ollama_model)

            supported = 0
            for i in range(1, len(claims[:12]) + 1):
                if f"{i}. SUPPORTED" in judgment.upper() or f"{i}.SUPPORTED" in judgment.upper():
                    # Make sure it's not "NOT_SUPPORTED"
                    line_check = judgment.upper()
                    pattern = f"{i}. NOT_SUPPORTED"
                    pattern2 = f"{i}.NOT_SUPPORTED"
                    if pattern not in line_check and pattern2 not in line_check:
                        supported += 1

            return round(supported / len(claims[:12]), 4)
        else:
            # Fallback: token overlap
            corpus = " ".join(contexts).lower()
            supported = 0
            for claim in claims:
                tokens = [t.lower() for t in re.findall(r"\w+", claim) if len(t) > 3]
                if not tokens:
                    supported += 1
                    continue
                matches = sum(1 for t in tokens if t in corpus)
                if matches / len(tokens) >= 0.35:
                    supported += 1
            return round(supported / len(claims), 4)

    # ---- 2. Answer Relevance (Embedding) -----------------------------------
    def evaluate_answer_relevance(self, query: str, response: str) -> float:
        """Embedding-based semantic similarity between query and response."""
        if not query or not response:
            return 0.0
        q_vec = self.embeddings.encode(query, normalize_embeddings=True)
        r_vec = self.embeddings.encode(response, normalize_embeddings=True)
        sim = self._cosine_sim(q_vec, r_vec)
        return round(max(0.0, min(1.0, (sim + 1.0) / 2.0)), 4)

    # ---- 3. Context Precision (Embedding) ----------------------------------
    def evaluate_context_precision(self, query: str, contexts: List[str]) -> float:
        """Average precision of relevant context chunks at each rank position."""
        if not query or not contexts:
            return 0.0
        q_vec = self.embeddings.encode(query, normalize_embeddings=True)
        precisions = []
        relevant_count = 0
        for k, ctx in enumerate(contexts, start=1):
            ctx_vec = self.embeddings.encode(ctx, normalize_embeddings=True)
            sim = self._cosine_sim(q_vec, ctx_vec)
            if sim >= 0.30:
                relevant_count += 1
                precisions.append(relevant_count / k)
        return round(float(np.mean(precisions)), 4) if precisions else 0.0

    # ---- 4. Context Recall -------------------------------------------------
    def evaluate_context_recall(self, response: str, contexts: List[str]) -> float:
        """Measures how many response facts are covered by the context.
        Uses the response as proxy ground truth when no explicit GT is given."""
        if not response or not contexts:
            return 1.0
        corpus = " ".join(contexts).lower()
        facts = [f.strip() for f in re.split(r"[.\n;]", response) if len(f.strip()) > 8]
        if not facts:
            return 1.0
        recalled = 0
        for fact in facts:
            tokens = [t.lower() for t in re.findall(r"\w+", fact) if len(t) > 3]
            if not tokens:
                recalled += 1
                continue
            matches = sum(1 for t in tokens if t in corpus)
            if matches / len(tokens) >= 0.30:
                recalled += 1
        return round(recalled / len(facts), 4)

    # ---- 5. Answer Correctness (LLM-as-Judge, optional) --------------------
    def evaluate_answer_correctness(self, query: str, response: str,
                                     contexts: List[str]) -> float:
        """LLM judges overall answer quality on a 1-5 scale."""
        if not self.use_llm_judge:
            return -1.0  # Skip if no Ollama

        context_text = "\n".join(contexts)[:3000]
        prompt = (
            "You are an evaluation judge. Rate the following answer on a scale of 1 to 5.\n"
            "1 = Completely wrong, 2 = Mostly wrong, 3 = Partially correct, "
            "4 = Mostly correct, 5 = Fully correct and complete.\n\n"
            f"QUESTION: {query}\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"ANSWER:\n{response[:1500]}\n\n"
            "Respond with ONLY a single number (1-5):"
        )
        result = _ollama_judge(prompt, model=self.ollama_model)
        # Parse the number
        nums = re.findall(r"[1-5]", result)
        if nums:
            return round(int(nums[0]) / 5.0, 4)
        return -1.0

    # ---- Full evaluation ---------------------------------------------------
    def evaluate_sample(self, query: str, response: str, contexts: List[str],
                        ground_truth: Optional[str] = None) -> Dict[str, Any]:
        """Runs all RAGAS metrics on a single sample."""
        faithfulness     = self.evaluate_faithfulness(response, contexts)
        answer_relevance = self.evaluate_answer_relevance(query, response)
        context_precision = self.evaluate_context_precision(query, contexts)
        context_recall   = self.evaluate_context_recall(response, contexts)

        # Optional LLM-judge correctness
        answer_correctness = self.evaluate_answer_correctness(query, response, contexts)

        metrics = [faithfulness, answer_relevance, context_precision, context_recall]
        ragas_score = round(float(np.mean(metrics)), 4)

        result = {
            "ragas_score": ragas_score,
            "metrics": {
                "faithfulness": faithfulness,
                "answer_relevance": answer_relevance,
                "context_precision": context_precision,
                "context_recall": context_recall,
            },
            "sample_details": {
                "query": query,
                "context_count": len(contexts),
                "response_length": len(response),
                "llm_judge": self.use_llm_judge,
            },
        }

        if answer_correctness >= 0:
            result["metrics"]["answer_correctness"] = answer_correctness

        return result


if __name__ == "__main__":
    query = "internet not working after recharge"
    contexts = [
        "Customer complaint: Mobile broadband internet access stopped working right after plan renewal.",
        "SOP Resolution: Verify network status, push OTA profile update, resolve within 24 hours.",
    ]
    response = (
        "We apologize for the issue. An OTA network profile update is being pushed. "
        "Service will resume within 24 hours."
    )

    evaluator = RAGASEvaluator()
    results = evaluator.evaluate_sample(query, response, contexts)

    print("\n=== RAGAS FRAMEWORK EVALUATION ===")
    print(f"LLM Judge Active   : {results['sample_details']['llm_judge']}")
    print(f"RAGAS Score        : {results['ragas_score']}")
    print(f"Faithfulness       : {results['metrics']['faithfulness']}")
    print(f"Answer Relevance   : {results['metrics']['answer_relevance']}")
    print(f"Context Precision  : {results['metrics']['context_precision']}")
    print(f"Context Recall     : {results['metrics']['context_recall']}")
    if "answer_correctness" in results["metrics"]:
        print(f"Answer Correctness : {results['metrics']['answer_correctness']}")
