"""
Document Editor for AI Studio
Handles the document editing panel (30% width on the right) with file system support
Created: 2025-06-05
"""

import gradio as gr
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import json
import os

from ..storage.database import DatabaseManager, Document as DBDocument
from ..core.session_manager import SessionManager
from ..utils.config import ConfigManager

logger = logging.getLogger(__name__)


class DocumentEditor:
    """
    Manages the document editor component of the UI.
    Handles document creation, editing, saving, and loading from both database and file system.
    """
    
    def __init__(self,
                 database_manager: DatabaseManager,
                 session_manager: SessionManager,
                 config_manager: ConfigManager):
        """
        Initialize DocumentEditor
        
        Args:
            database_manager: Database manager instance
            session_manager: Session manager instance
            config_manager: Configuration manager instance
        """
        self.db = database_manager
        self.session_mgr = session_manager
        self.config = config_manager
        
        # File system paths
        self.projects_path = Path(self.config.get('storage.projects_path'))
        self.templates_dir = self.projects_path / self.config.get('storage.templates_dir', '_templates')
        
        # Ensure directories exist
        self.projects_path.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Current document state
        self.current_file_path: Optional[Path] = None
        self.current_document_id: Optional[str] = None
        self.last_saved_content: str = ""
        
        # UI components (will be set in create_interface)
        self.file_browser = None
        self.file_path_display = None
        self.title_input = None
        self.content_editor = None
        self.save_status = None
        self.save_btn = None
        self.save_as_btn = None
        self.new_file_btn = None
        self.refresh_btn = None
        
        logger.info(f"DocumentEditor initialized with projects path: {self.projects_path}")
    
    def create_interface(self) -> Dict[str, Any]:
        """
        Create the document editor interface components
        
        Returns:
            Dictionary of Gradio components
        """
        with gr.Column(scale=3):  # 30% width for document editor
            # Document header
            with gr.Row():
                gr.Markdown("### 📄 Document Editor")
                self.refresh_btn = gr.Button("🔄", size="sm", scale=0)
            
            # File browser
            self.file_browser = gr.Dropdown(
                label="File Browser",
                choices=self._get_file_choices(),
                value=None,
                interactive=True,
                allow_custom_value=True,
                max_choices=10,  
                container=False,
                scale=1,  # Add this
                elem_classes=["compact-dropdown"]  
            )
            
            # Current file display
            self.file_path_display = gr.Textbox(
                label="Current File",
                value="No file selected",
                interactive=False,
                max_lines=1, 
                container=False,  # Add this if not there
                scale=1  # Add this
            )
            
            # File operations buttons
            with gr.Row():
                self.new_file_btn = gr.Button("New File", size="sm")
                self.save_btn = gr.Button("Save", size="sm", variant="primary")
                self.save_as_btn = gr.Button("Save As...", size="sm")
            
            # Document title (for database storage)
            self.title_input = gr.Textbox(
                label="Title (for database)",
                placeholder="Document title for session history...",
                lines=1,
                interactive=True,
                container=False  # Reduce padding
            )
            
            # Main editor
            self.content_editor = gr.Textbox(
                label="Content",
                placeholder="Start typing your document here...",
                lines=12,
                max_lines=20,  # Set a maximum
                interactive=True,
                show_label=False,
                container=False,  # Add this
                elem_id="doc_editor",
                

            )
            
            # Save status
            self.save_status = gr.Textbox(
                label="Status",
                value="Ready",
                interactive=False,
                max_lines=1,
                visible=True
            )
        
        # Set up event handlers
        self._setup_event_handlers()
        
        return {
            "file_browser": self.file_browser,
            "file_path_display": self.file_path_display,
            "title_input": self.title_input,
            "content_editor": self.content_editor,
            "save_status": self.save_status,
            "save_btn": self.save_btn,
            "save_as_btn": self.save_as_btn,
            "new_file_btn": self.new_file_btn,
            "refresh_btn": self.refresh_btn
        }
    
    def _setup_event_handlers(self):
        """Set up event handlers for UI components"""
        # File selection
        self.file_browser.change(
            fn=self.load_file,
            inputs=[self.file_browser],
            outputs=[self.file_path_display, self.title_input, self.content_editor, self.save_status]
        )
        
        # New file button
        self.new_file_btn.click(
            fn=self.create_new_file,
            outputs=[self.file_path_display, self.title_input, self.content_editor, self.save_status]
        )
        
        # Save button
        self.save_btn.click(
            fn=self.save_file,
            inputs=[self.content_editor, self.title_input],
            outputs=[self.save_status]
        )
        
        # Save As button
        self.save_as_btn.click(
            fn=self.handle_save_as,
            inputs=[self.content_editor, self.title_input],
            outputs=[self.save_status, self.file_path_display, self.file_browser]
        )
        
        # Refresh file list
        self.refresh_btn.click(
            fn=self.refresh_file_list,
            outputs=[self.file_browser]
        )
        
        # Auto-save on content change (debounced)
        self.content_editor.change(
            fn=self.auto_save,
            inputs=[self.content_editor, self.title_input],
            outputs=[self.save_status]
        )
    
    def _get_file_choices(self) -> List[str]:
        """Get list of files in the projects directory"""
        try:
            choices = []
            
            # Add templates
            template_files = list(self.templates_dir.glob("*.md")) + list(self.templates_dir.glob("*.txt"))
            for file in template_files:
                choices.append(f"📄 _templates/{file.name}")
            
            # Walk through projects directory
            for root, dirs, files in os.walk(self.projects_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                root_path = Path(root)
                relative_path = root_path.relative_to(self.projects_path)
                
                for file in files:
                    if file.endswith(('.md', '.txt', '.doc', '.docx')):
                        if relative_path == Path('.'):
                            choices.append(f"📄 {file}")
                        else:
                            choices.append(f"📁 {relative_path}/{file}")
            
            return sorted(choices)
        except Exception as e:
            logger.error(f"Error getting file choices: {e}")
            return []
    
    def create_new_file(self) -> Tuple[str, str, str, str]:
        """Create a new file"""
        self.current_file_path = None
        self.current_document_id = None
        self.last_saved_content = ""
        
        return (
            "Unsaved new file",
            "",
            "",
            "New file created - Save As to choose location"
        )
    
    def load_file(self, file_choice: str) -> Tuple[str, str, str, str]:
        """Load a file from the file system"""
        if not file_choice:
            return self.current_file_path or "No file selected", "", "", "No file selected"
        
        try:
            # Remove emoji prefix and get actual path
            file_path_str = file_choice.replace("📄 ", "").replace("📁 ", "")
            file_path = self.projects_path / file_path_str
            
            if not file_path.exists():
                return str(file_path), "", "", f"File not found: {file_path}"
            
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            
            # Update state
            self.current_file_path = file_path
            self.last_saved_content = content
            
            # Try to get title from filename
            title = file_path.stem.replace('_', ' ').replace('-', ' ').title()
            
            # Also save to database for session history
            self._save_to_database(title, content, {"file_path": str(file_path)})
            
            return (
                str(file_path),
                title,
                content,
                f"Loaded: {file_path.name}"
            )
            
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return "", "", "", f"Error: {str(e)}"
    
    def save_file(self, content: str, title: str) -> str:
        """Save the current file"""
        if not self.current_file_path:
            return "No file selected - use Save As"
        
        try:
            # Save to file system
            self.current_file_path.write_text(content, encoding='utf-8')
            self.last_saved_content = content
            
            # Also save to database
            self._save_to_database(title or self.current_file_path.stem, content, 
                                 {"file_path": str(self.current_file_path)})
            
            return f"Saved to {self.current_file_path.name} at {datetime.now().strftime('%H:%M:%S')}"
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return f"Error: {str(e)}"
    def save_as_file(self, content: str, title: str, filename: str) -> str:
        """
        Save content as a new file
        
        Args:
            content: Content to save
            title: Title for database
            filename: Filename/path to save as
            
        Returns:
            Status message
        """
        try:
            # If no extension, add .md
            if not any(filename.endswith(ext) for ext in ['.md', '.txt', '.doc']):
                filename += '.md'
            
            # Create full path
            full_path = self.projects_path / filename
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding='utf-8')
            
            # Update current file reference
            self.current_file_path = full_path
            self.last_saved_content = content
            
            # Save to database
            self._save_to_database(title or full_path.stem, content, {"file_path": str(full_path)})
            
            return f"Saved as: {filename}"
        
        except Exception as e:
            logger.error(f"Error in save_as: {e}")
            return f"Error: {str(e)}"
    
    
    def handle_save_as(self, content: str, title: str) -> Tuple[str, str, gr.Dropdown]:
        """
        Handle Save As button click - prompts for filename
        
        For now, we'll use the title as the filename
        In a full implementation, we'd have a popup dialog
        """
        if not title:
            return "Please enter a title/filename first", self.file_path_display.value, gr.Dropdown()
        
        # Use title as filename, sanitize it
        filename = title.replace(' ', '_').replace('/', '_')
        if not filename.endswith('.md'):
            filename += '.md'
        
        # Save the file
        status = self.save_as_file(content, title, filename)
        
        if "Saved as:" in status:
            # Update file browser
            new_choices = self._get_file_choices()
            return status, str(self.current_file_path), gr.Dropdown(choices=new_choices)
        else:
            return status, self.file_path_display.value, gr.Dropdown()
    
    def auto_save(self, content: str, title: str) -> str:
        """Auto-save if there's a current file"""
        if not self.current_file_path:
            return "No file selected"
        
        if content == self.last_saved_content:
            return "No changes to save"
        
        return self.save_file(content, title)
    
    def refresh_file_list(self) -> gr.Dropdown:
        """Refresh the file browser list"""
        choices = self._get_file_choices()
        return gr.Dropdown(choices=choices)
    
    def _save_to_database(self, title: str, content: str, metadata: Dict[str, Any]) -> None:
        """Save document to database for session history"""
        try:
            current_session = self.session_mgr.get_current_session()
            if not current_session:
                return
            
            if self.current_document_id:
                # Update existing
                self.db.update_document(
                    self.current_document_id,
                    title=title,
                    content=content
                )
            else:
                # Create new
                import uuid
                doc_id = f"doc_{uuid.uuid4().hex[:12]}"
                
                document = DBDocument(
                    id=doc_id,
                    session_id=current_session.session_id,
                    title=title,
                    content=content,
                    document_type="file",
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat(),
                    metadata=metadata
                )
                
                self.db.save_document(document)
                self.current_document_id = doc_id
                self.session_mgr.increment_document_count(current_session.session_id)
                
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    # Methods for LLM integration
    
    def list_files(self, directory: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List files in a directory (for LLM to browse)
        
        Args:
            directory: Relative directory path (None for root)
            
        Returns:
            List of file info dicts
        """
        try:
            base_path = self.projects_path
            if directory:
                base_path = self.projects_path / directory
            
            files = []
            
            # If listing a specific directory, just list its contents
            if directory:
                if base_path.exists() and base_path.is_dir():
                    for item in base_path.iterdir():
                        if item.is_file() and item.suffix in ['.md', '.txt', '.doc', '.docx']:
                            files.append({
                                "name": item.name,
                                "path": str(item.relative_to(self.projects_path)),
                                "type": "file",
                                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                            })
                        elif item.is_dir() and not item.name.startswith('.'):
                            files.append({
                                "name": item.name,
                                "path": str(item.relative_to(self.projects_path)),
                                "type": "directory"
                            })
            else:
                # If listing root, recursively find ALL files
                for root, dirs, filenames in os.walk(base_path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    root_path = Path(root)
                    
                    # Add directories
                    for d in dirs:
                        dir_path = root_path / d
                        files.append({
                            "name": d,
                            "path": str(dir_path.relative_to(self.projects_path)),
                            "type": "directory"
                        })
                    
                    # Add files
                    for filename in filenames:
                        if filename.endswith(('.md', '.txt', '.doc', '.docx')):
                            file_path = root_path / filename
                            files.append({
                                "name": filename,
                                "path": str(file_path.relative_to(self.projects_path)),
                                "type": "file",
                                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
            
            return sorted(files, key=lambda x: (x["type"], x["path"]))
        
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
        
    def create_file(self, file_path: str, content: str = "") -> bool:
        """
        Create a new file
        
        Args:
            file_path: Relative path for the new file
            content: Initial content
            
        Returns:
            Success boolean
        """
        try:
            full_path = self.projects_path / file_path
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding='utf-8')
            
            # Set as current file
            self.current_file_path = full_path
            self.last_saved_content = content
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return False
    
    def open_file(self, file_path: str) -> Optional[str]:
        """
        Open and read a file
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File content or None
        """
        try:
            full_path = self.projects_path / file_path
            
            if not full_path.exists():
                return None
            
            content = full_path.read_text(encoding='utf-8')
            
            # Set as current file
            self.current_file_path = full_path
            self.last_saved_content = content
            
            return content
            
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            return None
    
    def save_current_file(self, content: str) -> bool:
        """
        Save content to current file
        
        Args:
            content: Content to save
            
        Returns:
            Success boolean
        """
        if not self.current_file_path:
            return False
        
        try:
            self.current_file_path.write_text(content, encoding='utf-8')
            self.last_saved_content = content
            return True
        except Exception as e:
            logger.error(f"Error saving current file: {e}")
            return False
    
    def get_templates(self) -> List[Dict[str, str]]:
        """Get available templates"""
        templates = []
        try:
            for template in self.templates_dir.glob("*.md"):
                templates.append({
                    "name": template.stem.replace('_', ' ').title(),
                    "file": template.name,
                    "path": f"_templates/{template.name}"
                })
            return templates
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []