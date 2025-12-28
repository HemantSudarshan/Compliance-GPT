"""
ComplianceGPT - Evaluation Module

Handles RAG quality evaluation using RAGAS metrics.
"""

from src.evaluation.ragas_eval import (
    RAGASEvaluator,
    EvaluationResult,
    EvaluationReport,
    run_evaluation
)

__all__ = [
    "RAGASEvaluator",
    "EvaluationResult",
    "EvaluationReport",
    "run_evaluation",
]
