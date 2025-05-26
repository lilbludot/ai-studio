#!/usr/bin/env python3
"""
Quick test script for ConfigManager
This is temporary - will create proper tests later
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from src.utils.config import ConfigManager, Environment


def test_config_manager():
    print("Testing ConfigManager...\n")
    
    # Test 1: Initialize ConfigManager
    try:
        config = ConfigManager()
        print("✓ ConfigManager initialized successfully")
        print(f"  Environment: {config.environment.value}")
    except Exception as e:
        print(f"✗ Failed to initialize ConfigManager: {e}")
        return
    
    # Test 2: Get configuration values
    print("\n--- Configuration Values ---")
    print(f"App Name: {config.get('app_name')}")
    print(f"Version: {config.get('version')}")
    print(f"Debug Mode: {config.get('debug')}")
    print(f"Database Type: {config.get('database.type')}")
    print(f"Database Path: {config.get('database.path')}")
    
    # Test 3: Get provider configurations
    print("\n--- Provider Configurations ---")
    for provider_name in ['claude', 'openai', 'gemini']:
        provider = config.get_provider_config(provider_name)
        if provider:
            print(f"{provider_name.capitalize()}:")
            print(f"  Model: {provider.model}")
            print(f"  Enabled: {provider.enabled}")
            print(f"  API Key: {'SET' if provider.api_key else 'NOT SET'}")
    
    # Test 4: Get UI configuration
    print("\n--- UI Configuration ---")
    ui_config = config.get_ui_config()
    print(f"Host: {ui_config.host}:{ui_config.port}")
    print(f"Chat Panel: {ui_config.chat_panel_ratio * 100}%")
    print(f"Document Panel: {ui_config.document_panel_ratio * 100}%")
    
    # Test 5: Validate configuration
    print("\n--- Configuration Validation ---")
    validation = config.validate_config()
    if validation['valid']:
        print("✓ Configuration is valid")
    else:
        print("✗ Configuration has errors:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    # Test 6: Test setting values
    print("\n--- Testing Set/Get ---")
    config.set('test.value', 'Hello AI Studio')
    test_value = config.get('test.value')
    print(f"Set and retrieved test value: {test_value}")
    
    # Test 7: Environment variable override
    print("\n--- Testing Environment Variable Override ---")
    os.environ['CLAUDE_API_KEY'] = 'test-key-123'
    config2 = ConfigManager()
    claude_config = config2.get_provider_config('claude')
    print(f"Claude API Key from env: {'SET' if claude_config.api_key == 'test-key-123' else 'NOT SET'}")
    
    # Clean up
    del os.environ['CLAUDE_API_KEY']
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_config_manager()