"""
FastAPI Backend for ComplianceGPT

REST API for compliance Q&A with citations.
"""

import os
import sys
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
class QueryRequest(BaseModel):
    question: str
    regulation: Optional[str] = None


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
        
        return QueryResponse(
            answer=response.answer,
            citations=citations,
            has_context=response.has_context,
            provider=response.metadata.get("provider", "groq"),
            model=response.metadata.get("model", "llama-3.3-70b")
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


# Mount static files
frontend_path = project_root / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
