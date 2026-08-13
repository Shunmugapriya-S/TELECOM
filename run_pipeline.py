"""
RAG AI Pipeline - Interactive Testing Layer
============================================
Complete end-to-end interactive testing:
  - User input -> chunking -> embedding -> KB retrieval -> LoRA fine-tuned LLM (or Gemini fallback)
  - Input token count, output token count
  - LLM response
  - Hallucination rate + RAGAS evaluation

Usage:
    python run_pipeline.py                   # interactive mode
    python run_pipeline.py --query "..."     # single-query mode
    python run_pipeline.py --benchmark       # run benchmark on multiple test queries
"""

import os
import sys
import re
import time
import argparse
from pathlib import Path
from typing import Dict, Any

# ---- Force UTF-8 output on Windows (fixes cp1252 encoding errors) -----------
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---- Workspace root on sys.path --------------------------------------------
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

# Suppress LangSmith tracing (avoids 403 errors)
os.environ["LANGSMITH_TRACING"] = "false"

# ---- Suppress noisy INFO logs so pipeline output is clearly visible ----------
import logging
for _noisy in ("httpx", "pinecone", "faiss", "sentence_transformers",
               "google_genai", "google_genai.models", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# ---- Core imports ----------------------------------------------------------
from rag_engine.orchestration import Orchestrator
from rag_engine.rag_evaluation import HallucinationEvaluator
from rag_engine.ragas_eval import RAGASEvaluator

try:
    import tiktoken
    _ENCODER = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(_ENCODER.encode(text))
except Exception:
    def count_tokens(text: str) -> int:
        return max(1, int(len(text.split()) * 1.3))

# ---- Display helpers -------------------------------------------------------
LINE = "=" * 70
SEP  = "-" * 70


def safe_print(text: str) -> None:
    """Print text safely, replacing unencodable characters instead of crashing."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        # Fallback: encode to current stdout encoding replacing unknown chars
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe, flush=True)


def strip_markdown(text: str) -> str:
    """Convert markdown bold/italic to plain text for clean terminal display."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **bold** -> bold
    text = re.sub(r"\*(.+?)\*",   r"\1", text)   # *italic* -> italic
    text = re.sub(r"#{1,6}\s+",   "",    text)   # ## headings -> plain
    return text


def print_header(title: str) -> None:
    safe_print(f"\n{LINE}")
    safe_print(f"  {title}")
    safe_print(LINE)


def print_section(label: str, content: str) -> None:
    safe_print(f"\n{SEP}")
    safe_print(f"  {label}")
    safe_print(SEP)
    # Strip markdown so bold markers don't cause cp1252 issues
    clean = strip_markdown(content)
    safe_print(clean)
    sys.stdout.flush()


def token_stats(prompt: str, response: str) -> Dict[str, int]:
    inp = count_tokens(prompt)
    out = count_tokens(response)
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}


def print_eval_results(tokens: dict, halluc: dict, ragas: dict) -> None:
    print_header("[EVALUATION REPORT]")

    # --- Token usage
    safe_print("\n  [TOKEN USAGE]")
    safe_print(f"    Input Tokens   : {tokens['input_tokens']}")
    safe_print(f"    Output Tokens  : {tokens['output_tokens']}")
    safe_print(f"    Total Tokens   : {tokens['total_tokens']}")

    # --- Hallucination
    h = halluc
    faith = h["faithfulness"]["faithfulness_score"]
    hrate = h["hallucinations"]["hallucination_rate"]
    util  = h["context_utilization"]["context_utilization_score"]

    safe_print("\n  [HALLUCINATION EVALUATION]")
    safe_print(f"    Faithfulness Score     : {faith:.4f}  [{'GOOD' if faith >= 0.7 else 'LOW'}]")
    safe_print(f"    Hallucination Rate     : {hrate:.4f}  [{'CLEAN' if hrate == 0 else 'DETECTED'}]")
    safe_print(f"    Context Utilization    : {util:.4f}  [{'HIGH' if util >= 0.5 else 'LOW'}]")
    safe_print(f"    Overall Factuality     : {h['overall_factuality_score']:.4f}")

    if h["hallucinations"]["detected_hallucinations"]:
        safe_print("\n    [!] Detected Hallucinations:")
        for issue in h["hallucinations"]["detected_hallucinations"]:
            safe_print(f"        [{issue['type']}] {issue['detail']}")

    # --- RAGAS
    r = ragas
    rs = r["ragas_score"]
    grade = "PASS" if rs >= 0.7 else "MODERATE" if rs >= 0.5 else "FAIL"
    safe_print("\n  [RAGAS PERFORMANCE METRICS]")
    safe_print(f"    Faithfulness       : {r['metrics']['faithfulness']:.4f}")
    safe_print(f"    Answer Relevance   : {r['metrics']['answer_relevance']:.4f}")
    safe_print(f"    Context Precision  : {r['metrics']['context_precision']:.4f}")
    safe_print(f"    Context Recall     : {r['metrics']['context_recall']:.4f}")
    safe_print(f"    {'-' * 35}")
    safe_print(f"    RAGAS Score        : {rs:.4f}  [{grade}]")
    safe_print("")
    sys.stdout.flush()


