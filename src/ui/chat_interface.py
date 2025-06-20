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
        self.doc_editor = None
        
        # UI components (will be set in create_interface)
        self.chatbot = None
        self.msg_input = None
        self.send_btn = None
        self.clear_btn = None
        self.provider_dropdown = None
        self.model_dropdown = None
        
        logger.info("ChatInterface initialized")
        
    def set_document_editor(self, doc_editor):
        """Set reference to document editor for integration"""
        self.doc_editor = doc_editor
        logger.info("Document editor connected to chat interface")
        
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
                    interactive=True,
                    max_choices=10,  # Limit dropdown height
                    container=False  # Reduce padding
                )
                self.model_dropdown = gr.Dropdown(
                    choices=self._get_model_choices(),
                    value=self._get_default_model(),
                    label="Model",
                    scale=2,
                    interactive=True, 
                    max_choices=10,  # Limit dropdown height
                    container=False  # Reduce padding
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
                    lines=2,
                    max_lines=2,
                    scale=8,
                    show_label=False,
                    elem_id="message_input",
                    container=False,  # This reduces padding
                    elem_classes=["small-input"]  # For CSS targeting
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
        # NOTE: Send button and message input handlers are set up in connect_editor_to_chat()
        # to avoid duplication issues. DO NOT set them here!
        
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
    
    def connect_editor_to_chat(self):
        """Connect document editor to chat after both are initialized"""
        if self.doc_editor and hasattr(self.doc_editor, 'content_editor'):
            # IMPORTANT: Clear existing handlers first to prevent duplicates
            self.send_btn.click(fn=None)
            self.msg_input.submit(fn=None)
            
            # Now set up the handlers with editor integration
            self.send_btn.click(
                fn=self.send_message,
                inputs=[
                    self.msg_input, 
                    self.chatbot, 
                    self.provider_dropdown, 
                    self.model_dropdown,
                    self.doc_editor.content_editor
                ],
                outputs=[
                    self.msg_input, 
                    self.chatbot, 
                    self.status_text,
                    self.doc_editor.content_editor
                ],
                queue=False  # ADD THIS - prevents clearing outputs while processing
            )
            
            self.msg_input.submit(
                fn=self.send_message,
                inputs=[
                    self.msg_input, 
                    self.chatbot, 
                    self.provider_dropdown, 
                    self.model_dropdown,
                    self.doc_editor.content_editor
                ],
                outputs=[
                    self.msg_input, 
                    self.chatbot, 
                    self.status_text,
                    self.doc_editor.content_editor
                ],
                queue=False  # ADD THIS - prevents clearing outputs while processing
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
    
    def send_message(self, *args) -> Tuple[str, List[Tuple[str, str]], str, str]:
        """
        Send a message and get LLM response
        
        Args can be either:
            - message, history, provider, model (4 args)
            - message, history, provider, model, editor_content (5 args)
            
        Returns:
            Tuple of (cleared_input, updated_history, status, editor_update)
        """
        
   
        
        # Parse arguments
        if len(args) == 4:
            message, history, provider, model = args
            editor_content = None
        elif len(args) == 5:
            message, history, provider, model, editor_content = args
        else:
            return "", [], f"❌ Error: Invalid number of arguments: {len(args)}", ""
        
  
        
        # # Store the original editor content to preserve it
        # original_editor_content = editor_content if editor_content else ""
        
        original_editor_content = editor_content if editor_content is not None else ""
        
        # Variable to track editor updates
        editor_update = original_editor_content  # Start with current content
        
        if not message.strip():
            return message, history, "Message cannot be empty", original_editor_content
        
        # Import file tools at the top of the method
        from ..ui.file_tools import get_file_tools, execute_file_tool
        
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
            
            # Add system prompt
            system_prompt = """You are an AI assistant with access to a file system and document editor.

IMPORTANT: When the user asks you to perform an action (read, create, update files), you MUST use the appropriate tool immediately. Do not just describe what you will do - actually do it by calling the tool.

Available tools:
- list_files: List files in directories
- read_file: Read file contents (also displays in editor)
- create_file: Create new files
- update_file: Update existing files (replaces entire content)
- get_editor_content: Get current editor content
- apply_to_editor: Apply content to the editor

The user's projects are stored in ~/iCloud Drive/ClaudeProjects/

CRITICAL RULES:
1. When asked to read a file, USE the read_file tool immediately
2. When asked to create/update a file, USE the appropriate tool immediately
3. When asked to show file contents, USE the read_file tool first, then share what you found
4. Do NOT say "I will do X" - instead, DO X using the tools
5. After using a tool, wait for the tool result before proceeding
6. When a user mentions working with a specific file, IMMEDIATELY read it using read_file - don't wait for an explicit read request

TRIGGER PHRASES requiring immediate action:
- "let's work on [file]" → read_file
- "open [file]" → read_file
- "check [file]" → read_file
- "show me [file]" → read_file
- "what's in [file]" → read_file
- "create [file]" → create_file
- "make a new [file]" → create_file
- "update [file]" → update_file
- "edit [file]" → update_file
- "list files" or "what files" → list_files

INTENT RECOGNITION:
- ANY mention of a specific file by name → read_file immediately
- ANY request involving working with, looking at, editing, helping with, or collaborating on a file → read_file immediately  
- Don't wait to understand exactly what the user wants to do - if they mention a file, open it first
- Examples of file mentions that should trigger immediate read_file:
  * "june19.md" (just the filename)
  * "the cover letter" 
  * "that poem we were working on"
  * "help me with my resume"
  * "can we improve the jokes file"
  * "I'm thinking about the draft"
  
Remember: When in doubt, if a file is mentioned or implied, read it first. You can always ask clarifying questions AFTER the file is open in the editor.

IMPORTANT TOOL USAGE NOTE:
- Do NOT use JSON format like {"thought": "...", "command": "..."}
- Do NOT write out tool calls in code blocks
- Do NOT describe tool usage in any special format
- Simply use the tools directly through the provided tool interface
- The correct way to use tools is through the system's built-in tool calling mechanism, not through any text format

When you need to use a tool, just use it directly - don't write about using it or format it in any special way.

When you see a framed tool result (with ╔══╗ borders), this is the ACTUAL result of your tool use. Trust this as the authoritative state of the file system.
NEVER DO THIS:
- Never write "Tool: [toolname]" in your response
- Never write "Path: [filepath]" in your response  
- Never write "Content: [content]" in your response
- Never describe what tool you're going to use
- Never show tool syntax in your messages

INSTEAD:
- Just use the tool silently through the system
- After the tool executes, you'll see the result in a framed box
- Then you can talk about what happened

Example of WRONG behavior:
User: "Add a line to the file"
You: "Tool: update_file..." ❌ NO! Don't write this!

Example of CORRECT behavior:
User: "Add a line to the file"
You: [use tool silently, wait for result] "I've added the line to the file!"
"""

            if current_session and current_session.metadata.get("system_prompt"):
                system_prompt = current_session.metadata["system_prompt"] + "\n\n" + system_prompt
            
            llm_messages.append(
                LLMMessage(role="system", content=system_prompt)
            )
            
            # Add conversation history
            for msg in context.messages:
                llm_messages.append(
                    LLMMessage(role=msg.role, content=msg.content)
                )
            
            # Get file tools if doc_editor is available
            tools = None
            if self.doc_editor:
                tools = get_file_tools()
            
            # Send to LLM with tools
            response = self.provider_mgr.send_message(
                messages=llm_messages,
                model=model,
                provider=provider,
                temperature=0.7,
                max_tokens=1000,
                tools=tools
            )
            
            # Check if LLM wants to use a tool
            if response.function_call and self.doc_editor:
                tool_name = response.function_call['name']
                tool_input = response.function_call['input']
                
                # Execute the tool - NOW PASSING editor_content
                tool_result = execute_file_tool(tool_name, tool_input, self.doc_editor, editor_content)
                
                # Check if this is an editor update
                if tool_result.get('editor_action') == 'update':
                    editor_update = tool_result.get('editor_content', original_editor_content)
                # If not an editor action, preserve original content
                else:
                    editor_update = original_editor_content
                
                # Build a nice response about what happened
                if 'result' in tool_result:
                    tool_status = f"Used {tool_name} successfully"
                else:
                    tool_status = f"Error with {tool_name}: {tool_result['error']}"
                
                # Add tool use to messages for context
                assistant_content = response.content if response.content else f"Let me {tool_name.replace('_', ' ')} for you."
                llm_messages.append(LLMMessage(role="assistant", content=assistant_content))
                llm_messages.append(LLMMessage(
                    role="user", 
                    content=f"Tool result:\n{tool_result.get('result', tool_result.get('error'))}"
                ))
                
                # Get final response from LLM
                final_response = self.provider_mgr.send_message(
                    messages=llm_messages,
                    model=model,
                    provider=provider,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Use final response
                response_content = final_response.content
                response_tokens = final_response.total_tokens
                
            else:
                # No tool use, just regular response
                response_content = response.content
                response_tokens = response.total_tokens
                # Preserve editor content
                editor_update = original_editor_content
            
            # Save assistant response
            self.msg_store.save_message(
                role=MessageRole.ASSISTANT,
                content=response_content,
                session_id=session_id,
                metadata={
                    "model": model,
                    "tokens": response_tokens,
                    "provider": provider
                }
            )
            
            # Update history with response
            history[-1] = (message, response_content)
            
            # Calculate cost
            cost = self.provider_mgr.calculate_cost(
                model=model,
                input_tokens=response.usage['prompt_tokens'],
                output_tokens=response.usage['completion_tokens'],
                provider=provider
            )
            
            status = f"✓ {provider}/{model} - Tokens: {response_tokens} - Cost: ${cost:.4f}"
            
            
            return "", history, status, editor_update if editor_update is not None else original_editor_content
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return "", history, f"❌ Error: {str(e)}", original_editor_content
    
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