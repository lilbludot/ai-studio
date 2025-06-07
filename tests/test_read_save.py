#!/usr/bin/env python3
"""
Test reading and saving files with Claude
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.llm_providers.claude_provider import ClaudeProvider
from src.core.llm_providers.base_provider import LLMMessage
from src.ui.document_editor import DocumentEditor
from src.ui.file_tools import get_file_tools, execute_file_tool
from src.storage.database import DatabaseManager
from src.core.session_manager import SessionManager
from src.utils.config import ConfigManager


def run_tool_conversation(claude, messages, tools, doc_editor):
    """Helper function to handle tool use conversation"""
    # Send message
    response = claude.send_message(
        messages=messages,
        model="claude-3-haiku-20240307",
        tools=tools,
        max_tokens=1000
    )
    
    print(f"\nClaude: {response.content}")
    
    # Handle tool use
    if response.function_call:
        tool_name = response.function_call['name']
        tool_input = response.function_call['input']
        
        print(f"\n[Claude wants to use: {tool_name}]")
        print(f"[Parameters: {tool_input}]")
        
        # Execute tool
        result = execute_file_tool(tool_name, tool_input, doc_editor)
        
        print(f"\n[Tool result: {'Success' if 'result' in result else 'Error'}]")
        
        # Add to conversation
        assistant_content = response.content if response.content else f"I'll use the {tool_name} tool."
        messages.append(LLMMessage(role="assistant", content=assistant_content))
        messages.append(LLMMessage(
            role="user",
            content=f"Tool result:\n{result.get('result', result.get('error'))}"
        ))
        
        # Get Claude's response after tool use
        final_response = claude.send_message(
            messages=messages,
            model="claude-3-haiku-20240307",
            tools=tools,  # Include tools in case Claude needs another one
            max_tokens=1000
        )
        
        print(f"\nClaude: {final_response.content}")
        
        # Return updated messages and check if Claude wants to use another tool
        return messages, final_response.function_call is not None
    
    return messages, False


def test_read_and_save():
    """Test reading and updating files with Claude"""
    print("Testing Read and Save with Claude")
    print("=" * 50)
    
    # Setup
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ Error: CLAUDE_API_KEY not set")
        return
    
    # Initialize
    config = ConfigManager()
    db = DatabaseManager("test_read_save.db")
    session_mgr = SessionManager(config, db)
    doc_editor = DocumentEditor(db, session_mgr, config)
    claude = ClaudeProvider(api_key)
    tools = get_file_tools()
    
    print(f"✓ Initialized (Projects: {doc_editor.projects_path})")
    
    # Test 1: Read a file
    print("\n" + "="*50)
    print("TEST 1: Reading a file")
    print("="*50)
    
    messages = [
        LLMMessage(
            role="user",
            content="Can you read the cover letter template file in the _templates folder?"
        )
    ]
    
    # Run conversation (might take multiple tool calls)
    messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    while needs_more:
        messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    
    # Test 2: Update a file
    print("\n" + "="*50)
    print("TEST 2: Creating/Updating a file")
    print("="*50)
    
    messages = [
        LLMMessage(
            role="user",
            content="""Create a new file called 'test_note.md' in the JobSearch folder with this content:
# Test Note
Created by Claude on test run.
This is a test of the file creation system."""
        )
    ]
    
    messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    while needs_more:
        messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    
    # Test 3: Read what we just created
    print("\n" + "="*50)
    print("TEST 3: Verify the file was created")
    print("="*50)
    
    messages = [
        LLMMessage(
            role="user",
            content="Can you read back the test_note.md file we just created in JobSearch?"
        )
    ]
    
    messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    while needs_more:
        messages, needs_more = run_tool_conversation(claude, messages, tools, doc_editor)
    
    # Cleanup
    Path("test_read_save.db").unlink(missing_ok=True)
    
    # Also remove the test file we created
    test_file = doc_editor.projects_path / "JobSearch" / "test_note.md"
    if test_file.exists():
        test_file.unlink()
        print("\n✓ Cleaned up test file")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    test_read_and_save()