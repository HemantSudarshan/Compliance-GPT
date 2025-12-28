"""
run_ingestion.py - Document Ingestion Pipeline

Parses and indexes regulation PDFs into the vector database.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()


def run_ingestion(
    pdf_path: str,
    regulation_name: str,
    output_dir: str = "data/processed",
    skip_parsing: bool = False,
    skip_indexing: bool = False
):
    """
    Run the full ingestion pipeline.
    
    Args:
        pdf_path: Path to the PDF file
        regulation_name: Name of the regulation (e.g., 'GDPR')
        output_dir: Directory for processed files
        skip_parsing: Skip parsing if chunks already exist
        skip_indexing: Skip indexing to Weaviate
    """
    from src.ingestion.parser import parse_regulation_pdf
    from src.ingestion.chunker import chunk_parsed_elements
    from src.storage.weaviate_client import WeaviateClient
    from src.storage.indexer import DocumentIndexer
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # File paths
    parsed_file = output_dir / f"{regulation_name.lower()}_parsed.json"
    chunks_file = output_dir / f"{regulation_name.lower()}_chunks.json"
    
    print("=" * 60)
    print(f"ComplianceGPT - Ingestion Pipeline")
    print(f"Regulation: {regulation_name}")
    print(f"Source: {pdf_path}")
    print("=" * 60)
    
    # Step 1: Parse PDF
    if skip_parsing and parsed_file.exists():
        print(f"\n📄 Skipping parsing - using existing {parsed_file}")
        with open(parsed_file, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
        elements_count = parsed_data.get("total_elements", 0)
    else:
        print(f"\n📄 Step 1: Parsing PDF...")
        elements = parse_regulation_pdf(pdf_path, parsed_file, strategy="hi_res")
        elements_count = len(elements)
        print(f"   ✅ Extracted {elements_count} elements")
    
    # Step 2: Chunk elements
    if skip_parsing and chunks_file.exists():
        print(f"\n📦 Skipping chunking - using existing {chunks_file}")
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        chunks = chunks_data.get("chunks", [])
    else:
        print(f"\n📦 Step 2: Chunking elements...")
        
        # Load parsed elements
        with open(parsed_file, 'r', encoding='utf-8') as f:
            parsed_data = json.load(f)
        
        # Convert to ParsedElement objects
        from src.ingestion.parser import ParsedElement
        elements = [
            ParsedElement(
                element_id=e["element_id"],
                element_type=e["element_type"],
                text=e["text"],
                page_number=e["page_number"],
                source_file=e["source_file"],
                metadata=e.get("metadata", {}),
                bbox=e.get("bbox")
            )
            for e in parsed_data.get("elements", [])
        ]
        
        chunks = chunk_parsed_elements(elements, regulation_name)
        
        # Save chunks
        chunks_output = {
            "regulation": regulation_name,
            "total_chunks": len(chunks),
            "chunks": [c.to_dict() for c in chunks]
        }
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_output, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Created {len(chunks)} chunks")
        print(f"   📁 Saved to {chunks_file}")
    
    # Step 3: Index to Weaviate
    if skip_indexing:
        print(f"\n🔍 Skipping indexing (--skip-indexing flag)")
    else:
        print(f"\n🔍 Step 3: Indexing to Weaviate...")
        
        try:
            with WeaviateClient() as client:
                # Ensure collection exists
                client.create_collection(force_recreate=False)
                
                # Load chunks from file
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                # Index
                indexer = DocumentIndexer(client, batch_size=50)
                result = indexer.index_chunks(chunks_data.get("chunks", []))
                
                print(f"   ✅ Indexed {result['indexed']} chunks")
                if result['errors'] > 0:
                    print(f"   ⚠️ {result['errors']} errors occurred")
                
                # Final count
                total = client.get_object_count()
                print(f"   📊 Total objects in database: {total}")
                
        except Exception as e:
            print(f"   ❌ Indexing failed: {e}")
            print("   Make sure Weaviate is set up. Run: python scripts/setup_weaviate.py")
            return False
    
    print("\n" + "=" * 60)
    print("✅ Ingestion complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ingestion.py <pdf_path> [regulation_name] [options]")
        print("\nOptions:")
        print("  --skip-parsing    Skip PDF parsing (use existing)")
        print("  --skip-indexing   Skip Weaviate indexing")
        print("\nExample:")
        print("  python run_ingestion.py data/raw/gdpr.pdf GDPR")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    # Get regulation name from filename if not provided
    if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        regulation = sys.argv[2]
    else:
        regulation = Path(pdf_file).stem.upper()
    
    skip_parsing = "--skip-parsing" in sys.argv
    skip_indexing = "--skip-indexing" in sys.argv
    
    success = run_ingestion(
        pdf_file,
        regulation,
        skip_parsing=skip_parsing,
        skip_indexing=skip_indexing
    )
    
    sys.exit(0 if success else 1)
