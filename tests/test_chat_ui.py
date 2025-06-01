#!/usr/bin/env python3
"""
Test ChatInterface with proper UI component initialization
"""

import os
import sys
from pathlib import Path
import gradio as gr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.chat_interface import ChatInterface
from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore
from src.core.llm_providers.provider_manager import ProviderManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

def test_chat_with_ui():
    """Test ChatInterface with UI components properly initialized"""
    print("Testing ChatInterface with UI...")
    print("=" * 50)
    
    # Initialize backend components
    config = ConfigManager()
    db_path = config.get('database.path', 'test_chat_ui.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)
    msg_store = MessageStore(db, session_mgr)
    provider_mgr = ProviderManager(config)
    
    # Create ChatInterface
    chat = ChatInterface(msg_store, session_mgr, provider_mgr)
    
    # Create UI components in a Gradio context
    print("\n1. Creating UI components...")
    with gr.Blocks() as demo:
        components = chat.create_interface()
    
    print("✓ UI components created:")
    for name, comp in components.items():
        print(f"  - {name}: {type(comp).__name__}")
    
    # Now test sending a message
    print("\n2. Testing message sending...")
    
    # The send_message function expects (message, history)
    test_message = "Hello! What is 2+2?"
    history = []
    
    try:
        # Call send_message directly
        cleared_input, updated_history, status = chat.send_message(test_message, history)
        
        print(f"✓ Message sent successfully!")
        print(f"  User: {test_message}")
        if updated_history:
            print(f"  Assistant: {updated_history[0][1]}")
        print(f"  Status: {status}")
        
        # Test with another message
        test_message2 = "What's the capital of France?"
        cleared_input, updated_history, status = chat.send_message(test_message2, updated_history)
        
        print(f"\n✓ Second message sent!")
        print(f"  User: {test_message2}")
        if len(updated_history) > 1:
            print(f"  Assistant: {updated_history[1][1]}")
        print(f"  Status: {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check session info
    print("\n3. Session information:")
    current_session = session_mgr.get_current_session()
    if current_session:
        print(f"  Session: {current_session.name}")
        print(f"  Messages: {current_session.message_count}")
    
    print("\n✅ ChatInterface test complete!")

if __name__ == "__main__":
    test_chat_with_ui()