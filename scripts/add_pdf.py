"""
add_pdf.py - Easy Script to Add New Regulations

Usage:
    python scripts/add_pdf.py <pdf_path> <regulation_name>
    
Examples:
    python scripts/add_pdf.py data/raw/ccpa.pdf CCPA
    python scripts/add_pdf.py data/raw/pci_dss.pdf PCI-DSS
    python scripts/add_pdf.py data/raw/hipaa.pdf HIPAA
"""

import sys
import json
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import os

# Load environment
env_path = project_root / ".env"
load_dotenv(env_path, override=True)


def parse_pdf(pdf_path: str, regulation_name: str) -> list[dict]:
    """Parse PDF and create chunks."""
    from unstructured.partition.pdf import partition_pdf
    
    print(f"📄 Parsing: {pdf_path}")
    
    elements = partition_pdf(
        filename=pdf_path,
        strategy="fast",
        languages=["eng"]
    )
    
    print(f"   Found {len(elements)} elements")
    
    chunks = []
    for i, elem in enumerate(elements):
        text = str(elem).strip()
        if len(text) > 20:  # Skip very short elements
            meta = elem.metadata
            chunks.append({
                "chunk_id": f"{regulation_name}_chunk_{i:05d}",
                "text": text,
                "source_file": Path(pdf_path).name,
                "page_numbers": [getattr(meta, "page_number", 1) or 1],
                "element_ids": [f"elem_{i}"],
                "token_count": len(text.split()),
                "regulation": regulation_name,
                "chunk_index": i
            })
    
    print(f"   Created {len(chunks)} chunks")
    return chunks


def index_to_weaviate(chunks: list[dict], regulation_name: str):
    """Index chunks to Weaviate."""
    import weaviate
    from weaviate.classes.init import Auth
    
    url = os.getenv("WEAVIATE_URL")
    key = os.getenv("WEAVIATE_API_KEY")
    
    if not url:
        raise ValueError("WEAVIATE_URL not set in .env")
    
    print(f"📡 Connecting to Weaviate...")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=url,
        auth_credentials=Auth.api_key(key) if key else None
    )
    
    try:
        collection = client.collections.get("ComplianceChunk")
        
        print(f"📤 Indexing {len(chunks)} chunks...")
        with collection.batch.dynamic() as batch:
            for i, chunk in enumerate(chunks):
                batch.add_object(properties=chunk)
                if (i + 1) % 200 == 0:
                    print(f"   Indexed {i + 1}/{len(chunks)}")
        
        # Verify
        result = collection.aggregate.over_all(total_count=True)
        print(f"✅ Total objects in collection: {result.total_count}")
        
    finally:
        client.close()


def save_chunks(chunks: list[dict], regulation_name: str):
    """Save chunks to JSON for backup."""
    output_path = project_root / "data" / "processed" / f"{regulation_name.lower()}_chunks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "regulation": regulation_name,
        "total_chunks": len(chunks),
        "chunks": chunks
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Saved to {output_path}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nCurrently indexed regulations:")
        
        # Check what's indexed
        try:
            import weaviate
            from weaviate.classes.init import Auth
            
            url = os.getenv("WEAVIATE_URL")
            key = os.getenv("WEAVIATE_API_KEY")
            
            if url:
                client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=url,
                    auth_credentials=Auth.api_key(key) if key else None
                )
                
                col = client.collections.get("ComplianceChunk")
                result = col.aggregate.over_all(total_count=True)
                print(f"  Total chunks: {result.total_count}")
                client.close()
        except Exception as e:
            print(f"  Could not check: {e}")
        
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    regulation_name = sys.argv[2].upper()
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print(f"Adding Regulation: {regulation_name}")
    print(f"Source: {pdf_path}")
    print("=" * 60)
    
    # Parse
    chunks = parse_pdf(pdf_path, regulation_name)
    
    if not chunks:
        print("❌ No chunks created. Check PDF content.")
        sys.exit(1)
    
    # Save backup
    save_chunks(chunks, regulation_name)
    
    # Index
    index_to_weaviate(chunks, regulation_name)
    
    print("\n" + "=" * 60)
    print(f"✅ Successfully added {regulation_name}!")
    print("=" * 60)


if __name__ == "__main__":
    main()
