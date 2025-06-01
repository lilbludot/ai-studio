#!/usr/bin/env python3
"""
Debug version to find where the error is happening
"""

import os
import sys
from pathlib import Path
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.chat_interface import ChatInterface
from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore
from src.core.llm_providers.provider_manager import ProviderManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

def test_basic_setup():
    """Test just the basic setup"""
    print("1. Creating ConfigManager...")
    config = ConfigManager()
    print("   ✓ ConfigManager created")
    
    print("\n2. Creating DatabaseManager...")
    db_path = config.get('database.path', 'test_debug.db')
    db = DatabaseManager(db_path)
    print("   ✓ DatabaseManager created")
    
    print("\n3. Creating SessionManager...")
    print(f"   - Passing config type: {type(config)}")
    print(f"   - Passing db type: {type(db)}")
    
    try:
        session_mgr = SessionManager(config, db)
        print("   ✓ SessionManager created")
        
        print("\n4. Creating a test session...")
        session_id = session_mgr.create_session(
            name="Debug Test Session",
            project_type="test"
        )
        print(f"   ✓ Session created: {session_id}")
        
    except Exception as e:
        print(f"   ❌ Error creating SessionManager or session:")
        print(f"      {type(e).__name__}: {e}")
        traceback.print_exc()
        return None
    
    return config, db, session_mgr

def main():
    print("Debug Test - Finding the parameter issue")
    print("=" * 50)
    
    result = test_basic_setup()
    
    if result:
        print("\n✅ Basic setup working! The issue might be in ChatInterface.")
    else:
        print("\n❌ Issue found in basic setup")

if __name__ == "__main__":
    main()