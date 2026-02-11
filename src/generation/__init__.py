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

__all__ = [
    # Prompts
    "SYSTEM_PROMPT",
    "QUERY_TEMPLATE",
    "NO_CONTEXT_RESPONSE",
    "get_system_prompt",
    "format_query_prompt",
    "format_comparison_prompt",
    "get_no_context_response",
]

# Import heavy runtime components only when optional dependencies are available.
# This keeps lightweight modules (for example prompt utilities and unit tests)
# importable without Weaviate/LLM client packages installed.
try:
    from src.generation.citation_engine import (
        CitationEngine,
        Citation,
        CitedResponse,
        answer_compliance_question
    )
except ModuleNotFoundError:
    pass
else:
    __all__ += [
        "CitationEngine",
        "Citation",
        "CitedResponse",
        "answer_compliance_question",
    ]
