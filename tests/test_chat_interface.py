#!/usr/bin/env python3
"""
Test script for ChatInterface component
We'll test step by step to make sure everything works
"""

import os
import sys
from pathlib import Path
import gradio as gr  # Add this import

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.chat_interface import ChatInterface
from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore
from src.core.llm_providers.provider_manager import ProviderManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

def test_step(step_name: str, test_func):
    """Run a test step and report results"""
    print(f"\n{'='*50}")
    print(f"Testing: {step_name}")
    print('='*50)
    try:
        result = test_func()
        print(f"✅ {step_name} - PASSED")
        return result
    except Exception as e:
        print(f"❌ {step_name} - FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_1_setup_components():
    """Test 1: Set up all required components"""
    print("Setting up configuration...")
    config = ConfigManager()
    
    print("Setting up database...")
    # DatabaseManager expects a path, not a ConfigManager
    db_path = config.get('database.path', 'test_ai_studio.db')
    db = DatabaseManager(db_path)
    # No need to call initialize() - it's done in __init__
    
    print("Setting up session manager...")
    session_mgr = SessionManager(db, config)
    
    print("Setting up message store...")
    msg_store = MessageStore(db, session_mgr)
    
    print("Setting up provider manager...")
    provider_mgr = ProviderManager(config)
    
    return config, db, session_mgr, msg_store, provider_mgr

def test_2_create_chat_interface(msg_store, session_mgr, provider_mgr):
    """Test 2: Create ChatInterface instance"""
    print("Creating ChatInterface...")
    chat = ChatInterface(msg_store, session_mgr, provider_mgr)
    print(f"ChatInterface created: {chat}")
    return chat

def test_3_create_ui_components(chat):
    """Test 3: Create UI components"""
    print("Creating UI components...")
    
    # Gradio components need to be created within a Blocks context
    import gradio as gr
    
    with gr.Blocks() as demo:
        components = chat.create_interface()
    
    print("\nComponents created:")
    for name, component in components.items():
        print(f"  - {name}: {type(component).__name__}")
    
    return components, demo

def test_4_check_initial_state(chat):
    """Test 4: Check initial UI state"""
    print("Checking provider choices...")
    providers = chat._get_provider_choices()
    print(f"Available providers: {providers}")
    
    print("\nChecking model choices...")
    models = chat._get_model_choices()
    print(f"Available models: {models}")
    
    print("\nChecking default model...")
    default_model = chat._get_default_model()
    print(f"Default model: {default_model}")
    
    return True

def test_5_display_empty_conversation(chat):
    """Test 5: Display empty conversation"""
    print("Testing empty conversation display...")
    history = chat.display_conversation()
    print(f"Empty conversation: {history}")
    assert history == [], "Empty conversation should return empty list"
    return True

def main():
    print("ChatInterface Test Script")
    print("========================")
    print("We'll test each component step by step")
    
    # Test 1: Setup
    result = test_step("Setup Components", test_1_setup_components)
    if not result:
        print("\n⚠️  Stopping here - we need to fix the setup first")
        return
    
    config, db, session_mgr, msg_store, provider_mgr = result
    
    # Test 2: Create ChatInterface
    chat = test_step("Create ChatInterface", 
                     lambda: test_2_create_chat_interface(msg_store, session_mgr, provider_mgr))
    if not chat:
        print("\n⚠️  Stopping here - we need to fix ChatInterface creation")
        return
    
    # Test 3: Create UI Components
    result = test_step("Create UI Components", 
                          lambda: test_3_create_ui_components(chat))
    if not result:
        print("\n⚠️  Stopping here - we need to fix UI component creation")
        return
    
    components, demo = result  # Unpack both components and demo
    
    # Test 4: Check Initial State
    test_step("Check Initial State", 
              lambda: test_4_check_initial_state(chat))
    
    # Test 5: Display Empty Conversation
    test_step("Display Empty Conversation", 
              lambda: test_5_display_empty_conversation(chat))
    
    print("\n" + "="*50)
    print("BASIC TESTS COMPLETE!")
    print("="*50)
    print("\nThe ChatInterface is working! Next we could:")
    print("1. Test sending a message (requires API keys)")
    print("2. Test provider switching")
    print("3. Create a simple Gradio app to see it in action")
    print("\nWhat would you like to do next?")

if __name__ == "__main__":
    main()