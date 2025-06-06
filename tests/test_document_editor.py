#!/usr/bin/env python3
"""
Test script for DocumentEditor component with file system support
"""

import os
import sys
from pathlib import Path
import gradio as gr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.document_editor import DocumentEditor
from src.core.session_manager import SessionManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager

def test_document_editor():
    """Test the DocumentEditor component with file system features"""
    print("Testing DocumentEditor with File System Support...")
    print("=" * 50)
    
    # Initialize backend components
    config = ConfigManager()
    db_path = config.get('database.path', 'test_document_editor.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)
    
    # Create a test session
    session_id = session_mgr.create_session(
        name="Document Editor Test",
        project_type="test"
    )
    print(f"Created test session: {session_id}")
    
    # Create DocumentEditor
    doc_editor = DocumentEditor(db, session_mgr, config)
    print(f"Projects path: {doc_editor.projects_path}")
    
    # Create some test files if they don't exist
    print("\nSetting up test files...")
    
    # Create a template
    template_path = doc_editor.templates_dir / "cover_letter_template.md"
    if not template_path.exists():
        template_path.write_text("""# Cover Letter Template

Dear Hiring Manager,

I am writing to express my strong interest in the [POSITION] role at [COMPANY].

[Your introduction and why you're interested]

[Your relevant experience and skills]

[Why you're a good fit for the company]

Thank you for considering my application. I look forward to discussing how I can contribute to your team.

Sincerely,
[Your name]
""")
        print(f"Created template: {template_path.name}")
    
    # Create a sample project structure
    job_search_dir = doc_editor.projects_path / "JobSearch" / "Google"
    job_search_dir.mkdir(parents=True, exist_ok=True)
    
    sample_cover = job_search_dir / "cover_letter_draft.md"
    if not sample_cover.exists():
        sample_cover.write_text("""# Google ML Engineer - Cover Letter

Dear Google Hiring Team,

I am excited to apply for the Machine Learning Engineer position at Google...
""")
        print(f"Created sample: {sample_cover}")
    
    # Test file listing
    print("\n1. Testing file listing...")
    files = doc_editor.list_files()
    print(f"Found {len(files)} items in projects directory")
    for f in files[:5]:  # Show first 5
        print(f"  - {f['type']}: {f['name']}")
    
    # Test template listing
    print("\n2. Testing template listing...")
    templates = doc_editor.get_templates()
    print(f"Found {len(templates)} templates")
    for t in templates:
        print(f"  - {t['name']}")
    
    # Now create the UI
    print("\n3. Creating Gradio UI...")
    with gr.Blocks(title="Document Editor Test") as app:
        gr.Markdown("# Document Editor Test - File System Support")
        
        with gr.Row():
            # Left side - simulate LLM file operations
            with gr.Column(scale=7):
                gr.Markdown("### Simulate LLM File Operations")
                
                with gr.Tabs():
                    with gr.TabItem("Browse Files"):
                        browse_dir = gr.Textbox(
                            label="Directory (relative to projects, empty for root)",
                            value=""
                        )
                        browse_btn = gr.Button("List Files", variant="primary")
                        browse_output = gr.JSON(label="Files")
                    
                    with gr.TabItem("Create File"):
                        new_file_path = gr.Textbox(
                            label="File Path",
                            value="JobSearch/Amazon/cover_letter.md"
                        )
                        new_file_content = gr.Textbox(
                            label="Initial Content",
                            value="# Amazon SDE Position\n\nDear Amazon Team,\n\n",
                            lines=5
                        )
                        create_file_btn = gr.Button("Create File", variant="primary")
                        create_output = gr.Textbox(label="Result")
                    
                    with gr.TabItem("File Operations"):
                        file_to_open = gr.Textbox(
                            label="File to Open",
                            value="JobSearch/Google/cover_letter_draft.md"
                        )
                        open_btn = gr.Button("Open File")
                        
                        edit_content = gr.Textbox(
                            label="New Content to Save",
                            lines=5
                        )
                        save_current_btn = gr.Button("Save to Current File")
                        
                        file_op_output = gr.Textbox(label="Result", lines=5)
            
            # Right side - Document Editor
            components = doc_editor.create_interface()
        
        # Wire up the LLM simulation buttons
        def browse_files(directory):
            files = doc_editor.list_files(directory if directory else None)
            return files
        
        def create_new_file(path, content):
            success = doc_editor.create_file(path, content)
            if success:
                # Refresh file list
                return f"Created: {path}", gr.Dropdown(choices=doc_editor._get_file_choices())
            return f"Failed to create: {path}", gr.Dropdown()
        
        def open_file(path):
            content = doc_editor.open_file(path)
            if content:
                return f"Opened {path}:\n\n{content[:200]}..."
            return f"Could not open: {path}"
        
        def save_to_current(content):
            if doc_editor.current_file_path:
                success = doc_editor.save_current_file(content)
                return f"Saved to {doc_editor.current_file_path.name}: {'Success' if success else 'Failed'}"
            return "No file currently open"
        
        # Connect buttons
        browse_btn.click(
            fn=browse_files,
            inputs=[browse_dir],
            outputs=[browse_output]
        )
        
        create_file_btn.click(
            fn=create_new_file,
            inputs=[new_file_path, new_file_content],
            outputs=[create_output, components["file_browser"]]
        )
        
        open_btn.click(
            fn=open_file,
            inputs=[file_to_open],
            outputs=[file_op_output]
        )
        
        save_current_btn.click(
            fn=save_to_current,
            inputs=[edit_content],
            outputs=[file_op_output]
        )
    
    return app

if __name__ == "__main__":
    print("Starting Document Editor test with file system support...")
    app = test_document_editor()
    
    print("\n✅ DocumentEditor created successfully!")
    print("\nYou can now test:")
    print("- Browsing files in your projects directory")
    print("- Creating new files in specific locations")
    print("- Opening and editing existing files")
    print("- Using templates")
    print("- File system operations that the LLM could perform")
    print("\nStarting Gradio interface...")
    
    app.launch(
        server_name="127.0.0.1",
        server_port=7863,
        share=False,
        show_error=True
    )