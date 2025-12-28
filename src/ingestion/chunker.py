"""
chunker.py - Semantic Text Chunking

Splits parsed documents into optimal chunks for embedding.
Target: 512 tokens with 50 token overlap.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging
import tiktoken

# Flexible imports for different execution contexts
try:
    from src.ingestion.parser import ParsedElement
    from src.utils.logger import setup_logger
    from src.utils.config import config
    logger = setup_logger(__name__)
except ImportError:
    # Fallback for direct execution or testing
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    class config:
        chunk_size = 512
        chunk_overlap = 50
    
    # Import ParsedElement with fallback
    try:
        from parser import ParsedElement
    except ImportError:
        from dataclasses import dataclass as dc, field as f
        @dc
        class ParsedElement:
            element_id: str
            element_type: str
            text: str
            page_number: int
            source_file: str
            metadata: dict = f(default_factory=dict)
            bbox: Optional[dict] = None


@dataclass
class Chunk:
    """Represents a text chunk ready for embedding."""
    
    chunk_id: str
    text: str
    source_file: str
    page_numbers: list[int]
    element_ids: list[str]
    token_count: int
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "page_numbers": self.page_numbers,
            "element_ids": self.element_ids,
            "token_count": self.token_count,
            "metadata": self.metadata
        }


class SemanticChunker:
    """
    Chunks parsed elements into optimal sizes for embedding.
    
    Uses token-based chunking with configurable overlap to maintain
    context continuity across chunk boundaries.
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        model: str = "cl100k_base"  # GPT-4/3.5 tokenizer
    ):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
            model: Tokenizer model name
        """
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        self.tokenizer = tiktoken.get_encoding(model)
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.tokenizer.encode(text))
    
    def chunk_elements(
        self,
        elements: list[ParsedElement],
        regulation_name: str = "regulation"
    ) -> list[Chunk]:
        """
        Chunk a list of parsed elements into embedding-ready chunks.
        
        Args:
            elements: List of ParsedElement objects from parser
            regulation_name: Name of the regulation (e.g., 'GDPR')
            
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking {len(elements)} elements with size={self.chunk_size}, overlap={self.chunk_overlap}")
        
        chunks = []
        current_texts = []
        current_elements = []
        current_pages = set()
        current_tokens = 0
        
        for element in elements:
            element_tokens = self.count_tokens(element.text)
            
            # If single element exceeds chunk size, split it
            if element_tokens > self.chunk_size:
                # First, save any accumulated content
                if current_texts:
                    chunk = self._create_chunk(
                        current_texts,
                        current_elements,
                        current_pages,
                        current_tokens,
                        regulation_name,
                        len(chunks)
                    )
                    chunks.append(chunk)
                    current_texts = []
                    current_elements = []
                    current_pages = set()
                    current_tokens = 0
                
                # Split large element
                split_chunks = self._split_large_element(element, regulation_name, len(chunks))
                chunks.extend(split_chunks)
                continue
            
            # Check if adding this element exceeds chunk size
            if current_tokens + element_tokens > self.chunk_size and current_texts:
                # Save current chunk
                chunk = self._create_chunk(
                    current_texts,
                    current_elements,
                    current_pages,
                    current_tokens,
                    regulation_name,
                    len(chunks)
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_texts, overlap_elements, overlap_pages, overlap_tokens = self._get_overlap(
                    current_texts, current_elements, current_pages
                )
                current_texts = overlap_texts
                current_elements = overlap_elements
                current_pages = overlap_pages
                current_tokens = overlap_tokens
            
            # Add element to current chunk
            current_texts.append(element.text)
            current_elements.append(element)
            current_pages.add(element.page_number)
            current_tokens += element_tokens
        
        # Save final chunk
        if current_texts:
            chunk = self._create_chunk(
                current_texts,
                current_elements,
                current_pages,
                current_tokens,
                regulation_name,
                len(chunks)
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {len(elements)} elements")
        return chunks
    
    def _create_chunk(
        self,
        texts: list[str],
        elements: list[ParsedElement],
        pages: set[int],
        token_count: int,
        regulation_name: str,
        chunk_index: int
    ) -> Chunk:
        """Create a Chunk object from accumulated content."""
        source_file = elements[0].source_file if elements else "unknown"
        
        return Chunk(
            chunk_id=f"{regulation_name}_chunk_{chunk_index:04d}",
            text="\n\n".join(texts),
            source_file=source_file,
            page_numbers=sorted(list(pages)),
            element_ids=[e.element_id for e in elements],
            token_count=token_count,
            metadata={
                "regulation": regulation_name,
                "element_types": list(set(e.element_type for e in elements)),
                "chunk_index": chunk_index
            }
        )
    
    def _get_overlap(
        self,
        texts: list[str],
        elements: list[ParsedElement],
        pages: set[int]
    ) -> tuple[list[str], list[ParsedElement], set[int], int]:
        """Get overlap content from the end of current chunk."""
        overlap_texts = []
        overlap_elements = []
        overlap_pages = set()
        overlap_tokens = 0
        
        # Work backwards to get overlap
        for i in range(len(texts) - 1, -1, -1):
            text_tokens = self.count_tokens(texts[i])
            if overlap_tokens + text_tokens <= self.chunk_overlap:
                overlap_texts.insert(0, texts[i])
                overlap_elements.insert(0, elements[i])
                overlap_pages.add(elements[i].page_number)
                overlap_tokens += text_tokens
            else:
                break
        
        return overlap_texts, overlap_elements, overlap_pages, overlap_tokens
    
    def _split_large_element(
        self,
        element: ParsedElement,
        regulation_name: str,
        start_index: int
    ) -> list[Chunk]:
        """Split a large element into multiple chunks."""
        chunks = []
        text = element.text
        tokens = self.tokenizer.encode(text)
        
        chunk_idx = 0
        start = 0
        
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk = Chunk(
                chunk_id=f"{regulation_name}_chunk_{start_index + chunk_idx:04d}",
                text=chunk_text,
                source_file=element.source_file,
                page_numbers=[element.page_number],
                element_ids=[f"{element.element_id}_split_{chunk_idx}"],
                token_count=len(chunk_tokens),
                metadata={
                    "regulation": regulation_name,
                    "element_types": [element.element_type],
                    "chunk_index": start_index + chunk_idx,
                    "is_split": True
                }
            )
            chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap
            chunk_idx += 1
        
        return chunks


def chunk_parsed_elements(
    elements: list[ParsedElement],
    regulation_name: str = "regulation",
    chunk_size: int = None,
    chunk_overlap: int = None
) -> list[Chunk]:
    """
    Convenience function to chunk parsed elements.
    
    Args:
        elements: List of ParsedElement objects
        regulation_name: Name of the regulation
        chunk_size: Optional custom chunk size
        chunk_overlap: Optional custom overlap
        
    Returns:
        List of Chunk objects
    """
    chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.chunk_elements(elements, regulation_name)
