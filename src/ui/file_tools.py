"""
File operation tools for Claude
Defines the tools that Claude can use to interact with the file system
Created: 2025-06-20
"""

from typing import Dict, Any, List

def format_tool_result(tool_name: str, content: str, is_error: bool = False) -> str:
    """Format tool results with a clear visual frame"""
    status = "❌ ERROR" if is_error else "✅ SUCCESS"
    border = "═" * 60
    
    lines = [
        f"╔{border}╗",
        f"║ TOOL: {tool_name:<53} ║",
        f"║ STATUS: {status:<52} ║",
        f"╠{border}╣",
        "║" + " " * 60 + "║"
    ]
    
    # Split content into lines and add to frame
    content_lines = content.split('\n')
    for line in content_lines:
        # Handle long lines by wrapping
        while len(line) > 58:
            lines.append(f"║ {line[:58]} ║")
            line = line[58:]
        lines.append(f"║ {line:<58} ║")
    
    lines.append("║" + " " * 60 + "║")
    lines.append(f"╚{border}╝")
    
    return '\n'.join(lines)

def get_file_tools() -> List[Dict[str, Any]]:
    """
    Get the tool definitions for file operations.
    These are the "menu items" we show to Claude.
    
    Returns:
        List of tool definitions in Claude's expected format
    """
    return [
        {
            "name": "list_files",
            "description": "List files and folders in the projects directory. Returns a list of all files and subdirectories.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Optional: Specific subdirectory to list (e.g., 'JobSearch/Google'). Leave empty to list all files."
                    }
                },
                "required": []  # directory is optional
            }
        },
        {
            "name": "read_file",
            "description": "Read a file privately without displaying it in the editor. Use this for analyzing code, gathering information, or when you need to read multiple files. The content is returned to you but the editor remains unchanged.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file relative to projects directory (e.g., 'JobSearch/Google/cover_letter.md')"
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "open_and_display_file",
            "description": "Open a file and display it in the editor for the user to see and potentially edit. Use this when the user asks to work on a file, edit it, or explicitly wants to see it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file relative to projects directory (e.g., 'JobSearch/Google/cover_letter.md')"
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "create_file",
            "description": "Create a new file with specified content. Will create directories if needed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path for the new file (e.g., 'JobSearch/Meta/resume.md')"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        },
        {
            "name": "save_file",
            "description": "Save content to a file, replacing its entire contents. Use this to persist changes from the editor to the file system.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to save"
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete content to save to the file (replaces existing content)"
                    }
                },
                "required": ["file_path", "content"]
            }
        },
        {
            "name": "get_editor_content",
            "description": "Get the current content displayed in the document editor. Use this when the user refers to 'the editor', 'the document', or asks to see what they're working on.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "edit_text_in_editor",
            "description": "Edit the text currently displayed in the document editor. This is how you apply your proposed changes after discussing them with the user.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The new content to display in the editor"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "append"],
                        "description": "Whether to replace all content or append to existing content"
                    }
                },
                "required": ["content", "mode"]
            }
        }
    ]


def execute_file_tool(tool_name: str, tool_input: Dict[str, Any], doc_editor, editor_content: str = None) -> Dict[str, Any]:
    """
    Execute a file tool and return the result with formatted frame.
    """
    try:
        if tool_name == "list_files":
            # Get optional directory parameter
            directory = tool_input.get("directory", None)
            
            # Call DocumentEditor's list_files
            files = doc_editor.list_files(directory)
            
            if not files:
                return {"result": format_tool_result("list_files", "No files found.")}
            
            # Format output nicely
            output = f"Found {len(files)} items:\n\n"
            for f in files:
                if f["type"] == "directory":
                    output += f"📁 {f['path']}/\n"
                else:
                    output += f"📄 {f['path']}\n"
            
            return {"result": format_tool_result("list_files", output)}
        
        elif tool_name == "read_file":
            # NEW: Silent read without editor update
            file_path = tool_input["file_path"]
            
            # Call DocumentEditor's open_file (but don't update editor)
            content = doc_editor.open_file(file_path)
            
            if content is None:
                return {"error": format_tool_result("read_file", f"File not found: {file_path}", is_error=True)}
            
            # Return content WITHOUT editor update signal
            return {
                "result": format_tool_result("read_file", content)
                # No editor_action or editor_content - keeps editor unchanged
            }
        
        elif tool_name == "open_and_display_file":
            # RENAMED: This is the old read_file behavior
            file_path = tool_input["file_path"]
            
            # Call DocumentEditor's open_file
            content = doc_editor.open_file(file_path)
            
            if content is None:
                return {"error": format_tool_result("open_and_display_file", f"File not found: {file_path}", is_error=True)}
            
            # Return content WITH editor update signal
            return {
                "result": format_tool_result("open_and_display_file", content),
                "editor_action": "update",  # Signal to update the editor
                "editor_content": content   # Show in editor
            }
        
        elif tool_name == "create_file":
            file_path = tool_input["file_path"]
            content = tool_input["content"]
            
            # Call DocumentEditor's create_file
            success = doc_editor.create_file(file_path, content)
            
            if success:
                # Return success WITH editor update signal
                return {
                    "result": format_tool_result("create_file", f"Successfully created file: {file_path}"),
                    "editor_action": "update",  # Signal to update the editor
                    "editor_content": content   # Content to show in editor
                }
            else:
                return {"error": format_tool_result("create_file", f"Failed to create file: {file_path}", is_error=True)}
           
        elif tool_name == "save_file":
            file_path = tool_input["file_path"]
            content = tool_input["content"]
            
            # First open the file to set it as current
            existing = doc_editor.open_file(file_path)
            if existing is None:
                return {"error": format_tool_result("save_file", f"File not found: {file_path}", is_error=True)}
            
            # Then save the new content
            success = doc_editor.save_current_file(content)
            
            if success:
                # Return success WITH editor update signal
                return {
                    "result": format_tool_result("save_file", f"Successfully saved file: {file_path}"),
                    "editor_action": "update",  # Signal to update the editor
                    "editor_content": content   # Content to show in editor
                }
            else:
                return {"error": format_tool_result("save_file", f"Failed to save file: {file_path}", is_error=True)}
        
        elif tool_name == "get_editor_content":
            if editor_content is not None:
                if not editor_content.strip():
                    return {"result": format_tool_result("get_editor_content", "The editor is currently empty.")}
                return {"result": format_tool_result("get_editor_content", editor_content)}
            else:
                return {"error": format_tool_result("get_editor_content", "Unable to access editor content.", is_error=True)}
        
        elif tool_name == "edit_text_in_editor":
            # This tool signals that we want to update the editor
            new_content = tool_input["content"]
            mode = tool_input["mode"]
            
            if mode == "append" and editor_content:
                final_content = editor_content + "\n\n" + new_content
            else:
                final_content = new_content
            
            # Special case: edit_text_in_editor needs both framed result AND editor update signal
            return {
                "result": format_tool_result("edit_text_in_editor", "Content has been applied to the editor."),
                "editor_action": "update",  # Signal for UI
                "editor_content": final_content  # Content to apply
            }
        
        else:
            return {"error": format_tool_result(tool_name, f"Unknown tool: {tool_name}", is_error=True)}
            
    except Exception as e:
        return {"error": format_tool_result(tool_name, f"Error executing tool: {str(e)}", is_error=True)}