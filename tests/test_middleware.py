"""
test_middleware.py - Middleware Unit Tests

Tests for rate limiting, caching, and authentication middleware.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from fastapi import Request
from starlette.responses import Response


class TestResponseCache:
    """Tests for ResponseCache class."""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct defaults."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache(ttl_seconds=300, max_entries=1000)
        
        assert cache.ttl == 300
        assert cache.max_entries == 1000
        assert len(cache.cache) == 0
    
    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache()
        
        cache.set("key1", {"answer": "test answer"})
        result = cache.get("key1")
        
        assert result is not None
        assert result["answer"] == "test answer"
    
    def test_cache_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache()
        result = cache.get("nonexistent")
        
        assert result is None
    
    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache(ttl_seconds=1)
        
        cache.set("key1", {"data": "test"})
        
        # Should exist immediately
        assert cache.get("key1") is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_cache_make_key(self):
        """Test cache key generation."""
        from api.middleware import ResponseCache
        
        key1 = ResponseCache.make_key("What is GDPR?", "GDPR")
        key2 = ResponseCache.make_key("What is GDPR?", "GDPR")
        key3 = ResponseCache.make_key("What is CCPA?", "CCPA")
        
        # Same query should produce same key
        assert key1 == key2
        
        # Different query should produce different key
        assert key1 != key3
    
    def test_cache_key_case_insensitive(self):
        """Test cache keys are case-insensitive for queries."""
        from api.middleware import ResponseCache
        
        key1 = ResponseCache.make_key("What is GDPR?")
        key2 = ResponseCache.make_key("what is gdpr?")
        
        assert key1 == key2
    
    def test_cache_clear(self):
        """Test cache clear operation."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert len(cache.cache) == 2
        
        cache.clear()
        
        assert len(cache.cache) == 0
    
    def test_cache_max_entries_cleanup(self):
        """Test cache cleans up when max entries reached."""
        from api.middleware import ResponseCache
        
        cache = ResponseCache(max_entries=5, ttl_seconds=300)
        
        # Add more than max entries
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")
        
        # Should have cleaned up to near max
        assert len(cache.cache) <= 5


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware class."""
    
    def test_is_allowed_under_limit(self):
        """Test requests under limit are allowed."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock(), requests_per_minute=30)
        
        client_ip = "192.168.1.1"
        
        # Add some requests
        for _ in range(25):
            middleware._record_request(client_ip)
        
        assert middleware._is_allowed(client_ip)
    
    def test_is_not_allowed_over_limit(self):
        """Test requests over limit are blocked."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock(), requests_per_minute=30)
        
        client_ip = "192.168.1.2"
        
        # Exceed limit
        for _ in range(35):
            middleware._record_request(client_ip)
        
        assert not middleware._is_allowed(client_ip)
    
    def test_different_ips_tracked_separately(self):
        """Test each IP has its own rate limit."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock(), requests_per_minute=30)
        
        # Fill up IP 1
        for _ in range(30):
            middleware._record_request("192.168.1.1")
        
        # IP 2 should still be allowed
        assert middleware._is_allowed("192.168.1.2")
    
    def test_get_client_ip_direct(self):
        """Test getting client IP from direct connection."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock())
        
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        ip = middleware._get_client_ip(request)
        
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_forwarded(self):
        """Test getting client IP from X-Forwarded-For header."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock())
        
        request = Mock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        ip = middleware._get_client_ip(request)
        
        assert ip == "10.0.0.1"
    
    def test_get_client_ip_real_ip(self):
        """Test getting client IP from X-Real-IP header."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock())
        
        request = Mock()
        request.headers = {"X-Real-IP": "10.0.0.5"}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        ip = middleware._get_client_ip(request)
        
        assert ip == "10.0.0.5"
    
    def test_cleanup_removes_old_records(self):
        """Test cleanup removes expired request records."""
        from api.middleware import RateLimitMiddleware
        
        middleware = RateLimitMiddleware(Mock())
        middleware.cleanup_interval = 0  # Force immediate cleanup
        
        # Add old timestamp (61 seconds ago)
        old_time = time.time() - 61
        middleware.request_counts["192.168.1.1"] = [old_time]
        middleware.last_cleanup = 0
        
        # Trigger cleanup
        middleware._cleanup_old_records()
        
        # Old records should be removed
        assert len(middleware.request_counts.get("192.168.1.1", [])) == 0


class TestAPIKeyMiddleware:
    """Tests for APIKeyMiddleware class."""
    
    def test_disabled_allows_all(self):
        """Test disabled middleware allows all requests."""
        from api.middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(Mock(), enabled=False)
        
        assert not middleware.enabled
    
    def test_valid_api_key_accepted(self):
        """Test valid API key is accepted."""
        from api.middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(
            Mock(),
            api_keys=["valid-key-123"],
            enabled=True
        )
        
        assert "valid-key-123" in middleware.api_keys
    
    def test_multiple_api_keys_supported(self):
        """Test multiple API keys can be configured."""
        from api.middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(
            Mock(),
            api_keys=["key1", "key2", "key3"],
            enabled=True
        )
        
        assert "key1" in middleware.api_keys
        assert "key2" in middleware.api_keys
        assert "key3" in middleware.api_keys
    
    def test_exempt_paths_not_checked(self):
        """Test exempt paths bypass authentication."""
        from api.middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(
            Mock(),
            exempt_paths=["/api/health", "/"],
            enabled=True
        )
        
        assert "/api/health" in middleware.exempt_paths


class TestErrorHandlingMiddleware:
    """Tests for ErrorHandlingMiddleware class."""
    
    def test_generate_request_id(self):
        """Test request ID generation."""
        from api.middleware import ErrorHandlingMiddleware
        
        middleware = ErrorHandlingMiddleware(Mock())
        
        request = Mock()
        request.url.path = "/api/query"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        
        id1 = middleware._generate_request_id(request)
        
        # Should be 12 character hex string
        assert len(id1) == 12
        assert all(c in "0123456789abcdef" for c in id1)
    
    def test_debug_mode_setting(self):
        """Test debug mode configuration."""
        from api.middleware import ErrorHandlingMiddleware
        
        middleware_debug = ErrorHandlingMiddleware(Mock(), debug=True)
        middleware_prod = ErrorHandlingMiddleware(Mock(), debug=False)
        
        assert middleware_debug.debug is True
        assert middleware_prod.debug is False


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware class."""
    
    def test_initialization(self):
        """Test middleware initialization."""
        from api.middleware import RequestLoggingMiddleware
        
        middleware = RequestLoggingMiddleware(Mock(), log_headers=True)
        
        assert middleware.log_headers is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
