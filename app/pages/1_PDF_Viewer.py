"""
1_PDF_Viewer.py - PDF Source Verification Page

Displays PDF documents with highlighted source paragraphs.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="PDF Viewer", page_icon="📄", layout="wide")

st.header("📄 PDF Source Viewer")
st.markdown("View and verify source documents from regulatory PDFs.")

# Sidebar - File selection
with st.sidebar:
    st.header("📁 Select Document")
    
    # Get available PDFs
    pdf_dir = project_root / "data" / "raw"
    pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
    
    if pdf_files:
        selected_pdf = st.selectbox(
            "Choose a PDF",
            options=[f.name for f in pdf_files],
            index=0
        )
        pdf_path = pdf_dir / selected_pdf
    else:
        st.warning("No PDFs found in data/raw/")
        selected_pdf = None
        pdf_path = None
    
    st.divider()
    
    # Page navigation
    page_number = st.number_input("Go to page", min_value=1, value=1, step=1)

# Main content
if pdf_path and pdf_path.exists():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📖 {selected_pdf}")
        
        try:
            # Try to use streamlit-pdf-viewer
            from streamlit_pdf_viewer import pdf_viewer
            
            # Read PDF bytes
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            pdf_viewer(
                pdf_bytes,
                width=800,
                height=800,
                pages_to_render=[page_number]
            )
        except ImportError:
            st.info("Install `streamlit-pdf-viewer` for embedded PDF viewing")
            
            # Fallback: Download link
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download PDF",
                    data=f.read(),
                    file_name=selected_pdf,
                    mime="application/pdf"
                )
                
        except Exception as e:
            st.error(f"Error loading PDF: {e}")
            
            # Fallback: Download link
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download PDF Instead",
                    data=f.read(),
                    file_name=selected_pdf,
                    mime="application/pdf"
                )
    
    with col2:
        st.subheader("📊 Document Info")
        
        # File info
        file_size = pdf_path.stat().st_size / 1024
        st.metric("File Size", f"{file_size:.1f} KB")
        
        # Check for parsed data
        parsed_file = project_root / "data" / "processed" / f"{pdf_path.stem.lower()}_chunks.json"
        
        if parsed_file.exists():
            import json
            with open(parsed_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
            
            st.success("✅ Document Indexed")
            st.metric("Total Chunks", chunks_data.get("total_chunks", "N/A"))
            st.metric("Regulation", chunks_data.get("regulation", pdf_path.stem.upper()))
        else:
            st.warning("⚠️ Not indexed yet")
            st.info("Run ingestion to index this document")
            st.code(f"python scripts/run_ingestion.py data/raw/{selected_pdf}")

else:
    st.info("👆 Add PDF files to `data/raw/` to view them here")
    
    st.markdown("""
    ### How to add documents:
    
    1. Download regulation PDFs:
       - **GDPR**: [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679)
       - **CCPA**: [CA Attorney General](https://oag.ca.gov/privacy/ccpa)
       - **PCI-DSS**: [PCI Council](https://www.pcisecuritystandards.org/)
    
    2. Place them in `data/raw/` folder
    
    3. Run ingestion:
       ```bash
       python scripts/run_ingestion.py data/raw/gdpr.pdf GDPR
       ```
    """)
