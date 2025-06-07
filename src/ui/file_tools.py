"""
File operation tools for Claude
Defines the tools that Claude can use to interact with the file system
Created: 2025-06-05
"""

from typing import Dict, Any, List

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
            "description": "Read the contents of a file. Returns the full text content of the file.",
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
            "name": "update_file",
            "description": "Update an existing file with new content. Replaces the entire file content.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to update"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the file (replaces existing content)"
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
            "name": "apply_to_editor",
            "description": "Apply new content directly to the document editor. This will replace the current editor content and the user will see the changes immediately. Use this when the user asks you to write, create, or modify content for them.",
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
    Execute a file tool and return the result.
    This is the "translator" between Claude's request and our DocumentEditor.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Parameters from Claude
        doc_editor: DocumentEditor instance
        editor_content: Current editor content (for editor tools)
        
    Returns:
        Dict with either 'result' (success) or 'error' (failure)
    """
    try:
        if tool_name == "list_files":
            # Get optional directory parameter
            directory = tool_input.get("directory", None)
            
            # Call DocumentEditor's list_files
            files = doc_editor.list_files(directory)
            
            if not files:
                return {"result": "No files found."}
            
            # Format output nicely
            output = f"Found {len(files)} items:\n\n"
            for f in files:
                if f["type"] == "directory":
                    output += f"📁 {f['path']}/\n"
                else:
                    output += f"📄 {f['path']}\n"
            
            return {"result": output}
        
        elif tool_name == "read_file":
            file_path = tool_input["file_path"]
            
            # Call DocumentEditor's open_file
            content = doc_editor.open_file(file_path)
            
            if content is None:
                return {"error": f"File not found: {file_path}"}
            
            return {"result": content}
        
        elif tool_name == "create_file":
            file_path = tool_input["file_path"]
            content = tool_input["content"]
            
            # Call DocumentEditor's create_file
            success = doc_editor.create_file(file_path, content)
            
            if success:
                return {"result": f"Successfully created file: {file_path}"}
            else:
                return {"error": f"Failed to create file: {file_path}"}
        
        elif tool_name == "update_file":
            file_path = tool_input["file_path"]
            content = tool_input["content"]
            
            # First open the file to set it as current
            existing = doc_editor.open_file(file_path)
            if existing is None:
                return {"error": f"File not found: {file_path}"}
            
            # Then save the new content
            success = doc_editor.save_current_file(content)
            
            if success:
                return {"result": f"Successfully updated file: {file_path}"}
            else:
                return {"error": f"Failed to update file: {file_path}"}
        
        elif tool_name == "get_editor_content":
            if editor_content is not None:
                if not editor_content.strip():
                    return {"result": "The editor is currently empty."}
                return {"result": editor_content}
            else:
                return {"error": "Unable to access editor content."}
        
        elif tool_name == "apply_to_editor":
            # This tool signals that we want to update the editor
            new_content = tool_input["content"]
            mode = tool_input["mode"]
            
            if mode == "append" and editor_content:
                final_content = editor_content + "\n\n" + new_content
            else:
                final_content = new_content
            
            return {
                "result": "Content has been applied to the editor.",
                "editor_action": "update",  # Signal for UI
                "editor_content": final_content  # Content to apply
            }
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
            
    except Exception as e:
        return {"error": f"Error executing {tool_name}: {str(e)}"}