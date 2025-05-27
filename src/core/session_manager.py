"""
Session Manager for AI Studio
Handles session lifecycle and state management
Created: 2025-05-23
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..storage.database import DatabaseManager, Session as DBSession
from ..utils.config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """In-memory session state"""
    session_id: str
    name: str
    project_type: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    document_count: int = 0
    last_activity: Optional[str] = None
    is_active: bool = True


class SessionManager:
    """
    Manages conversation sessions for AI Studio.
    Handles session creation, loading, state management, and persistence.
    """
    
    def __init__(self, config_manager: ConfigManager, database_manager: DatabaseManager):
        """
        Initialize SessionManager
        
        Args:
            config_manager: Configuration manager instance
            database_manager: Database manager instance
        """
        self.config = config_manager
        self.db = database_manager
        
        # Cache for active sessions
        self._active_sessions: Dict[str, SessionState] = {}
        
        # Current session
        self._current_session_id: Optional[str] = None
        
        # Default user (MVP - single user)
        self.default_user_id = "kinga"
        
        logger.info("SessionManager initialized")
    
    def create_session(self, 
                      name: str, 
                      project_type: str = "general",
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session
        
        Args:
            name: Human-readable session name
            project_type: Type of project (job_search, coding, research, etc.)
            metadata: Additional session metadata
            
        Returns:
            session_id: Unique identifier for the session
        """
        # Generate unique session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        # Create timestamp
        now = datetime.utcnow().isoformat()
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        # Add default metadata
        metadata.update({
            "created_via": "session_manager",
            "client_version": self.config.get("version", "0.1.0"),
            "environment": self.config.environment.value
        })
        
        # Create database session
        db_session = DBSession(
            id=session_id,
            name=name,
            project_type=project_type,
            created_at=now,
            updated_at=now,
            metadata=metadata,
            user_id=self.default_user_id,
            active=True
        )
        
        # Save to database
        self.db.create_session(db_session)
        
        # Create in-memory state
        session_state = SessionState(
            session_id=session_id,
            name=name,
            project_type=project_type,
            created_at=now,
            updated_at=now,
            metadata=metadata,
            message_count=0,
            document_count=0,
            last_activity=now,
            is_active=True
        )
        
        # Cache the session
        self._active_sessions[session_id] = session_state
        
        # Set as current session
        self._current_session_id = session_id
        
        logger.info(f"Created session: {session_id} - {name} ({project_type})")
        
        return session_id
    
    def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load a session from database
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionState if found, None otherwise
        """
        # Check cache first
        if session_id in self._active_sessions:
            self._current_session_id = session_id
            return self._active_sessions[session_id]
        
        # Load from database
        db_session = self.db.get_session(session_id)
        if not db_session:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        # Get message and document counts
        messages = self.db.get_session_messages(session_id)
        documents = self.db.get_session_documents(session_id)
        
        # Create state
        session_state = SessionState(
            session_id=db_session.id,
            name=db_session.name,
            project_type=db_session.project_type,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            metadata=db_session.metadata,
            message_count=len(messages),
            document_count=len(documents),
            last_activity=db_session.updated_at,
            is_active=db_session.active
        )
        
        # Cache it
        self._active_sessions[session_id] = session_state
        
        # Set as current
        self._current_session_id = session_id
        
        logger.info(f"Loaded session: {session_id} - {session_state.name}")
        
        return session_state
    
    def get_current_session(self) -> Optional[SessionState]:
        """Get the currently active session"""
        if not self._current_session_id:
            return None
        
        return self._active_sessions.get(self._current_session_id)
    
    def set_current_session(self, session_id: str) -> bool:
        """
        Set the current active session
        
        Args:
            session_id: Session to make current
            
        Returns:
            True if successful, False if session not found
        """
        if session_id not in self._active_sessions:
            # Try to load it
            if not self.load_session(session_id):
                return False
        
        self._current_session_id = session_id
        return True
    
    def get_active_sessions(self) -> List[SessionState]:
        """Get all active sessions in memory"""
        return list(self._active_sessions.values())
    
    def get_user_sessions(self, 
                         user_id: Optional[str] = None,
                         project_type: Optional[str] = None,
                         active_only: bool = True) -> List[SessionState]:
        """
        Get all sessions for a user, optionally filtered
        
        Args:
            user_id: User ID (defaults to default user)
            project_type: Filter by project type
            active_only: Only return active sessions
            
        Returns:
            List of session states
        """
        if user_id is None:
            user_id = self.default_user_id
        
        # Get from database
        db_sessions = self.db.get_user_sessions(user_id, active_only)
        
        # Filter by project type if specified
        if project_type:
            db_sessions = [s for s in db_sessions if s.project_type == project_type]
        
        # Convert to SessionState objects
        session_states = []
        for db_session in db_sessions:
            # Use cached version if available
            if db_session.id in self._active_sessions:
                session_states.append(self._active_sessions[db_session.id])
            else:
                # Create state object
                messages = self.db.get_session_messages(db_session.id)
                documents = self.db.get_session_documents(db_session.id)
                
                state = SessionState(
                    session_id=db_session.id,
                    name=db_session.name,
                    project_type=db_session.project_type,
                    created_at=db_session.created_at,
                    updated_at=db_session.updated_at,
                    metadata=db_session.metadata,
                    message_count=len(messages),
                    document_count=len(documents),
                    last_activity=db_session.updated_at,
                    is_active=db_session.active
                )
                session_states.append(state)
        
        return session_states
    
    def update_session_metadata(self, 
                               session_id: str, 
                               metadata_updates: Dict[str, Any]) -> bool:
        """
        Update session metadata
        
        Args:
            session_id: Session to update
            metadata_updates: Metadata fields to update
            
        Returns:
            True if successful
        """
        # Get current session
        if session_id not in self._active_sessions:
            if not self.load_session(session_id):
                return False
        
        session_state = self._active_sessions[session_id]
        
        # Update metadata
        session_state.metadata.update(metadata_updates)
        session_state.updated_at = datetime.utcnow().isoformat()
        session_state.last_activity = session_state.updated_at
        
        # Update in database
        return self.db.update_session(session_id, {
            "metadata": session_state.metadata
        })
    
    def update_session_activity(self, session_id: str) -> None:
        """Update session's last activity timestamp"""
        if session_id in self._active_sessions:
            now = datetime.utcnow().isoformat()
            self._active_sessions[session_id].last_activity = now
            self._active_sessions[session_id].updated_at = now
            
            # Update database
            self.db.update_session(session_id, {})
    
    def increment_message_count(self, session_id: str) -> None:
        """Increment message count for a session"""
        if session_id in self._active_sessions:
            self._active_sessions[session_id].message_count += 1
            self.update_session_activity(session_id)
    
    def increment_document_count(self, session_id: str) -> None:
        """Increment document count for a session"""
        if session_id in self._active_sessions:
            self._active_sessions[session_id].document_count += 1
            self.update_session_activity(session_id)
    
    def archive_session(self, session_id: str) -> bool:
        """
        Archive a session (mark as inactive)
        
        Args:
            session_id: Session to archive
            
        Returns:
            True if successful
        """
        # Update database
        success = self.db.update_session(session_id, {"active": False})
        
        # Update cache if present
        if session_id in self._active_sessions:
            self._active_sessions[session_id].is_active = False
            
            # If it was current session, clear it
            if self._current_session_id == session_id:
                self._current_session_id = None
        
        logger.info(f"Archived session: {session_id}")
        
        return success
    
    def delete_session(self, session_id: str) -> bool:
        """
        Permanently delete a session and all its data
        
        Args:
            session_id: Session to delete
            
        Returns:
            True if successful
        """
        # Remove from database (cascades to messages and documents)
        success = self.db.delete_session(session_id)
        
        if success:
            # Remove from cache
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
            
            # Clear current session if it was deleted
            if self._current_session_id == session_id:
                self._current_session_id = None
                
            logger.info(f"Deleted session: {session_id}")
        
        return success
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a session
        
        Args:
            session_id: Session to analyze
            
        Returns:
            Dictionary of statistics
        """
        # Load session if not cached
        if session_id not in self._active_sessions:
            if not self.load_session(session_id):
                return {}
        
        session_state = self._active_sessions[session_id]
        
        # Get messages for detailed stats
        messages = self.db.get_session_messages(session_id)
        
        # Calculate stats
        user_messages = [m for m in messages if m.role == "user"]
        assistant_messages = [m for m in messages if m.role == "assistant"]
        
        total_tokens = sum(
            m.metadata.get("tokens", 0) 
            for m in assistant_messages
        )
        
        stats = {
            "session_id": session_id,
            "name": session_state.name,
            "project_type": session_state.project_type,
            "created_at": session_state.created_at,
            "last_activity": session_state.last_activity,
            "message_count": session_state.message_count,
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "document_count": session_state.document_count,
            "total_tokens": total_tokens,
            "is_active": session_state.is_active,
            "duration_hours": self._calculate_duration(
                session_state.created_at, 
                session_state.last_activity
            )
        }
        
        return stats
    
    def _calculate_duration(self, start: str, end: str) -> float:
        """Calculate duration between two ISO timestamps in hours"""
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            return duration.total_seconds() / 3600
        except:
            return 0.0
    
    def search_sessions(self, 
                       query: str,
                       user_id: Optional[str] = None) -> List[SessionState]:
        """
        Search sessions by name or metadata
        
        Args:
            query: Search query
            user_id: User to search (defaults to default user)
            
        Returns:
            List of matching sessions
        """
        if user_id is None:
            user_id = self.default_user_id
        
        # Get all user sessions
        all_sessions = self.get_user_sessions(user_id, active_only=False)
        
        # Simple search in name and project type
        query_lower = query.lower()
        matches = []
        
        for session in all_sessions:
            if (query_lower in session.name.lower() or 
                query_lower in session.project_type.lower()):
                matches.append(session)
        
        return matches
    
    def export_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Export all session data for backup or transfer
        
        Args:
            session_id: Session to export
            
        Returns:
            Complete session data including messages and documents
        """
        # Get session
        db_session = self.db.get_session(session_id)
        if not db_session:
            return {}
        
        # Get all related data
        messages = self.db.get_session_messages(session_id)
        documents = self.db.get_session_documents(session_id)
        
        # Build export
        export_data = {
            "session": {
                "id": db_session.id,
                "name": db_session.name,
                "project_type": db_session.project_type,
                "created_at": db_session.created_at,
                "updated_at": db_session.updated_at,
                "metadata": db_session.metadata,
                "user_id": db_session.user_id,
                "active": db_session.active
            },
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "content_type": m.content_type,
                    "created_at": m.created_at,
                    "metadata": m.metadata
                }
                for m in messages
            ],
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "content": d.content,
                    "document_type": d.document_type,
                    "created_at": d.created_at,
                    "updated_at": d.updated_at,
                    "metadata": d.metadata
                }
                for d in documents
            ],
            "export_metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        }
        
        return export_data