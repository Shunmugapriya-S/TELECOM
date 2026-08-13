from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")


class HistoryMerger:
    """Consolidates complaint and customer history into a single structured view."""

    def merge(self, chunks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        customer_history: List[str] = []
        complaint_history: List[str] = []
        confirmed_facts: List[str] = []
        unknowns: List[str] = []

        for item in chunks:
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if not text:
                continue

            if metadata.get("customer_id") or "customer" in text.lower():
                customer_history.append(text)
            if metadata.get("complaint_id") or "complaint" in text.lower() or "ticket" in text.lower():
                complaint_history.append(text)

            if "verified" in text.lower() or "confirmed" in text.lower() or "status" in text.lower():
                confirmed_facts.append(text)
            if "unknown" in text.lower() or "pending" in text.lower() or "not verified" in text.lower() or "unclear" in text.lower():
                unknowns.append(text)

        return {
            "customer_history": customer_history[:5],
            "complaint_history": complaint_history[:5],
            "confirmed_facts": confirmed_facts[:5],
            "unknowns": unknowns[:5],
        }


class TemporalScorer:
    """Stricter temporal scoring for distinguishing present vs historical telecom facts."""

    PRESENT_MARKERS = [
        "today", "now", "currently", "currently active", "ongoing", "recently", "this week", "in progress",
        "after recharge", "after payment", "since", "within 24 hours", "immediately", "this month"
    ]
    PAST_MARKERS = [
        "previously", "earlier", "before", "last week", "last month", "before this", "historical", "old issue",
        "was reported", "had issue", "was resolved", "previous complaint", "earlier this month"
    ]
    UNKNOWN_MARKERS = ["unknown", "unclear", "not verified", "pending", "awaiting", "not available", "tbd"]

    def score(self, text: str) -> Dict[str, float]:
        normalized = text.lower()
        presence = 0.0
        history = 0.0
        unknown = 0.0

        for marker in self.PRESENT_MARKERS:
            if marker in normalized:
                presence += 0.25
        for marker in self.PAST_MARKERS:
            if marker in normalized:
                history += 0.25
        for marker in self.UNKNOWN_MARKERS:
            if marker in normalized:
                unknown += 0.25

        if "status" in normalized and "resolved" in normalized:
            presence += 0.15
        if "was" in normalized and "issue" in normalized:
            history += 0.2

        total = max(1.0, presence + history + unknown)
        return {
            "present_score": round(min(1.0, presence / total), 3),
            "past_score": round(min(1.0, history / total), 3),
            "unknown_score": round(min(1.0, unknown / total), 3),
        }


class RerankLayer:
    """Requirement-aware reranking for telecom RAG context."""

    REQUIREMENT_KEYS = [
        "Retrieved knowledge",
        "Customer history",
        "Complaint history",
        "Temporal context",
        "Confirmed facts",
        "Possible subtext",
        "Unknown information",
        "Business rules",
        "Required action",
    ]

    def __init__(self):
        self.keyword_map = {
            "Retrieved knowledge": ["network", "signal", "internet", "billing", "recharge", "plan", "service", "error", "issue"],
            "Customer history": ["customer", "account", "plan", "subscription", "mobile", "usage", "history"],
            "Complaint history": ["complaint", "ticket", "previous issue", "prior case", "past complaint", "reported before"],
            "Temporal context": ["today", "yesterday", "last week", "since", "after", "before", "recent", "now", "hours", "days"],
            "Confirmed facts": ["confirmed", "verified", "active", "resolved", "status", "completed", "updated"],
            "Possible subtext": ["frustrated", "angry", "upset", "dissatisfied", "annoyed", "concerned", "urgent"],
            "Unknown information": ["unknown", "missing", "pending", "not verified", "unclear", "awaiting", "not available"],
            "Business rules": ["sla", "policy", "refund", "credit", "chargeback", "guarantee", "tariff", "terms"],
            "Required action": ["action required", "escalate", "callback", "verify", "refresh", "resolve", "credit", "retry", "investigate"],
        }
        self.temporal_scorer = TemporalScorer()
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_chain = self._init_gemini_rerank_chain()

    def _init_gemini_rerank_chain(self):
        if not self.gemini_api_key:
            return None

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.output_parsers import JsonOutputParser
            from langchain_core.prompts import ChatPromptTemplate

            model = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=self.gemini_api_key,
                temperature=0.1,
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are a telecom case-ranking expert. Rank the candidate knowledge blocks for a customer support query. "
                 "Return valid JSON only with keys: 'ranked' as a list of objects in priority order. "
                 "Each object must contain: 'text', 'rerank_score', 'requirement_scores' where requirement_scores is an object keyed by the exact requirement names: "
                 "Retrieved knowledge, Customer history, Complaint history, Temporal context, Confirmed facts, Possible subtext, Unknown information, Business rules, Required action. "
                 "Use a 0.0 to 1.0 scale. Keep text as the exact chunk text from the input."
                 ),
                ("human", "Query:\n{query}\n\nCandidates:\n{candidates}")
            ])

            return prompt | model | JsonOutputParser()
        except Exception:
            return None

    def _score_chunk(self, text: str, metadata: Dict[str, Any]) -> Dict[str, float]:
        normalized = text.lower()
        scores = {key: 0.0 for key in self.REQUIREMENT_KEYS}

        for key, words in self.keyword_map.items():
            matches = sum(1 for word in words if word in normalized)
            if matches:
                scores[key] = min(1.0, 0.25 + (matches * 0.15))

        if metadata.get("customer_id") or "customer" in normalized:
            scores["Customer history"] += 0.3
        if metadata.get("complaint_id") or "complaint" in normalized or "ticket" in normalized:
            scores["Complaint history"] += 0.4
        if metadata.get("priority") or "priority" in normalized:
            scores["Required action"] += 0.2
        if metadata.get("sentiment") or any(word in normalized for word in ["frustrated", "angry", "upset"]):
            scores["Possible subtext"] += 0.2
        if metadata.get("raw_text") or "status" in normalized:
            scores["Confirmed facts"] += 0.2
        if metadata.get("doc_type") == "telecom_sop":
            scores["Business rules"] += 0.3
            scores["Retrieved knowledge"] += 0.2

        temporal = self.temporal_scorer.score(text)
        scores["Temporal context"] = max(scores["Temporal context"], temporal["present_score"], temporal["past_score"])
        if temporal["unknown_score"] > 0.0:
            scores["Unknown information"] = max(scores["Unknown information"], temporal["unknown_score"])

        return {k: round(min(1.0, v), 3) for k, v in scores.items()}

    def _gemini_rerank(self, search_results: Iterable[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        items = list(search_results or [])
        if not items or self.gemini_chain is None:
            return []

        payload = []
        for idx, res in enumerate(items[:8], start=1):
            chunk = res.get("chunk", {}) if isinstance(res, dict) else {}
            text = str(chunk.get("text") or chunk.get("raw_text") or "").strip()
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            if not text:
                continue
            payload.append({
                "index": idx,
                "text": text,
                "metadata": metadata,
                "score": float(res.get("score", 0.0)) if isinstance(res, dict) else 0.0,
            })

        if not payload:
            return []

        try:
            response = self.gemini_chain.invoke({
                "query": query,
                "candidates": json.dumps(payload, ensure_ascii=False),
            })
            ranked_items = response.get("ranked", []) if isinstance(response, dict) else []
            cleaned: List[Dict[str, Any]] = []

            for item in ranked_items:
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                req_scores = item.get("requirement_scores", {}) or {}
                cleaned.append({
                    "text": text,
                    "metadata": {},
                    "score": float(item.get("score", 0.0) or 0.0),
                    "rerank_score": float(item.get("rerank_score", 0.0) or 0.0),
                    "requirement_scores": {k: float(v) for k, v in req_scores.items() if isinstance(v, (int, float))},
                })

            if cleaned:
                return cleaned
        except Exception:
            pass

        return []

    def rerank(self, search_results: Iterable[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        gemini_ranked = self._gemini_rerank(search_results, query)
        if gemini_ranked:
            return gemini_ranked

        ranked: List[Dict[str, Any]] = []
        for res in search_results or []:
            chunk = res.get("chunk", {}) if isinstance(res, dict) else {}
            text = str(chunk.get("text") or chunk.get("raw_text") or "").strip()
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            score = float(res.get("score", 0.0)) if isinstance(res, dict) else 0.0

            if not text:
                continue

            requirement_scores = self._score_chunk(text, metadata)
            composite_score = score + sum(requirement_scores.values()) / len(requirement_scores)

            ranked.append({
                "text": text,
                "metadata": metadata or {},
                "score": score,
                "rerank_score": round(composite_score, 4),
                "requirement_scores": requirement_scores,
            })

        return sorted(ranked, key=lambda x: x["rerank_score"], reverse=True)


class ContextEngineer:
    """Context engineering layer for RAG retrieval and prompt construction."""

    def __init__(self, max_context_chars: int = 4000, max_chunks: int = 5, min_score: float = 0.0):
        self.max_context_chars = max_context_chars
        self.max_chunks = max_chunks
        self.min_score = min_score
        self.rerank_layer = RerankLayer()
        self.history_merger = HistoryMerger()

    def normalize_results(self, search_results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for res in search_results or []:
            chunk = res.get("chunk", {}) if isinstance(res, dict) else {}
            text = str(chunk.get("text") or chunk.get("raw_text") or "").strip()
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            score = float(res.get("score", 0.0)) if isinstance(res, dict) else 0.0

            if not text:
                continue

            normalized.append({
                "text": text,
                "metadata": metadata or {},
                "score": score,
            })
        return sorted(normalized, key=lambda x: x["score"], reverse=True)

    def deduplicate(self, chunks: List[Dict[str, Any]], similarity_threshold: float = 0.80) -> List[Dict[str, Any]]:
        unique: List[Dict[str, Any]] = []

        for chunk in chunks:
            text = chunk["text"]
            duplicate = False
            for kept in unique:
                if self._text_similarity(text, kept["text"]) >= similarity_threshold:
                    duplicate = True
                    break
            if not duplicate:
                unique.append(chunk)

        return unique

    def _text_similarity(self, a: str, b: str) -> float:
        a_tokens = set(re.findall(r"\w+", a.lower()))
        b_tokens = set(re.findall(r"\w+", b.lower()))
        if not a_tokens or not b_tokens:
            return 0.0
        overlap = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return overlap / union if union else 0.0

    def rank_context(self, search_results: Iterable[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
        normalized = self.normalize_results(search_results)
        filtered = [item for item in normalized if item["score"] >= self.min_score]
        deduped = self.deduplicate(filtered)
        reranked = self.rerank_layer.rerank([{"chunk": item, "score": item["score"]} for item in deduped], query)
        return reranked[: self.max_chunks]

    def merge_customer_and_complaint_history(self, search_results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        context_items = []
        for res in search_results or []:
            chunk = res.get("chunk", {}) if isinstance(res, dict) else {}
            context_items.append({
                "text": str(chunk.get("text") or chunk.get("raw_text") or "").strip(),
                "metadata": chunk.get("metadata", {}) if isinstance(chunk, dict) else {},
            })
        return self.history_merger.merge(context_items)

    def compress_context(self, chunks: List[Dict[str, Any]]) -> str:
        blocks: List[str] = []
        used_chars = 0

        for item in chunks:
            text = item["text"].strip()
            metadata = item.get("metadata", {})
            source = metadata.get("source_type") or metadata.get("doc_type") or "document"
            score = item.get("rerank_score", item.get("score", 0.0))

            snippet = text
            if len(snippet) > 700:
                snippet = snippet[:700].rsplit(" ", 1)[0] + "..."

            block = (
                f"[Source: {source} | Relevance: {score:.3f}]\n"
                f"{snippet}\n"
            )

            if used_chars + len(block) > self.max_context_chars:
                break
            blocks.append(block)
            used_chars += len(block)

        return "\n".join(blocks)

    def build_requirement_aware_context(self, search_results: Iterable[Dict[str, Any]], user_query: str = "") -> Dict[str, List[str]]:
        ranked = self.rank_context(search_results, user_query)
        sections = {key: [] for key in self.rerank_layer.REQUIREMENT_KEYS}

        for item in ranked:
            for key in self.rerank_layer.REQUIREMENT_KEYS:
                if item.get("requirement_scores", {}).get(key, 0.0) > 0.15:
                    sections[key].append(item["text"].strip())

        for key in sections:
            sections[key] = sections[key][:3]

        return sections

    def build_prompt(self, system_prompt: str, user_query: str, search_results: Iterable[Dict[str, Any]]) -> str:
        ranked = self.rank_context(search_results, user_query)
        sections = self.build_requirement_aware_context(ranked, user_query)
        context_block = self.compress_context(ranked)

        if not context_block.strip():
            context_block = "No relevant context retrieved. Answer using general telecom support knowledge."

        requirement_text = "\n".join(
            f"• {title}: {', '.join(items) if items else 'No direct evidence found.'}"
            for title, items in sections.items()
        )

        return (
            f"{system_prompt}\n\n"
            f"[RETRIEVED_CONTEXT]\n{context_block}\n\n"
            f"[REQUIREMENT_AWARE_CONTEXT]\n{requirement_text}\n\n"
            f"[USER_QUERY]\n{user_query}\n\n"
            f"Answer in a clear, support-focused manner, grounded in the retrieved context and explicitly covering the structured requirements above."
        )

    def build_context_summary(self, search_results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        ranked = self.rank_context(search_results)
        return {
            "total_chunks": len(ranked),
            "best_score": ranked[0]["rerank_score"] if ranked else 0.0,
            "context_text": self.compress_context(ranked),
            "requirement_scores": ranked[0].get("requirement_scores", {}) if ranked else {},
            "history_summary": self.merge_customer_and_complaint_history(ranked),
        }


context_engineer = ContextEngineer()
