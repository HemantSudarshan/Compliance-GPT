"""
ComplianceGPT - Generation Module

Handles LLM-based answer generation with citations.
"""

from src.generation.prompts import (
    SYSTEM_PROMPT,
    QUERY_TEMPLATE,
    NO_CONTEXT_RESPONSE,
    get_system_prompt,
    format_query_prompt,
    format_comparison_prompt,
    get_no_context_response
)
from src.generation.citation_engine import (
    CitationEngine,
    Citation,
    CitedResponse,
    answer_compliance_question
)

__all__ = [
    # Prompts
    "SYSTEM_PROMPT",
    "QUERY_TEMPLATE",
    "NO_CONTEXT_RESPONSE",
    "get_system_prompt",
    "format_query_prompt",
    "format_comparison_prompt",
    "get_no_context_response",
    # Citation Engine
    "CitationEngine",
    "Citation",
    "CitedResponse",
    "answer_compliance_question",
]
