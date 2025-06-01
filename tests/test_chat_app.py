#!/usr/bin/env python3
"""
Simple Gradio app to test the ChatInterface
This creates a minimal UI with just the chat functionality
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

def create_app():
    """Create and configure the Gradio app"""
    # Initialize backend components
    print("Initializing backend components...")
    config = ConfigManager()
    db_path = config.get('database.path', 'test_chat_app.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)  # CORRECT: db first, then config
    msg_store = MessageStore(db, session_mgr)
    provider_mgr = ProviderManager(config)
    
    # Create ChatInterface
    print("Creating chat interface...")
    chat_interface = ChatInterface(msg_store, session_mgr, provider_mgr)
    
    # Create Gradio app
    print("Building Gradio app...")
    with gr.Blocks(title="AI Studio - Chat Test") as app:
        gr.Markdown("# AI Studio - Chat Interface Test")
        gr.Markdown("Testing the chat functionality with multiple LLM providers")
        
        # Create the chat interface
        components = chat_interface.create_interface()
        
        # Add a session info display
        with gr.Row():
            session_info = gr.Textbox(
                label="Session Info",
                value="No session active",
                interactive=False
            )
            
            def update_session_info():
                current = session_mgr.get_current_session()
                if current:
                    return f"Session: {current.name} (ID: {current.session_id[:8]}...)"
                return "No session active"
            
            # Update session info when chat is used
            chat_interface.send_btn.click(
                fn=update_session_info,
                outputs=[session_info]
            )
    
    return app

def main():
    """Run the app"""
    print("Starting AI Studio Chat Test...")
    print("=" * 50)
    
    app = create_app()
    
    print("\n✅ App created successfully!")
    print("\nStarting Gradio interface...")
    print("You can now test:")
    print("- Sending messages to Claude or OpenAI")
    print("- Switching between providers")
    print("- Seeing token usage and costs")
    print("\nPress Ctrl+C to stop the server")
    
    # Launch the app
    app.launch(
        server_name="127.0.0.1",  # Use localhost instead of 0.0.0.0
        server_port=7860,
        share=False,
        show_error=True,
        show_api=False  # Skip API generation to avoid errors
    )

if __name__ == "__main__":
    main()