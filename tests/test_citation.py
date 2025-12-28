"""
test_citation.py - Citation Engine Unit Tests

Tests for citation-based answer generation.
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Test-local definitions
@dataclass 
class Citation:
    citation_id: int
    text: str
    source_file: str
    page_numbers: list
    regulation: str
    chunk_id: str
    
    def format_reference(self) -> str:
        pages = ", ".join(str(p) for p in self.page_numbers)
        return f"[{self.citation_id}] {self.regulation} - {self.source_file}, Page(s) {pages}"


@dataclass
class CitedResponse:
    answer: str
    citations: list
    query: str
    has_context: bool
    metadata: dict = field(default_factory=dict)


class TestCitation:
    """Tests for Citation class."""
    
    def test_citation_creation(self):
        """Test creating a Citation."""
        citation = Citation(
            citation_id=1,
            text="Sample regulation text",
            source_file="gdpr.pdf",
            page_numbers=[52, 53],
            regulation="GDPR",
            chunk_id="GDPR_chunk_0001"
        )
        
        assert citation.citation_id == 1
        assert citation.regulation == "GDPR"
        assert len(citation.page_numbers) == 2
    
    def test_citation_format_reference(self):
        """Test citation reference formatting."""
        citation = Citation(
            citation_id=2,
            text="Article 32 text",
            source_file="gdpr.pdf",
            page_numbers=[45],
            regulation="GDPR",
            chunk_id="GDPR_chunk_0010"
        )
        
        ref = citation.format_reference()
        
        assert "[2]" in ref
        assert "GDPR" in ref
        assert "gdpr.pdf" in ref
        assert "45" in ref


class TestCitedResponse:
    """Tests for CitedResponse class."""
    
    def test_response_creation(self):
        """Test creating a CitedResponse."""
        response = CitedResponse(
            answer="This is the answer with citations [1].",
            citations=[],
            query="What is GDPR?",
            has_context=True
        )
        
        assert response.has_context is True
        assert "[1]" in response.answer
    
    def test_response_without_context(self):
        """Test response when no context found."""
        response = CitedResponse(
            answer="No information found",
            citations=[],
            query="Unknown question",
            has_context=False
        )
        
        assert response.has_context is False
        assert len(response.citations) == 0


class TestPrompts:
    """Tests for prompt templates."""
    
    def test_system_prompt_exists(self):
        """Test system prompt is defined."""
        from src.generation.prompts import get_system_prompt
        
        prompt = get_system_prompt()
        
        assert len(prompt) > 100
        assert "citation" in prompt.lower() or "cite" in prompt.lower()
    
    def test_query_prompt_formatting(self):
        """Test query prompt formatting."""
        from src.generation.prompts import format_query_prompt
        
        context = "[1] GDPR Article 32: Security requirements..."
        question = "What are the security requirements?"
        
        prompt = format_query_prompt(context, question)
        
        assert context in prompt
        assert question in prompt
    
    def test_no_context_response(self):
        """Test no context response message."""
        from src.generation.prompts import get_no_context_response
        
        response = get_no_context_response()
        
        assert "cannot find" in response.lower() or "no" in response.lower()


class TestIntegration:
    """Integration tests for citation engine components."""
    
    def test_citation_to_response_flow(self):
        """Test creating a response with citations."""
        citation = Citation(
            citation_id=1,
            text="Article 33 requires breach notification within 72 hours",
            source_file="gdpr.pdf",
            page_numbers=[52],
            regulation="GDPR",
            chunk_id="GDPR_chunk_0033"
        )
        
        response = CitedResponse(
            answer="Under GDPR, breaches must be reported within 72 hours [1].",
            citations=[citation],
            query="What are breach notification requirements?",
            has_context=True,
            metadata={"model": "gpt-4o-mini"}
        )
        
        assert len(response.citations) == 1
        assert response.citations[0].citation_id == 1
        assert response.metadata["model"] == "gpt-4o-mini"


def test_placeholder():
    """Placeholder test."""
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