# ---- Single query runner ---------------------------------------------------
def run_single_query(
    orchestrator: Orchestrator,
    halluc_eval: HallucinationEvaluator,
    ragas_eval: RAGASEvaluator,
    query: str,
    strategy: str = "semantic",
    use_local: bool = True,
    top_k: int = 5,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Full RAG pipeline: retrieve -> prompt -> LLM -> evaluate."""

    if verbose:
        print_header("[RAG AI PIPELINE] Processing Query")
        safe_print(f"\n  USER QUERY : {query}")
        safe_print(f"  Strategy   : {strategy} | Top-K: {top_k} | Local LLM: {use_local}")
        sys.stdout.flush()

    t0 = time.time()
    pipeline_out = orchestrator.run_pipeline(
        query=query,
        strategy=strategy,
        use_local=use_local,
        top_k=top_k,
    )
    elapsed = round(time.time() - t0, 2)

    response    = pipeline_out["response"]
    full_prompt = pipeline_out["full_prompt"]
    chunks      = pipeline_out["chunks"]
    llm_source  = pipeline_out["llm_source"]
    chunk_texts = [
        c.get("chunk", {}).get("text", "")
        for c in chunks
        if c.get("chunk", {}).get("text")
    ]

    if verbose:
        safe_print(f"\n  Completed in {elapsed}s  |  LLM: {llm_source}")
        safe_print(f"  Retrieved {len(chunks)} context chunks from knowledge base.")
        sys.stdout.flush()

    tokens = token_stats(full_prompt, response)

    # ---- ALWAYS print the LLM response  ------------------------------------
    if verbose:
        # Strip any markdown bold/heading markers that could break cp1252
        display_response = strip_markdown(response) if response else "[No response generated]"
        safe_print(f"\n{SEP}")
        safe_print("  [LLM RESPONSE]")
        safe_print(SEP)
        safe_print(display_response)
        safe_print(SEP)
        sys.stdout.flush()

    halluc_result = halluc_eval.run_full_evaluation(response, chunk_texts)
    ragas_result  = ragas_eval.evaluate_sample(query, response, chunk_texts)

    if verbose:
        print_eval_results(tokens, halluc_result, ragas_result)

    return {
        "query":              query,
        "response":           response,
        "llm_source":         llm_source,
        "elapsed_sec":        elapsed,
        "tokens":             tokens,
        "hallucination_eval": halluc_result,
        "ragas_eval":         ragas_result,
        "chunks_count":       len(chunks),
    }


# ---- Benchmark mode --------------------------------------------------------
BENCHMARK_QUERIES = [
    "internet not working after recharge",
    "billing issue and duplicate charge on my account",
    "network signal dropped after recent plan change",
    "SIM activation pending for 3 days",
    "refund not received for failed transaction",
]


def run_benchmark(
    orchestrator, halluc_eval, ragas_eval,
    strategy="semantic", use_local=True,
) -> None:
    print_header("[BENCHMARK MODE] Telecom RAG Evaluation Suite")

    results = []
    for i, q in enumerate(BENCHMARK_QUERIES, 1):
        print(f"\n[{i}/{len(BENCHMARK_QUERIES)}] {q}")
        r = run_single_query(
            orchestrator, halluc_eval, ragas_eval,
            query=q, strategy=strategy, use_local=use_local, verbose=False,
        )
        results.append(r)
        print(
            f"  RAGAS: {r['ragas_eval']['ragas_score']:.4f}  "
            f"Faith: {r['hallucination_eval']['faithfulness']['faithfulness_score']:.4f}  "
            f"Halluc: {r['hallucination_eval']['hallucinations']['hallucination_rate']:.4f}  "
            f"Tokens in/out: {r['tokens']['input_tokens']}/{r['tokens']['output_tokens']}  "
            f"Time: {r['elapsed_sec']}s"
        )

    n = len(results)
    print_header("[BENCHMARK SUMMARY]")
    print(f"  Queries tested         : {n}")
    print(f"  Avg RAGAS Score        : {round(sum(r['ragas_eval']['ragas_score'] for r in results)/n, 4)}")
    print(f"  Avg Faithfulness       : {round(sum(r['hallucination_eval']['faithfulness']['faithfulness_score'] for r in results)/n, 4)}")
    print(f"  Avg Hallucination Rate : {round(sum(r['hallucination_eval']['hallucinations']['hallucination_rate'] for r in results)/n, 4)}")
    print(f"  Avg Input Tokens       : {int(sum(r['tokens']['input_tokens'] for r in results)/n)}")
    print(f"  Avg Output Tokens      : {int(sum(r['tokens']['output_tokens'] for r in results)/n)}")
    print(f"  Avg Response Time      : {round(sum(r['elapsed_sec'] for r in results)/n, 2)}s")
    print()


# ---- Interactive loop -------------------------------------------------------
def interactive_loop(
    orchestrator, halluc_eval, ragas_eval,
    strategy, use_local, top_k,
) -> None:
    print_header("[INTERACTIVE MODE] RAG AI Pipeline")
    print("  Enter your query and press ENTER to run the full pipeline.")
    print("  Type 'exit' or 'quit' to stop.")

    while True:
        print(f"\n{SEP}")
        try:
            user_input = input("  Enter your query: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Exiting. Goodbye!")
            break

        if not user_input:
            print("  [!] Empty query. Please enter a valid question.")
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("  Exiting. Goodbye!")
            break

        run_single_query(
            orchestrator, halluc_eval, ragas_eval,
            query=user_input, strategy=strategy,
            use_local=use_local, top_k=top_k, verbose=True,
        )


# ---- Entry point ------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="RAG AI Pipeline Interactive Testing Layer")
    ap.add_argument("--query",     "-q", default=None,
                    help="Run a single query non-interactively")
    ap.add_argument("--strategy",  "-s", default="semantic",
                    choices=["semantic", "hybrid", "relevant"])
    ap.add_argument("--top_k",          type=int, default=5,
                    help="Context chunks to retrieve")
    ap.add_argument("--no_local",       dest="use_local", action="store_false",
                    default=True,
                    help="Use Gemini / synthesis instead of local LoRA model")
    ap.add_argument("--benchmark", "-b", action="store_true",
                    help="Run benchmark evaluation on the standard test set")
    args = ap.parse_args()

    print_header("[INIT] RAG AI Pipeline — Loading Components...")
    print("  Loading: Pinecone | FAISS | EmbeddingsEngine | LLM | Evaluators...")
    orchestrator = Orchestrator()
    halluc_eval  = HallucinationEvaluator()
    ragas_eval   = RAGASEvaluator()
    print("  All pipeline components ready.\n")

    if args.benchmark:
        run_benchmark(orchestrator, halluc_eval, ragas_eval,
                      strategy=args.strategy, use_local=args.use_local)
    elif args.query:
        run_single_query(
            orchestrator, halluc_eval, ragas_eval,
            query=args.query, strategy=args.strategy,
            use_local=args.use_local, top_k=args.top_k, verbose=True,
        )
    else:
        interactive_loop(
            orchestrator, halluc_eval, ragas_eval,
            strategy=args.strategy, use_local=args.use_local, top_k=args.top_k,
        )


if __name__ == "__main__":
    main()
