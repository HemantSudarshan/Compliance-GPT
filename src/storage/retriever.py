"""
retriever.py - Hybrid Search Retriever

Implements hybrid (semantic + keyword) search with configurable alpha.
"""

import logging
from typing import Optional
from dataclasses import dataclass

# Flexible imports
try:
    from src.utils.logger import setup_logger
    from src.utils.config import config
    from src.storage.weaviate_client import WeaviateClient, COLLECTION_NAME
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    COLLECTION_NAME = "ComplianceChunk"
    
    @dataclass
    class config:
        top_k: int = 5
        hybrid_alpha: float = 0.3


@dataclass
class RetrievalResult:
    """Represents a retrieved chunk with score."""
    
    chunk_id: str
    text: str
    source_file: str
    page_numbers: list
    regulation: str
    score: float
    metadata: dict
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_numbers": self.page_numbers,
            "regulation": self.regulation,
            "score": self.score,
            "metadata": self.metadata
        }


class HybridRetriever:
    """
    Retrieves relevant chunks using hybrid search.
    
    Combines semantic (vector) and keyword (BM25) search
    with configurable weighting via alpha parameter.
    """
    
    def __init__(
        self,
        weaviate_client: "WeaviateClient",
        top_k: int = None,
        alpha: float = None
    ):
        """
        Initialize the retriever.
        
        Args:
            weaviate_client: Connected WeaviateClient instance
            top_k: Number of results to return
            alpha: Hybrid search alpha (0=keyword, 1=semantic, 0.3 recommended)
        """
        self.client = weaviate_client
        self.top_k = top_k or config.top_k
        self.alpha = alpha if alpha is not None else config.hybrid_alpha
        
        # Compliance-specific synonyms for query expansion
        self.synonyms = {
            "unauthorized access": "personal data breach security incident",
            "breach": "personal data breach security incident notification Article 33 Article 34",
            "employee access": "controller processor internal security breach",
            "data breach": "personal data breach notification 72 hours supervisory authority",
            "erasure": "right to erasure right to be forgotten Article 17 deletion",
            "deletion": "erasure right to be forgotten Article 17",
            "consent": "data subject consent lawful basis Article 7 freely given",
            "fines": "penalties administrative fines Article 83 sanctions",
            "penalties": "fines administrative fines Article 83 sanctions infringement",
            "rights": "data subject rights access rectification erasure portability",
            "security": "technical measures organizational measures Article 32 encryption",
            "ml model": "automated decision profiling Article 22 machine learning",
            "machine learning": "automated decision profiling Article 22 algorithmic",
            "ai": "automated decision profiling Article 22 artificial intelligence",
            "notification": "notify supervisory authority 72 hours Article 33",
            "dpia": "data protection impact assessment Article 35 high risk",
            "transfer": "international transfer third country adequacy Article 44",
            "biometric": "special categories sensitive data Article 9",
        }
    
    def _expand_query(self, query: str) -> str:
        """Expand query with compliance-specific synonyms."""
        query_lower = query.lower()
        expanded = query
        
        for term, synonyms in self.synonyms.items():
            if term in query_lower:
                expanded = f"{expanded} {synonyms}"
        
        # Also add regulation name to query for better matching
        if "gdpr" not in query_lower and any(word in query_lower for word in ["article", "breach", "consent", "erasure", "data"]):
            expanded = f"{expanded} GDPR"
        
        return expanded
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        alpha: Optional[float] = None,
        regulation_filter: Optional[str] = None
    ) -> list[RetrievalResult]:
        """
        Perform hybrid search for relevant chunks.
        
        Args:
            query: Search query string
            top_k: Override default top_k
            alpha: Override default alpha
            regulation_filter: Filter by regulation name
            
        Returns:
            List of RetrievalResult objects
        """
        from weaviate.classes.query import MetadataQuery, Filter
        
        k = top_k or self.top_k
        
        # Query expansion - add synonyms for better keyword matching
        expanded_query = self._expand_query(query)
        
        logger.info(f"Searching for: '{query[:50]}...' (top_k={k}, using BM25)")
        logger.info(f"Expanded query: '{expanded_query[:100]}...'")
        
        collection = self.client.get_collection()
        
        # Build filter if regulation specified
        filters = None
        if regulation_filter:
            filters = Filter.by_property("regulation").equal(regulation_filter)
        
        # Perform BM25 keyword search (no vectorizer needed)
        try:
            response = collection.query.bm25(
                query=expanded_query,
                limit=k,
                return_metadata=MetadataQuery(score=True),
                filters=filters
            )
            
            results = []
            for obj in response.objects:
                result = RetrievalResult(
                    chunk_id=obj.properties.get("chunk_id", ""),
                    text=obj.properties.get("text", ""),
                    source_file=obj.properties.get("source_file", ""),
                    page_numbers=obj.properties.get("page_numbers", []),
                    regulation=obj.properties.get("regulation", ""),
                    score=obj.metadata.score if obj.metadata else 0.0,
                    metadata={
                        "token_count": obj.properties.get("token_count", 0),
                        "chunk_index": obj.properties.get("chunk_index", 0),
                        "element_ids": obj.properties.get("element_ids", [])
                    }
                )
                results.append(result)
            
            logger.info(f"Found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def search_by_keyword(
        self,
        query: str,
        top_k: Optional[int] = None,
        regulation_filter: Optional[str] = None
    ) -> list[RetrievalResult]:
        """
        Perform keyword-only (BM25) search.
        
        Args:
            query: Search query string
            top_k: Number of results
            regulation_filter: Filter by regulation
            
        Returns:
            List of RetrievalResult objects
        """
        return self.search(query, top_k=top_k, alpha=0.0, regulation_filter=regulation_filter)
    
    def search_by_semantic(
        self,
        query: str,
        top_k: Optional[int] = None,
        regulation_filter: Optional[str] = None
    ) -> list[RetrievalResult]:
        """
        Perform semantic-only (vector) search.
        
        Args:
            query: Search query string
            top_k: Number of results
            regulation_filter: Filter by regulation
            
        Returns:
            List of RetrievalResult objects
        """
        return self.search(query, top_k=top_k, alpha=1.0, regulation_filter=regulation_filter)
    
    def get_context_for_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        regulation_filter: Optional[str] = None
    ) -> str:
        """
        Get formatted context string for LLM generation.
        
        Args:
            query: Search query
            top_k: Number of chunks to include
            regulation_filter: Filter by regulation
            
        Returns:
            Formatted context string with citations
        """
        results = self.search(query, top_k=top_k, regulation_filter=regulation_filter)
        
        if not results:
            return "No relevant context found in the document database."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            citation = f"[{i}]"
            source = f"{result.source_file}, Page {result.page_numbers}"
            context_parts.append(
                f"{citation} Source: {source}\n{result.text}\n"
            )
        
        return "\n---\n".join(context_parts)


