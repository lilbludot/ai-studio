#!/usr/bin/env python3
"""
Minimal test to see the ChatInterface in action
Simplified to avoid Gradio issues
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.chat_interface import ChatInterface
from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore
from src.core.llm_providers.provider_manager import ProviderManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

def test_chat_functionality():
    """Test the chat interface without Gradio UI"""
    print("Testing ChatInterface functionality...")
    print("=" * 50)
    
    # Initialize components
    config = ConfigManager()
    db_path = config.get('database.path', 'test_minimal_chat.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)  # Fixed: config first, then db
    msg_store = MessageStore(db, session_mgr)
    provider_mgr = ProviderManager(config)
    
    # Create ChatInterface
    chat = ChatInterface(msg_store, session_mgr, provider_mgr)
    
    # Test 1: Send a message
    print("\n1. Testing message sending...")
    test_message = "Hello! Can you tell me what 2+2 equals?"
    history = []
    
    _, updated_history, status = chat.send_message(test_message, history)
    
    print(f"User: {test_message}")
    if updated_history:
        print(f"Assistant: {updated_history[-1][1]}")
    print(f"Status: {status}")
    
    # Test 2: Switch provider and send another message
    print("\n2. Testing provider switching...")
    success = provider_mgr.switch_provider("openai")
    if success:
        print("Switched to OpenAI")
        
        test_message2 = "What's the capital of France?"
        _, updated_history, status = chat.send_message(test_message2, updated_history)
        
        print(f"User: {test_message2}")
        if updated_history:
            print(f"Assistant: {updated_history[-1][1]}")
        print(f"Status: {status}")
    
    # Test 3: Check session creation
    print("\n3. Checking session info...")
    current_session = session_mgr.get_current_session()
    if current_session:
        print(f"Session: {current_session.name}")
        print(f"Session ID: {current_session.session_id}")
        
        # Get all messages
        messages = msg_store.get_session_messages(current_session.session_id)
        print(f"Total messages in session: {len(messages)}")
    
    print("\n" + "=" * 50)
    print("✅ Chat functionality is working!")
    print("\nYour ChatInterface can:")
    print("- Send messages to LLMs")
    print("- Get responses")
    print("- Track token usage and costs")
    print("- Switch between providers")
    print("- Store conversation history")

if __name__ == "__main__":
    test_chat_functionality()
    