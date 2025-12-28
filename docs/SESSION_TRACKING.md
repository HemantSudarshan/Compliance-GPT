# Session Tracking and Query History

This document describes the session tracking and query history functionality in ComplianceGPT.

## Overview

ComplianceGPT now includes built-in session tracking and query history using SQLite. This feature allows you to:

- Track user sessions across the application
- Log all queries and their responses
- Retrieve query history for analysis
- Monitor system usage statistics

## Architecture

### Database Schema

The system uses SQLite with two main tables:

1. **sessions** - Stores user session information
   - `session_id` (TEXT, PRIMARY KEY) - Unique session identifier (UUID)
   - `created_at` (TEXT) - Session creation timestamp
   - `last_activity` (TEXT) - Last activity timestamp
   - `metadata` (TEXT, JSON) - Additional session metadata

2. **queries** - Stores query and response history
   - `query_id` (TEXT, PRIMARY KEY) - Unique query identifier (UUID)
   - `session_id` (TEXT, FOREIGN KEY) - Reference to session
   - `question` (TEXT) - User's question
   - `answer` (TEXT) - Generated answer
   - `regulation_filter` (TEXT) - Applied regulation filter
   - `num_citations` (INTEGER) - Number of citations
   - `has_context` (INTEGER) - Whether context was found
   - `timestamp` (TEXT) - Query timestamp
   - `metadata` (TEXT, JSON) - Additional metadata (provider, model, etc.)

### Storage Location

The SQLite database is stored at: `data/sessions.db`

This file is excluded from git via `.gitignore`.

## Usage

### Python API

#### Creating a Session

```python
from src.storage.session_db import SessionDatabase

db = SessionDatabase()
session = db.create_session(metadata={"user": "john", "source": "web"})
print(f"Session ID: {session.session_id}")
```

#### Logging a Query

```python
db.log_query(
    session_id=session.session_id,
    question="What is GDPR?",
    answer="GDPR is the General Data Protection Regulation...",
    regulation_filter="GDPR",
    num_citations=3,
    has_context=True,
    metadata={"provider": "groq", "model": "llama-3.3-70b"}
)
```

#### Retrieving Query History

```python
# Get history for a specific session
history = db.get_session_history(session.session_id, limit=50)

for record in history:
    print(f"Q: {record.question}")
    print(f"A: {record.answer[:100]}...")
    print(f"Citations: {record.num_citations}")
```

#### Getting Statistics

```python
# Session statistics
stats = db.get_session_stats(session.session_id)
print(f"Total queries: {stats['query_count']}")

# Database-wide statistics
db_stats = db.get_database_stats()
print(f"Total sessions: {db_stats['total_sessions']}")
print(f"Total queries: {db_stats['total_queries']}")
```

### Streamlit Integration

The Streamlit app automatically:
1. Creates a new session when the app starts
2. Logs every query and response
3. Displays query history in the sidebar

The session is stored in `st.session_state` and persists during the user's session.

### FastAPI Endpoints

#### Create a Session

```http
POST /api/sessions
Content-Type: application/json

{
  "metadata": {
    "source": "api",
    "user_agent": "MyApp/1.0"
  }
}
```

Response:
```json
{
  "session_id": "uuid-here",
  "created_at": "2025-12-28T16:00:00+00:00",
  "last_activity": "2025-12-28T16:00:00+00:00",
  "metadata": {"source": "api", "user_agent": "MyApp/1.0"}
}
```

#### Query with Session Tracking

```http
POST /api/query
Content-Type: application/json

{
  "question": "What is GDPR?",
  "regulation": "GDPR",
  "session_id": "uuid-here"
}
```

The query and response will be automatically logged if `session_id` is provided.

#### Get Session History

```http
GET /api/sessions/{session_id}/history?limit=50
```

Response:
```json
{
  "session_id": "uuid-here",
  "queries": [
    {
      "query_id": "query-uuid",
      "question": "What is GDPR?",
      "answer": "GDPR is...",
      "regulation_filter": "GDPR",
      "num_citations": 3,
      "timestamp": "2025-12-28T16:00:00+00:00"
    }
  ]
}
```

## Features

### Automatic Session Management

- Sessions are created automatically when users interact with the application
- Last activity timestamp is updated on each query
- Sessions persist across application restarts

### Query History

- All queries are logged with full context
- History is ordered by timestamp (newest first)
- Supports pagination with configurable limits
- Includes metadata about LLM provider and model used

### Statistics

- Track number of queries per session
- Monitor total database usage
- Analyze query patterns and performance

### Error Handling

- Logging failures don't break queries
- Graceful degradation if database is unavailable
- Transaction-safe operations

## Testing

Run the test suite:

```bash
pytest tests/test_session_db.py -v
```

All 15 tests should pass, covering:
- Session creation and retrieval
- Query logging
- History retrieval with pagination
- Statistics calculation
- Session deletion
- Multi-session handling

## Demo

A demo script is provided to showcase the functionality:

```bash
python demo_session_tracking.py
```

This will:
1. Create a new session
2. Log sample queries
3. Display query history
4. Show session and database statistics

## Performance

- Database operations are transaction-safe
- Indexes on `session_id` and `timestamp` for fast queries
- Connection pooling via context managers
- Minimal overhead on query processing

## Security

- No sensitive data is logged by default
- Database file permissions should be restricted
- Use HTTPS for API endpoints in production
- Consider encrypting sensitive metadata

## Future Enhancements

Potential improvements:
- Session expiration and cleanup
- Query analytics dashboard
- Export functionality (CSV, JSON)
- Advanced search and filtering
- User authentication integration
- Session replay functionality
