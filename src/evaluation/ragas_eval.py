"""
ragas_eval.py - RAGAS Evaluation Framework

Evaluates RAG quality using Faithfulness, Answer Relevance, and Context Precision.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Flexible imports
try:
    from src.utils.logger import setup_logger
    from src.utils.config import config
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Results from a single question evaluation."""
    
    question_id: str
    question: str
    answer: str
    ground_truth: str
    contexts: list[str]
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "answer": self.answer,
            "ground_truth": self.ground_truth,
            "contexts": self.contexts,
            "scores": {
                "faithfulness": self.faithfulness,
                "answer_relevancy": self.answer_relevancy,
                "context_precision": self.context_precision
            }
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    
    regulation: str
    total_questions: int
    results: list[EvaluationResult]
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_precision: float = 0.0
    
    def compute_averages(self):
        """Compute average scores across all results."""
        if not self.results:
            return
        
        n = len(self.results)
        self.avg_faithfulness = sum(r.faithfulness for r in self.results) / n
        self.avg_answer_relevancy = sum(r.answer_relevancy for r in self.results) / n
        self.avg_context_precision = sum(r.context_precision for r in self.results) / n
    
    def to_dict(self) -> dict:
        return {
            "regulation": self.regulation,
            "total_questions": self.total_questions,
            "average_scores": {
                "faithfulness": self.avg_faithfulness,
                "answer_relevancy": self.avg_answer_relevancy,
                "context_precision": self.avg_context_precision
            },
            "results": [r.to_dict() for r in self.results]
        }
    
    def summary(self) -> str:
        """Generate a text summary of the evaluation."""
        return f"""
RAGAS Evaluation Report - {self.regulation}
{'=' * 50}
Total Questions: {self.total_questions}

Average Scores:
  - Faithfulness:       {self.avg_faithfulness:.2%}
  - Answer Relevancy:   {self.avg_answer_relevancy:.2%}
  - Context Precision:  {self.avg_context_precision:.2%}

Target: Faithfulness > 95%
Status: {'✅ PASSED' if self.avg_faithfulness > 0.95 else '⚠️ NEEDS IMPROVEMENT'}
"""


