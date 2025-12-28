"""
parser.py - PDF Document Parser

Uses Unstructured.io to parse regulatory PDFs with metadata extraction.
Implements: hi_res strategy for table/layout preservation, bounding box extraction.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element

# Flexible imports for different execution contexts
try:
    from src.utils.logger import setup_logger
    from src.utils.config import config
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Fallback config
    class config:
        chunk_size = 512
        chunk_overlap = 50


@dataclass
class ParsedElement:
    """Represents a parsed element from a PDF document."""
    
    element_id: str
    element_type: str
    text: str
    page_number: int
    source_file: str
    metadata: dict = field(default_factory=dict)
    bbox: Optional[dict] = None  # {"x1": float, "y1": float, "x2": float, "y2": float}
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class PDFParser:
    """
    Parses regulatory PDF documents using Unstructured.io.
    
    Extracts text, tables, and metadata with bounding box coordinates
    for source verification.
    """
    
    def __init__(
        self,
        strategy: str = "hi_res",
        languages: list[str] = None,
        extract_images: bool = False
    ):
        """
        Initialize the PDF parser.
        
        Args:
            strategy: Parsing strategy ('hi_res', 'fast', 'ocr_only')
            languages: List of languages for OCR (e.g., ['eng'])
            extract_images: Whether to extract images from PDF
        """
        self.strategy = strategy
        self.languages = languages or ["eng"]
        self.extract_images = extract_images
        
    def parse(self, pdf_path: str | Path) -> list[ParsedElement]:
        """
        Parse a PDF document and extract elements with metadata.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of ParsedElement objects
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        logger.info(f"Parsing PDF: {pdf_path.name} with strategy '{self.strategy}'")
        
        try:
            # Parse PDF with Unstructured
            elements = partition_pdf(
                filename=str(pdf_path),
                strategy=self.strategy,
                languages=self.languages,
                extract_images_in_pdf=self.extract_images,
                infer_table_structure=True,
                include_page_breaks=True,
            )
            
            logger.info(f"Extracted {len(elements)} raw elements from {pdf_path.name}")
            
            # Convert to ParsedElement objects
            parsed_elements = []
            for i, element in enumerate(elements):
                parsed = self._convert_element(element, pdf_path.name, i)
                if parsed and parsed.text.strip():  # Skip empty elements
                    parsed_elements.append(parsed)
            
            logger.info(f"Converted to {len(parsed_elements)} parsed elements")
            return parsed_elements
            
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path.name}: {e}")
            raise
    
    def _convert_element(
        self,
        element: Element,
        source_file: str,
        index: int
    ) -> Optional[ParsedElement]:
        """
        Convert an Unstructured element to a ParsedElement.
        
        Args:
            element: Unstructured Element object
            source_file: Source PDF filename
            index: Element index
            
        Returns:
            ParsedElement or None if conversion fails
        """
        try:
            # Get element metadata
            meta = element.metadata
            
            # Extract bounding box if available
            bbox = None
            if hasattr(meta, 'coordinates') and meta.coordinates:
                coords = meta.coordinates
                if hasattr(coords, 'points') and coords.points:
                    points = coords.points
                    # Get bounding box from corner points
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    bbox = {
                        "x1": min(x_coords),
                        "y1": min(y_coords),
                        "x2": max(x_coords),
                        "y2": max(y_coords)
                    }
            
            # Build metadata dict
            metadata = {}
            if hasattr(meta, 'page_number'):
                metadata['page_number'] = meta.page_number
            if hasattr(meta, 'filename'):
                metadata['filename'] = meta.filename
            if hasattr(meta, 'filetype'):
                metadata['filetype'] = meta.filetype
            if hasattr(meta, 'parent_id'):
                metadata['parent_id'] = meta.parent_id
            if hasattr(meta, 'category_depth'):
                metadata['category_depth'] = meta.category_depth
                
            # Get page number (default to 1 if not available)
            page_number = getattr(meta, 'page_number', 1) or 1
            
            return ParsedElement(
                element_id=f"{source_file}_{index}",
                element_type=type(element).__name__,
                text=str(element),
                page_number=page_number,
                source_file=source_file,
                metadata=metadata,
                bbox=bbox
            )
            
        except Exception as e:
            logger.warning(f"Failed to convert element {index}: {e}")
            return None
    
    def save_to_json(
        self,
        elements: list[ParsedElement],
        output_path: str | Path
    ) -> None:
        """
        Save parsed elements to a JSON file.
        
        Args:
            elements: List of ParsedElement objects
            output_path: Output JSON file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "total_elements": len(elements),
            "elements": [e.to_dict() for e in elements]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(elements)} elements to {output_path}")


def parse_regulation_pdf(
    pdf_path: str | Path,
    output_path: Optional[str | Path] = None,
    strategy: str = "hi_res"
) -> list[ParsedElement]:
    """
    Convenience function to parse a regulation PDF.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save JSON output
        strategy: Parsing strategy
        
    Returns:
        List of ParsedElement objects
    """
    parser = PDFParser(strategy=strategy)
    elements = parser.parse(pdf_path)
    
    if output_path:
        parser.save_to_json(elements, output_path)
    
    return elements


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "data/processed/parsed_output.json"
        
        elements = parse_regulation_pdf(pdf_file, output_file)
        print(f"Parsed {len(elements)} elements from {pdf_file}")
    else:
        print("Usage: python parser.py <pdf_path> [output_json_path]")
