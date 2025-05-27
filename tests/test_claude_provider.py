#!/usr/bin/env python3
"""
Test for Claude Provider
Note: This requires a valid CLAUDE_API_KEY environment variable
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.llm_providers.claude_provider import ClaudeProvider
from src.core.llm_providers.base_provider import LLMMessage


def test_claude_provider():
    print("Testing Claude Provider...\n")
    
    # Get API key from environment
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ Error: CLAUDE_API_KEY environment variable not set")
        print("Please set it with: export CLAUDE_API_KEY='your-key-here'")
        return
    
    try:
        # 1. Initialize provider
        provider = ClaudeProvider(api_key)
        print(f"✓ Initialized {provider}")
        
        # 2. Get available models
        models = provider.get_available_models()
        print(f"\n✓ Available models: {len(models)}")
        for model in models:
            print(f"  - {model.display_name} ({model.name})")
            print(f"    Max tokens: {model.max_tokens:,}")
            print(f"    Cost: ${model.cost_per_1k_input}/1k in, ${model.cost_per_1k_output}/1k out")
        
        # 3. Test token estimation
        test_text = "Hello, Claude! How are you today?"
        tokens = provider.estimate_tokens(test_text, "claude-3-5-sonnet-20241022")
        print(f"\n✓ Token estimate for '{test_text}': {tokens} tokens")
        
        # 4. Test model validation
        valid = provider.validate_model("claude-3-5-sonnet-20241022")
        invalid = provider.validate_model("gpt-4")
        print(f"\n✓ Model validation:")
        print(f"  - claude-3-5-sonnet: {valid}")
        print(f"  - gpt-4: {invalid}")
        
        # 5. Test message sending (small test)
        print("\n✓ Testing message send...")
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant. Be concise."),
            LLMMessage(role="user", content="Say 'Hello test!' and nothing else.")
        ]
        
        response = provider.send_message(
            messages=messages,
            model="claude-3-haiku-20240307",  # Use cheapest model for test
            max_tokens=50,
            temperature=0
        )
        
        print(f"  Response: {response.content}")
        print(f"  Tokens used: {response.total_tokens}")
        print(f"  Cost: ${provider.calculate_cost('claude-3-haiku-20240307', response.usage['prompt_tokens'], response.usage['completion_tokens']):.6f}")
        
        # 6. Test streaming
        print("\n✓ Testing streaming...")
        print("  Stream: ", end="", flush=True)
        
        messages = [
            LLMMessage(role="user", content="Count to 5 slowly.")
        ]
        
        total_content = ""
        for chunk in provider.stream_message(
            messages=messages,
            model="claude-3-haiku-20240307",
            max_tokens=50,
            temperature=0
        ):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                total_content += chunk.content
            if chunk.is_final:
                print(f"\n  Streaming complete!")
                print(f"  Total tokens: {chunk.usage['total_tokens']}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_claude_provider()