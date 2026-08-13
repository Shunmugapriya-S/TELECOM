#!/usr/bin/env python3
"""
COMPREHENSIVE RAG SYSTEM TESTING & EVALUATION
Complete pipeline: Query → Retrieval → Generation → Evaluation → Root Cause Analysis
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json
from datetime import datetime

# Setup rag_engine package namespace dynamically
from types import ModuleType
if "rag_engine" not in sys.modules:
    root_dir = Path(__file__).resolve().parent
    while root_dir.parent != root_dir and not (root_dir / "requirements.txt").exists():
        root_dir = root_dir.parent
    m = ModuleType("rag_engine")
    m.__path__ = [str(root_dir)]
    sys.modules["rag_engine"] = m

from rag_engine.orchestration import Orchestrator
from rag_engine.rag_evaluation import HallucinationEvaluator
from rag_engine.prompt_templates import (
    detect_language,
    build_system_prompt,
    build_user_prompt,
    format_context_blocks,
    build_full_prompt,
)


class RootCauseAnalyzer:
    """Advanced root cause analysis for RAG system issues"""
    
    @staticmethod
    def analyze(query: str, retrieved_chunks: List[dict], response: str,
                evaluation_results: Dict) -> Dict:
        """
        Perform comprehensive root cause analysis
        """
        issues = []
        recommendations = []
        
        # Extract evaluation metrics
        faithfulness = evaluation_results.get("faithfulness", {})
        hallucinations = evaluation_results.get("hallucinations", {})
        utilization = evaluation_results.get("context_utilization", {})
        
        # ===== RETRIEVAL ANALYSIS =====
        if len(retrieved_chunks) < 3:
            issues.append({
                "component": "RETRIEVAL",
                "severity": "HIGH",
                "issue": "Insufficient retrieval - Less than 3 documents retrieved",
                "cause": "Query may be too specific or indexed documents don't match"
            })
            recommendations.append("Increase top_k parameter (try 8-10)")
            recommendations.append("Use hybrid search strategy combining semantic + keyword")
            recommendations.append("Review and expand document index")
        
        if utilization.get("context_utilization_score", 0) < 0.5:
            issues.append({
                "component": "RETRIEVAL",
                "severity": "MEDIUM",
                "issue": f"Low context utilization - Only {utilization.get('utilized_blocks', 0)}/{utilization.get('total_context_blocks', 1)} blocks used",
                "cause": "Retrieved documents may not be relevant to query"
            })
            recommendations.append("Consider using semantic reranking")
            recommendations.append("Check embedding model quality")
            recommendations.append("Verify vector store indexing completeness")
        
        # ===== HALLUCINATION ANALYSIS =====
        if hallucinations.get("has_hallucination", False):
            halluc_count = hallucinations.get("hallucination_count", 0)
            halluc_rate = hallucinations.get("hallucination_rate", 0)
            
            issues.append({
                "component": "LLM",
                "severity": "HIGH",
                "issue": f"Hallucinations detected - {halluc_count} ungrounded claims ({halluc_rate:.1%} rate)",
                "cause": "Model generated information not supported by context"
            })
            recommendations.append("Lower temperature parameter (0.1-0.3) for more deterministic responses")
            recommendations.append("Use greedy decoding (top_p=0.9, top_k=40)")
            recommendations.append("Add explicit prompt instruction: 'Only answer based on provided context'")
            recommendations.append("Increase max_length to allow model to be more thorough")
        
        # ===== FAITHFULNESS ANALYSIS =====
        faithfulness_score = faithfulness.get("faithfulness_score", 0)
        if faithfulness_score < 0.6:
            unsupported = faithfulness.get("unsupported_claims", [])
            issues.append({
                "component": "LLM",
                "severity": "MEDIUM",
                "issue": f"Low faithfulness - Score {faithfulness_score:.1%}, {len(unsupported)} unsupported claims",
                "cause": "LLM not properly grounding responses in retrieved context"
            })
            recommendations.append("Restructure prompt to emphasize context reliance")
            recommendations.append("Use chain-of-thought prompting: 'Based on context, ...'")
            recommendations.append("Verify fine-tuned model is properly loaded")
            recommendations.append("Consider fine-tuning model specifically for your domain")
        elif faithfulness_score >= 0.8:
            pass  # Good faithfulness
        
        # ===== RESPONSE QUALITY ANALYSIS =====
        response_length = len(response.split())
        if response_length < 20:
            issues.append({
                "component": "LLM",
                "severity": "MEDIUM",
                "issue": f"Response too brief ({response_length} words) - May indicate model uncertainty",
                "cause": "Model may not have sufficient context or is stopping prematurely"
            })
            recommendations.append("Increase max_new_tokens parameter")
            recommendations.append("Check if model is properly initialized")
            recommendations.append("Verify GPU/CPU memory is sufficient")
        elif response_length > 500:
            issues.append({
                "component": "LLM",
                "severity": "LOW",
                "issue": f"Response very long ({response_length} words) - May contain redundancy",
                "cause": "Model may be over-generating or repeating information"
            })
            recommendations.append("Reduce max_new_tokens")
            recommendations.append("Use beam search with smaller beam width")
        
        # ===== MODEL EVALUATION =====
        if hallucinations.get("hallucination_count", 0) > 3:
            issues.append({
                "component": "MODEL",
                "severity": "HIGH",
                "issue": "Fine-tuned model quality issues",
                "cause": "Model may need re-training or parameter adjustment"
            })
            recommendations.append("Review fine-tuning dataset quality")
            recommendations.append("Check LoRA adapter configuration (rank, alpha, dropout)")
            recommendations.append("Consider re-training with different hyperparameters")
            recommendations.append("Test with base model for comparison")
        
        return {
            "identified_issues": issues if issues else [{"component": "SYSTEM", "severity": "INFO", "issue": "No major issues detected", "cause": "N/A"}],
            "recommendations": recommendations if recommendations else ["System performing as expected"],
            "overall_health": "EXCELLENT" if len(issues) == 0 else "GOOD" if len(issues) == 1 else "NEEDS ATTENTION",
            "issue_count": len(issues)
        }


class ComprehensiveRAGTester:
    """Complete RAG testing framework"""
    
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.evaluator = HallucinationEvaluator()
        self.analyzer = RootCauseAnalyzer()
        self.test_history = []
    
    def run_complete_test(self, query: str, strategy: str = "semantic",
                         use_local: bool = True, verbose: bool = True) -> Dict:
        """
        Execute complete RAG pipeline with full evaluation
        """
        if verbose:
            print(f"\n{'='*100}")
            print(f"COMPREHENSIVE RAG TESTING - {strategy.upper()} STRATEGY")
            print(f"{'='*100}\n")
        
        test_result = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "strategy": strategy,
            "pipeline_stages": {}
        }
        
        # ===== STAGE 1: RETRIEVAL =====
        if verbose:
            print(f"[STAGE 1/4] RETRIEVAL (Strategy: {strategy})")
            print("-" * 100)
        
        try:
            if strategy == "semantic":
                retrieved = self.orchestrator.semantic_search(query, top_k=5)
            elif strategy == "hybrid":
                retrieved = self.orchestrator.hybrid_search(query, top_k=8)
            else:
                retrieved = self.orchestrator.relevant_search(query, top_k=5)
            
            context_texts = [c.get("chunk", {}).get("text", "") for c in retrieved]
            
            if verbose:
                print(f"✓ Retrieved {len(retrieved)} documents")
                for i, chunk in enumerate(context_texts[:3], 1):
                    print(f"  [{i}] {chunk[:80]}...")
                print()
            
            test_result["pipeline_stages"]["retrieval"] = {
                "status": "SUCCESS",
                "documents_retrieved": len(retrieved),
                "top_matches": context_texts[:3]
            }
        except Exception as e:
            if verbose:
                print(f"✗ Retrieval failed: {str(e)}\n")
            test_result["pipeline_stages"]["retrieval"] = {"status": "FAILED", "error": str(e)}
            return test_result
        
        # ===== STAGE 2: LLM GENERATION =====
        if verbose:
            print(f"[STAGE 2/4] LLM GENERATION")
            print("-" * 100)
        
        try:
            language = detect_language(query)
            system_prompt = build_system_prompt(language)
            user_prompt = build_user_prompt(query, language)
            context = format_context_blocks([c.get("chunk", {}) for c in retrieved])
            full_prompt = build_full_prompt(system_prompt, context, user_prompt)
            
            if use_local:
                try:
                    import torch
                    from rag_engine.ai_agents import local_model
                    
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    if verbose:
                        print(f"Loading fine-tuned model on device: {device}")
                    
                    model, tokenizer = local_model.load_local_model(
                        "ai_agents/gemma_3_lora/content/gemma_3_lora",
                        adapter_dir=None,
                        device=device,
                        local_only=True
                    )
                    response = local_model.generate_text(model, tokenizer, full_prompt)
                except Exception as e:
                    if verbose:
                        print(f"Note: Local model loading issue, using fallback")
                    response = f"[Error with local model: {str(e)}]"
            else:
                from rag_engine.ai_agents.LLM import TelecomLLMClient
                client = TelecomLLMClient()
                response = client.generate_response(system_prompt, query, context)
            
            if verbose:
                print(f"✓ Generated response ({len(response.split())} words)")
                print(f"\nResponse Preview:")
                print(f"  {response[:200]}...\n")
            
            test_result["pipeline_stages"]["generation"] = {
                "status": "SUCCESS",
                "response_length": len(response),
                "response": response
            }
        except Exception as e:
            if verbose:
                print(f"✗ Generation failed: {str(e)}\n")
            test_result["pipeline_stages"]["generation"] = {"status": "FAILED", "error": str(e)}
            return test_result
        
        # ===== STAGE 3: EVALUATION =====
        if verbose:
            print(f"[STAGE 3/4] MODEL EVALUATION")
            print("-" * 100)
        
        try:
            eval_results = self.evaluator.run_full_evaluation(response, context_texts)
            
            if verbose:
                print(f"Overall Factuality Score: {eval_results['overall_factuality_score']:.2%}")
                print(f"Faithfulness Score: {eval_results['faithfulness']['faithfulness_score']:.2%}")
                print(f"  - Verified Claims: {eval_results['faithfulness']['verified_claims']}/{eval_results['faithfulness']['total_claims']}")
                print(f"Hallucination Rate: {eval_results['hallucinations']['hallucination_rate']:.2%}")
                print(f"  - Hallucinations Detected: {eval_results['hallucinations']['hallucination_count']}")
                print(f"Context Utilization: {eval_results['context_utilization']['context_utilization_score']:.2%}")
                print(f"  - Utilized Blocks: {eval_results['context_utilization']['utilized_blocks']}/{eval_results['context_utilization']['total_context_blocks']}\n")
            
            test_result["pipeline_stages"]["evaluation"] = eval_results
        except Exception as e:
            if verbose:
                print(f"✗ Evaluation failed: {str(e)}\n")
            test_result["pipeline_stages"]["evaluation"] = {"status": "FAILED", "error": str(e)}
        
        # ===== STAGE 4: ROOT CAUSE ANALYSIS =====
        if verbose:
            print(f"[STAGE 4/4] ROOT CAUSE ANALYSIS & RECOMMENDATIONS")
            print("-" * 100)
        
        try:
            root_cause = self.analyzer.analyze(query, retrieved, response, eval_results)
            
            if verbose:
                print(f"\nSystem Health: {root_cause['overall_health']}")
                print(f"Issues Found: {root_cause['issue_count']}\n")
                
                if root_cause['identified_issues']:
                    print("Issues:")
                    for issue in root_cause['identified_issues']:
                        severity_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "ℹ️"}
                        emoji = severity_emoji.get(issue.get("severity", "INFO"), "•")
                        print(f"  {emoji} [{issue.get('component', 'UNKNOWN')}] {issue.get('issue', 'Unknown')}")
                        print(f"     Cause: {issue.get('cause', 'N/A')}")
                
                if root_cause['recommendations']:
                    print(f"\nRecommendations:")
                    for rec in root_cause['recommendations']:
                        print(f"  → {rec}")
                print()
            
            test_result["pipeline_stages"]["root_cause_analysis"] = root_cause
        except Exception as e:
            if verbose:
                print(f"✗ Analysis failed: {str(e)}\n")
            test_result["pipeline_stages"]["root_cause_analysis"] = {"status": "FAILED", "error": str(e)}
        
        # ===== SUMMARY =====
        if verbose:
            print("=" * 100)
            print("TEST SUMMARY")
            print("=" * 100)
            print(f"Query: {query}")
            print(f"Strategy: {strategy}")
            overall_health = root_cause.get('overall_health', 'UNKNOWN')
            status_icon = "✓" if overall_health == "EXCELLENT" else "⚠" if overall_health == "NEEDS ATTENTION" else "→"
            print(f"Status: {status_icon} {overall_health}")
            print("=" * 100 + "\n")
        
        self.test_history.append(test_result)
        return test_result
    
    def compare_strategies(self, query: str, verbose: bool = True) -> Dict:
        """Compare all retrieval strategies for a single query"""
        if verbose:
            print(f"\n{'='*100}")
            print(f"COMPARING ALL RETRIEVAL STRATEGIES FOR QUERY: {query}")
            print(f"{'='*100}\n")
        
        results = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "strategy_comparison": {}
        }
        
        for strategy in ["semantic", "hybrid", "relevant"]:
            result = self.run_complete_test(query, strategy=strategy, use_local=True, verbose=verbose)
            results["strategy_comparison"][strategy] = result
        
        return results
    
    def save_report(self, filename: str = "rag_test_report.json"):
        """Save all tests to report"""
        with open(filename, 'w') as f:
            json.dump(self.test_history, f, indent=2, default=str)
        print(f"\n✓ Report saved to: {filename}")


def main():
    """Interactive RAG testing interface"""
    tester = ComprehensiveRAGTester()
    
    print("\n" + "="*100)
    print("COMPREHENSIVE RAG SYSTEM TESTING & EVALUATION")
    print("="*100)
    
    while True:
        print("\nOptions:")
        print("  1. Test with Semantic Search")
        print("  2. Test with Hybrid Search")
        print("  3. Test with Relevant Search")
        print("  4. Compare All Strategies")
        print("  5. Save Report")
        print("  6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "6":
            print("\n✓ Exiting RAG testing system")
            break
        
        if choice in ["1", "2", "3", "4"]:
            query = input("\nEnter your query: ").strip()
            if not query:
                print("✗ Query cannot be empty!")
                continue
            
            if choice == "4":
                tester.compare_strategies(query)
            else:
                strategy_map = {"1": "semantic", "2": "hybrid", "3": "relevant"}
                tester.run_complete_test(query, strategy=strategy_map[choice])
        
        elif choice == "5":
            filename = input("Enter filename (default: rag_test_report.json): ").strip()
            if not filename:
                filename = "rag_test_report.json"
            tester.save_report(filename)
        
        else:
            print("✗ Invalid option!")


if __name__ == "__main__":
    main()
