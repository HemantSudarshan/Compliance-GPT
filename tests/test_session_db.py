"""
test_session_db.py - Tests for Session Database

Tests session management and query history functionality.
"""

import pytest
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone

from src.storage.session_db import (
    SessionDatabase,
    Session,
    QueryRecord,
    get_session_database
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = SessionDatabase(db_path)
    yield db
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


def test_session_creation(temp_db):
    """Test creating a new session."""
    metadata = {"source": "test", "user_agent": "pytest"}
    session = temp_db.create_session(metadata=metadata)
    
    assert session.session_id is not None
    assert len(session.session_id) == 36  # UUID length
    assert session.created_at is not None
    assert session.last_activity is not None
    assert session.metadata == metadata


def test_get_session(temp_db):
    """Test retrieving a session by ID."""
    # Create a session
    created_session = temp_db.create_session(metadata={"test": "data"})
    
    # Retrieve it
    retrieved_session = temp_db.get_session(created_session.session_id)
    
    assert retrieved_session is not None
    assert retrieved_session.session_id == created_session.session_id
    assert retrieved_session.metadata == {"test": "data"}


def test_get_nonexistent_session(temp_db):
    """Test retrieving a session that doesn't exist."""
    session = temp_db.get_session("nonexistent-id")
    assert session is None


def test_update_session_activity(temp_db):
    """Test updating session activity timestamp."""
    session = temp_db.create_session()
    original_activity = session.last_activity
    
    # Wait a bit and update
    time.sleep(0.1)
    temp_db.update_session_activity(session.session_id)
    
    # Retrieve and check
    updated_session = temp_db.get_session(session.session_id)
    assert updated_session.last_activity > original_activity


def test_log_query(temp_db):
    """Test logging a query."""
    session = temp_db.create_session()
    
    record = temp_db.log_query(
        session_id=session.session_id,
        question="What is GDPR?",
        answer="GDPR is the General Data Protection Regulation.",
        regulation_filter="GDPR",
        num_citations=3,
        has_context=True,
        metadata={"provider": "groq", "model": "llama-3.3-70b"}
    )
    
    assert record.query_id is not None
    assert record.session_id == session.session_id
    assert record.question == "What is GDPR?"
    assert record.answer == "GDPR is the General Data Protection Regulation."
    assert record.regulation_filter == "GDPR"
    assert record.num_citations == 3
    assert record.has_context is True
    assert record.metadata["provider"] == "groq"


def test_get_session_history(temp_db):
    """Test retrieving session history."""
    session = temp_db.create_session()
    
    # Log multiple queries
    queries = [
        "What is GDPR?",
        "What are data breach requirements?",
        "What is right to erasure?"
    ]
    
    for q in queries:
        temp_db.log_query(
            session_id=session.session_id,
            question=q,
            answer=f"Answer to: {q}",
            num_citations=2
        )
    
    # Get history
    history = temp_db.get_session_history(session.session_id)
    
    assert len(history) == 3
    # Should be in reverse chronological order (newest first)
    assert history[0].question == "What is right to erasure?"
    assert history[1].question == "What are data breach requirements?"
    assert history[2].question == "What is GDPR?"


def test_get_session_history_with_limit(temp_db):
    """Test getting session history with a limit."""
    session = temp_db.create_session()
    
    # Log 10 queries
    for i in range(10):
        temp_db.log_query(
            session_id=session.session_id,
            question=f"Question {i}",
            answer=f"Answer {i}",
            num_citations=1
        )
    
    # Get only 5
    history = temp_db.get_session_history(session.session_id, limit=5)
    assert len(history) == 5


def test_get_all_queries(temp_db):
    """Test getting all queries across sessions."""
    # Create two sessions
    session1 = temp_db.create_session()
    session2 = temp_db.create_session()
    
    # Log queries in each
    temp_db.log_query(
        session_id=session1.session_id,
        question="Session 1 query",
        answer="Answer 1",
        num_citations=1
    )
    
    temp_db.log_query(
        session_id=session2.session_id,
        question="Session 2 query",
        answer="Answer 2",
        num_citations=2
    )
    
    # Get all queries
    all_queries = temp_db.get_all_queries()
    assert len(all_queries) == 2


def test_get_session_stats(temp_db):
    """Test getting session statistics."""
    session = temp_db.create_session()
    
    # Log some queries
    for i in range(5):
        temp_db.log_query(
            session_id=session.session_id,
            question=f"Question {i}",
            answer=f"Answer {i}",
            num_citations=i
        )
    
    stats = temp_db.get_session_stats(session.session_id)
    
    assert stats["session_id"] == session.session_id
    assert stats["query_count"] == 5
    assert "created_at" in stats
    assert "last_activity" in stats


def test_delete_session(temp_db):
    """Test deleting a session."""
    session = temp_db.create_session()
    
    # Log some queries
    temp_db.log_query(
        session_id=session.session_id,
        question="Test question",
        answer="Test answer",
        num_citations=1
    )
    
    # Verify session exists
    assert temp_db.get_session(session.session_id) is not None
    
    # Delete session
    result = temp_db.delete_session(session.session_id)
    assert result is True
    
    # Verify session is gone
    assert temp_db.get_session(session.session_id) is None
    
    # Verify queries are also gone
    history = temp_db.get_session_history(session.session_id)
    assert len(history) == 0


def test_delete_nonexistent_session(temp_db):
    """Test deleting a session that doesn't exist."""
    result = temp_db.delete_session("nonexistent-id")
    assert result is False


def test_get_database_stats(temp_db):
    """Test getting overall database statistics."""
    # Create sessions and queries
    session1 = temp_db.create_session()
    session2 = temp_db.create_session()
    
    temp_db.log_query(
        session_id=session1.session_id,
        question="Q1",
        answer="A1",
        num_citations=1
    )
    
    temp_db.log_query(
        session_id=session2.session_id,
        question="Q2",
        answer="A2",
        num_citations=2
    )
    
    stats = temp_db.get_database_stats()
    
    assert stats["total_sessions"] == 2
    assert stats["total_queries"] == 2
    assert stats["first_session"] is not None
    assert stats["last_activity"] is not None


def test_factory_function():
    """Test the factory function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        db = get_session_database(db_path)
        assert isinstance(db, SessionDatabase)
        assert db.db_path == db_path
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_multiple_sessions(temp_db):
    """Test multiple sessions don't interfere with each other."""
    session1 = temp_db.create_session(metadata={"user": "user1"})
    session2 = temp_db.create_session(metadata={"user": "user2"})
    
    # Log queries for each session
    temp_db.log_query(
        session_id=session1.session_id,
        question="Session 1 question",
        answer="Session 1 answer",
        num_citations=1
    )
    
    temp_db.log_query(
        session_id=session2.session_id,
        question="Session 2 question",
        answer="Session 2 answer",
        num_citations=2
    )
    
    # Verify histories are separate
    history1 = temp_db.get_session_history(session1.session_id)
    history2 = temp_db.get_session_history(session2.session_id)
    
    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0].question == "Session 1 question"
    assert history2[0].question == "Session 2 question"


def test_query_without_optional_fields(temp_db):
    """Test logging a query without optional fields."""
    session = temp_db.create_session()
    
    record = temp_db.log_query(
        session_id=session.session_id,
        question="Simple question",
        answer="Simple answer"
    )
    
    assert record.regulation_filter is None
    assert record.num_citations == 0
    assert record.has_context is True
    assert record.metadata == {}
