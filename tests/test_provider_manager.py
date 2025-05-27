#!/usr/bin/env python3
"""
Test for Provider Manager
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.llm_providers.provider_manager import ProviderManager
from src.core.llm_providers.base_provider import LLMMessage
from src.utils.config import ConfigManager


def test_provider_manager():
    print("Testing Provider Manager...\n")
    
    # Set API keys if not already set
    if not os.getenv("CLAUDE_API_KEY"):
        print("⚠️  Warning: CLAUDE_API_KEY not set")
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
    
    try:
        # 1. Initialize
        config = ConfigManager()
        manager = ProviderManager(config)
        print(f"✓ ProviderManager initialized")
        
        # 2. List available providers
        providers = manager.list_available_providers()
        print(f"\n✓ Available providers: {providers}")
        print(f"  Current provider: {manager.current_provider_name}")
        
        # 3. Get provider stats
        stats = manager.get_provider_stats()
        print(f"\n✓ Provider statistics:")
        for name, stat in stats.items():
            print(f"  {name}:")
            print(f"    - Models: {stat['model_count']}")
            print(f"    - Cheapest: {stat['cheapest_model']}")
            print(f"    - Current: {stat['is_current']}")
        
        # 4. Get all models
        all_models = manager.get_all_models()
        print(f"\n✓ All available models:")
        for provider, models in all_models.items():
            print(f"  {provider}: {len(models)} models")
            for model in models[:2]:  # Show first 2
                print(f"    - {model.display_name}")
        
        # 5. Test sending a message (if we have at least one provider)
        if providers:
            print(f"\n✓ Testing message send with {manager.current_provider_name}...")
            
            messages = [
                LLMMessage(role="user", content="Say 'Hello from Provider Manager!' and nothing else.")
            ]
            
            # Let manager choose the model
            response = manager.send_message(
                messages=messages,
                max_tokens=50,
                temperature=0
            )
            
            print(f"  Response: {response.content}")
            print(f"  Model used: {response.model}")
            print(f"  Tokens: {response.total_tokens}")
        
        # 6. Test provider switching
        if len(providers) > 1:
            print(f"\n✓ Testing provider switching...")
            other_provider = [p for p in providers if p != manager.current_provider_name][0]
            
            success = manager.switch_provider(other_provider)
            print(f"  Switched to {other_provider}: {success}")
            
            # Send message with new provider
            response = manager.send_message(
                messages=messages,
                max_tokens=50,
                temperature=0
            )
            print(f"  Response from {other_provider}: {response.content}")
        
        # 7. Test specific model selection
        print(f"\n✓ Testing specific model selection...")
        # Use Claude Haiku if available, otherwise cheapest model
        if "claude" in providers:
            response = manager.send_message(
                messages=messages,
                model="claude-3-haiku-20240307",
                provider="claude",
                max_tokens=30
            )
            print(f"  Claude Haiku response: {response.content}")
        
        # 8. Test token estimation
        test_text = "This is a test message for token counting."
        if providers:
            current_provider = manager.get_current_provider()
            models = current_provider.get_available_models()
            if models:
                tokens = manager.estimate_tokens(test_text, models[0].name)
                print(f"\n✓ Token estimate for '{test_text}': {tokens} tokens")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_provider_manager()