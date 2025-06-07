#!/usr/bin/env python3
"""
Test file tools with Claude
Tests the complete flow: Claude using tools to access your files
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


def test_file_tools_with_claude():
    """Test Claude using file tools to access the projects directory"""
    print("Testing File Tools with Claude")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ Error: CLAUDE_API_KEY not set")
        return
    
    # Initialize components needed for DocumentEditor
    print("\n1. Initializing components...")
    config = ConfigManager()
    db = DatabaseManager("test_file_tools.db")
    session_mgr = SessionManager(config, db)
    doc_editor = DocumentEditor(db, session_mgr, config)
    print(f"✓ DocumentEditor initialized")
    print(f"  Projects path: {doc_editor.projects_path}")
    
    # Create Claude provider
    claude = ClaudeProvider(api_key)
    print("✓ Claude provider initialized")
    
    # Get tool definitions
    tools = get_file_tools()
    print(f"✓ Loaded {len(tools)} file tools")
    
    # Test conversation
    print("\n2. Starting conversation...")
    messages = [
        LLMMessage(
            role="user",
            content="Can you list all the files in my projects directory?"
        )
    ]
    
    try:
        # Send message with tools
        response = claude.send_message(
            messages=messages,
            model="claude-3-haiku-20240307",  # Cheapest model
            tools=tools,
            max_tokens=1000
        )
        
        print(f"\nClaude's response: {response.content}")
        
        # Check if Claude wants to use a tool
        if response.function_call:
            tool_name = response.function_call['name']
            tool_input = response.function_call['input']
            
            print(f"\n✓ Claude wants to use tool: {tool_name}")
            print(f"  With input: {tool_input}")
            
            # Execute the tool
            print(f"\n3. Executing tool...")
            result = execute_file_tool(tool_name, tool_input, doc_editor)
            
            if 'result' in result:
                print("✓ Tool executed successfully!")
                print("\nTool output:")
                print("-" * 40)
                print(result['result'])
                print("-" * 40)
            else:
                print(f"❌ Tool error: {result['error']}")
            
            # Send result back to Claude
            print("\n4. Sending result back to Claude...")
            
            # Add Claude's tool use to history
            # Include the tool use in the content if there's no text
            assistant_content = response.content if response.content else f"I'll use the {tool_name} tool to help you with that."
            messages.append(LLMMessage(
                role="assistant",
                content=assistant_content
            ))
            
            # Add tool result
            messages.append(LLMMessage(
                role="user",
                content=f"Tool result:\n{result.get('result', result.get('error'))}"
            ))
            
            # Get Claude's final response
            final_response = claude.send_message(
                messages=messages,
                model="claude-3-haiku-20240307",
                max_tokens=1000
            )
            
            print(f"\nClaude's final response:")
            print("=" * 50)
            print(final_response.content)
            print("=" * 50)
            
        else:
            print("\n⚠️  Claude didn't use any tools")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test database
        Path("test_file_tools.db").unlink(missing_ok=True)
        print("\n✓ Cleanup complete")


if __name__ == "__main__":
    test_file_tools_with_claude()