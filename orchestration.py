from typing import List, Optional
import sys
import json
from pathlib import Path

# If this file is executed from inside the folder (python orchestration.py),
# ensure the workspace root is on sys.path so imports like `rag_engine.*` work.
try:
    from rag_engine.retriever import TelecomRAGRetriever
    from rag_engine.prompt_templates import (
        detect_language,
        build_system_prompt,
        build_user_prompt,
        format_context_blocks,
        build_full_prompt,
    )
    from rag_engine.ai_agents.LLM import TelecomLLMClient
except ModuleNotFoundError:
    workspace_root = Path(__file__).resolve().parents[0].parent
    sys.path.insert(0, str(workspace_root))
    from rag_engine.retriever import TelecomRAGRetriever
    from rag_engine.prompt_templates import (
        detect_language,
        build_system_prompt,
        build_user_prompt,
        format_context_blocks,
        build_full_prompt,
    )
    from rag_engine.ai_agents.LLM import TelecomLLMClient


# ---- Ollama client ---------------------------------------------------------
class OllamaClient:
    """Lightweight client for local Ollama models (REST API at localhost:11434)."""

    def __init__(self, model: str = "gemma3:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2,
                 max_tokens: int = 512) -> str:
        """Call Ollama /api/generate and return the full response text."""
        import urllib.request

        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip()

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        import urllib.request
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False


class Orchestrator:
    """Orchestration layer: semantic/hybrid/relevant search + prompt construction + LLM call.

    Supports three LLM backends:
      1. Local Ollama model (use_local=True) — default: gemma3:latest
      2. Remote Gemini via LangChain (use_local=False)
      3. Intelligent offline synthesis fallback
    """

    def __init__(self, ollama_model: str = "gemma3:latest"):
        self.retriever = TelecomRAGRetriever()
        self.gemini_client = TelecomLLMClient()
        self.ollama = OllamaClient(model=ollama_model)

    def semantic_search(self, query: str, top_k: int = 5) -> List[dict]:
        """Pure semantic (embedding) search using the vector store."""
        return self.retriever.retrieve(query, top_k=top_k)

    def relevant_search(self, query: str, top_k: int = 5) -> List[dict]:
        """Relevance-tuned search (uses retriever's reranking via ContextEngineer)."""
        raw = self.retriever.retrieve(query, top_k=top_k)
        return raw

    def hybrid_search(self, query: str, top_k: int = 8) -> List[dict]:
        """Hybrid search: combine semantic vector retrieval with lightweight keyword expansion."""
        semantic = self.retriever.retrieve(query, top_k=top_k)
        q_tokens = [t.lower() for t in query.split() if len(t) > 3]
        extra = []
        for candidate in semantic:
            text = candidate.get("chunk", {}).get("text", "")
            if any(tok in text.lower() for tok in q_tokens):
                extra.append(candidate)
        seen = set()
        merged = []
        for item in (semantic + extra):
            t = item.get("chunk", {}).get("text", "")
            if t and t not in seen:
                seen.add(t)
                merged.append(item)
        return merged[:top_k]

    def _prepare_prompt(self, query: str, chunks: List[dict]) -> (str, str, str):
        language = detect_language(query)
        system = build_system_prompt(language)
        user = build_user_prompt(query, language)
        context = format_context_blocks([c.get("chunk", {}) for c in chunks])
        full = build_full_prompt(system, context, user)
        return system, context, full

    def run_flow(self, query: str, strategy: str = "semantic", use_local: bool = True,
                 top_k: int = 5, **kwargs) -> str:
        """Execute the full orchestration: retrieve -> prompt -> LLM"""
        res = self.run_pipeline(
            query=query,
            strategy=strategy,
            use_local=use_local,
            top_k=top_k,
        )
        return res["response"]

    def run_pipeline(self, query: str, strategy: str = "semantic", use_local: bool = True,
                     top_k: int = 5, **kwargs) -> dict:
        """Executes orchestration returning structured pipeline dictionary."""
        if strategy == "semantic":
            chunks = self.semantic_search(query, top_k=top_k)
        elif strategy == "hybrid":
            chunks = self.hybrid_search(query, top_k=top_k)
        else:
            chunks = self.relevant_search(query, top_k=top_k)

        system_prompt, context_text, full_prompt = self._prepare_prompt(query, chunks)
        llm_source = ""

        response = ""
        if use_local:
            # ---- Try Ollama local model first ----
            try:
                if self.ollama.is_available():
                    print(f"Calling Ollama model '{self.ollama.model}'...")
                    response = self.ollama.generate(
                        prompt=full_prompt,
                        system=system_prompt,
                        temperature=0.2,
                        max_tokens=512,
                    )
                    llm_source = f"ollama_{self.ollama.model}"
                else:
                    raise ConnectionError("Ollama server not reachable at localhost:11434")
            except Exception as e:
                print(f"Ollama local model notice: {e}. Falling back to Gemini / synthesis.")
                response = self.gemini_client.generate_response(system_prompt, query, retrieved_context=context_text)
                llm_source = "gemini_client_fallback"
        else:
            response = self.gemini_client.generate_response(system_prompt, query, retrieved_context=context_text)
            llm_source = "gemini_client"

        return {
            "query": query,
            "strategy": strategy,
            "chunks": chunks,
            "system_prompt": system_prompt,
            "context_text": context_text,
            "full_prompt": full_prompt,
            "response": response,
            "llm_source": llm_source,
        }


# convenience
def orchestrate_query(query: str, **kwargs) -> str:
    orch = Orchestrator()
    return orch.run_flow(query, **kwargs)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run orchestration: retrieval + prompt + LLM")
    ap.add_argument("query", nargs='?', help="User query to run through orchestration (optional). If omitted, you'll be prompted.")
    ap.add_argument("--strategy", choices=["semantic", "hybrid", "relevant"], default="semantic")
    ap.add_argument("--no_local", dest="use_local", action="store_false", help="Use remote Gemini instead of local model")
    ap.add_argument("--base_model", default="ai_agents/gemma_3_lora/content/gemma_3_lora", help="Base model name or local path")
    ap.add_argument("--adapter_dir", default=None, help="Path to LoRA adapter folder (optional)")
    ap.add_argument("--top_k", type=int, default=5)
    args = ap.parse_args()

    if not args.query:
        try:
            args.query = input("Enter your query: ")
        except KeyboardInterrupt:
            print("\nNo query provided; exiting.")
            raise SystemExit(1)

    orch = Orchestrator()
    result = orch.run_flow(
        args.query,
        strategy=args.strategy,
        use_local=args.use_local,
        base_model=args.base_model,
        adapter_dir=args.adapter_dir,
        top_k=args.top_k,
    )

    print("\n=== ORCHESTRATION RESULT ===\n")
    print(result)
