"""
ComplianceGPT - Main Application

Premium Streamlit interface for regulatory compliance Q&A.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
env_path = project_root / ".env"
load_dotenv(env_path, override=True)

# Page configuration
st.set_page_config(
    page_title="ComplianceGPT",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Dark Theme CSS
st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hero header with gradient */
    .hero-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(74,144,217,0.1) 0%, transparent 70%);
        animation: pulse 4s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 0.8; }
    }
    
    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #e8d5b7 0%, #f5f5f5 50%, #94b9e8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        font-size: 1.2rem;
        color: rgba(255,255,255,0.7);
        text-align: center;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }
    
    .hero-badges {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 1.5rem;
        position: relative;
        z-index: 1;
    }
    
    .badge {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        padding: 0.5rem 1rem;
        border-radius: 50px;
        color: #fff;
        font-size: 0.85rem;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Chat container */
    .chat-container {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Citation cards */
    .citation-card {
        background: linear-gradient(135deg, rgba(74,144,217,0.15) 0%, rgba(30,58,95,0.3) 100%);
        border: 1px solid rgba(74,144,217,0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.75rem 0;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .citation-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(74,144,217,0.2);
    }
    
    .citation-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    
    .citation-number {
        background: linear-gradient(135deg, #4A90D9, #1E3A5F);
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .citation-regulation {
        background: rgba(46, 125, 50, 0.2);
        color: #81c784;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .citation-source {
        color: rgba(255,255,255,0.6);
        font-size: 0.85rem;
    }
    
    .citation-text {
        color: rgba(255,255,255,0.85);
        font-style: italic;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-top: 0.5rem;
        padding-left: 1rem;
        border-left: 3px solid rgba(74,144,217,0.5);
    }
    
    /* Sidebar styling */
    .sidebar-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #4A90D9;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .example-btn {
        background: linear-gradient(135deg, rgba(74,144,217,0.2), rgba(30,58,95,0.3));
        border: 1px solid rgba(74,144,217,0.3);
        border-radius: 8px;
        padding: 0.75rem;
        color: white;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    .example-btn:hover {
        background: linear-gradient(135deg, rgba(74,144,217,0.3), rgba(30,58,95,0.4));
        transform: translateX(4px);
    }
    
    /* Status indicators */
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        font-size: 0.9rem;
    }
    
    .status-success {
        background: rgba(46, 125, 50, 0.2);
        color: #81c784;
    }
    
    .status-warning {
        background: rgba(255, 167, 38, 0.2);
        color: #ffb74d;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: rgba(255,255,255,0.5);
        font-size: 0.85rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin-top: 2rem;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Chat input styling */
    .stChatInput {
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# Hero Header
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">⚖️ ComplianceGPT</h1>
    <p class="hero-subtitle">AI-Powered Regulatory Compliance with Zero-Hallucination Citations</p>
    <div class="hero-badges">
        <span class="badge">🔍 GDPR</span>
        <span class="badge">🛡️ CCPA</span>
        <span class="badge">💳 PCI-DSS</span>
        <span class="badge">✨ Groq AI</span>
    </div>
</div>
""", unsafe_allow_html=True)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "citations" not in st.session_state:
    st.session_state.citations = {}

# Initialize session tracking
if "session_id" not in st.session_state:
    from src.storage.session_db import SessionDatabase
    db = SessionDatabase()
    session = db.create_session(metadata={"source": "streamlit"})
    st.session_state.session_id = session.session_id
    st.session_state.session_db = db


