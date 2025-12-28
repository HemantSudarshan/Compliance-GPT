#!/usr/bin/env python3
"""
Demo script for session tracking functionality.

This script demonstrates how to use the session tracking system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.storage.session_db import SessionDatabase


def demo_session_tracking():
    """Demonstrate session tracking functionality."""
    print("=" * 60)
    print("ComplianceGPT - Session Tracking Demo")
    print("=" * 60)
    
    # Initialize database
    db = SessionDatabase()
    print(f"\n✓ Database initialized at: {db.db_path}")
    
    # Create a new session
    session = db.create_session(metadata={
        "user_agent": "Demo Script",
        "source": "demo"
    })
    print(f"\n✓ Created session: {session.session_id}")
    
    # Log some sample queries
    sample_queries = [
        {
            "question": "What is GDPR?",
            "answer": "GDPR (General Data Protection Regulation) is a comprehensive data protection law...",
            "regulation": "GDPR",
            "citations": 5
        },
        {
            "question": "What are data breach notification requirements?",
            "answer": "Under GDPR, organizations must notify the supervisory authority within 72 hours...",
            "regulation": "GDPR",
            "citations": 3
        },
        {
            "question": "What is the right to erasure?",
            "answer": "The right to erasure, also known as 'right to be forgotten', allows individuals...",
            "regulation": "GDPR",
            "citations": 4
        }
    ]
    
    print(f"\n✓ Logging {len(sample_queries)} queries...")
    for i, query_data in enumerate(sample_queries, 1):
        db.log_query(
            session_id=session.session_id,
            question=query_data["question"],
            answer=query_data["answer"],
            regulation_filter=query_data["regulation"],
            num_citations=query_data["citations"],
            has_context=True,
            metadata={"provider": "groq", "model": "llama-3.3-70b"}
        )
        print(f"  {i}. {query_data['question']}")
    
    # Get session history
    print("\n" + "=" * 60)
    print("Query History")
    print("=" * 60)
    history = db.get_session_history(session.session_id)
    
    for i, record in enumerate(history, 1):
        print(f"\n[{i}] {record.question}")
        print(f"    Regulation: {record.regulation_filter or 'All'}")
        print(f"    Citations: {record.num_citations}")
        print(f"    Time: {record.timestamp}")
    
    # Get session stats
    print("\n" + "=" * 60)
    print("Session Statistics")
    print("=" * 60)
    stats = db.get_session_stats(session.session_id)
    print(f"Session ID: {stats['session_id']}")
    print(f"Total Queries: {stats['query_count']}")
    print(f"Created: {stats['created_at']}")
    print(f"Last Activity: {stats['last_activity']}")
    
    # Get overall database stats
    print("\n" + "=" * 60)
    print("Database Statistics")
    print("=" * 60)
    db_stats = db.get_database_stats()
    print(f"Total Sessions: {db_stats['total_sessions']}")
    print(f"Total Queries: {db_stats['total_queries']}")
    print(f"First Session: {db_stats['first_session']}")
    print(f"Last Activity: {db_stats['last_activity']}")
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    demo_session_tracking()
