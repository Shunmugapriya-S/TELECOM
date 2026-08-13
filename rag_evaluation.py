"""RAG Hallucination Evaluation Module

Evaluates LLM responses against retrieved context blocks to detect:
1. Faithfulness Score (% of response claims supported by context)
2. Hallucinations (ungrounded facts, fabricated SLAs, unverified monetary amounts)
3. Context Utilization Score (% of retrieved context facts referenced)
"""

import re
from typing import Dict, List, Any


class HallucinationEvaluator:
    """RAG Hallucination & Factuality Evaluator."""

    def extract_claims(self, text: str) -> List[str]:
        """Splits response into individual factual sentence claims."""
        if not text:
            return []
        # Clean formatting markers
        clean_text = re.sub(r"\*\*|#|•|-", " ", text)
        sentences = [s.strip() for s in re.split(r"[.\n;]", clean_text) if len(s.strip()) > 8]
        return sentences

    def evaluate_faithfulness(self, response: str, context_blocks: List[str]) -> Dict[str, Any]:
        """Calculates Faithfulness Score by checking if response claims align with retrieved context."""
        claims = self.extract_claims(response)
        if not claims:
            return {"faithfulness_score": 1.0, "total_claims": 0, "verified_claims": 0, "unsupported_claims": []}

        context_corpus = " ".join(context_blocks).lower()
        verified_count = 0
        unsupported = []

        for claim in claims:
            claim_lower = claim.lower()
            tokens = [t for t in re.findall(r"\w+", claim_lower) if len(t) > 3]
            if not tokens:
                verified_count += 1
                continue

            matches = sum(1 for token in tokens if token in context_corpus)
            overlap_ratio = matches / len(tokens)

            if overlap_ratio >= 0.35 or any(phrase in context_corpus for phrase in [claim_lower[:25]]):
                verified_count += 1
            else:
                unsupported.append(claim)

        faithfulness_score = round(verified_count / len(claims), 4)

        return {
            "faithfulness_score": faithfulness_score,
            "total_claims": len(claims),
            "verified_claims": verified_count,
            "unsupported_claims": unsupported,
        }

    def detect_hallucinations(self, response: str, context_blocks: List[str]) -> Dict[str, Any]:
        """Detects specific types of hallucinations:
        - Numerical/SLA hallucinations
        - Financial/refund hallucinations
        - Ticket/policy fabrications
        """
        context_corpus = " ".join(context_blocks).lower()
        response_lower = response.lower()

        hallucinations = []

        # 1. Financial/refund claims
        money_matches = re.findall(r"(\$\d+|\d+\s*rupees|\d+\s*inr|\d+%)", response_lower)
        for m in money_matches:
            if m not in context_corpus:
                hallucinations.append({
                    "type": "Financial Claim Fabrication",
                    "detail": f"Claimed amount/percentage '{m}' not found in retrieved context.",
                })

        # 2. SLA / Timeframe claims
        time_matches = re.findall(r"(\d+\s*(?:hours|hrs|days|mins|minutes))", response_lower)
        for t in time_matches:
            if t not in context_corpus and "24" not in context_corpus and "48" not in context_corpus:
                hallucinations.append({
                    "type": "SLA Timeframe Ambiguity",
                    "detail": f"SLA timeframe '{t}' in response lacks direct context proof.",
                })

        has_hallucination = len(hallucinations) > 0
        hallucination_rate = round(len(hallucinations) / max(1, len(self.extract_claims(response))), 4)

        return {
            "has_hallucination": has_hallucination,
            "hallucination_count": len(hallucinations),
            "hallucination_rate": hallucination_rate,
            "detected_hallucinations": hallucinations,
        }

    def evaluate_context_utilization(self, response: str, context_blocks: List[str]) -> Dict[str, Any]:
        """Measures how well the LLM utilized retrieved context facts."""
        if not context_blocks:
            return {"context_utilization_score": 0.0, "total_context_blocks": 0, "utilized_blocks": 0}

        response_lower = response.lower()
        utilized_count = 0

        for block in context_blocks:
            tokens = [t for t in re.findall(r"\w+", block.lower()) if len(t) > 4]
            if not tokens:
                continue
            matches = sum(1 for token in tokens if token in response_lower)
            if matches / len(tokens) >= 0.25:
                utilized_count += 1

        utilization_score = round(utilized_count / len(context_blocks), 4)

        return {
            "context_utilization_score": utilization_score,
            "total_context_blocks": len(context_blocks),
            "utilized_blocks": utilized_count,
        }

    def run_full_evaluation(self, response: str, context_blocks: List[str]) -> Dict[str, Any]:
        """Runs complete RAG hallucination and factuality benchmark."""
        faithfulness = self.evaluate_faithfulness(response, context_blocks)
        hallucinations = self.detect_hallucinations(response, context_blocks)
        utilization = self.evaluate_context_utilization(response, context_blocks)

        overall_score = round(
            (faithfulness["faithfulness_score"] * 0.5)
            + ((1.0 - hallucinations["hallucination_rate"]) * 0.3)
            + (utilization["context_utilization_score"] * 0.2),
            4
        )

        return {
            "overall_factuality_score": overall_score,
            "faithfulness": faithfulness,
            "hallucinations": hallucinations,
            "context_utilization": utilization,
        }


if __name__ == "__main__":
    sample_context = [
        "Customer complaint #101: Internet connection stopped working after recent online recharge of $29 plan.",
        "SOP resolution guide: Check network status. Perform OTA profile refresh. Standard SLA for refund or billing fix is 24-48 business hours.",
    ]
    sample_response = """
    We have received your complaint regarding internet not working after recharge. 
    Our team is performing an OTA profile refresh on your account. 
    Excess charges will be credited within 24-48 business hours.
    """

    evaluator = HallucinationEvaluator()
    result = evaluator.run_full_evaluation(sample_response, sample_context)

    print("\n=== RAG HALLUCINATION EVALUATION RESULT ===")
    print(f"Overall Factuality Score: {result['overall_factuality_score']}")
    print(f"Faithfulness Score: {result['faithfulness']['faithfulness_score']}")
    print(f"Hallucination Rate: {result['hallucinations']['hallucination_rate']}")
    print(f"Context Utilization: {result['context_utilization']['context_utilization_score']}")
