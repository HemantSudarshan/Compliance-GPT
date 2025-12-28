"""
2_Metrics.py - Quality Metrics Dashboard

Displays system configuration and performance metrics.
"""

import streamlit as st
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Metrics", page_icon="📊", layout="wide")

st.header("📊 System Metrics & Configuration")
st.markdown("Monitor system health, configuration, and indexed documents.")

# Load config
try:
    from src.utils.config import config
    config_loaded = True
except Exception as e:
    config_loaded = False
    st.error(f"Config error: {e}")


# Configuration Status
st.subheader("⚙️ Configuration Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**LLM Provider**")
    if config_loaded:
        provider = config.llm_provider.upper()
        if provider == "GEMINI":
            st.success(f"🌟 {provider} (Free)")
        elif provider == "GROQ":
            st.success(f"⚡ {provider} (Free)")
        else:
            st.info(f"💰 {provider} (Paid)")
        st.caption(f"Model: {config.llm_model}")
    else:
        st.error("Not configured")

with col2:
    st.markdown("**API Key Status**")
    if config_loaded:
        api_key = config.get_api_key()
        if api_key:
            st.success("✅ API Key Set")
            st.caption(f"Key: {api_key[:8]}...{api_key[-4:]}")
        else:
            st.error("❌ No API Key")
            st.caption("Set in .env file")
    else:
        st.error("Not configured")

with col3:
    st.markdown("**Weaviate Status**")
    if config_loaded and config.weaviate_url:
        try:
            from src.storage.weaviate_client import WeaviateClient
            with WeaviateClient() as client:
                health = client.health_check()
                if health.get("status") == "healthy":
                    st.success("✅ Connected")
                    st.caption(f"Objects: {health.get('object_count', 0)}")
                else:
                    st.warning("⚠️ Not healthy")
        except Exception as e:
            st.error("❌ Connection failed")
            st.caption(str(e)[:50])
    else:
        st.warning("⚠️ Not configured")
        st.caption("Set WEAVIATE_URL in .env")

st.divider()

# Indexed Documents
st.subheader("📚 Indexed Documents")

processed_dir = project_root / "data" / "processed"

if processed_dir.exists():
    chunk_files = list(processed_dir.glob("*_chunks.json"))
    
    if chunk_files:
        for chunk_file in chunk_files:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Regulation", data.get("regulation", chunk_file.stem.upper()))
                with col2:
                    st.metric("Chunks", data.get("total_chunks", "N/A"))
                with col3:
                    # Estimate tokens
                    chunks = data.get("chunks", [])
                    total_tokens = sum(c.get("token_count", 0) for c in chunks)
                    st.metric("Total Tokens", f"{total_tokens:,}")
                with col4:
                    st.metric("File", chunk_file.name)
                    
            except Exception as e:
                st.warning(f"Error reading {chunk_file.name}: {e}")
    else:
        st.info("No documents indexed yet.")
        st.markdown("""
        Run the ingestion pipeline:
        ```bash
        python scripts/run_ingestion.py data/raw/gdpr.pdf GDPR
        ```
        """)
else:
    st.warning("No processed data directory found.")

st.divider()

# Search Settings
st.subheader("🔍 Search Configuration")

if config_loaded:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Top-K Results", config.top_k, help="Number of chunks retrieved per query")
    
    with col2:
        alpha_desc = "Keyword-biased" if config.hybrid_alpha < 0.5 else "Semantic-biased"
        st.metric("Hybrid Alpha", f"{config.hybrid_alpha} ({alpha_desc})", 
                  help="0=keyword only, 1=semantic only")
    
    with col3:
        st.metric("Chunk Size", f"{config.chunk_size} tokens", help="Target chunk size")

st.divider()

# Quick Actions
st.subheader("🚀 Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Refresh Metrics", use_container_width=True):
        st.rerun()

with col2:
    if st.button("📋 View Config", use_container_width=True):
        if config_loaded:
            st.json({
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model,
                "top_k": config.top_k,
                "hybrid_alpha": config.hybrid_alpha,
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "weaviate_configured": bool(config.weaviate_url)
            })

with col3:
    env_example = project_root / ".env.example"
    if env_example.exists():
        with open(env_example, 'r') as f:
            st.download_button(
                "📥 Download .env Template",
                f.read(),
                file_name=".env",
                mime="text/plain",
                use_container_width=True
            )
