"""
session_db.py - SQLite Database for User Session Tracking and Query History

Provides session management and query history tracking for ComplianceGPT.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a user session."""
    session_id: str
    created_at: str
    last_activity: str
    metadata: Dict[str, Any]


@dataclass
class QueryRecord:
    """Represents a query and its response."""
    query_id: str
    session_id: str
    question: str
    answer: str
    regulation_filter: Optional[str]
    num_citations: int
    has_context: bool
    timestamp: str
    metadata: Dict[str, Any]


class SessionDatabase:
    """
    SQLite database for managing user sessions and query history.
    
    Stores:
    - User sessions with metadata
    - Query history with answers and citations
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the session database.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/sessions.db
        """
        if db_path is None:
            # Default to data directory
            project_root = Path(__file__).parent.parent.parent
            db_dir = project_root / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "sessions.db"
        
        self.db_path = str(db_path)
        self._init_database()
        logger.info(f"SessionDatabase initialized at {self.db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Queries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    query_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    regulation_filter TEXT,
                    num_citations INTEGER DEFAULT 0,
                    has_context INTEGER DEFAULT 1,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_queries_session 
                ON queries(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_queries_timestamp 
                ON queries(timestamp DESC)
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """
        Create a new user session.
        
        Args:
            metadata: Optional metadata to store with session (e.g., user agent, IP)
            
        Returns:
            Created Session object
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, created_at, last_activity, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, timestamp, timestamp, metadata_json))
            conn.commit()
        
        logger.info(f"Created session: {session_id}")
        return Session(
            session_id=session_id,
            created_at=timestamp,
            last_activity=timestamp,
            metadata=metadata or {}
        )
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, created_at, last_activity, metadata
                FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return Session(
                    session_id=row[0],
                    created_at=row[1],
                    last_activity=row[2],
                    metadata=json.loads(row[3]) if row[3] else {}
                )
        return None
    
    def update_session_activity(self, session_id: str):
        """
        Update the last activity timestamp for a session.
        
        Args:
            session_id: Session ID to update
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions SET last_activity = ?
                WHERE session_id = ?
            """, (timestamp, session_id))
            conn.commit()
    
    def log_query(
        self,
        session_id: str,
        question: str,
        answer: str,
        regulation_filter: Optional[str] = None,
        num_citations: int = 0,
        has_context: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QueryRecord:
        """
        Log a query and its response.
        
        Args:
            session_id: Session ID
            question: User's question
            answer: Generated answer
            regulation_filter: Applied regulation filter
            num_citations: Number of citations in response
            has_context: Whether context was found
            metadata: Additional metadata (provider, model, etc.)
            
        Returns:
            Created QueryRecord object
        """
        query_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO queries (
                    query_id, session_id, question, answer, 
                    regulation_filter, num_citations, has_context, 
                    timestamp, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_id, session_id, question, answer,
                regulation_filter, num_citations, int(has_context),
                timestamp, metadata_json
            ))
            conn.commit()
        
        # Update session activity
        self.update_session_activity(session_id)
        
        logger.info(f"Logged query {query_id} for session {session_id}")
        return QueryRecord(
            query_id=query_id,
            session_id=session_id,
            question=question,
            answer=answer,
            regulation_filter=regulation_filter,
            num_citations=num_citations,
            has_context=has_context,
            timestamp=timestamp,
            metadata=metadata or {}
        )
    
    def get_session_history(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> List[QueryRecord]:
        """
        Get query history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of queries to return
            
        Returns:
            List of QueryRecord objects, ordered by timestamp (newest first)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query_id, session_id, question, answer,
                       regulation_filter, num_citations, has_context,
                       timestamp, metadata
                FROM queries
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            return [
                QueryRecord(
                    query_id=row[0],
                    session_id=row[1],
                    question=row[2],
                    answer=row[3],
                    regulation_filter=row[4],
                    num_citations=row[5],
                    has_context=bool(row[6]),
                    timestamp=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                )
                for row in rows
            ]
    
    def get_all_queries(self, limit: int = 100) -> List[QueryRecord]:
        """
        Get all queries across all sessions.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of QueryRecord objects, ordered by timestamp (newest first)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query_id, session_id, question, answer,
                       regulation_filter, num_citations, has_context,
                       timestamp, metadata
                FROM queries
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [
                QueryRecord(
                    query_id=row[0],
                    session_id=row[1],
                    question=row[2],
                    answer=row[3],
                    regulation_filter=row[4],
                    num_citations=row[5],
                    has_context=bool(row[6]),
                    timestamp=row[7],
                    metadata=json.loads(row[8]) if row[8] else {}
                )
                for row in rows
            ]
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary with session statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get query count
            cursor.execute("""
                SELECT COUNT(*) FROM queries WHERE session_id = ?
            """, (session_id,))
            query_count = cursor.fetchone()[0]
            
            # Get session info
            cursor.execute("""
                SELECT created_at, last_activity FROM sessions WHERE session_id = ?
            """, (session_id,))
            session_info = cursor.fetchone()
            
            if session_info:
                return {
                    "session_id": session_id,
                    "query_count": query_count,
                    "created_at": session_info[0],
                    "last_activity": session_info[1]
                }
            return {}
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its queries.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if session not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete queries first (foreign key constraint)
            cursor.execute("DELETE FROM queries WHERE session_id = ?", (session_id,))
            
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                logger.info(f"Deleted session: {session_id}")
            return deleted
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get overall database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM queries")
            query_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT MIN(created_at), MAX(last_activity) FROM sessions
            """)
            date_range = cursor.fetchone()
            
            return {
                "total_sessions": session_count,
                "total_queries": query_count,
                "first_session": date_range[0] if date_range[0] else None,
                "last_activity": date_range[1] if date_range[1] else None
            }


def get_session_database(db_path: Optional[str] = None) -> SessionDatabase:
    """
    Factory function to get a SessionDatabase instance.
    
    Args:
        db_path: Optional path to database file
        
    Returns:
        SessionDatabase instance
    """
    return SessionDatabase(db_path)


if __name__ == "__main__":
    # Test the database
    print("Testing SessionDatabase...")
    
    db = SessionDatabase()
    
    # Create a session
    session = db.create_session(metadata={"source": "test"})
    print(f"Created session: {session.session_id}")
    
    # Log some queries
    db.log_query(
        session_id=session.session_id,
        question="What is GDPR?",
        answer="GDPR is the General Data Protection Regulation...",
        regulation_filter="GDPR",
        num_citations=3,
        metadata={"provider": "groq", "model": "llama-3.3-70b"}
    )
    
    db.log_query(
        session_id=session.session_id,
        question="What are data breach requirements?",
        answer="Organizations must notify within 72 hours...",
        regulation_filter="GDPR",
        num_citations=5,
        metadata={"provider": "groq", "model": "llama-3.3-70b"}
    )
    
    # Get history
    history = db.get_session_history(session.session_id)
    print(f"\nSession history ({len(history)} queries):")
    for record in history:
        print(f"  - {record.question[:50]}...")
    
    # Get stats
    stats = db.get_session_stats(session.session_id)
    print(f"\nSession stats: {stats}")
    
    # Get database stats
    db_stats = db.get_database_stats()
    print(f"\nDatabase stats: {db_stats}")
    
    print("\n✅ SessionDatabase test completed!")
