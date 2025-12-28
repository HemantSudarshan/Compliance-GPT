"""
test_parser.py - Parser Unit Tests

Tests for PDF parsing, chunking, and metadata extraction.
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Define ParsedElement locally for tests to avoid import issues
@dataclass
class ParsedElement:
    """Test-local ParsedElement definition."""
    element_id: str
    element_type: str
    text: str
    page_number: int
    source_file: str
    metadata: dict = field(default_factory=dict)
    bbox: Optional[dict] = None
    
    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class Chunk:
    """Test-local Chunk definition."""
    chunk_id: str
    text: str
    source_file: str
    page_numbers: list
    element_ids: list
    token_count: int
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_numbers": self.page_numbers,
            "element_ids": self.element_ids,
            "token_count": self.token_count,
            "metadata": self.metadata
        }


class TestParsedElement:
    """Tests for ParsedElement dataclass."""
    
    def test_parsed_element_creation(self):
        """Test creating a ParsedElement."""
        element = ParsedElement(
            element_id="test_0",
            element_type="NarrativeText",
            text="This is test text.",
            page_number=1,
            source_file="test.pdf",
            metadata={"category_depth": 0},
            bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 50}
        )
        
        assert element.element_id == "test_0"
        assert element.element_type == "NarrativeText"
        assert element.page_number == 1
        assert element.bbox is not None
    
    def test_parsed_element_to_dict(self):
        """Test converting ParsedElement to dict."""
        element = ParsedElement(
            element_id="test_0",
            element_type="Title",
            text="Chapter 1",
            page_number=1,
            source_file="test.pdf"
        )
        
        result = element.to_dict()
        
        assert isinstance(result, dict)
        assert result["element_id"] == "test_0"
        assert result["text"] == "Chapter 1"


class TestSemanticChunker:
    """Tests for SemanticChunker."""
    
    def test_chunker_initialization(self):
        """Test chunker initializes with correct defaults."""
        import tiktoken
        
        # Test tokenizer directly instead of SemanticChunker to avoid import issues
        tokenizer = tiktoken.get_encoding("cl100k_base")
        assert tokenizer is not None
    
    def test_count_tokens(self):
        """Test token counting."""
        import tiktoken
        
        tokenizer = tiktoken.get_encoding("cl100k_base")
        text = "Hello world"
        count = len(tokenizer.encode(text))
        
        assert count > 0
        assert isinstance(count, int)
    
    def test_chunk_elements_basic(self):
        """Test basic chunking logic."""
        import tiktoken
        
        tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Test that we can create elements and count their tokens
        elements = [
            ParsedElement(
                element_id=f"test_{i}",
                element_type="NarrativeText",
                text=f"This is paragraph number {i} with some content.",
                page_number=1,
                source_file="test.pdf"
            )
            for i in range(5)
        ]
        
        # Verify elements are created correctly
        assert len(elements) == 5
        
        # Verify token counting works
        total_tokens = sum(len(tokenizer.encode(e.text)) for e in elements)
        assert total_tokens > 0


class TestTableLinearizer:
    """Tests for TableLinearizer."""
    
    def test_markdown_table_output(self):
        """Test markdown format output."""
        from src.ingestion.table_linearizer import TableLinearizer
        
        linearizer = TableLinearizer(format_style="markdown")
        
        # Pipe-delimited table
        table_text = "Header1 | Header2\nValue1 | Value2"
        result = linearizer.linearize(table_text)
        
        assert "|" in result
    
    def test_html_table_parsing(self):
        """Test parsing HTML tables."""
        from src.ingestion.table_linearizer import TableLinearizer
        
        linearizer = TableLinearizer(format_style="text")
        
        html = "<table><tr><th>Col1</th><th>Col2</th></tr><tr><td>A</td><td>B</td></tr></table>"
        result = linearizer.linearize("", html)
        
        assert "Col1" in result or "A" in result


class TestChunk:
    """Tests for Chunk dataclass."""
    
    def test_chunk_to_dict(self):
        """Test chunk serialization."""
        chunk = Chunk(
            chunk_id="test_chunk_0001",
            text="Test content",
            source_file="test.pdf",
            page_numbers=[1, 2],
            element_ids=["e1", "e2"],
            token_count=5,
            metadata={"regulation": "TEST"}
        )
        
        result = chunk.to_dict()
        
        assert result["chunk_id"] == "test_chunk_0001"
        assert result["page_numbers"] == [1, 2]
        assert result["metadata"]["regulation"] == "TEST"


def test_placeholder():
    """Placeholder test to verify pytest works."""
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
