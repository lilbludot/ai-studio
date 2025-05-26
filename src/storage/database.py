"""
Database Manager for AI Studio
Handles SQLite database operations with future Firestore migration support
Created: 2025-05-23
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
import threading
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Message roles in conversations"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ContentType(Enum):
    """Types of content in messages"""
    TEXT = "text"
    DOCUMENT = "document"
    CODE = "code"
    ARTIFACT = "artifact"


@dataclass
class Session:
    """Session data model"""
    id: str
    name: str
    project_type: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    user_id: str = "kinga"  # Default user for MVP
    active: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create Session from dictionary"""
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        return cls(**data)


@dataclass
class Message:
    """Message data model"""
    id: str
    session_id: str
    role: str
    content: str
    content_type: str
    created_at: str
    metadata: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create Message from dictionary"""
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        return cls(**data)


@dataclass
class Document:
    """Document data model"""
    id: str
    session_id: str
    title: str
    content: str
    document_type: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create Document from dictionary"""
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        return cls(**data)


class DatabaseManager:
    """
    Manages SQLite database operations for AI Studio.
    Designed with abstraction to support future Firestore migration.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize DatabaseManager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database
        self._initialize_database()
        logger.info(f"DatabaseManager initialized with database at {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    def _initialize_database(self) -> None:
        """Create database tables if they don't exist"""
        schema = """
        -- Sessions table
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            project_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'kinga',
            active BOOLEAN DEFAULT 1,
            metadata TEXT DEFAULT '{}'
        );
        
        -- Messages table
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'text',
            created_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        );
        
        -- Documents table
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            document_type TEXT DEFAULT 'markdown',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents(session_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);
        """
        
        with self.transaction() as conn:
            conn.executescript(schema)
        
        logger.debug("Database schema initialized")
    
    # Session Management
    
    def create_session(self, session: Session) -> str:
        """Create a new session"""
        query = """
        INSERT INTO sessions (id, name, project_type, created_at, updated_at, 
                            user_id, active, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.transaction() as conn:
            conn.execute(query, (
                session.id,
                session.name,
                session.project_type,
                session.created_at,
                session.updated_at,
                session.user_id,
                session.active,
                json.dumps(session.metadata)
            ))
        
        logger.info(f"Created session: {session.id}")
        return session.id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        query = "SELECT * FROM sessions WHERE id = ?"
        
        cursor = self.connection.execute(query, (session_id,))
        row = cursor.fetchone()
        
        if row:
            return Session.from_dict(dict(row))
        return None
    
    def get_user_sessions(self, user_id: str = "kinga", 
                         active_only: bool = True) -> List[Session]:
        """Get all sessions for a user"""
        query = "SELECT * FROM sessions WHERE user_id = ?"
        params = [user_id]
        
        if active_only:
            query += " AND active = 1"
        
        query += " ORDER BY updated_at DESC"
        
        cursor = self.connection.execute(query, params)
        return [Session.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session fields"""
        # Build dynamic update query
        allowed_fields = ['name', 'project_type', 'active', 'metadata']
        fields_to_update = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                fields_to_update.append(f"{field} = ?")
                if field == 'metadata' and isinstance(value, dict):
                    value = json.dumps(value)
                values.append(value)
        
        if not fields_to_update:
            return False
        
        # Always update updated_at
        fields_to_update.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        
        values.append(session_id)
        
        query = f"UPDATE sessions SET {', '.join(fields_to_update)} WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, values)
            return cursor.rowcount > 0
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data"""
        query = "DELETE FROM sessions WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, (session_id,))
            return cursor.rowcount > 0
    
    # Message Management
    
    def save_message(self, message: Message) -> str:
        """Save a message to the database"""
        query = """
        INSERT INTO messages (id, session_id, role, content, content_type, 
                            created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.transaction() as conn:
            conn.execute(query, (
                message.id,
                message.session_id,
                message.role,
                message.content,
                message.content_type,
                message.created_at,
                json.dumps(message.metadata)
            ))
        
        # Update session's updated_at
        self.update_session(message.session_id, {})
        
        return message.id
    
    def get_session_messages(self, session_id: str, 
                           limit: Optional[int] = None) -> List[Message]:
        """Get messages for a session"""
        query = """
        SELECT * FROM messages 
        WHERE session_id = ? 
        ORDER BY created_at ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.connection.execute(query, (session_id,))
        return [Message.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a single message by ID"""
        query = "SELECT * FROM messages WHERE id = ?"
        
        cursor = self.connection.execute(query, (message_id,))
        row = cursor.fetchone()
        
        if row:
            return Message.from_dict(dict(row))
        return None
    
    def update_message(self, message_id: str, content: str) -> bool:
        """Update message content"""
        query = "UPDATE messages SET content = ? WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, (content, message_id))
            return cursor.rowcount > 0
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        query = "DELETE FROM messages WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, (message_id,))
            return cursor.rowcount > 0
    
    # Document Management
    
    def save_document(self, document: Document) -> str:
        """Save a document"""
        query = """
        INSERT INTO documents (id, session_id, title, content, document_type,
                             created_at, updated_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with self.transaction() as conn:
            conn.execute(query, (
                document.id,
                document.session_id,
                document.title,
                document.content,
                document.document_type,
                document.created_at,
                document.updated_at,
                json.dumps(document.metadata)
            ))
        
        return document.id
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        query = "SELECT * FROM documents WHERE id = ?"
        
        cursor = self.connection.execute(query, (document_id,))
        row = cursor.fetchone()
        
        if row:
            return Document.from_dict(dict(row))
        return None
    
    def get_session_documents(self, session_id: str) -> List[Document]:
        """Get all documents for a session"""
        query = """
        SELECT * FROM documents 
        WHERE session_id = ? 
        ORDER BY updated_at DESC
        """
        
        cursor = self.connection.execute(query, (session_id,))
        return [Document.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def update_document(self, document_id: str, 
                       title: Optional[str] = None,
                       content: Optional[str] = None) -> bool:
        """Update a document"""
        fields_to_update = []
        values = []
        
        if title is not None:
            fields_to_update.append("title = ?")
            values.append(title)
        
        if content is not None:
            fields_to_update.append("content = ?")
            values.append(content)
        
        if not fields_to_update:
            return False
        
        fields_to_update.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        
        values.append(document_id)
        
        query = f"UPDATE documents SET {', '.join(fields_to_update)} WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, values)
            return cursor.rowcount > 0
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        query = "DELETE FROM documents WHERE id = ?"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, (document_id,))
            return cursor.rowcount > 0
    
    # Utility Methods
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a raw query and return results"""
        cursor = self.connection.execute(query, params)
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        return results
    
    def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            with self.transaction() as conn:
                for query, params in queries:
                    conn.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            backup_db = sqlite3.connect(backup_path)
            with backup_db:
                self.connection.backup(backup_db)
            backup_db.close()
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "total_sessions": 0,
            "total_messages": 0,
            "total_documents": 0,
            "database_size": 0,
            "tables": {}
        }
        
        # Get counts
        for table in ['sessions', 'messages', 'documents']:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self.execute_query(query)
            count = result[0]['count'] if result else 0
            stats[f"total_{table}"] = count
            
        # Get database file size
        if self.db_path.exists():
            stats["database_size"] = self.db_path.stat().st_size
        
        # Get table info
        query = "SELECT name, sql FROM sqlite_master WHERE type='table'"
        tables = self.execute_query(query)
        stats["tables"] = {t['name']: t['sql'] for t in tables}
        
        return stats
    
    def cleanup_old_data(self, days: int = 90) -> int:
        """Clean up old inactive sessions and their data"""
        cutoff_date = datetime.utcnow().isoformat()
        # This is a placeholder - would need proper date arithmetic
        
        query = """
        DELETE FROM sessions 
        WHERE active = 0 
        AND updated_at < ?
        """
        
        with self.transaction() as conn:
            cursor = conn.execute(query, (cutoff_date,))
            return cursor.rowcount
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
            logger.info("Database connection closed")