def search_regulations(
    query: str,
    top_k: int = 5,
    alpha: float = 0.3,
    regulation: Optional[str] = None,
    weaviate_url: Optional[str] = None,
    weaviate_api_key: Optional[str] = None
) -> list[RetrievalResult]:
    """
    Convenience function to search regulations.
    
    Args:
        query: Search query
        top_k: Number of results
        alpha: Hybrid search alpha
        regulation: Filter by regulation
        weaviate_url: Optional Weaviate URL
        weaviate_api_key: Optional API key
        
    Returns:
        List of RetrievalResult objects
    """
    from src.storage.weaviate_client import WeaviateClient
    
    with WeaviateClient(url=weaviate_url, api_key=weaviate_api_key) as client:
        retriever = HybridRetriever(client, top_k=top_k, alpha=alpha)
        return retriever.search(query, regulation_filter=regulation)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
        from src.storage.weaviate_client import WeaviateClient
        
        print(f"Searching for: {query}\n")
        
        with WeaviateClient() as client:
            retriever = HybridRetriever(client)
            results = retriever.search(query)
            
            for i, result in enumerate(results, 1):
                print(f"\n[{i}] Score: {result.score:.4f}")
                print(f"    Source: {result.source_file}, Pages: {result.page_numbers}")
                print(f"    Text: {result.text[:200]}...")
    else:
        print("Usage: python retriever.py <query>")
