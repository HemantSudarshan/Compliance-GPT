"""
3_Change_Detection.py - Regulatory Change Detection Page

Compares different versions of regulations to detect changes.
"""

import streamlit as st
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Change Detection", page_icon="🔍", layout="wide")

st.header("🔍 Regulatory Change Detection")
st.markdown("Compare different versions of regulations to identify changes.")

# Sidebar
with st.sidebar:
    st.header("📂 Select Versions")
    
    # Get available chunk files
    processed_dir = project_root / "data" / "processed"
    chunk_files = list(processed_dir.glob("*_chunks.json")) if processed_dir.exists() else []
    
    if len(chunk_files) >= 2:
        file_options = [f.name for f in chunk_files]
        
        old_version = st.selectbox("Old Version", file_options, index=0)
        new_version = st.selectbox("New Version", file_options, index=min(1, len(file_options)-1))
        
        if old_version == new_version:
            st.warning("Select different files to compare")
    else:
        st.info("Need at least 2 chunk files to compare")
        old_version = None
        new_version = None
    
    st.divider()
    
    st.header("⚙️ Settings")
    similarity_threshold = st.slider(
        "Similarity Threshold",
        min_value=0.5,
        max_value=1.0,
        value=0.8,
        step=0.05,
        help="Threshold for detecting modifications vs additions"
    )

# Main content
if old_version and new_version and old_version != new_version:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📄 Old: {old_version}")
        old_path = processed_dir / old_version
        with open(old_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        st.metric("Chunks", old_data.get("total_chunks", len(old_data.get("chunks", []))))
    
    with col2:
        st.subheader(f"📄 New: {new_version}")
        new_path = processed_dir / new_version
        with open(new_path, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        st.metric("Chunks", new_data.get("total_chunks", len(new_data.get("chunks", []))))
    
    st.divider()
    
    if st.button("🔍 Detect Changes", type="primary", use_container_width=True):
        with st.spinner("Analyzing differences..."):
            try:
                from src.evaluation.change_detector import ChangeDetector
                
                detector = ChangeDetector(similarity_threshold=similarity_threshold)
                report = detector.compare_documents(old_path, new_path)
                
                # Display results
                st.success(f"Analysis complete! Found {report.total_changes} changes.")
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Similarity", f"{report.similarity_score:.1%}")
                with col2:
                    st.metric("Additions", report.additions, delta=report.additions if report.additions else None)
                with col3:
                    st.metric("Removals", report.removals, delta=-report.removals if report.removals else None)
                with col4:
                    st.metric("Modifications", report.modifications)
                
                st.divider()
                
                # Changes list
                if report.changes:
                    st.subheader("📋 Detailed Changes")
                    
                    for i, change in enumerate(report.changes[:20], 1):  # Show first 20
                        if change.change_type == "added":
                            icon = "✅"
                            color = "green"
                        elif change.change_type == "removed":
                            icon = "❌"
                            color = "red"
                        else:
                            icon = "✏️"
                            color = "orange"
                        
                        with st.expander(f"{icon} {change.change_type.upper()} - {change.section}"):
                            if change.old_text:
                                st.markdown("**Old text:**")
                                st.text(change.old_text[:300] + "..." if len(change.old_text or "") > 300 else change.old_text)
                            if change.new_text:
                                st.markdown("**New text:**")
                                st.text(change.new_text[:300] + "..." if len(change.new_text or "") > 300 else change.new_text)
                            if change.similarity > 0:
                                st.caption(f"Similarity: {change.similarity:.1%}")
                else:
                    st.info("No significant changes detected between versions.")
                    
            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.info("👆 Select two different chunk files to compare in the sidebar")
    
    st.markdown("""
    ### How to use Change Detection:
    
    1. **Index multiple versions** of a regulation:
       ```bash
       python scripts/run_ingestion.py gdpr_v1.pdf GDPR_V1 --skip-indexing
       python scripts/run_ingestion.py gdpr_v2.pdf GDPR_V2 --skip-indexing
       ```
    
    2. **Select versions** in the sidebar
    
    3. **Click "Detect Changes"** to see:
       - Overall similarity score
       - Added, removed, and modified sections
       - Detailed diff view
    
    ### Use Cases:
    - Track regulatory updates over time
    - Identify compliance impact of new requirements
    - Audit document changes
    """)
