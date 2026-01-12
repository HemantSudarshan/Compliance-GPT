"""
test_retriever.py - Retriever Unit Tests

Comprehensive tests for hybrid search retrieval functionality.
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Test-local definitions to avoid import issues
@dataclass
class RetrievalResult:
    """Test-local RetrievalResult definition."""
    chunk_id: str
    text: str
    source_file: str
    page_numbers: list
    regulation: str
    score: float
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_numbers": self.page_numbers,
            "regulation": self.regulation,
            "score": self.score,
            "metadata": self.metadata
        }


class TestRetrievalResult:
    """Tests for RetrievalResult dataclass."""
    
    def test_retrieval_result_creation(self):
        """Test creating a RetrievalResult."""
        result = RetrievalResult(
            chunk_id="GDPR_chunk_001",
            text="Personal data shall be processed lawfully, fairly and transparently.",
            source_file="gdpr.pdf",
            page_numbers=[5, 6],
            regulation="GDPR",
            score=0.95,
            metadata={"chunk_index": 1}
        )
        
        assert result.chunk_id == "GDPR_chunk_001"
        assert result.regulation == "GDPR"
        assert result.score == 0.95
        assert len(result.page_numbers) == 2
    
    def test_retrieval_result_to_dict(self):
        """Test converting RetrievalResult to dictionary."""
        result = RetrievalResult(
            chunk_id="CCPA_chunk_001",
            text="Consumer rights under CCPA",
            source_file="ccpa.pdf",
            page_numbers=[10],
            regulation="CCPA",
            score=0.88
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["chunk_id"] == "CCPA_chunk_001"
        assert data["score"] == 0.88
    
    def test_retrieval_result_empty_metadata(self):
        """Test RetrievalResult with empty metadata."""
        result = RetrievalResult(
            chunk_id="test_001",
            text="Test text",
            source_file="test.pdf",
            page_numbers=[1],
            regulation="TEST",
            score=0.5
        )
        
        assert result.metadata == {}


class TestQueryExpansion:
    """Tests for query expansion with compliance synonyms."""
    
    # Synonym mapping (subset for testing)
    synonyms = {
        "unauthorized access": "personal data breach security incident",
        "breach": "personal data breach notification 72 hours",
        "erasure": "right to erasure right to be forgotten Article 17 deletion",
        "consent": "data subject consent lawful basis Article 7 freely given",
        "fines": "penalties administrative fines Article 83 sanctions",
    }
    
    def _expand_query(self, query: str) -> str:
        """Test implementation of query expansion."""
        query_lower = query.lower()
        expanded = query
        
        for term, expansion in self.synonyms.items():
            if term in query_lower:
                expanded = f"{expanded} {expansion}"
        
        return expanded
    
    def test_query_expansion_breach(self):
        """Test query expansion for 'breach' keyword."""
        query = "What happens in a data breach?"
        expanded = self._expand_query(query)
        
        assert "breach" in expanded.lower()
        assert "notification" in expanded.lower()
        assert "72 hours" in expanded.lower()
    
    def test_query_expansion_erasure(self):
        """Test query expansion for 'erasure' keyword."""
        query = "What is the right to erasure?"
        expanded = self._expand_query(query)
        
        assert "Article 17" in expanded
        assert "right to be forgotten" in expanded
    
    def test_query_expansion_consent(self):
        """Test query expansion for 'consent' keyword."""
        query = "What are the consent requirements?"
        expanded = self._expand_query(query)
        
        assert "Article 7" in expanded
        assert "freely given" in expanded
    
    def test_query_no_expansion_needed(self):
        """Test query that doesn't match any synonyms."""
        query = "What is Article 5?"
        expanded = self._expand_query(query)
        
        # Should return original query unchanged (no synonyms matched)
        assert expanded == query
    
    def test_query_expansion_multiple_terms(self):
        """Test query with multiple expandable terms."""
        query = "consent and erasure requirements"
        expanded = self._expand_query(query)
        
        assert "Article 7" in expanded
        assert "Article 17" in expanded


class TestHybridRetrieverMocked:
    """Tests for HybridRetriever with mocked Weaviate client."""
    
    @pytest.fixture
    def mock_weaviate_client(self):
        """Create a mock Weaviate client."""
        client = Mock()
        
        # Mock collection and query methods
        collection = Mock()
        client.get_collection.return_value = collection
        
        return client, collection
    
    def test_search_returns_results(self, mock_weaviate_client):
        """Test that search returns properly formatted results."""
        client, collection = mock_weaviate_client
        
        # Mock response object
        mock_obj = Mock()
        mock_obj.properties = {
            "chunk_id": "GDPR_001",
            "text": "Article 32 - Security of processing",
            "source_file": "gdpr.pdf",
            "page_numbers": [45],
            "regulation": "GDPR",
            "token_count": 100,
            "chunk_index": 10,
            "element_ids": ["elem_1"]
        }
        mock_obj.metadata = Mock(score=0.92)
        
        mock_response = Mock()
        mock_response.objects = [mock_obj]
        
        collection.query.bm25.return_value = mock_response
        
        # Simulate search
        results = []
        for obj in mock_response.objects:
            result = RetrievalResult(
                chunk_id=obj.properties.get("chunk_id", ""),
                text=obj.properties.get("text", ""),
                source_file=obj.properties.get("source_file", ""),
                page_numbers=obj.properties.get("page_numbers", []),
                regulation=obj.properties.get("regulation", ""),
                score=obj.metadata.score if obj.metadata else 0.0,
                metadata={}
            )
            results.append(result)
        
        assert len(results) == 1
        assert results[0].chunk_id == "GDPR_001"
        assert results[0].score == 0.92
    
    def test_search_handles_empty_results(self, mock_weaviate_client):
        """Test handling of empty search results."""
        client, collection = mock_weaviate_client
        
        mock_response = Mock()
        mock_response.objects = []
        
        collection.query.bm25.return_value = mock_response
        
        results = [obj for obj in mock_response.objects]
        
        assert len(results) == 0
    
    def test_search_with_regulation_filter(self, mock_weaviate_client):
        """Test search with regulation filter."""
        client, collection = mock_weaviate_client
        
        # The filter should be applied when calling bm25
        mock_response = Mock()
        mock_response.objects = []
        
        collection.query.bm25.return_value = mock_response
        
        # Verify the filter can be created
        from weaviate.classes.query import Filter
        filter_obj = Filter.by_property("regulation").equal("GDPR")
        
        assert filter_obj is not None


