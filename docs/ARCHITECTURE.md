# ComplianceGPT Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              COMPLIANCEGPT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           CLIENT LAYER                                    │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │   │
│  │  │   Streamlit  │    │   REST API   │    │  Web Client  │                │   │
│  │  │     App      │    │   Clients    │    │  (HTML/JS)   │                │   │
│  │  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                │   │
│  └─────────┼───────────────────┼───────────────────┼────────────────────────┘   │
│            │                   │                   │                            │
│            ▼                   ▼                   ▼                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         API GATEWAY LAYER                                 │   │
│  │  ┌────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                       FastAPI Application                           │  │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │  │   │
│  │  │  │  Rate   │ │  Auth   │ │ Logging │ │ Caching │ │   Error     │  │  │   │
│  │  │  │ Limiter │ │  Check  │ │ Midware │ │  Layer  │ │  Handler    │  │  │   │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘  │  │   │
│  │  │       └───────────┴───────────┴───────────┴─────────────┘         │  │   │
│  │  │                              │                                     │  │   │
│  │  │  ┌───────────────────────────┴───────────────────────────────┐    │  │   │
│  │  │  │                      API ENDPOINTS                         │    │  │   │
│  │  │  │  /api/query  │  /api/stats  │  /health  │  /metrics       │    │  │   │
│  │  │  │  /api/audit  │  /api/cache  │  /admin   │  /api/version   │    │  │   │
│  │  │  └───────────────────────────────────────────────────────────┘    │  │   │
│  │  └────────────────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         BUSINESS LOGIC LAYER                              │   │
│  │                                                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐     │   │
│  │  │                    QUERY PROCESSING PIPELINE                     │     │   │
│  │  │                                                                  │     │   │
│  │  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │     │   │
│  │  │  │  Query   │───▶│ Hybrid   │───▶│ Context  │───▶│ Response │  │     │   │
│  │  │  │ Parser   │    │ Retriever│    │ Builder  │    │Generator │  │     │   │
│  │  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │     │   │
│  │  │                                                                  │     │   │
│  │  └─────────────────────────────────────────────────────────────────┘     │   │
│  │                                                                           │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐   │   │
│  │  │   Citation Engine   │  │   Query Expansion   │  │  RAGAS Eval     │   │   │
│  │  │  ├─ Source tagging  │  │  ├─ Synonyms        │  │  ├─ Faithfulness│   │   │
│  │  │  ├─ Quote extraction│  │  ├─ Related terms   │  │  ├─ Relevance   │   │   │
│  │  │  └─ Reference links │  │  └─ Concept mapping │  │  └─ Context     │   │   │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────────┘   │   │
│  │                                                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│            ┌─────────────────────────┼─────────────────────────┐               │
│            │                         │                         │               │
│            ▼                         ▼                         ▼               │
│  ┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    │
│  │   STORAGE LAYER │    │    LLM PROVIDERS    │    │   EXTERNAL SERVICES │    │
│  │                 │    │                     │    │                     │    │
│  │ ┌─────────────┐ │    │ ┌───────────────┐   │    │ ┌───────────────┐   │    │
│  │ │  Weaviate   │ │    │ │     Groq      │   │    │ │   Tavily      │   │    │
│  │ │  (Vector)   │ │    │ │  (llama-3.3)  │   │    │ │  Web Search   │   │    │
│  │ └─────────────┘ │    │ └───────────────┘   │    │ └───────────────┘   │    │
│  │                 │    │ ┌───────────────┐   │    │                     │    │
│  │ ┌─────────────┐ │    │ │    Gemini     │   │    │ ┌───────────────┐   │    │
│  │ │   BM25      │ │    │ │   (2.0-flash) │   │    │ │   Webhooks    │   │    │
│  │ │ (Keyword)   │ │    │ └───────────────┘   │    │ │   (Alerts)    │   │    │
│  │ └─────────────┘ │    │ ┌───────────────┐   │    │ └───────────────┘   │    │
│  │                 │    │ │    OpenAI     │   │    │                     │    │
│  │ ┌─────────────┐ │    │ │   (gpt-4o)    │   │    │ ┌───────────────┐   │    │
│  │ │    JSON     │ │    │ └───────────────┘   │    │ │  Prometheus   │   │    │
│  │ │  (Chunks)   │ │    │                     │    │ │   Endpoint    │   │    │
│  │ └─────────────┘ │    │                     │    │ └───────────────┘   │    │
│  └─────────────────┘    └─────────────────────┘    └─────────────────────┘    │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                           INFRASTRUCTURE LAYER                                   │
│                                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │
│  │    Docker     │  │  Kubernetes   │  │    GitHub     │  │   Hugging     │    │
│  │  Container    │  │   Cluster     │  │   Actions     │  │    Face       │    │
│  │               │  │               │  │    CI/CD      │  │   Spaces      │    │
│  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Client Layer
- **Streamlit App**: Interactive compliance assistant with chat interface
- **REST API Clients**: Programmatic access for integrations
- **Web Client**: Static HTML/CSS/JS frontend for embedding

### 2. API Gateway Layer
- **FastAPI Application**: High-performance async API framework
- **Middleware Stack**:
  - Rate Limiter: 30 req/min per IP (configurable)
  - Auth Check: API key validation
  - Logging Middleware: Structured request logging
  - Caching Layer: TTL-based response cache
  - Error Handler: Consistent error responses

