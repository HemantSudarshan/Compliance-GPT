"""
setup_weaviate.py - Weaviate Schema Setup

Creates the Weaviate collection schema for ComplianceGPT.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()


def setup_weaviate(force_recreate: bool = False):
    """
    Set up Weaviate collection for ComplianceGPT.
    
    Args:
        force_recreate: If True, delete and recreate existing collection
    """
    from src.storage.weaviate_client import WeaviateClient
    
    print("=" * 50)
    print("ComplianceGPT - Weaviate Setup")
    print("=" * 50)
    
    # Check environment variables
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_key = os.getenv("WEAVIATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not weaviate_url:
        print("\n❌ WEAVIATE_URL not set in environment")
        print("\nTo set up Weaviate Cloud:")
        print("1. Go to https://console.weaviate.cloud/")
        print("2. Create a free sandbox cluster")
        print("3. Copy the cluster URL and API key")
        print("4. Add to your .env file:")
        print("   WEAVIATE_URL=https://your-cluster.weaviate.network")
        print("   WEAVIATE_API_KEY=your-api-key")
        return False
    
    if not openai_key:
        print("\n⚠️ OPENAI_API_KEY not set - vectorization will fail")
        print("Add to your .env file: OPENAI_API_KEY=your-key")
        return False
    
    print(f"\n📡 Connecting to: {weaviate_url}")
    
    try:
        with WeaviateClient() as client:
            # Health check
            health = client.health_check()
            print(f"\n🔍 Health Check: {health['status']}")
            
            if health['status'] != 'healthy':
                print(f"❌ Cluster not healthy: {health}")
                return False
            
            # Create collection
            if force_recreate:
                print("\n🗑️ Force recreate enabled - deleting existing collection...")
            
            created = client.create_collection(force_recreate=force_recreate)
            
            if created:
                print("\n✅ Collection 'ComplianceChunk' created successfully!")
            else:
                print("\n✅ Collection 'ComplianceChunk' already exists")
            
            # Final status
            final_health = client.health_check()
            print(f"\n📊 Final Status:")
            print(f"   - Collection exists: {final_health.get('collection_exists', False)}")
            print(f"   - Object count: {final_health.get('object_count', 0)}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False


def verify_setup():
    """Verify Weaviate setup is working."""
    from src.storage.weaviate_client import WeaviateClient
    
    print("\n" + "=" * 50)
    print("Verifying Setup...")
    print("=" * 50)
    
    try:
        with WeaviateClient() as client:
            health = client.health_check()
            
            if health['status'] == 'healthy' and health.get('collection_exists'):
                print("\n✅ Weaviate setup verified successfully!")
                print(f"   Objects in collection: {health.get('object_count', 0)}")
                return True
            else:
                print(f"\n⚠️ Setup verification issues: {health}")
                return False
                
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    verify_only = "--verify" in sys.argv or "-v" in sys.argv
    
    if verify_only:
        success = verify_setup()
    else:
        success = setup_weaviate(force_recreate=force)
        if success:
            verify_setup()
    
    print("\n" + "=" * 50)
    if success:
        print("Setup complete! You can now index documents.")
        print("\nNext steps:")
        print("1. Add a GDPR PDF to data/raw/gdpr.pdf")
        print("2. Run: python scripts/run_ingestion.py data/raw/gdpr.pdf GDPR")
    else:
        print("Setup incomplete. Check the errors above.")
    print("=" * 50)
    
    sys.exit(0 if success else 1)