def check_configuration():
    """Check if the system is properly configured."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            break
    
    llm_provider = os.getenv("LLM_PROVIDER", "groq")
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    weaviate_url = os.getenv("WEAVIATE_URL", "")
    
    has_llm = bool(groq_key or gemini_key)
    has_weaviate = bool(weaviate_url)
    
    return has_llm and has_weaviate, llm_provider


def get_answer(question: str, regulation: str = None):
    """Get answer from the citation engine."""
    from src.storage.weaviate_client import WeaviateClient
    from src.generation.citation_engine import CitationEngine
    
    with WeaviateClient() as client:
        engine = CitationEngine(client)
        response = engine.query(
            question,
            regulation_filter=regulation if regulation != "All" else None
        )
        return response


# Sidebar
with st.sidebar:
    st.markdown('<p class="sidebar-header">⚙️ Configuration</p>', unsafe_allow_html=True)
    
    is_configured, provider = check_configuration()
    
    if is_configured:
        st.markdown(f"""
        <div class="status-indicator status-success">
            ✅ Connected • {provider.upper()}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-indicator status-warning">
            ⚠️ Setup needed
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown('<p class="sidebar-header">📚 Regulation Filter</p>', unsafe_allow_html=True)
    regulation = st.selectbox(
        "Select Regulation",
        ["All", "GDPR", "CCPA", "PCI-DSS"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown('<p class="sidebar-header">💡 Try These Questions</p>', unsafe_allow_html=True)
    
    example_questions = [
        "What are the data breach notification requirements?",
        "What is the right to erasure?",
        "What are the principles of data processing?",
        "What are GDPR violation penalties?",
        "What is a Data Protection Impact Assessment?"
    ]
    
    for q in example_questions:
        if st.button(f"📌 {q[:35]}...", key=q, use_container_width=True):
            st.session_state.pending_question = q
    
    st.divider()
    
    # Query History Section
    st.markdown('<p class="sidebar-header">📜 Query History</p>', unsafe_allow_html=True)
    
    if "session_db" in st.session_state and "session_id" in st.session_state:
        history = st.session_state.session_db.get_session_history(
            st.session_state.session_id, 
            limit=10
        )
        
        if history:
            for record in history:
                question_preview = record.question[:40] + "..." if len(record.question) > 40 else record.question
                with st.expander(f"❓ {question_preview}", expanded=False):
                    st.markdown(f"**Question:** {record.question}")
                    st.markdown(f"**Regulation:** {record.regulation_filter or 'All'}")
                    st.markdown(f"**Citations:** {record.num_citations}")
                    st.markdown(f"**Time:** {record.timestamp[:19]}")
        else:
            st.markdown("*No queries yet*")
    
    st.divider()
    
    if st.button("🗑️ Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.citations = {}
        st.rerun()
    
    st.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: rgba(74,144,217,0.1); border-radius: 8px;">
        <p style="font-size: 0.85rem; color: rgba(255,255,255,0.7); margin: 0;">
            💡 <strong>Powered by:</strong><br/>
            • Groq LLama 3.3 70B<br/>
            • Weaviate Vector DB<br/>
            • Zero-hallucination RAG
        </p>
    </div>
    """, unsafe_allow_html=True)


# Main chat area
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "⚖️"):
            st.markdown(message["content"])
            
            # Show citations for assistant messages
            if message["role"] == "assistant" and i in st.session_state.citations:
                citations = st.session_state.citations[i]
                if citations:
                    with st.expander(f"📚 View {len(citations)} Sources", expanded=False):
                        for citation in citations:
                            st.markdown(f"""
                            <div class="citation-card">
                                <div class="citation-header">
                                    <span class="citation-number">{citation.citation_id}</span>
                                    <span class="citation-regulation">{citation.regulation}</span>
                                    <span class="citation-source">{citation.source_file} • Page {', '.join(map(str, citation.page_numbers))}</span>
                                </div>
                                <div class="citation-text">"{citation.text[:250]}..."</div>
                            </div>
                            """, unsafe_allow_html=True)

    # Handle pending question from sidebar
    if "pending_question" in st.session_state:
        prompt = st.session_state.pending_question
        del st.session_state.pending_question
    else:
        prompt = st.chat_input("Ask any compliance question...")

    # Process new question
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)
        
        # Get response
        with st.chat_message("assistant", avatar="⚖️"):
            if not is_configured:
                response_text = """⚠️ **Configuration Required**
                
Please set up your `.env` file with API keys.
Get free keys at:
- **Groq:** [console.groq.com](https://console.groq.com)
- **Weaviate:** [console.weaviate.cloud](https://console.weaviate.cloud)
"""
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            else:
                with st.spinner("🔍 Searching regulations..."):
                    try:
                        response = get_answer(prompt, regulation)
                        
                        if response:
                            response_text = response.answer
                            
                            if response.has_context:
                                response_text += f"\n\n---\n*📚 {len(response.citations)} sources from {regulation if regulation != 'All' else 'all regulations'}*"
                            
                            st.markdown(response_text)
                            
                            msg_idx = len(st.session_state.messages)
                            st.session_state.citations[msg_idx] = response.citations
                            
                            if response.citations:
                                with st.expander(f"📚 View {len(response.citations)} Sources", expanded=False):
                                    for citation in response.citations:
                                        st.markdown(f"""
                                        <div class="citation-card">
                                            <div class="citation-header">
                                                <span class="citation-number">{citation.citation_id}</span>
                                                <span class="citation-regulation">{citation.regulation}</span>
                                                <span class="citation-source">{citation.source_file} • Page {', '.join(map(str, citation.page_numbers))}</span>
                                            </div>
                                            <div class="citation-text">"{citation.text[:250]}..."</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                            
                            st.session_state.messages.append({"role": "assistant", "content": response_text})
                            
                            # Log query to session database
                            if "session_db" in st.session_state and "session_id" in st.session_state:
                                try:
                                    st.session_state.session_db.log_query(
                                        session_id=st.session_state.session_id,
                                        question=prompt,
                                        answer=response.answer,
                                        regulation_filter=regulation if regulation != "All" else None,
                                        num_citations=len(response.citations),
                                        has_context=response.has_context,
                                        metadata=response.metadata
                                    )
                                except Exception as e:
                                    # Don't fail the query if logging fails
                                    import logging
                                    logging.warning(f"Failed to log query: {e}")
                        else:
                            st.error("❌ Could not get response")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})

# Footer
st.markdown("""
<div class="footer">
    <p>ComplianceGPT v2.0 • Built with ❤️ for Compliance Professionals</p>
    <p>Zero-Hallucination AI • Every Answer Backed by Sources</p>
</div>
""", unsafe_allow_html=True)
