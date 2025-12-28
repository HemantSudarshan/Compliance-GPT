"""
FastAPI Backend for ComplianceGPT

REST API for compliance Q&A with citations.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
    version="2.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class SessionCreateRequest(BaseModel):
    metadata: Optional[dict] = None


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    metadata: dict


class QueryRequest(BaseModel):
    question: str
    regulation: Optional[str] = None
    session_id: Optional[str] = None


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
    session_id: Optional[str] = None


class QueryHistoryItem(BaseModel):
    query_id: str
    question: str
    answer: str
    regulation_filter: Optional[str]
    num_citations: int
    timestamp: str


class QueryHistoryResponse(BaseModel):
    session_id: str
    queries: list[QueryHistoryItem]


class HealthResponse(BaseModel):
    status: str
    weaviate: str
    llm_provider: str
    indexed_chunks: int


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
            indexed_chunks=health.get("object_count", 0)
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            weaviate=str(e),
            llm_provider=os.getenv("LLM_PROVIDER", "groq"),
            indexed_chunks=0
        )


@app.post("/api/query")
async def query_compliance(request: QueryRequest) -> QueryResponse:
    """Answer a compliance question with citations."""
    try:
        from src.storage.weaviate_client import WeaviateClient
        from src.generation.citation_engine import CitationEngine
        from src.storage.session_db import SessionDatabase
        
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
        
        # Log query to session database if session_id provided
        if request.session_id:
            try:
                db = SessionDatabase()
                db.log_query(
                    session_id=request.session_id,
                    question=request.question,
                    answer=response.answer,
                    regulation_filter=request.regulation if request.regulation != "All" else None,
                    num_citations=len(response.citations),
                    has_context=response.has_context,
                    metadata=response.metadata
                )
            except Exception as e:
                # Don't fail the query if logging fails
                logging.warning(f"Failed to log query: {e}")
        
        return QueryResponse(
            answer=response.answer,
            citations=citations,
            has_context=response.has_context,
            provider=response.metadata.get("provider", "groq"),
            model=response.metadata.get("model", "llama-3.3-70b"),
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.post("/api/sessions")
async def create_session(request: SessionCreateRequest) -> SessionResponse:
    """Create a new user session."""
    try:
        from src.storage.session_db import SessionDatabase
        
        db = SessionDatabase()
        session = db.create_session(metadata=request.metadata)
        
        return SessionResponse(
            session_id=session.session_id,
            created_at=session.created_at,
            last_activity=session.last_activity,
            metadata=session.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 50) -> QueryHistoryResponse:
    """Get query history for a session."""
    try:
        from src.storage.session_db import SessionDatabase
        
        db = SessionDatabase()
        
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get query history
        history = db.get_session_history(session_id, limit=limit)
        
        queries = [
            QueryHistoryItem(
                query_id=record.query_id,
                question=record.question,
                answer=record.answer,
                regulation_filter=record.regulation_filter,
                num_citations=record.num_citations,
                timestamp=record.timestamp
            )
            for record in history
        ]
        
        return QueryHistoryResponse(
            session_id=session_id,
            queries=queries
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files
frontend_path = project_root / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
