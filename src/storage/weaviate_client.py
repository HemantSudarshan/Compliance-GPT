"""
weaviate_client.py - Weaviate Vector Database Client

Handles connection and schema setup for Weaviate Cloud.
"""

import logging
from typing import Optional
from dataclasses import dataclass

# Flexible imports for different execution contexts
try:
    from src.utils.logger import setup_logger
    from src.utils.config import config
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    @dataclass
    class config:
        weaviate_url: str = ""
        weaviate_api_key: str = ""
        openai_api_key: str = ""
        embedding_model: str = "text-embedding-3-large"

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter


# Schema definition for ComplianceGPT
COLLECTION_NAME = "ComplianceChunk"

COLLECTION_SCHEMA = {
    "name": COLLECTION_NAME,
    "description": "Regulatory document chunks for compliance Q&A",
    "properties": [
        Property(name="chunk_id", data_type=DataType.TEXT, description="Unique chunk identifier"),
        Property(name="text", data_type=DataType.TEXT, description="Chunk text content"),
        Property(name="source_file", data_type=DataType.TEXT, description="Source PDF filename"),
        Property(name="page_numbers", data_type=DataType.INT_ARRAY, description="Page numbers covered"),
        Property(name="element_ids", data_type=DataType.TEXT_ARRAY, description="Source element IDs"),
        Property(name="token_count", data_type=DataType.INT, description="Token count"),
        Property(name="regulation", data_type=DataType.TEXT, description="Regulation name (GDPR, CCPA, etc.)"),
        Property(name="chunk_index", data_type=DataType.INT, description="Chunk index within regulation"),
    ],
}


class WeaviateClient:
    """
    Client for Weaviate vector database operations.
    
    Handles connection, schema management, and collection operations
    for the ComplianceGPT RAG system.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize Weaviate client.
        
        Args:
            url: Weaviate cluster URL (defaults to env)
            api_key: Weaviate API key (defaults to env)
            openai_api_key: OpenAI API key for vectorization (defaults to env)
        """
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        
        # Find .env file - look in common locations
        possible_paths = [
            Path(__file__).parent.parent.parent / ".env",  # From src/storage/
            Path.cwd() / ".env",
            Path.home() / "ComplianceGPT" / ".env",
        ]
        for env_path in possible_paths:
            if env_path.exists():
                load_dotenv(env_path, override=True)
                break
        
        self.url = url or os.getenv("WEAVIATE_URL", "")
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY", "")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = None
        
    def connect(self) -> "WeaviateClient":
        """
        Establish connection to Weaviate cluster.
        
        Returns:
            Self for method chaining
        """
        if not self.url:
            raise ValueError("Weaviate URL not configured. Set WEAVIATE_URL in .env")
        
        logger.info(f"Connecting to Weaviate at {self.url}")
        
        try:
            # Connect to Weaviate Cloud
            self._client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.url,
                auth_credentials=Auth.api_key(self.api_key) if self.api_key else None,
                headers={
                    "X-OpenAI-Api-Key": self.openai_api_key
                } if self.openai_api_key else None
            )
            
            # Verify connection
            if self._client.is_ready():
                logger.info("Successfully connected to Weaviate")
            else:
                raise ConnectionError("Weaviate cluster is not ready")
                
            return self
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close the Weaviate connection."""
        if self._client:
            self._client.close()
            logger.info("Disconnected from Weaviate")
    
    def __enter__(self) -> "WeaviateClient":
        """Context manager entry."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
    
    @property
    def client(self):
        """Get the underlying Weaviate client."""
        if not self._client:
            raise ConnectionError("Not connected to Weaviate. Call connect() first.")
        return self._client
    
    def create_collection(self, force_recreate: bool = False) -> bool:
        """
        Create the ComplianceChunk collection with schema.
        
        Args:
            force_recreate: If True, delete existing collection first
            
        Returns:
            True if collection was created, False if already exists
        """
        collection_name = COLLECTION_NAME
        
        # Check if collection exists
        if self.client.collections.exists(collection_name):
            if force_recreate:
                logger.warning(f"Deleting existing collection: {collection_name}")
                self.client.collections.delete(collection_name)
            else:
                logger.info(f"Collection {collection_name} already exists")
                return False
        
        logger.info(f"Creating collection: {collection_name}")
        
        # Create collection with OpenAI vectorizer
        self.client.collections.create(
            name=collection_name,
            description=COLLECTION_SCHEMA["description"],
            vectorizer_config=Configure.Vectorizer.text2vec_openai(
                model="text-embedding-3-large",
                dimensions=3072  # text-embedding-3-large dimensions
            ),
            properties=COLLECTION_SCHEMA["properties"]
        )
        
        logger.info(f"Created collection: {collection_name}")
        return True
    
    def get_collection(self):
        """Get the ComplianceChunk collection."""
        return self.client.collections.get(COLLECTION_NAME)
    
    def delete_collection(self) -> bool:
        """Delete the ComplianceChunk collection."""
        if self.client.collections.exists(COLLECTION_NAME):
            self.client.collections.delete(COLLECTION_NAME)
            logger.info(f"Deleted collection: {COLLECTION_NAME}")
            return True
        return False
    
    def get_object_count(self) -> int:
        """Get the number of objects in the collection."""
        try:
            collection = self.get_collection()
            result = collection.aggregate.over_all(total_count=True)
            return result.total_count or 0
        except Exception as e:
            logger.warning(f"Could not get object count: {e}")
            return 0
    
    def health_check(self) -> dict:
        """
        Perform a health check on the Weaviate connection.
        
        Returns:
            Dictionary with health status information
        """
        try:
            is_ready = self.client.is_ready()
            is_live = self.client.is_live()
            object_count = self.get_object_count() if is_ready else 0
            
            return {
                "status": "healthy" if is_ready and is_live else "unhealthy",
                "is_ready": is_ready,
                "is_live": is_live,
                "collection_exists": self.client.collections.exists(COLLECTION_NAME),
                "object_count": object_count
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


def get_weaviate_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None
) -> WeaviateClient:
    """
    Factory function to create a Weaviate client.
    
    Args:
        url: Optional Weaviate URL override
        api_key: Optional API key override
        openai_api_key: Optional OpenAI key override
        
    Returns:
        Connected WeaviateClient instance
    """
    client = WeaviateClient(url=url, api_key=api_key, openai_api_key=openai_api_key)
    return client.connect()


if __name__ == "__main__":
    # Test connection
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("Testing Weaviate connection...")
    
    try:
        with WeaviateClient() as client:
            health = client.health_check()
            print(f"Health check: {health}")
            
            if health["status"] == "healthy":
                print("✅ Weaviate connection successful!")
            else:
                print("⚠️ Weaviate is not fully healthy")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure you have set these environment variables:")
        print("  - WEAVIATE_URL")
        print("  - WEAVIATE_API_KEY")
        print("  - OPENAI_API_KEY")
