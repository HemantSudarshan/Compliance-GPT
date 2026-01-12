"""
test_api.py - API Endpoint Tests

Tests for FastAPI endpoints including validation, error handling, and responses.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        with patch.dict('os.environ', {
            'WEAVIATE_URL': 'http://test:8080',
            'LLM_PROVIDER': 'groq'
        }):
            from api.main import app
            return TestClient(app)
    
    def test_health_returns_status(self, client):
        """Test health endpoint returns proper structure."""
        with patch('src.storage.weaviate_client.WeaviateClient') as mock_weaviate:
            mock_instance = MagicMock()
            mock_instance.__enter__ = Mock(return_value=mock_instance)
            mock_instance.__exit__ = Mock(return_value=False)
            mock_instance.health_check.return_value = {
                "status": "healthy",
                "object_count": 100
            }
            mock_weaviate.return_value = mock_instance
            
            response = client.get("/api/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "weaviate" in data
            assert "llm_provider" in data


class TestRegulationsEndpoint:
    """Tests for /api/regulations endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_regulations_returns_list(self, client):
        """Test regulations endpoint returns list."""
        response = client.get("/api/regulations")
        
        assert response.status_code == 200
        data = response.json()
        assert "regulations" in data
        assert isinstance(data["regulations"], list)
        assert len(data["regulations"]) >= 3
    
    def test_regulations_have_required_fields(self, client):
        """Test each regulation has required fields."""
        response = client.get("/api/regulations")
        
        data = response.json()
        for reg in data["regulations"]:
            assert "id" in reg
            assert "name" in reg
            assert "icon" in reg
    
    def test_regulations_include_gdpr_ccpa(self, client):
        """Test GDPR and CCPA are included."""
        response = client.get("/api/regulations")
        
        data = response.json()
        ids = [r["id"] for r in data["regulations"]]
        
        assert "GDPR" in ids
        assert "CCPA" in ids


class TestVersionEndpoint:
    """Tests for /api/version endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_version_returns_info(self, client):
        """Test version endpoint returns version info."""
        response = client.get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "name" in data
        assert data["name"] == "ComplianceGPT"


class TestQueryEndpoint:
    """Tests for /api/query endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_query_validates_empty_question(self, client):
        """Test query rejects empty question."""
        response = client.post("/api/query", json={
            "question": ""
        })
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_query_validates_short_question(self, client):
        """Test query rejects too-short question."""
        response = client.post("/api/query", json={
            "question": "Hi"
        })
        
        # Should fail validation (min_length=3)
        assert response.status_code == 422
    
    def test_query_validates_long_question(self, client):
        """Test query rejects too-long question."""
        long_question = "What is GDPR? " * 100  # ~1400 chars
        response = client.post("/api/query", json={
            "question": long_question
        })
        
        # Should fail validation (max_length=1000)
        assert response.status_code == 422
    
    def test_query_accepts_valid_request(self, client):
        """Test query accepts valid request structure."""
        # This test checks validation passes, actual query would need mocking
        with patch('src.storage.weaviate_client.WeaviateClient') as mock_weaviate:
            with patch('src.generation.citation_engine.CitationEngine') as mock_engine:
                mock_response = Mock()
                mock_response.answer = "Test answer"
                mock_response.citations = []
                mock_response.has_context = True
                mock_response.metadata = {"provider": "groq", "model": "llama-3.3-70b"}
                
                mock_engine_instance = Mock()
                mock_engine_instance.query.return_value = mock_response
                mock_engine.return_value = mock_engine_instance
                
                mock_client_instance = MagicMock()
                mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
                mock_client_instance.__exit__ = Mock(return_value=False)
                mock_weaviate.return_value = mock_client_instance
                
                response = client.post("/api/query", json={
                    "question": "What is GDPR Article 32?"
                })
                
                # Should process successfully
                assert response.status_code == 200


class TestStatsEndpoint:
    """Tests for /api/stats endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_stats_returns_counts(self, client):
        """Test stats endpoint returns statistics."""
        response = client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "cache_size" in data
        assert "uptime_seconds" in data


class TestCacheEndpoint:
    """Tests for /api/cache endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_clear_cache_succeeds(self, client):
        """Test cache clear endpoint works."""
        response = client.delete("/api/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestMiddleware:
    """Tests for API middleware."""
    
    def test_rate_limit_not_triggered_under_limit(self):
        """Test rate limiter allows requests under limit."""
        from api.middleware import RateLimitMiddleware
        
        # Create a mock app
        mock_app = Mock()
        middleware = RateLimitMiddleware(mock_app, requests_per_minute=30)
        
        # Simulate requests under limit
        client_ip = "192.168.1.1"
        for _ in range(25):
            middleware._record_request(client_ip)
        
        assert middleware._is_allowed(client_ip)
    
    def test_rate_limit_triggered_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        from api.middleware import RateLimitMiddleware
        
        mock_app = Mock()
        middleware = RateLimitMiddleware(mock_app, requests_per_minute=30)
        
        client_ip = "192.168.1.2"
        for _ in range(35):
            middleware._record_request(client_ip)
        
        assert not middleware._is_allowed(client_ip)
    
    def test_cache_stores_and_retrieves(self):
        """Test response cache stores and retrieves values."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache(ttl_seconds=300)
        
        key = cache.make_key("What is GDPR?", "GDPR")
        cache.set(key, {"answer": "test"})
        
        result = cache.get(key)
        assert result is not None
        assert result["answer"] == "test"
    
    def test_cache_expires_old_entries(self):
        """Test cache expires entries after TTL."""
        from api.middleware import ResponseCache
        import time
        
        cache = ResponseCache(ttl_seconds=1)  # 1 second TTL
        
        key = "test_key"
        cache.set(key, {"answer": "test"})
        
        # Should exist immediately
        assert cache.get(key) is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired
        assert cache.get(key) is None


class TestInputValidation:
    """Tests for input validation and sanitization."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.main import app
        return TestClient(app)
    
    def test_query_strips_whitespace(self, client):
        """Test question whitespace is stripped."""
        # Just test the model validation
        from api.main import QueryRequest
        
        request = QueryRequest(question="  What is GDPR?  ")
        assert request.question == "What is GDPR?"
    
    def test_handles_special_characters(self, client):
        """Test special characters in query don't break validation."""
        from api.main import QueryRequest
        
        request = QueryRequest(question="What is Article 32? (security & encryption)")
        assert "Article 32" in request.question


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
