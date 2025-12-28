"""
indexer.py - Document Indexer

Batch indexes chunks into Weaviate with embeddings.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Flexible imports
try:
    from src.utils.logger import setup_logger
    from src.utils.config import config
    from src.storage.weaviate_client import WeaviateClient, COLLECTION_NAME
    from src.ingestion.chunker import Chunk
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    COLLECTION_NAME = "ComplianceChunk"
    
    @dataclass
    class config:
        openai_api_key: str = ""


class DocumentIndexer:
    """
    Indexes document chunks into Weaviate vector database.
    
    Handles batch uploads with progress tracking and error handling.
    """
    
    def __init__(self, weaviate_client: "WeaviateClient", batch_size: int = 100):
        """
        Initialize the indexer.
        
        Args:
            weaviate_client: Connected WeaviateClient instance
            batch_size: Number of objects to upload per batch
        """
        self.client = weaviate_client
        self.batch_size = batch_size
        self._indexed_count = 0
        self._error_count = 0
    
    def index_chunks(
        self,
        chunks: list,
        show_progress: bool = True
    ) -> dict:
        """
        Index a list of chunks into Weaviate.
        
        Args:
            chunks: List of Chunk objects or dicts
            show_progress: Whether to log progress
            
        Returns:
            Dictionary with indexing statistics
        """
        if not chunks:
            logger.warning("No chunks to index")
            return {"indexed": 0, "errors": 0}
        
        logger.info(f"Starting to index {len(chunks)} chunks...")
        
        collection = self.client.get_collection()
        
        self._indexed_count = 0
        self._error_count = 0
        
        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            
            try:
                with collection.batch.dynamic() as batch_writer:
                    for chunk in batch:
                        chunk_data = self._prepare_chunk_data(chunk)
                        if chunk_data:
                            batch_writer.add_object(properties=chunk_data)
                            self._indexed_count += 1
                
                if show_progress:
                    progress = min(i + self.batch_size, len(chunks))
                    logger.info(f"Indexed {progress}/{len(chunks)} chunks")
                    
            except Exception as e:
                logger.error(f"Batch indexing error: {e}")
                self._error_count += len(batch)
        
        result = {
            "indexed": self._indexed_count,
            "errors": self._error_count,
            "total": len(chunks)
        }
        
        logger.info(f"Indexing complete: {result}")
        return result
    
    def _prepare_chunk_data(self, chunk) -> Optional[dict]:
        """
        Prepare chunk data for Weaviate insertion.
        
        Args:
            chunk: Chunk object or dict
            
        Returns:
            Dictionary formatted for Weaviate
        """
        try:
            # Handle both Chunk objects and dicts
            if hasattr(chunk, 'to_dict'):
                data = chunk.to_dict()
            elif isinstance(chunk, dict):
                data = chunk
            else:
                logger.warning(f"Unknown chunk type: {type(chunk)}")
                return None
            
            # Map to Weaviate schema
            return {
                "chunk_id": data.get("chunk_id", ""),
                "text": data.get("text", ""),
                "source_file": data.get("source_file", ""),
                "page_numbers": data.get("page_numbers", []),
                "element_ids": data.get("element_ids", []),
                "token_count": data.get("token_count", 0),
                "regulation": data.get("metadata", {}).get("regulation", "unknown"),
                "chunk_index": data.get("metadata", {}).get("chunk_index", 0)
            }
            
        except Exception as e:
            logger.warning(f"Failed to prepare chunk data: {e}")
            self._error_count += 1
            return None
    
    def index_from_json(
        self,
        json_path: str | Path,
        regulation_name: Optional[str] = None
    ) -> dict:
        """
        Index chunks from a JSON file.
        
        Args:
            json_path: Path to JSON file with chunks
            regulation_name: Optional regulation name override
            
        Returns:
            Indexing statistics
        """
        json_path = Path(json_path)
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        logger.info(f"Loading chunks from {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both formats: list of chunks or {"chunks": [...]}
        if isinstance(data, list):
            chunks = data
        elif isinstance(data, dict) and "chunks" in data:
            chunks = data["chunks"]
        elif isinstance(data, dict) and "elements" in data:
            # This is parsed elements, not chunks
            raise ValueError("JSON contains parsed elements, not chunks. Run chunker first.")
        else:
            raise ValueError(f"Unknown JSON format in {json_path}")
        
        # Override regulation name if provided
        if regulation_name:
            for chunk in chunks:
                if isinstance(chunk, dict):
                    if "metadata" not in chunk:
                        chunk["metadata"] = {}
                    chunk["metadata"]["regulation"] = regulation_name
        
        return self.index_chunks(chunks)
    
    def delete_by_regulation(self, regulation_name: str) -> int:
        """
        Delete all chunks for a specific regulation.
        
        Args:
            regulation_name: Name of regulation to delete
            
        Returns:
            Number of objects deleted
        """
        from weaviate.classes.query import Filter
        
        collection = self.client.get_collection()
        
        # Count before deletion
        before = self.client.get_object_count()
        
        # Delete objects matching regulation
        collection.data.delete_many(
            where=Filter.by_property("regulation").equal(regulation_name)
        )
        
        # Count after deletion
        after = self.client.get_object_count()
        deleted = before - after
        
        logger.info(f"Deleted {deleted} chunks for regulation: {regulation_name}")
        return deleted


def index_regulation_chunks(
    chunks: list,
    weaviate_url: Optional[str] = None,
    weaviate_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    batch_size: int = 100
) -> dict:
    """
    Convenience function to index regulation chunks.
    
    Args:
        chunks: List of Chunk objects or dicts
        weaviate_url: Optional Weaviate URL
        weaviate_api_key: Optional Weaviate API key
        openai_api_key: Optional OpenAI API key
        batch_size: Batch size for uploads
        
    Returns:
        Indexing statistics
    """
    from src.storage.weaviate_client import WeaviateClient
    
    with WeaviateClient(
        url=weaviate_url,
        api_key=weaviate_api_key,
        openai_api_key=openai_api_key
    ) as client:
        # Ensure collection exists
        client.create_collection(force_recreate=False)
        
        # Index chunks
        indexer = DocumentIndexer(client, batch_size=batch_size)
        return indexer.index_chunks(chunks)


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        regulation = sys.argv[2] if len(sys.argv) > 2 else None
        
        from src.storage.weaviate_client import WeaviateClient
        
        print(f"Indexing chunks from {json_file}...")
        
        with WeaviateClient() as client:
            client.create_collection(force_recreate=False)
            indexer = DocumentIndexer(client)
            result = indexer.index_from_json(json_file, regulation)
            print(f"Result: {result}")
    else:
        print("Usage: python indexer.py <chunks.json> [regulation_name]")
