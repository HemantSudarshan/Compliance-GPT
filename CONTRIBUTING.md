# Contributing to ComplianceGPT

Thank you for your interest in contributing to ComplianceGPT! 🎉

## 📋 Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## 📜 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Please:
- Be kind and courteous
- Respect different viewpoints
- Accept constructive feedback gracefully
- Focus on what's best for the community

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git
- A Weaviate Cloud account (free tier)
- An LLM API key (Groq/Gemini recommended - free)

### Fork and Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/ComplianceGPT.git
cd ComplianceGPT
```

## 💻 Development Setup

### 1. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example config
cp .env.example .env

# Edit .env with your API keys
# Required: LLM_PROVIDER, API key for your provider, WEAVIATE_URL, WEAVIATE_API_KEY
```

### 4. Verify Setup
```bash
# Run tests
pytest

# Start the API
python -m uvicorn api.main:app --reload
```

## 🤝 How to Contribute

### Types of Contributions

| Type | Description |
|------|-------------|
| 🐛 Bug Fixes | Fix issues and errors |
| ✨ Features | Add new functionality |
| 📝 Documentation | Improve docs and comments |
| 🧪 Tests | Add or improve tests |
| 🔧 Refactoring | Code quality improvements |
| 🌐 Translations | Internationalization |

### Finding Issues
- Check [Issues](https://github.com/yourusername/ComplianceGPT/issues)
- Look for `good first issue` labels
- Ask in discussions if you need guidance

### Creating Issues
Before creating an issue:
1. Search existing issues
2. Include reproduction steps for bugs
3. Provide context for feature requests

## 📤 Pull Request Process

### 1. Create a Branch
```bash
# Feature
git checkout -b feature/your-feature-name

# Bug fix
git checkout -b fix/issue-description

# Documentation
git checkout -b docs/what-you-documented
```

### 2. Make Changes
- Follow coding standards
- Write/update tests
- Update documentation if needed

### 3. Test Your Changes
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_retriever.py

# Run with coverage
pytest --cov=src
```

### 4. Commit Changes
```bash
# Use conventional commits
git commit -m "feat: add new regulation parser"
git commit -m "fix: correct citation formatting"
git commit -m "docs: update API documentation"
git commit -m "test: add retriever edge case tests"
```

### 5. Push and Create PR
```bash
git push origin your-branch-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference to related issues
- Screenshots if UI changes

### PR Checklist
- [ ] Code follows project style guide
- [ ] All tests pass
- [ ] New code has tests
- [ ] Documentation updated
- [ ] No merge conflicts

## 📏 Coding Standards

### Python Style
- Follow [PEP 8](https://pep8.org/)
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public functions

```python
def process_query(
    query: str,
    regulation: str | None = None,
    top_k: int = 5
) -> QueryResponse:
    """
    Process a compliance query and return cited answer.
    
    Args:
        query: The user's question
        regulation: Optional filter (GDPR, CCPA, etc.)
        top_k: Number of context chunks to retrieve
        
    Returns:
        QueryResponse with answer and citations
        
    Raises:
        ValueError: If query is empty
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    # Implementation...
```

### File Organization
```
src/
├── ingestion/      # Document parsing and chunking
├── storage/        # Weaviate and indexing
├── generation/     # LLM and citations
├── evaluation/     # RAGAS metrics
└── utils/          # Config, logging, helpers
```

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `citation_engine.py` |
| Classes | PascalCase | `CitationEngine` |
| Functions | snake_case | `process_query()` |
| Constants | UPPER_SNAKE | `MAX_TOKENS` |

## 🧪 Testing Guidelines

### Test Structure
```python
class TestCitationEngine:
    """Tests for CitationEngine class."""
    
    def test_query_returns_citations(self):
        """Test that queries return proper citations."""
        # Arrange
        engine = CitationEngine(mock_client)
        
        # Act
        response = engine.query("What is GDPR?")
        
        # Assert
        assert response.citations
        assert response.has_context
```

### Test Coverage Goals
- Minimum 80% coverage for new code
- All public APIs must have tests
- Edge cases and error handling tested

### Running Tests
```bash
# All tests
pytest

# Verbose output
pytest -v

# Specific file
pytest tests/test_citation.py

# With coverage
pytest --cov=src --cov-report=html
```

## 📚 Documentation

### Code Documentation
- All public functions need docstrings
- Complex logic needs inline comments
- Type hints are required

### README Updates
Update README.md when:
- Adding new features
- Changing configuration options
- Modifying API endpoints

### Changelog
For significant changes, add entry to CHANGELOG.md:
```markdown
## [1.1.0] - 2025-01-15
### Added
- New PCI-DSS regulation support
- Query caching for improved performance

### Fixed
- Citation formatting edge case
```

## 🏗️ Project Architecture

```
ComplianceGPT/
├── api/                 # FastAPI endpoints
│   ├── main.py         # Main application
│   └── middleware.py   # Rate limiting, auth
├── src/                 # Core library
│   ├── ingestion/      # PDF parsing
│   ├── storage/        # Vector DB
│   ├── generation/     # LLM integration
│   └── evaluation/     # RAGAS metrics
├── app/                 # Streamlit UI
├── frontend/           # Static web UI
├── tests/              # Test suite
├── scripts/            # Utility scripts
└── data/               # Data storage
```

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Thanked in our community

## ❓ Questions?

- Open a [Discussion](https://github.com/yourusername/ComplianceGPT/discussions)
- Join our community chat
- Check existing issues

---

Thank you for contributing to ComplianceGPT! Your efforts help make compliance easier for everyone. 💙
