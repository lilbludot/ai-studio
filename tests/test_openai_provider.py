#!/usr/bin/env python3
"""
Test for OpenAI Provider
Note: This requires a valid OPENAI_API_KEY environment variable
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.llm_providers.openai_provider import OpenAIProvider
from src.core.llm_providers.base_provider import LLMMessage


def test_openai_provider():
    print("Testing OpenAI Provider...\n")
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set it with: export OPENAI_API_KEY='sk-...'")
        return
    
    try:
        # 1. Initialize provider
        provider = OpenAIProvider(api_key)
        print(f"✓ Initialized {provider}")
        
        # 2. Get available models
        models = provider.get_available_models()
        print(f"\n✓ Available models: {len(models)}")
        for model in models:
            print(f"  - {model.display_name} ({model.name})")
            print(f"    Max tokens: {model.max_tokens:,}")
            print(f"    Cost: ${model.cost_per_1k_input}/1k in, ${model.cost_per_1k_output}/1k out")
            caps = []
            if model.supports_functions:
                caps.append("functions")
            if model.supports_vision:
                caps.append("vision")
            if model.supports_json_mode:
                caps.append("json")
            print(f"    Capabilities: {', '.join(caps)}")
        
        # 3. Test token estimation
        test_text = "Hello, GPT! How are you today?"
        tokens = provider.estimate_tokens(test_text, "gpt-3.5-turbo")
        print(f"\n✓ Token estimate for '{test_text}': {tokens} tokens")
        
        # 4. Test model validation
        valid = provider.validate_model("gpt-4")
        invalid = provider.validate_model("claude-3")
        print(f"\n✓ Model validation:")
        print(f"  - gpt-4: {valid}")
        print(f"  - claude-3: {invalid}")
        
        # 5. Test message sending (small test)
        print("\n✓ Testing message send...")
        messages = [
            LLMMessage(role="system", content="You are a helpful assistant. Be very concise."),
            LLMMessage(role="user", content="Say 'Hello from GPT!' and nothing else.")
        ]
        
        response = provider.send_message(
            messages=messages,
            model="gpt-4o-mini",  # Use cheapest model for test
            max_tokens=50,
            temperature=0
        )
        
        print(f"  Response: {response.content}")
        print(f"  Tokens used: {response.total_tokens}")
        print(f"  Cost: ${provider.calculate_cost('gpt-4o-mini', response.usage['prompt_tokens'], response.usage['completion_tokens']):.6f}")
        
        # 6. Test streaming
        print("\n✓ Testing streaming...")
        print("  Stream: ", end="", flush=True)
        
        messages = [
            LLMMessage(role="user", content="Count from 1 to 5 with commas between.")
        ]
        
        total_content = ""
        final_usage = None
        for chunk in provider.stream_message(
            messages=messages,
            model="gpt-4o-mini",
            max_tokens=50,
            temperature=0
        ):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                total_content += chunk.content
            if chunk.is_final:
                final_usage = chunk.usage
                print(f"\n  Streaming complete!")
        
        if final_usage:
            total = final_usage['prompt_tokens'] + final_usage['completion_tokens']
            print(f"  Estimated tokens: {total}")
        
        # 7. Test JSON mode (if you want to test this feature)
        print("\n✓ Testing JSON mode...")
        messages = [
            LLMMessage(
                role="user", 
                content='Return a JSON object with "status": "ok" and "message": "Hello from JSON mode"'
            )
        ]
        
        response = provider.send_message(
            messages=messages,
            model="gpt-4o-mini",
            max_tokens=50,
            temperature=0,
            response_format="json_object"
        )
        
        print(f"  JSON Response: {response.content}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_openai_provider()