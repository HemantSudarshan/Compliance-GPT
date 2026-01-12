"""
FastAPI Backend for ComplianceGPT

REST API for compliance Q&A with citations.
Includes rate limiting, caching, and error handling middleware.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Header, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root / ".env"
load_dotenv(env_path, override=True)

# Create FastAPI app
app = FastAPI(
    title="ComplianceGPT API",
    description="AI-Powered Regulatory Compliance with Citations",
    version="2.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Import and add middleware
from api.middleware import (
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    APIKeyMiddleware,
    HTTPSEnforceMiddleware,
    response_cache
)

# Add middleware (order matters - first added is outermost)
app.add_middleware(HTTPSEnforceMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=int(os.getenv("RATE_LIMIT_REQUESTS", "30")))
app.add_middleware(APIKeyMiddleware)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin router (for multi-tenancy management)
from api.admin import router as admin_router
app.include_router(admin_router)

# Set up health check routes
from api.health import setup_health_routes
setup_health_routes(app, version="2.1.0")


# Request/Response models with validation
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="The compliance question to ask")
    regulation: Optional[str] = Field(None, description="Filter by regulation (GDPR, CCPA, PCI-DSS)")
    
    @field_validator('question')
    @classmethod
    def clean_question(cls, v: str) -> str:
        return v.strip()


class CitationResponse(BaseModel):
    citation_id: int
    text: str
    source_file: str
    page_numbers: list
    regulation: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    has_context: bool
    provider: str
    model: str
    cached: bool = False
    response_time_ms: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    weaviate: str
    llm_provider: str
    indexed_chunks: int
    timestamp: str
    version: str = "2.1"


class StatsResponse(BaseModel):
    total_queries: int
    cache_size: int
    uptime_seconds: float


# Track startup time for stats
_startup_time = datetime.now()
_query_count = 0


# Admin authentication dependency
async def verify_admin_token(x_admin_token: str = Header(None)):
    """Verify admin API token for protected endpoints."""
    admin_token = os.getenv("ADMIN_API_TOKEN")
    
    if not admin_token:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints are not configured. Set ADMIN_API_TOKEN in .env"
        )
    
    if not x_admin_token or x_admin_token != admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token. Provide X-Admin-Token header."
        )
    
    return x_admin_token


# API Routes
@app.get("/")
async def root():
    """Serve the frontend."""
    return FileResponse(project_root / "frontend" / "index.html")


@app.get("/api/health")
async def health_check() -> HealthResponse:
    """Check system health."""
    try:
        from src.storage.weaviate_client import WeaviateClient
        
        with WeaviateClient() as client:
            health = client.health_check()
            
        return HealthResponse(
            status="healthy" if health.get("status") == "healthy" else "degraded",
            weaviate=health.get("status", "unknown"),
            llm_provider=os.getenv("LLM_PROVIDER", "groq"),
            indexed_chunks=health.get("object_count", 0),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            weaviate=str(e),
            llm_provider=os.getenv("LLM_PROVIDER", "groq"),
            indexed_chunks=0,
            timestamp=datetime.now().isoformat()
        )


@app.get("/api/stats")
async def get_stats() -> StatsResponse:
    """Get API usage statistics."""
    global _query_count
    uptime = (datetime.now() - _startup_time).total_seconds()
    return StatsResponse(
        total_queries=_query_count,
        cache_size=len(response_cache.cache),
        uptime_seconds=uptime
    )


@app.post("/api/query")
async def query_compliance(request: QueryRequest) -> QueryResponse:
    """Answer a compliance question with citations."""
    import time
    global _query_count
    start_time = time.time()
    
    # Check cache first
    cache_key = response_cache.make_key(request.question, request.regulation)
    cached_response = response_cache.get(cache_key)
    
    if cached_response:
        cached_response["cached"] = True
        cached_response["response_time_ms"] = (time.time() - start_time) * 1000
        return QueryResponse(**cached_response)
    
    try:
        from src.storage.weaviate_client import WeaviateClient
        from src.generation.citation_engine import CitationEngine
        
        with WeaviateClient() as client:
            engine = CitationEngine(client)
            response = engine.query(
                request.question,
                regulation_filter=request.regulation if request.regulation != "All" else None
            )
        
        citations = [
            CitationResponse(
                citation_id=c.citation_id,
                text=c.text,
                source_file=c.source_file,
                page_numbers=c.page_numbers,
                regulation=c.regulation
            )
            for c in response.citations
        ]
        
        result = QueryResponse(
            answer=response.answer,
            citations=citations,
            has_context=response.has_context,
            provider=response.metadata.get("provider", "groq"),
            model=response.metadata.get("model", "llama-3.3-70b"),
            cached=False,
            response_time_ms=(time.time() - start_time) * 1000
        )
        
        # Cache the response
        response_cache.set(cache_key, result.model_dump())
        _query_count += 1
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cache")
async def clear_cache(token: str = Depends(verify_admin_token)):
    """Clear the response cache (admin endpoint - requires X-Admin-Token header)."""
    response_cache.clear()
    return {"status": "success", "message": "Cache cleared"}


@app.get("/api/regulations")
async def get_regulations():
    """Get available regulations."""
    return {
        "regulations": [
            {"id": "all", "name": "All Regulations", "icon": "📚"},
            {"id": "GDPR", "name": "GDPR", "icon": "🇪🇺"},
            {"id": "CCPA", "name": "CCPA", "icon": "🇺🇸"},
            {"id": "PCI-DSS", "name": "PCI-DSS", "icon": "💳"},
        ]
    }


@app.get("/api/version")
async def get_version():
    """Get API version info."""
    return {
        "version": "2.1",
        "name": "ComplianceGPT",
        "python": sys.version.split()[0],
        "features": [
            "rate_limiting",
            "caching",
            "multi_llm_support",
            "hybrid_search",
            "audit_logging",
            "prometheus_metrics"
        ]
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    from api.metrics import metrics
    
    return PlainTextResponse(
        content=metrics.format_prometheus(),
        media_type="text/plain; charset=utf-8"
    )


@app.get("/api/audit")
async def get_audit_logs(
    limit: int = Query(default=50, le=500),
    action: Optional[str] = None,
    token: str = Depends(verify_admin_token)
):
    """Get recent audit logs (admin endpoint - requires X-Admin-Token header)."""
    from api.audit import audit_logger
    
    logs = audit_logger.query_logs(action=action, limit=limit)
    return {"logs": logs, "count": len(logs)}


# Mount static files
frontend_path = project_root / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