### 3. Business Logic Layer
- **Query Processing Pipeline**:
  1. Query parsing and validation
  2. Hybrid retrieval (BM25 + semantic)
  3. Context building and relevance ranking
  4. Response generation with citations

- **Core Services**:
  - Citation Engine: Source attribution and quote extraction
  - Query Expansion: Synonym and concept mapping
  - RAGAS Evaluation: Quality metrics

### 4. Storage Layer
- **Weaviate Cloud**: Vector database for semantic search
- **BM25 Index**: Keyword-based retrieval
- **JSON Storage**: Document chunks and metadata

### 5. LLM Providers
- **Groq** (Default): llama-3.3-70b-versatile
- **Gemini**: gemini-2.0-flash-exp
- **OpenAI**: gpt-4o-mini

### 6. External Services
- **Tavily**: Web search for current regulations
- **Webhooks**: Alert notifications
- **Prometheus**: Metrics collection

## Data Flow

```
User Query
    │
    ▼
┌─────────────────┐
│ API Validation  │
│ (Pydantic)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Rate Limiting   │
│ & Auth Check    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ Cache Lookup    │─────▶│ Return Cache │
│ (if enabled)    │ HIT  │   Response   │
└────────┬────────┘      └──────────────┘
         │ MISS
         ▼
┌─────────────────┐
│ Query Expansion │
│ (synonyms)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ Hybrid Search   │─────▶│   Weaviate   │
│ (BM25 + Vector) │      │   (Vector)   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│ Context Builder │
│ (Top-K chunks)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│ LLM Generation  │─────▶│ Groq/Gemini  │
│ (with prompt)   │      │   /OpenAI    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│ Citation Engine │
│ (source tags)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response Format │
│ & Cache Store   │
└────────┬────────┘
         │
         ▼
    API Response
```

## Deployment Architecture

### Production (Kubernetes)

```
┌─────────────────────────────────────────────────────────────────┐
│                        KUBERNETES CLUSTER                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    INGRESS CONTROLLER                       │ │
│  │                    (nginx / traefik)                        │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────┼─────────────────────────────────┐ │
│  │                      SERVICE MESH                           │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │ │
│  │  │   Pod (API)     │  │   Pod (API)     │  │  Pod (API)  │ │ │
│  │  │   Replica 1     │  │   Replica 2     │  │  Replica 3  │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────┘ │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   ConfigMap     │  │     Secret      │  │       HPA       │  │
│  │  (env config)   │  │  (API keys)     │  │   (autoscale)   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                            │
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │  Weaviate   │   │    Groq     │   │    Monitoring       │   │
│  │   Cloud     │   │     API     │   │   (Prometheus)      │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Layer 1: Network Security                                   │ │
│  │  • TLS 1.3 encryption                                      │ │
│  │  • Network policies (Kubernetes)                           │ │
│  │  • Firewall rules                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Layer 2: Application Security                               │ │
│  │  • API key authentication                                  │ │
│  │  • Rate limiting (per IP/tenant)                           │ │
│  │  • Input validation (Pydantic)                             │ │
│  │  • SQL injection protection (N/A - no SQL)                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Layer 3: Data Security                                      │ │
│  │  • Secrets management (K8s Secrets)                        │ │
│  │  • No PII storage in logs                                  │ │
│  │  • Audit logging                                           │ │
│  │  • Data encryption at rest                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Layer 4: Operational Security                               │ │
│  │  • Security scanning (Snyk, Bandit)                        │ │
│  │  • Dependency auditing                                     │ │
│  │  • Container image scanning                                │ │
│  │  • Incident response procedures                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
ComplianceGPT/
├── api/                    # API Layer
│   ├── main.py            # FastAPI application
│   ├── middleware.py      # Middleware stack
│   ├── metrics.py         # Prometheus metrics
│   ├── audit.py           # Audit logging
│   ├── health.py          # Health checks
│   ├── tenants.py         # Multi-tenancy
│   ├── admin.py           # Admin endpoints
│   └── tracing.py         # Distributed tracing
│
├── src/                    # Business Logic
│   ├── generation/        # Response generation
│   │   ├── citation_engine.py
│   │   └── prompts.py
│   ├── storage/           # Data storage
│   │   ├── retriever.py
│   │   ├── indexer.py
│   │   └── weaviate_client.py
│   ├── ingestion/         # Data ingestion
│   │   ├── parser.py
│   │   ├── chunker.py
│   │   └── table_linearizer.py
│   ├── evaluation/        # Quality evaluation
│   │   ├── ragas_eval.py
│   │   └── change_detector.py
│   └── utils/             # Utilities
│       ├── config.py
│       ├── logger.py
│       └── web_search.py
│
├── app/                    # Streamlit Frontend
│   ├── Home.py
│   └── pages/
│
├── tests/                  # Test Suite
│   ├── test_citation.py
│   ├── test_parser.py
│   ├── test_retriever.py
│   ├── test_middleware.py
│   └── load/
│       └── locustfile.py
│
├── deploy/                 # Deployment
│   └── kubernetes/
│       └── deployment.yaml
│
├── scripts/                # Utility Scripts
│   ├── run_ingestion.py
│   ├── run_evaluation.py
│   ├── migrations.py
│   └── add_pdf.py
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   └── RUNBOOK.md
│
├── .github/workflows/      # CI/CD
│   └── ci-cd.yml
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```
