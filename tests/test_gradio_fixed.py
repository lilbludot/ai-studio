#!/usr/bin/env python3
"""
Fixed Gradio app that should work with your setup
"""

import os
import sys
from pathlib import Path
import gradio as gr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore, MessageRole
from src.core.llm_providers.provider_manager import ProviderManager
from src.core.llm_providers.base_provider import LLMMessage
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager
from datetime import datetime

def create_simple_app():
    """Create a simplified Gradio app"""
    # Initialize backend
    config = ConfigManager()
    db_path = config.get('database.path', 'gradio_chat.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)  # CORRECT: config first, then db
    msg_store = MessageStore(db, session_mgr)
    provider_mgr = ProviderManager(config)
    
    # Create or get session
    sessions = session_mgr.get_active_sessions()
    if sessions:
        session_id = sessions[0].session_id
    else:
        session_id = session_mgr.create_session(
            name=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            project_type="general"
        )
    
    def chat_function(message, history):
        """Handle chat interactions"""
        if not message:
            return "", history
        
        # Save user message
        msg_store.save_message(
            role=MessageRole.USER,
            content=message,
            session_id=session_id
        )
        
        # Build context
        context = msg_store.build_context(session_id)
        
        # Prepare messages for LLM
        llm_messages = []
        if context.system_prompt:
            llm_messages.append(
                LLMMessage(role="system", content=context.system_prompt)
            )
        
        for msg in context.messages:
            llm_messages.append(
                LLMMessage(role=msg.role, content=msg.content)
            )
        
        # Get response
        try:
            response = provider_mgr.send_message(
                messages=llm_messages,
                model="claude-3-5-sonnet-20241022",  # Default model
                temperature=0.7,
                max_tokens=1000
            )
            
            # Save assistant response
            msg_store.save_message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                session_id=session_id,
                metadata={
                    "model": response.model,
                    "tokens": response.total_tokens
                }
            )
            
            # Update history
            history.append((message, response.content))
            
            return "", history
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            history.append((message, error_msg))
            return "", history
    
    # Create the interface
    with gr.Blocks(title="AI Chat Test") as demo:
        gr.Markdown("# AI Chat Interface Test")
        gr.Markdown("Chat with Claude or OpenAI")
        
        chatbot = gr.Chatbot(
            label="Conversation",
            height=400
        )
        
        msg = gr.Textbox(
            label="Message",
            placeholder="Type your message here...",
            lines=2
        )
        
        with gr.Row():
            submit = gr.Button("Send", variant="primary")
            clear = gr.Button("Clear")
        
        # Set up events
        submit.click(
            fn=chat_function,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            fn=chat_function,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        clear.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, msg]
        )
        
        gr.Markdown("**Note**: Using Claude 3.5 Sonnet by default")
    
    return demo

if __name__ == "__main__":
    print("Starting simplified Gradio chat...")
    app = create_simple_app()
    
    # Use simpler launch parameters
    app.launch(
        server_port=7861,  # Different port to avoid conflicts
        share=False,
        quiet=True  # Suppress extra output
    )