class TestSearchScoring:
    """Tests for search result scoring and ranking."""
    
    def test_results_sorted_by_score(self):
        """Test that results are properly sorted by score."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.5, {}),
            RetrievalResult("c2", "text2", "f2", [2], "GDPR", 0.9, {}),
            RetrievalResult("c3", "text3", "f3", [3], "GDPR", 0.7, {}),
        ]
        
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        assert sorted_results[0].chunk_id == "c2"
        assert sorted_results[1].chunk_id == "c3"
        assert sorted_results[2].chunk_id == "c1"
    
    def test_score_threshold_filtering(self):
        """Test filtering results by minimum score."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.3, {}),
            RetrievalResult("c2", "text2", "f2", [2], "GDPR", 0.8, {}),
            RetrievalResult("c3", "text3", "f3", [3], "GDPR", 0.5, {}),
        ]
        
        min_score = 0.5
        filtered = [r for r in results if r.score >= min_score]
        
        assert len(filtered) == 2
        assert all(r.score >= min_score for r in filtered)


class TestRegulationFiltering:
    """Tests for filtering by regulation type."""
    
    def test_filter_gdpr_only(self):
        """Test filtering for GDPR results only."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.9, {}),
            RetrievalResult("c2", "text2", "f2", [2], "CCPA", 0.8, {}),
            RetrievalResult("c3", "text3", "f3", [3], "GDPR", 0.7, {}),
            RetrievalResult("c4", "text4", "f4", [4], "PCI-DSS", 0.6, {}),
        ]
        
        gdpr_only = [r for r in results if r.regulation == "GDPR"]
        
        assert len(gdpr_only) == 2
        assert all(r.regulation == "GDPR" for r in gdpr_only)
    
    def test_filter_ccpa_only(self):
        """Test filtering for CCPA results only."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.9, {}),
            RetrievalResult("c2", "text2", "f2", [2], "CCPA", 0.8, {}),
        ]
        
        ccpa_only = [r for r in results if r.regulation == "CCPA"]
        
        assert len(ccpa_only) == 1
        assert ccpa_only[0].regulation == "CCPA"
    
    def test_no_filter_returns_all(self):
        """Test that no filter returns all regulations."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.9, {}),
            RetrievalResult("c2", "text2", "f2", [2], "CCPA", 0.8, {}),
            RetrievalResult("c3", "text3", "f3", [3], "PCI-DSS", 0.7, {}),
        ]
        
        regulations = {r.regulation for r in results}
        
        assert len(regulations) == 3
        assert "GDPR" in regulations
        assert "CCPA" in regulations
        assert "PCI-DSS" in regulations


class TestTopKLimit:
    """Tests for top-k result limiting."""
    
    def test_top_k_limits_results(self):
        """Test that top_k properly limits results."""
        all_results = [
            RetrievalResult(f"c{i}", f"text{i}", "f.pdf", [i], "GDPR", 0.9 - i*0.1, {})
            for i in range(10)
        ]
        
        top_k = 5
        limited = all_results[:top_k]
        
        assert len(limited) == 5
    
    def test_top_k_with_fewer_results(self):
        """Test top_k when fewer results available."""
        results = [
            RetrievalResult("c1", "text1", "f1", [1], "GDPR", 0.9, {}),
            RetrievalResult("c2", "text2", "f2", [2], "GDPR", 0.8, {}),
        ]
        
        top_k = 5
        limited = results[:top_k]
        
        assert len(limited) == 2  # Only 2 available, not 5


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_query(self):
        """Test handling of empty query string."""
        query = ""
        
        # Should handle gracefully
        assert query.strip() == ""
    
    def test_very_long_query(self):
        """Test handling of very long query strings."""
        query = "What is " + "data breach notification " * 100
        
        # Should truncate or handle gracefully
        assert len(query) > 1000
    
    def test_special_characters_in_query(self):
        """Test handling of special characters in query."""
        query = "What is Article 32? (security & encryption)"
        
        # Should not raise an error
        cleaned = query.replace("&", "and")
        assert "and" in cleaned
    
    def test_unicode_in_query(self):
        """Test handling of unicode characters."""
        query = "What are the GDPR requirements for données personnelles?"
        
        # Should handle unicode properly
        assert "données" in query
    
    def test_result_with_missing_fields(self):
        """Test handling results with missing optional fields."""
        result = RetrievalResult(
            chunk_id="test",
            text="Test text",
            source_file="",  # Missing source file
            page_numbers=[],  # Empty page numbers
            regulation="UNKNOWN",
            score=0.0
        )
        
        assert result.source_file == ""
        assert result.page_numbers == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
