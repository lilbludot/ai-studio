"""
Message Store for AI Studio
Handles message storage, retrieval, and conversation management
Created: 2025-05-27
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..storage.database import DatabaseManager, Message as DBMessage, ContentType, MessageRole
from ..core.session_manager import SessionManager

logger = logging.getLogger(__name__)


@dataclass
class MessageContext:
    """Context for building LLM prompts"""
    messages: List[DBMessage]
    system_prompt: Optional[str] = None
    total_tokens: int = 0
    truncated: bool = False


class MessageStore:
    """
    Manages message storage and retrieval for conversations.
    Handles conversation history, context building, and message operations.
    """
    
    def __init__(self, database_manager: DatabaseManager, session_manager: SessionManager):
        """
        Initialize MessageStore
        
        Args:
            database_manager: Database manager instance
            session_manager: Session manager instance
        """
        self.db = database_manager
        self.session_mgr = session_manager
        
        logger.info("MessageStore initialized")
    
    def save_message(self,
                    role: MessageRole,
                    content: str,
                    session_id: Optional[str] = None,
                    content_type: ContentType = ContentType.TEXT,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Save a message to the current or specified session
        
        Args:
            role: Message role (USER, ASSISTANT, SYSTEM)
            content: Message content
            session_id: Session ID (uses current if not specified)
            content_type: Type of content
            metadata: Additional metadata
            
        Returns:
            message_id: Unique identifier for the message
        """
        # Get session ID
        if session_id is None:
            current_session = self.session_mgr.get_current_session()
            if not current_session:
                raise ValueError("No active session and no session_id provided")
            session_id = current_session.session_id
        
        # Generate message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
            
        # Add default metadata
        metadata.update({
            "char_count": len(content),
            "word_count": len(content.split()),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Create message
        message = DBMessage(
            id=message_id,
            session_id=session_id,
            role=role.value if isinstance(role, MessageRole) else role,
            content=content,
            content_type=content_type.value if isinstance(content_type, ContentType) else content_type,
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata
        )
        
        # Save to database
        self.db.save_message(message)
        
        # Update session manager
        self.session_mgr.increment_message_count(session_id)
        
        logger.info(f"Saved message {message_id} to session {session_id}")
        
        return message_id
    
    def get_session_messages(self,
                           session_id: Optional[str] = None,
                           limit: Optional[int] = None,
                           role_filter: Optional[MessageRole] = None) -> List[DBMessage]:
        """
        Get messages for a session
        
        Args:
            session_id: Session ID (uses current if not specified)
            limit: Maximum number of messages to return
            role_filter: Filter by message role
            
        Returns:
            List of messages in chronological order
        """
        # Get session ID
        if session_id is None:
            current_session = self.session_mgr.get_current_session()
            if not current_session:
                return []
            session_id = current_session.session_id
        
        # Get messages from database
        messages = self.db.get_session_messages(session_id, limit)
        
        # Apply role filter if specified
        if role_filter:
            role_value = role_filter.value if isinstance(role_filter, MessageRole) else role_filter
            messages = [m for m in messages if m.role == role_value]
        
        return messages
    
    def get_conversation_history(self,
                               session_id: Optional[str] = None,
                               max_messages: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history formatted for LLM consumption
        
        Args:
            session_id: Session ID (uses current if not specified)
            max_messages: Maximum messages to include
            
        Returns:
            List of message dictionaries ready for LLM APIs
        """
        messages = self.get_session_messages(session_id, limit=max_messages)
        
        # Format for LLM
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at
            })
        
        return formatted
    
    def build_context(self,
                     session_id: Optional[str] = None,
                     max_tokens: int = 4000,
                     include_system: bool = True) -> MessageContext:
        """
        Build context for LLM prompt within token limits
        
        Args:
            session_id: Session ID (uses current if not specified)
            max_tokens: Maximum tokens for context
            include_system: Include system prompt
            
        Returns:
            MessageContext with messages and metadata
        """
        # Get all messages
        messages = self.get_session_messages(session_id)
        
        if not messages:
            return MessageContext(messages=[], total_tokens=0)
        
        # Simple token estimation (4 chars = 1 token)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        # Build context from most recent messages
        context_messages = []
        total_tokens = 0
        
        # Add system prompt if requested
        system_prompt = None
        if include_system:
            # Get from session metadata or use default
            current_session = self.session_mgr.get_current_session()
            if current_session and current_session.metadata.get("system_prompt"):
                system_prompt = current_session.metadata["system_prompt"]
                total_tokens += estimate_tokens(system_prompt)
        
        # Add messages from most recent, working backwards
        for msg in reversed(messages):
            msg_tokens = estimate_tokens(msg.content)
            
            if total_tokens + msg_tokens > max_tokens:
                # Would exceed limit
                break
                
            context_messages.insert(0, msg)
            total_tokens += msg_tokens
        
        return MessageContext(
            messages=context_messages,
            system_prompt=system_prompt,
            total_tokens=total_tokens,
            truncated=len(context_messages) < len(messages)
        )
    
    def update_message(self, message_id: str, new_content: str) -> bool:
        """
        Update message content
        
        Args:
            message_id: Message to update
            new_content: New content
            
        Returns:
            True if successful
        """
        success = self.db.update_message(message_id, new_content)
        
        if success:
            # Update session activity
            message = self.db.get_message(message_id)
            if message:
                self.session_mgr.update_session_activity(message.session_id)
        
        return success
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete a message
        
        Args:
            message_id: Message to delete
            
        Returns:
            True if successful
        """
        # Get message first to update session
        message = self.db.get_message(message_id)
        
        success = self.db.delete_message(message_id)
        
        if success and message:
            # Note: We don't decrement message count as it would require 
            # recounting all messages. Stats will be accurate on next load.
            self.session_mgr.update_session_activity(message.session_id)
        
        return success
    
    def get_message_by_id(self, message_id: str) -> Optional[DBMessage]:
        """Get a specific message by ID"""
        return self.db.get_message(message_id)
    
    def bulk_export_messages(self, 
                           session_id: Optional[str] = None,
                           format: str = "json") -> str:
        """
        Export messages in bulk
        
        Args:
            session_id: Session to export (uses current if not specified)
            format: Export format (json, markdown, txt)
            
        Returns:
            Exported content as string
        """
        messages = self.get_session_messages(session_id)
        
        if format == "json":
            return json.dumps([{
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
                "metadata": m.metadata
            } for m in messages], indent=2)
            
        elif format == "markdown":
            lines = []
            for msg in messages:
                timestamp = msg.created_at.split('T')[0]
                lines.append(f"### {msg.role.upper()} - {timestamp}")
                lines.append(f"\n{msg.content}\n")
            return "\n".join(lines)
            
        elif format == "txt":
            lines = []
            for msg in messages:
                lines.append(f"{msg.role}: {msg.content}")
                lines.append("-" * 50)
            return "\n".join(lines)
            
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_conversation_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed conversation statistics
        
        Args:
            session_id: Session to analyze (uses current if not specified)
            
        Returns:
            Dictionary of statistics
        """
        messages = self.get_session_messages(session_id)
        
        if not messages:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "total_chars": 0,
                "total_words": 0,
                "avg_message_length": 0
            }
        
        # Calculate stats
        user_messages = [m for m in messages if m.role == MessageRole.USER.value]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT.value]
        
        total_chars = sum(len(m.content) for m in messages)
        total_words = sum(len(m.content.split()) for m in messages)
        
        # Token stats from metadata
        total_tokens = sum(
            m.metadata.get("tokens", 0) 
            for m in assistant_messages
        )
        
        stats = {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "system_messages": len([m for m in messages if m.role == MessageRole.SYSTEM.value]),
            "total_chars": total_chars,
            "total_words": total_words,
            "total_tokens": total_tokens,
            "avg_message_length": total_chars // len(messages) if messages else 0,
            "first_message": messages[0].created_at if messages else None,
            "last_message": messages[-1].created_at if messages else None
        }
        
        return stats
    
    def find_messages_by_content(self,
                               search_text: str,
                               session_id: Optional[str] = None,
                               case_sensitive: bool = False) -> List[DBMessage]:
        """
        Search messages by content
        
        Args:
            search_text: Text to search for
            session_id: Session to search (None for current)
            case_sensitive: Case sensitive search
            
        Returns:
            List of matching messages
        """
        messages = self.get_session_messages(session_id)
        
        if not case_sensitive:
            search_text = search_text.lower()
        
        matches = []
        for msg in messages:
            content = msg.content if case_sensitive else msg.content.lower()
            if search_text in content:
                matches.append(msg)
        
        return matches
    
    def get_last_assistant_message(self, session_id: Optional[str] = None) -> Optional[DBMessage]:
        """Get the most recent assistant message"""
        messages = self.get_session_messages(session_id)
        
        for msg in reversed(messages):
            if msg.role == MessageRole.ASSISTANT.value:
                return msg
                
        return None
    
    def get_last_user_message(self, session_id: Optional[str] = None) -> Optional[DBMessage]:
        """Get the most recent user message"""
        messages = self.get_session_messages(session_id)
        
        for msg in reversed(messages):
            if msg.role == MessageRole.USER.value:
                return msg
                
        return None