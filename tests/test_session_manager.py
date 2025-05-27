#!/usr/bin/env python3
"""
Quick test for SessionManager
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.session_manager import SessionManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager


def test_session_manager():
    print("Testing SessionManager...\n")
    
    # Initialize components
    config = ConfigManager()
    db = DatabaseManager("test_sessions.db")
    session_mgr = SessionManager(config, db)
    
    try:
        # 1. Create sessions
        session1_id = session_mgr.create_session(
            name="Google ML Application",
            project_type="job_search",
            metadata={"company": "Google", "role": "ML Engineer"}
        )
        print(f"✓ Created session 1: {session1_id}")
        
        session2_id = session_mgr.create_session(
            name="AI Studio Development",
            project_type="coding"
        )
        print(f"✓ Created session 2: {session2_id}")
        
        # 2. Get current session
        current = session_mgr.get_current_session()
        print(f"✓ Current session: {current.name}")
        
        # 3. Switch sessions
        session_mgr.set_current_session(session1_id)
        print(f"✓ Switched to: {session_mgr.get_current_session().name}")
        
        # 4. Get all user sessions
        all_sessions = session_mgr.get_user_sessions()
        print(f"\n✓ Found {len(all_sessions)} sessions:")
        for s in all_sessions:
            print(f"  - {s.name} ({s.project_type})")
        
        # 5. Update activity (simulate messages)
        session_mgr.increment_message_count(session1_id)
        session_mgr.increment_message_count(session1_id)
        print(f"\n✓ Updated message count")
        
        # 6. Get stats
        stats = session_mgr.get_session_stats(session1_id)
        print(f"\n✓ Session stats:")
        print(f"  Messages: {stats['message_count']}")
        print(f"  Created: {stats['created_at'][:10]}")
        
        # 7. Search sessions
        results = session_mgr.search_sessions("Google")
        print(f"\n✓ Search found {len(results)} sessions matching 'Google'")
        
        # Cleanup
        db.close()
        Path("test_sessions.db").unlink()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        db.close()
        if Path("test_sessions.db").exists():
            Path("test_sessions.db").unlink()


if __name__ == "__main__":
    test_session_manager()