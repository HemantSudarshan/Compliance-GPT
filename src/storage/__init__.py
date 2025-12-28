"""
ComplianceGPT - Storage Module

Handles vector database operations with Weaviate.
"""

from src.storage.weaviate_client import (
    WeaviateClient,
    get_weaviate_client,
    COLLECTION_NAME,
    COLLECTION_SCHEMA
)
from src.storage.indexer import (
    DocumentIndexer,
    index_regulation_chunks
)
from src.storage.retriever import (
    HybridRetriever,
    RetrievalResult,
    search_regulations
)

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
]
