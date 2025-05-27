"""
Chat Interface for AI Studio
Handles the chat UI component and message interactions
Created: 2025-05-27
"""

import gradio as gr
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import uuid

from ..core.message_store import MessageStore, MessageRole
from ..core.session_manager import SessionManager
from ..core.llm_providers.provider_manager import ProviderManager
from ..core.llm_providers.base_provider import LLMMessage

logger = logging.getLogger(__name__)


class ChatInterface:
    """
    Manages the chat interface component of the UI.
    Handles message display, user input, and LLM interactions.
    """
    
    def __init__(self, 
                 message_store: MessageStore,
                 session_manager: SessionManager,
                 provider_manager: ProviderManager):
        """
        Initialize ChatInterface
        
        Args:
            message_store: Message storage manager
            session_manager: Session manager
            provider_manager: LLM provider manager
        """
        self.msg_store = message_store
        self.session_mgr = session_manager
        self.provider_mgr = provider_manager
        
        # UI components (will be set in create_interface)
        self.chatbot = None
        self.msg_input = None
        self.send_btn = None
        self.clear_btn = None
        self.provider_dropdown = None
        self.model_dropdown = None
        
        logger.info("ChatInterface initialized")
    
    def create_interface(self) -> Dict[str, Any]:
        """
        Create the chat interface components
        
        Returns:
            Dictionary of Gradio components
        """
        with gr.Column(scale=7):  # 70% width for chat
            # Chat header
            with gr.Row():
                gr.Markdown("### 💬 Conversation")
                self.provider_dropdown = gr.Dropdown(
                    choices=self._get_provider_choices(),
                    value=self.provider_mgr.current_provider_name,
                    label="Provider",
                    scale=1,
                    interactive=True
                )
                self.model_dropdown = gr.Dropdown(
                    choices=self._get_model_choices(),
                    value=self._get_default_model(),
                    label="Model",
                    scale=2,
                    interactive=True
                )
            
            # Chat display
            self.chatbot = gr.Chatbot(
                label="Chat",
                elem_id="chatbot",
                height=500,
                show_label=False
            )
            
            # Input area
            with gr.Row():
                self.msg_input = gr.Textbox(
                    label="Message",
                    placeholder="Type your message here...",
                    lines=3,
                    scale=8,
                    show_label=False
                )
                
                with gr.Column(scale=1, min_width=80):
                    self.send_btn = gr.Button("Send", variant="primary", size="lg")
                    self.clear_btn = gr.Button("Clear", size="sm")
            
            # Status info
            self.status_text = gr.Textbox(
                label="Status",
                interactive=False,
                max_lines=1,
                visible=False
            )
        
        # Set up event handlers
        self._setup_event_handlers()
        
        return {
            "chatbot": self.chatbot,
            "msg_input": self.msg_input,
            "send_btn": self.send_btn,
            "clear_btn": self.clear_btn,
            "provider_dropdown": self.provider_dropdown,
            "model_dropdown": self.model_dropdown,
            "status_text": self.status_text
        }
    
    def _setup_event_handlers(self):
        """Set up event handlers for UI components"""
        # Send message handlers
        self.send_btn.click(
            fn=self.send_message,
            inputs=[self.msg_input, self.chatbot],
            outputs=[self.msg_input, self.chatbot, self.status_text]
        )
        
        self.msg_input.submit(
            fn=self.send_message,
            inputs=[self.msg_input, self.chatbot],
            outputs=[self.msg_input, self.chatbot, self.status_text]
        )
        
        # Clear chat
        self.clear_btn.click(
            fn=self.clear_conversation,
            outputs=[self.chatbot, self.status_text]
        )
        
        # Provider change
        self.provider_dropdown.change(
            fn=self.change_provider,
            inputs=[self.provider_dropdown],
            outputs=[self.model_dropdown, self.status_text]
        )
    
    def display_conversation(self, session_id: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Display conversation for a session
        
        Args:
            session_id: Session to display
            
        Returns:
            List of (user_message, assistant_message) tuples for Gradio
        """
        messages = self.msg_store.get_session_messages(session_id)
        
        # Convert to Gradio format
        conversation = []
        user_msg = None
        
        for msg in messages:
            if msg.role == MessageRole.USER.value:
                user_msg = msg.content
            elif msg.role == MessageRole.ASSISTANT.value and user_msg:
                conversation.append((user_msg, msg.content))
                user_msg = None
        
        # Add pending user message if exists
        if user_msg:
            conversation.append((user_msg, None))
        
        return conversation
    
    def send_message(self, 
                    message: str, 
                    history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]], str]:
        """
        Send a message and get LLM response
        
        Args:
            message: User's message
            history: Current chat history
            
        Returns:
            Tuple of (cleared_input, updated_history, status)
        """
        if not message.strip():
            return message, history, "Message cannot be empty"
        
        try:
            # Get current session
            current_session = self.session_mgr.get_current_session()
            if not current_session:
                # Create a new session if none exists
                session_id = self.session_mgr.create_session(
                    name=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    project_type="general"
                )
            else:
                session_id = current_session.session_id
            
            # Save user message
            self.msg_store.save_message(
                role=MessageRole.USER,
                content=message,
                session_id=session_id
            )
            
            # Add to history immediately
            history = history + [(message, None)]
            
            # Build context for LLM
            context = self.msg_store.build_context(session_id)
            
            # Prepare messages for LLM
            llm_messages = []
            
            # Add system prompt if available
            if context.system_prompt:
                llm_messages.append(
                    LLMMessage(role="system", content=context.system_prompt)
                )
            
            # Add conversation history
            for msg in context.messages:
                llm_messages.append(
                    LLMMessage(role=msg.role, content=msg.content)
                )
            
            # Get selected model
            model = self.model_dropdown.value
            provider = self.provider_dropdown.value
            
            # Send to LLM
            response = self.provider_mgr.send_message(
                messages=llm_messages,
                model=model,
                provider=provider,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Save assistant response
            self.msg_store.save_message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                session_id=session_id,
                metadata={
                    "model": response.model,
                    "tokens": response.total_tokens,
                    "provider": provider
                }
            )
            
            # Update history with response
            history[-1] = (message, response.content)
            
            # Calculate cost
            cost = self.provider_mgr.calculate_cost(
                model=response.model,
                input_tokens=response.usage['prompt_tokens'],
                output_tokens=response.usage['completion_tokens'],
                provider=provider
            )
            
            status = f"✓ {provider}/{model} - Tokens: {response.total_tokens} - Cost: ${cost:.4f}"
            
            return "", history, status
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return "", history, f"❌ Error: {str(e)}"
    
    def clear_conversation(self) -> Tuple[List, str]:
        """
        Clear the current conversation
        
        Returns:
            Tuple of (empty_history, status)
        """
        # Note: This only clears the UI, not the database
        return [], "Conversation cleared (history preserved in database)"
    
    def change_provider(self, provider_name: str) -> Tuple[gr.Dropdown, str]:
        """
        Change the current provider
        
        Args:
            provider_name: Provider to switch to
            
        Returns:
            Tuple of (updated_model_dropdown, status)
        """
        success = self.provider_mgr.switch_provider(provider_name)
        
        if success:
            # Update model choices
            choices = self._get_model_choices(provider_name)
            default = self._get_default_model(provider_name)
            
            return gr.Dropdown(choices=choices, value=default), f"Switched to {provider_name}"
        else:
            return gr.Dropdown(), f"Failed to switch to {provider_name}"
    
    def _get_provider_choices(self) -> List[str]:
        """Get list of available providers"""
        return self.provider_mgr.list_available_providers()
    
    def _get_model_choices(self, provider: Optional[str] = None) -> List[str]:
        """Get list of available models for a provider"""
        if provider is None:
            provider = self.provider_mgr.current_provider_name
        
        if provider:
            prov = self.provider_mgr.get_provider(provider)
            if prov:
                models = prov.get_available_models()
                return [m.name for m in models]
        
        return []
    
    def _get_default_model(self, provider: Optional[str] = None) -> Optional[str]:
        """Get default model for a provider"""
        if provider is None:
            provider = self.provider_mgr.current_provider_name
        
        if provider:
            prov = self.provider_mgr.get_provider(provider)
            if prov and hasattr(prov, 'default_model'):
                return prov.default_model
            elif prov:
                models = prov.get_available_models()
                if models:
                    return models[0].name
        
        return None
    
    def format_message_for_display(self, message: str) -> str:
        """
        Format message for display in chat
        
        Args:
            message: Raw message text
            
        Returns:
            Formatted message
        """
        # This is where we could add markdown rendering, code highlighting, etc.
        return message
    
    def handle_regenerate_response(self, history: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Regenerate the last assistant response
        
        Args:
            history: Current chat history
            
        Returns:
            Updated history
        """
        if not history:
            return history
        
        # Get last user message
        last_user_msg = history[-1][0]
        
        # Remove last exchange and resend
        history = history[:-1]
        _, updated_history, _ = self.send_message(last_user_msg, history)
        
        return updated_history