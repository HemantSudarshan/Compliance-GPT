"""
middleware.py - FastAPI Middleware Components

Provides rate limiting, authentication, and error handling middleware.
"""

import time
import os
import hashlib
from typing import Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse.
    
    Features:
    - Configurable requests per minute limit
    - IP-based tracking
    - Sliding window algorithm
    - Exempt paths (health checks)
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 30,
        exempt_paths: list[str] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.exempt_paths = exempt_paths or ["/api/health", "/", "/static"]
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if not self._is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self._record_request(client_ip)
        
        # Periodic cleanup
        self._cleanup_old_records()
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_allowed(self, client_ip: str) -> bool:
        """Check if the client is within rate limits."""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Count requests in the current window
        recent_requests = [
            ts for ts in self.request_counts[client_ip]
            if ts > window_start
        ]
        
        return len(recent_requests) < self.requests_per_minute
    
    def _record_request(self, client_ip: str):
        """Record a request timestamp."""
        self.request_counts[client_ip].append(time.time())
    
    def _cleanup_old_records(self):
        """Remove old request records to prevent memory bloat."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        window_start = now - 60
        
        for client_ip in list(self.request_counts.keys()):
            self.request_counts[client_ip] = [
                ts for ts in self.request_counts[client_ip]
                if ts > window_start
            ]
            
            # Remove empty entries
            if not self.request_counts[client_ip]:
                del self.request_counts[client_ip]
        
        self.last_cleanup = now


# =============================================================================
# API Key Authentication Middleware
# =============================================================================

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Optional API key authentication middleware.
    
    Features:
    - Header-based API key validation
    - Multiple valid keys support
    - Exempt paths for public endpoints
    - Configurable via environment variable
    """
    
    def __init__(
        self,
        app,
        api_keys: list[str] = None,
        header_name: str = "X-API-Key",
        exempt_paths: list[str] = None,
        enabled: bool = None
    ):
        super().__init__(app)
        
        # Get API keys from environment or parameter
        env_keys = os.getenv("COMPLIANCEGPT_API_KEYS", "")
        self.api_keys = set(api_keys or [])
        if env_keys:
            self.api_keys.update(env_keys.split(","))
        
        self.header_name = header_name
        self.exempt_paths = exempt_paths or [
            "/api/health",
            "/",
            "/static",
            "/docs",
            "/openapi.json"
        ]
        
        # Enable/disable based on env or parameter
        if enabled is None:
            self.enabled = bool(self.api_keys) and os.getenv("ENABLE_API_AUTH", "false").lower() == "true"
        else:
            self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip if authentication is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get(self.header_name)
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication required",
                    "message": f"Missing {self.header_name} header"
                }
            )
        
        # Validate API key
        if api_key not in self.api_keys:
            logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Invalid API key",
                    "message": "The provided API key is not valid"
                }
            )
        
        return await call_next(request)


# =============================================================================
# Error Handling Middleware
# =============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Features:
    - Catches unhandled exceptions
    - Returns consistent error responses
    - Logs errors for debugging
    - Hides internal details in production
    """
    
    def __init__(self, app, debug: bool = None):
        super().__init__(app)
        self.debug = debug if debug is not None else os.getenv("DEBUG", "false").lower() == "true"
    
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        
        except Exception as e:
            logger.exception(f"Unhandled error processing {request.method} {request.url.path}")
            
            # Build error response
            error_response = {
                "error": "Internal server error",
                "message": "An unexpected error occurred while processing your request",
                "request_id": self._generate_request_id(request)
            }
            
            # Include details in debug mode
            if self.debug:
                error_response["debug"] = {
                    "exception": type(e).__name__,
                    "detail": str(e)
                }
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response
            )
    
    def _generate_request_id(self, request: Request) -> str:
        """Generate a unique request ID for tracking."""
        data = f"{time.time()}{request.url.path}{request.client.host if request.client else ''}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/Response logging middleware.
    
    Features:
    - Logs request method, path, and timing
    - Tracks response status codes
    - Useful for monitoring and debugging
    """
    
    def __init__(self, app, log_headers: bool = False):
        super().__init__(app)
        self.log_headers = log_headers
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        if self.log_headers:
            logger.debug(f"  Headers: {dict(request.headers)}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log response
        status_emoji = "✓" if response.status_code < 400 else "✗"
        logger.info(f"← {status_emoji} {response.status_code} ({duration:.0f}ms)")
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.0f}ms"
        
        return response


# =============================================================================
# Simple In-Memory Cache
# =============================================================================

class ResponseCache:
    """
    Simple in-memory cache for API responses.
    
    Features:
    - TTL-based expiration
    - Query-based cache keys
    - Memory-efficient LRU-like cleanup
    """
    
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 1000):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.cache: dict[str, tuple[any, float]] = {}
    
    def get(self, key: str) -> Optional[any]:
        """Get a cached value if not expired."""
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: any):
        """Cache a value with current timestamp."""
        # Cleanup if cache is full
        if len(self.cache) >= self.max_entries:
            self._cleanup()
        
        self.cache[key] = (value, time.time())
    
    def _cleanup(self):
        """Remove expired entries and oldest if still over limit."""
        now = time.time()
        
        # Remove expired
        self.cache = {
            k: v for k, v in self.cache.items()
            if now - v[1] <= self.ttl
        }
        
        # If still over limit, remove oldest
        if len(self.cache) >= self.max_entries:
            sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])
            for key in sorted_keys[:len(self.cache) - self.max_entries + 100]:
                del self.cache[key]
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
    
    @staticmethod
    def make_key(query: str, regulation: str = None) -> str:
        """Generate a cache key from query parameters."""
        data = f"{query.lower().strip()}:{regulation or 'all'}"
        return hashlib.md5(data.encode()).hexdigest()


# Global cache instance
response_cache = ResponseCache()


# =============================================================================
# HTTPS Enforcement Middleware
# =============================================================================

class HTTPSEnforceMiddleware(BaseHTTPMiddleware):
    """
    Enforce HTTPS in production environments.
    
    Features:
    - Only active when ENVIRONMENT=production
    - Allows local development over HTTP
    - Returns 400 for non-HTTPS production requests
    """
    
    def __init__(self, app, enabled: bool = None):
        super().__init__(app)
        
        if enabled is None:
            env = os.getenv("ENVIRONMENT", "development").lower()
            self.enabled = env == "production"
        else:
            self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled:
            return await call_next(request)
        
        # Check if request is HTTPS
        if request.url.scheme != "https":
            # Allow localhost/127.0.0.1 for testing
            host = request.headers.get("host", "").split(":")[0]
            if host in ["localhost", "127.0.0.1"]:
                return await call_next(request)
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "HTTPS required",
                    "message": "This API requires HTTPS in production. Please use https:// instead of http://"
                }
            )
        
        return await call_next(request)