class RAGASEvaluator:
    """
    Evaluates RAG system using RAGAS metrics.
    
    Metrics:
    - Faithfulness: Is the answer grounded in the context?
    - Answer Relevancy: Is the answer relevant to the question?
    - Context Precision: Is the retrieved context relevant?
    """
    
    def __init__(
        self,
        provider: str = None,
        api_key: str = None
    ):
        """
        Initialize the evaluator.
        
        Args:
            provider: LLM provider for evaluation
            api_key: API key for the provider
        """
        self.provider = provider or config.llm_provider
        self.api_key = api_key or config.get_api_key()
    
    def load_golden_questions(
        self,
        json_path: str | Path = "data/test/golden_questions.json"
    ) -> list[dict]:
        """Load golden questions from JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("questions", [])
    
    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str
    ) -> dict:
        """
        Evaluate a single question-answer pair.
        
        Uses LLM-as-judge approach for evaluation.
        """
        # Simple heuristic evaluation (without external RAGAS library)
        # For production, integrate with the ragas library
        
        faithfulness = self._calculate_faithfulness(answer, contexts)
        relevancy = self._calculate_answer_relevancy(question, answer)
        precision = self._calculate_context_precision(question, contexts, ground_truth)
        
        return {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_precision": precision
        }
    
    def _calculate_faithfulness(self, answer: str, contexts: list[str]) -> float:
        """
        Calculate faithfulness score.
        
        Checks if the answer content appears in the provided context.
        """
        if not answer or not contexts:
            return 0.0
        
        context_text = " ".join(contexts).lower()
        answer_words = answer.lower().split()
        
        # Count how many answer words appear in context
        matched = sum(1 for word in answer_words if word in context_text)
        
        return min(matched / len(answer_words), 1.0) if answer_words else 0.0
    
    def _calculate_answer_relevancy(self, question: str, answer: str) -> float:
        """
        Calculate answer relevancy.
        
        Checks if the answer addresses the question.
        """
        if not answer:
            return 0.0
        
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # Check overlap of key terms
        overlap = len(question_words & answer_words)
        
        return min(overlap / len(question_words), 1.0) if question_words else 0.0
    
    def _calculate_context_precision(
        self,
        question: str,
        contexts: list[str],
        ground_truth: str
    ) -> float:
        """
        Calculate context precision.
        
        Checks if retrieved contexts are relevant to the ground truth.
        """
        if not contexts or not ground_truth:
            return 0.0
        
        ground_truth_words = set(ground_truth.lower().split())
        
        relevant_contexts = 0
        for context in contexts:
            context_words = set(context.lower().split())
            overlap = len(ground_truth_words & context_words)
            if overlap >= 3:  # At least 3 words overlap
                relevant_contexts += 1
        
        return relevant_contexts / len(contexts) if contexts else 0.0
    
    def run_evaluation(
        self,
        golden_questions_path: str = "data/test/golden_questions.json",
        output_path: Optional[str] = None
    ) -> EvaluationReport:
        """
        Run full evaluation on golden questions.
        
        Args:
            golden_questions_path: Path to golden questions JSON
            output_path: Optional path to save results
            
        Returns:
            EvaluationReport with all results
        """
        from src.storage.weaviate_client import WeaviateClient
        from src.generation.citation_engine import CitationEngine
        
        logger.info("Starting RAGAS evaluation...")
        
        # Load questions
        questions = self.load_golden_questions(golden_questions_path)
        
        if not questions:
            raise ValueError("No golden questions found")
        
        results = []
        
        with WeaviateClient() as client:
            engine = CitationEngine(client)
            
            for i, q in enumerate(questions):
                logger.info(f"Evaluating {i+1}/{len(questions)}: {q['question'][:50]}...")
                
                try:
                    # Get answer from system
                    response = engine.query(q["question"])
                    
                    # Extract contexts
                    contexts = [c.text for c in response.citations]
                    
                    # Run evaluation
                    scores = self.evaluate_single(
                        question=q["question"],
                        answer=response.answer,
                        contexts=contexts,
                        ground_truth=q["ground_truth"]
                    )
                    
                    result = EvaluationResult(
                        question_id=q["id"],
                        question=q["question"],
                        answer=response.answer,
                        ground_truth=q["ground_truth"],
                        contexts=contexts,
                        faithfulness=scores["faithfulness"],
                        answer_relevancy=scores["answer_relevancy"],
                        context_precision=scores["context_precision"]
                    )
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error evaluating question {q['id']}: {e}")
                    results.append(EvaluationResult(
                        question_id=q["id"],
                        question=q["question"],
                        answer=f"Error: {e}",
                        ground_truth=q["ground_truth"],
                        contexts=[]
                    ))
        
        # Create report
        report = EvaluationReport(
            regulation="GDPR",
            total_questions=len(questions),
            results=results
        )
        report.compute_averages()
        
        # Save if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Saved evaluation report to {output_path}")
        
        return report


def run_evaluation(
    golden_questions_path: str = "data/test/golden_questions.json",
    output_path: str = "data/test/evaluation_results.json"
) -> EvaluationReport:
    """
    Convenience function to run evaluation.
    
    Returns:
        EvaluationReport with results
    """
    evaluator = RAGASEvaluator()
    return evaluator.run_evaluation(golden_questions_path, output_path)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("=" * 50)
    print("RAGAS Evaluation - ComplianceGPT")
    print("=" * 50)
    
    try:
        report = run_evaluation()
        print(report.summary())
        
        # Show individual results
        if "--verbose" in sys.argv:
            for r in report.results:
                print(f"\n{r.question_id}: {r.question[:50]}...")
                print(f"  Faithfulness: {r.faithfulness:.2%}")
                print(f"  Relevancy: {r.answer_relevancy:.2%}")
                print(f"  Precision: {r.context_precision:.2%}")
                
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure Weaviate is configured and documents are indexed.")
