#!/usr/bin/env python3
"""
Minimal test for Claude tool use
Just tests if Claude can see and call a simple tool
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.llm_providers.claude_provider import ClaudeProvider
from src.core.llm_providers.base_provider import LLMMessage

def test_claude_minimal():
    """Test Claude with a simple tool"""
    print("Testing Claude Tool Use - Minimal Test")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ Error: CLAUDE_API_KEY not set")
        return
    
    # Create Claude provider
    claude = ClaudeProvider(api_key)
    print("✓ Claude provider initialized")
    
    # Define a simple test tool
    tools = [
        {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    ]
    
    # Test message
    messages = [
        LLMMessage(
            role="user",
            content="What's the weather like in Portland, Oregon?"
        )
    ]
    
    try:
        print("\nSending message with tool...")
        
        # Send with tools
        response = claude.send_message(
            messages=messages,
            model="claude-3-haiku-20240307",  # Cheapest model
            tools=tools,
            max_tokens=500
        )
        
        print(f"\n✓ Got response!")
        print(f"Content: {response.content}")
        print(f"Tool call: {response.function_call}")
        
        if response.function_call:
            print(f"\n🎉 SUCCESS! Claude wants to use tool: {response.function_call['name']}")
            print(f"   With input: {response.function_call['input']}")
        else:
            print("\n⚠️  Claude didn't call the tool")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_claude_minimal()