#!/usr/bin/env python3
"""
AI Studio - Main Application
Combines ChatInterface and DocumentEditor into a unified interface
Created: 2025-06-05
"""

import os
import sys
from pathlib import Path
import gradio as gr
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.chat_interface import ChatInterface
from src.ui.document_editor import DocumentEditor
from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore
from src.core.llm_providers.provider_manager import ProviderManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIStudioApp:
    """Main application class that combines all components"""
    
    def __init__(self):
        """Initialize the AI Studio application"""
        logger.info("Initializing AI Studio...")
        
        # Initialize configuration
        self.config = ConfigManager()
        
        # Initialize database
        db_path = self.config.get('database.path', 'ai_studio.db')
        self.db = DatabaseManager(db_path)
        
        # Initialize core components
        self.session_mgr = SessionManager(self.config, self.db)
        self.msg_store = MessageStore(self.db, self.session_mgr)
        self.provider_mgr = ProviderManager(self.config)
        
        # Initialize UI components
        self.chat_interface = ChatInterface(self.msg_store, self.session_mgr, self.provider_mgr)
        self.doc_editor = DocumentEditor(self.db, self.session_mgr, self.config)
        self.chat_interface.set_document_editor(self.doc_editor)
        
        # Create or load session
        self._initialize_session()
        
        logger.info("AI Studio initialized successfully")
    
    def _initialize_session(self):
        """Initialize or load the session"""
        sessions = self.session_mgr.get_active_sessions()
        
        if sessions:
            # Use the most recent session
            session = sessions[0]
            self.session_mgr.set_current_session(session.session_id)
            logger.info(f"Loaded existing session: {session.name}")
        else:
            # Create a new session
            session_id = self.session_mgr.create_session(
                name=f"AI Studio Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                project_type="general",
                metadata={"created_by": "main_app"}
            )
            logger.info(f"Created new session: {session_id}")
    
    def create_interface(self):
        """Create the main Gradio interface"""
        with gr.Blocks(
            title="AI Studio",
            theme=gr.themes.Base(),
            css="""
            .container { display: flex; height: 100vh; }
            #chatbot { height: 500px; }
            /* Fix dropdown heights */
            .dropdown-menu {
                max-height: 300px !important;
                overflow-y: auto !important;
            }
            /* Control input heights */
            #message_input textarea { 
                max-height: 80px !important; 
                min-height: 60px !important;
            }
            #doc_editor textarea {
                height: 400px !important;
            }
            /* Reduce padding around components */
            .block { padding: 0.5rem !important; }
            """
        ) as app:
            # Header
            with gr.Row():
                gr.Markdown("# 🤖 AI Studio")
                gr.Markdown(
                    "Chat with AI assistants and edit documents simultaneously",
                    elem_classes=["subtitle"]
                )
            
            # Main container with two panels
            with gr.Row(equal_height=True):
                # Chat Interface (70% width)
                with gr.Column(scale=7):
                    chat_components = self.chat_interface.create_interface()
                
                # Document Editor (30% width)
                with gr.Column(scale=3):
                    doc_components = self.doc_editor.create_interface()
            
            self.chat_interface.connect_editor_to_chat()
            
            # Connect components for interaction
            self._connect_components(chat_components, doc_components)
            
            # Footer with session info
            with gr.Row():
                session_info = gr.Textbox(
                    label="Session Info",
                    value=self._get_session_info(),
                    interactive=False,
                    scale=3
                )
                
                # Refresh session info button
                refresh_btn = gr.Button("🔄 Refresh", scale=1)
                refresh_btn.click(
                    fn=self._get_session_info,
                    outputs=[session_info]
                )
        
        return app
    
    def _connect_components(self, chat_components, doc_components):
        """Connect chat and document components for interaction"""
        # This is where we'll add the logic for the LLM to control the document editor
        # For now, they work independently but share the same session
        
        # Future: Add handlers here for:
        # - LLM creating/editing documents based on chat
        # - Updating document list when new files are created
        # - Syncing content between chat and editor
        pass
    
    def _get_session_info(self):
        """Get current session information"""
        current = self.session_mgr.get_current_session()
        if current:
            providers = self.provider_mgr.list_available_providers()
            return (
                f"Session: {current.name} | "
                f"Messages: {current.message_count} | "
                f"Documents: {current.document_count} | "
                f"Providers: {', '.join(providers)}"
            )
        return "No active session"
    
    def launch(self):
        """Launch the application"""
        app = self.create_interface()
        
        # Get UI configuration
        ui_config = self.config.get_ui_config()
        
        logger.info(f"Launching AI Studio on {ui_config.host}:{ui_config.port}")
        
        app.launch(
            server_name=ui_config.host,
            server_port=ui_config.port,
            share=ui_config.share,
            show_error=True,
            show_api=False  # Disable API docs to avoid issues
        )


def main():
    """Main entry point"""
    print("\n" + "="*50)
    print("🚀 Starting AI Studio")
    print("="*50 + "\n")
    
    # Check for API keys
    if not os.getenv("CLAUDE_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: No API keys found in environment")
        print("Set at least one of: CLAUDE_API_KEY or OPENAI_API_KEY")
        print()
    
    try:
        # Create and launch the app
        app = AIStudioApp()
        app.launch()
    except KeyboardInterrupt:
        print("\n\n👋 AI Studio stopped by user")
    except Exception as e:
        logger.error(f"Failed to start AI Studio: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()