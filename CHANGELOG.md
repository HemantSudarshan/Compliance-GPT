# Changelog

All notable changes to ComplianceGPT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Request rate limiting middleware (30 req/min default)
- API key authentication support (optional)
- Response caching for improved performance
- Request/response logging middleware
- API statistics endpoint (`/api/stats`)
- Version endpoint (`/api/version`)
- Cache management endpoint (`/api/cache`)
- Centralized logging with colored output
- Input validation with Pydantic
- Comprehensive test suite for retriever
- API endpoint tests
- SECURITY.md documentation
- CONTRIBUTING.md guidelines

### Changed
- Enhanced QueryRequest with validation (min/max length)
- Improved error handling with request IDs
- API version bumped to 2.1

### Fixed
- Missing logger utility module

## [2.0.0] - 2025-12-28

### Added
- Multi-LLM provider support (OpenAI, Gemini, Groq)
- Web search fallback for unanswered questions
- Query expansion with compliance synonyms
- Modern glassmorphism web UI
- Streamlit-based admin interface
- PDF viewer with annotations
- Change detection for regulation updates
- RAGAS evaluation framework
- Docker support with docker-compose
- Hugging Face Spaces deployment

### Changed
- Switched from vector-based to BM25 keyword search
- Improved citation engine with better prompts
- Restructured project layout

## [1.0.0] - 2025-12-01

### Added
- Initial release
- GDPR, CCPA, PCI-DSS support
- Citation-backed answers
- Weaviate vector database integration
- FastAPI backend
- Basic web frontend

---

## Version History Summary

| Version | Release Date | Highlights |
|---------|--------------|------------|
| 2.1.0   | TBD          | Rate limiting, caching, improved testing |
| 2.0.0   | 2025-12-28   | Multi-LLM, web fallback, modern UI |
| 1.0.0   | 2025-12-01   | Initial release |
