"""
ComplianceGPT - Storage Module

Handles vector database operations with Weaviate and session tracking.
"""

# Lazy imports to avoid requiring all dependencies for partial use
def __getattr__(name):
    """Lazy import to avoid requiring weaviate for session_db."""
    if name in ["WeaviateClient", "get_weaviate_client", "COLLECTION_NAME", "COLLECTION_SCHEMA"]:
        from src.storage.weaviate_client import (
            WeaviateClient,
            get_weaviate_client,
            COLLECTION_NAME,
            COLLECTION_SCHEMA
        )
        return globals()[name]
    elif name in ["DocumentIndexer", "index_regulation_chunks"]:
        from src.storage.indexer import (
            DocumentIndexer,
            index_regulation_chunks
        )
        return globals()[name]
    elif name in ["HybridRetriever", "RetrievalResult", "search_regulations"]:
        from src.storage.retriever import (
            HybridRetriever,
            RetrievalResult,
            search_regulations
        )
        return globals()[name]
    elif name in ["SessionDatabase", "get_session_database", "Session", "QueryRecord"]:
        from src.storage.session_db import (
            SessionDatabase,
            get_session_database,
            Session,
            QueryRecord
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Client
    "WeaviateClient",
    "get_weaviate_client",
    "COLLECTION_NAME",
    "COLLECTION_SCHEMA",
    # Indexer
    "DocumentIndexer",
    "index_regulation_chunks",
    # Retriever
    "HybridRetriever",
    "RetrievalResult",
    "search_regulations",
    # Session tracking
    "SessionDatabase",
    "get_session_database",
    "Session",
    "QueryRecord",
]
