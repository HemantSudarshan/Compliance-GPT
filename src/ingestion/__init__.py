"""
ComplianceGPT - Ingestion Module

Handles PDF parsing, chunking, and table linearization for regulatory documents.
"""

from src.ingestion.parser import PDFParser, ParsedElement, parse_regulation_pdf
from src.ingestion.chunker import SemanticChunker, Chunk, chunk_parsed_elements
from src.ingestion.table_linearizer import TableLinearizer, linearize_table

__all__ = [
    "PDFParser",
    "ParsedElement", 
    "parse_regulation_pdf",
    "SemanticChunker",
    "Chunk",
    "chunk_parsed_elements",
    "TableLinearizer",
    "linearize_table",
]
