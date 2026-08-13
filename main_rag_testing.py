#!/usr/bin/env python3
"""
RAG COMPLETE SYSTEM - MAIN ENTRY POINT
Run comprehensive RAG tests with manual query input
"""

import sys
from pathlib import Path

# Add workspace to path
from types import ModuleType
if "rag_engine" not in sys.modules:
    root_dir = Path(__file__).resolve().parent
    while root_dir.parent != root_dir and not (root_dir / "requirements.txt").exists():
        root_dir = root_dir.parent
    m = ModuleType("rag_engine")
    m.__path__ = [str(root_dir)]
    sys.modules["rag_engine"] = m

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from rag_engine.rag_complete_testing import ComprehensiveRAGTester


def print_banner():
    print("\n" + "="*100)
    print("█" * 100)
    print("█" + " "*98 + "█")
    print("█" + " COMPREHENSIVE RAG SYSTEM - FINAL TESTING & EVALUATION".center(98) + "█")
    print("█" + " "*98 + "█")
    print("█" * 100)
    print("="*100)
    print()
    print("Features:")
    print("  ✓ Manual Query Input - You control what to test")
    print("  ✓ Retrieval Testing - Semantic, Hybrid, and Relevant search strategies")
    print("  ✓ LLM Generation - Fine-tuned Gemma 3 model with LoRA adapter")
    print("  ✓ Model Evaluation - Hallucination detection, Faithfulness scoring")
    print("  ✓ Root Cause Analysis - Detailed issue identification and recommendations")
    print("  ✓ Comprehensive Reports - Save results for analysis")
    print("\n" + "="*100 + "\n")


def main():
    print_banner()
    
    tester = ComprehensiveRAGTester()
    test_count = 0
    
    while True:
        print("\n" + "-"*100)
        print("MAIN MENU")
        print("-"*100)
        print("\n1. Run Semantic Search Test")
        print("2. Run Hybrid Search Test")
        print("3. Run Relevant Search Test")
        print("4. Compare All Search Strategies (All 3 methods)")
        print("5. View Test History")
        print("6. Save Test Report to JSON")
        print("7. Exit\n")
        
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == "7":
            print("\n" + "="*100)
            print("Thank you for using Comprehensive RAG System!")
            print(f"Tests performed: {test_count}")
            print("="*100 + "\n")
            break
        
        if choice in ["1", "2", "3"]:
            print("\n" + "="*100)
            query = input("\n📝 Enter your query (what do you want to know?): ").strip()
            print("="*100)
            
            if not query:
                print("\n✗ Query cannot be empty. Please try again.")
                continue
            
            strategy_map = {
                "1": "semantic",
                "2": "hybrid",
                "3": "relevant"
            }
            strategy = strategy_map[choice]
            
            test_count += 1
            print(f"\n🚀 Running Test #{test_count}...")
            tester.run_complete_test(query, strategy=strategy, use_local=True, verbose=True)
        
        elif choice == "4":
            print("\n" + "="*100)
            query = input("\n📝 Enter your query for comparison: ").strip()
            print("="*100)
            
            if not query:
                print("\n✗ Query cannot be empty. Please try again.")
                continue
            
            test_count += 3
            print(f"\n🚀 Comparing all strategies for your query...")
            tester.compare_strategies(query, verbose=True)
        
        elif choice == "5":
            print("\n" + "="*100)
            print("TEST HISTORY")
            print("="*100)
            
            if not tester.test_history:
                print("\nNo tests performed yet.")
            else:
                for i, test in enumerate(tester.test_history, 1):
                    print(f"\nTest #{i}")
                    print(f"  Query: {test.get('query', 'N/A')}")
                    print(f"  Strategy: {test.get('strategy', 'N/A')}")
                    print(f"  Timestamp: {test.get('timestamp', 'N/A')}")
                    
                    if 'evaluation' in test.get('pipeline_stages', {}):
                        eval_data = test['pipeline_stages']['evaluation']
                        if 'overall_factuality_score' in eval_data:
                            print(f"  Overall Score: {eval_data['overall_factuality_score']:.2%}")
        
        elif choice == "6":
            filename = input("\nEnter filename for report (default: rag_test_report.json): ").strip()
            if not filename:
                filename = "rag_test_report.json"
            
            tester.save_report(filename)
        
        else:
            print("\n✗ Invalid choice. Please select 1-7.")


if __name__ == "__main__":
    main()
