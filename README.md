# ComplianceGPT ⚖️

**AI-Powered Regulatory Compliance Assistant with Zero-Hallucination Citations**

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live%20Demo-FF4B4B)](https://huggingface.co/spaces/YOUR_USERNAME/compliancegpt)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 What is ComplianceGPT?

ComplianceGPT is a production-ready RAG (Retrieval-Augmented Generation) system that answers regulatory compliance questions with **exact citations** from source documents. Every answer includes page numbers and quoted text, ensuring verifiable compliance guidance.

### ✨ Key Features

- 📝 **Citation-Backed Answers** - Every claim linked to source documents
- 🔍 **Hybrid Search** - Semantic + keyword search for optimal retrieval
- 📊 **Multi-Regulation Support** - GDPR, CCPA, PCI-DSS ready
- 🆓 **Free LLM Options** - Works with Gemini/Groq (free tier)
- 📄 **PDF Source Viewer** - View original regulations with highlights
- 🔄 **Change Detection** - Track regulatory updates over time
- 📜 **Session Tracking** - Query history and usage analytics with SQLite

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/YOUR_USERNAME/compliancegpt.git
cd compliancegpt
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your keys:
# - GEMINI_API_KEY (free at https://aistudio.google.com/apikey)
# - WEAVIATE_URL and WEAVIATE_API_KEY (free at https://console.weaviate.cloud)
```

### 3. Index a Regulation
```bash
python scripts/run_ingestion.py data/raw/gdpr.pdf GDPR
```

### 4. Run the App
```bash
streamlit run app/Home.py
```

## 📁 Project Structure

```
compliancegpt/
├── app/                    # Streamlit UI
│   ├── Home.py            # Main chat interface
│   └── pages/             # PDF Viewer, Metrics, Change Detection
├── src/
│   ├── ingestion/         # PDF parsing & chunking
│   ├── storage/           # Weaviate vector DB
│   ├── generation/        # Citation engine & prompts
│   └── evaluation/        # RAGAS evaluation
├── scripts/               # Setup & ingestion scripts
├── data/
│   ├── raw/               # Source PDFs
│   ├── processed/         # Parsed chunks
│   └── test/              # Evaluation data
└── tests/                 # Unit tests
```

## 🔧 Technology Stack

| Component | Technology | Cost |
|-----------|-----------|------|
| LLM | Gemini/Groq/OpenAI | Free/Paid |
| Vector DB | Weaviate Cloud | Free tier |
| Parsing | Unstructured.io | Free |
| Frontend | Streamlit | Free |
| Evaluation | RAGAS | Free |
| Session Tracking | SQLite | Free |

## 📜 Session Tracking

ComplianceGPT includes built-in session tracking and query history:

- **Automatic Session Management** - Sessions created automatically
- **Query History** - All queries logged with full context
- **Usage Analytics** - Track queries, citations, and performance
- **REST API** - Session management endpoints
- **Privacy-Focused** - Local SQLite database

See [Session Tracking Documentation](docs/SESSION_TRACKING.md) for details.

## 📊 Evaluation Results

| Metric | Score | Target |
|--------|-------|--------|
| Faithfulness | TBD | >95% |
| Answer Relevancy | TBD | >90% |
| Context Precision | TBD | >85% |

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines first.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---
Built with ❤️ for compliance professionals
