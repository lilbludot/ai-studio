#!/usr/bin/env python3
"""
Simple test for DatabaseManager
Tests basic functionality before committing
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.database import DatabaseManager, Session, Message, Document
import uuid
from datetime import datetime


def test_database_manager():
    print("Testing DatabaseManager...\n")
    
    # Use a test database
    db_path = "test_ai_studio.db"
    
    try:
        # 1. Initialize DatabaseManager
        db = DatabaseManager(db_path)
        print("✓ DatabaseManager initialized")
        
        # 2. Create a session
        session = Session(
            id=str(uuid.uuid4()),
            name="Job Search - Google",
            project_type="cover_letter",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            metadata={"company": "Google", "position": "ML Engineer"},
            user_id="kinga"
        )
        session_id = db.create_session(session)
        print(f"✓ Created session: {session.name}")
        
        # 3. Save some messages
        # User message
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content="Help me write a cover letter for a Google ML position",
            content_type="text",
            created_at=datetime.utcnow().isoformat(),
            metadata={"char_count": 47}
        )
        db.save_message(user_msg)
        print("✓ Saved user message")
        
        # Assistant response
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content="I'd be happy to help you write a cover letter for Google's ML position. Let's start by...",
            content_type="text",
            created_at=datetime.utcnow().isoformat(),
            metadata={"model": "claude-3-5-sonnet", "tokens": 50}
        )
        db.save_message(assistant_msg)
        print("✓ Saved assistant message")
        
        # 4. Retrieve messages
        messages = db.get_session_messages(session_id)
        print(f"\n--- Retrieved {len(messages)} messages ---")
        for msg in messages:
            print(f"{msg.role}: {msg.content[:50]}...")
        
        # 5. Create a document
        doc = Document(
            id=str(uuid.uuid4()),
            session_id=session_id,
            title="Google ML Engineer Cover Letter - Draft 1",
            content="Dear Hiring Manager at Google...",
            document_type="cover_letter",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            metadata={"version": 1, "status": "draft"}
        )
        doc_id = db.save_document(doc)
        print(f"\n✓ Saved document: {doc.title}")
        
        # 6. Get all user sessions
        sessions = db.get_user_sessions("kinga")
        print(f"\n--- Found {len(sessions)} sessions for user 'kinga' ---")
        for s in sessions:
            print(f"  - {s.name} ({s.project_type})")
        
        # 7. Get database stats
        stats = db.get_database_stats()
        print("\n--- Database Stats ---")
        print(f"Sessions: {stats['total_sessions']}")
        print(f"Messages: {stats['total_messages']}")
        print(f"Documents: {stats['total_documents']}")
        print(f"Database size: {stats['database_size']} bytes")
        
        # 8. Test updating
        updated = db.update_session(session_id, {"name": "Job Search - Google (Updated)"})
        print(f"\n✓ Updated session: {updated}")
        
        # Clean up - close connection
        db.close()
        print("\n✅ All tests passed!")
        
        # Remove test database
        if Path(db_path).exists():
            Path(db_path).unlink()
            print(f"Cleaned up test database: {db_path}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        if Path(db_path).exists():
            Path(db_path).unlink()


if __name__ == "__main__":
    test_database_manager()