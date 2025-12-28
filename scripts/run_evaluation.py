"""
run_evaluation.py - Run RAGAS Evaluation

Evaluates the ComplianceGPT system using golden questions.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


def main():
    """Run the RAGAS evaluation."""
    from src.evaluation.ragas_eval import run_evaluation
    
    print("=" * 60)
    print("ComplianceGPT - RAGAS Evaluation")
    print("=" * 60)
    
    golden_path = "data/test/golden_questions.json"
    output_path = "data/test/evaluation_results.json"
    
    print(f"\nGolden Questions: {golden_path}")
    print(f"Output: {output_path}")
    print()
    
    try:
        report = run_evaluation(golden_path, output_path)
        print(report.summary())
        
        # Detailed results
        print("\nDetailed Results:")
        print("-" * 40)
        for r in report.results:
            status = "✅" if r.faithfulness > 0.7 else "⚠️"
            print(f"{status} {r.question_id}: F={r.faithfulness:.0%} R={r.answer_relevancy:.0%} P={r.context_precision:.0%}")
        
        print("\n" + "=" * 60)
        if report.avg_faithfulness > 0.95:
            print("🎉 Target Faithfulness (>95%) ACHIEVED!")
        else:
            print(f"⚠️ Faithfulness: {report.avg_faithfulness:.0%} (target: >95%)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Weaviate is configured in .env")
        print("  2. GDPR is indexed (run: python scripts/run_ingestion.py)")
        print("  3. LLM provider is configured")
        sys.exit(1)


if __name__ == "__main__":
    main()
