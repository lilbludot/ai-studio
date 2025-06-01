#!/usr/bin/env python3
"""
Test ChatInterface functionality by calling the backend directly
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_manager import SessionManager
from src.core.message_store import MessageStore, MessageRole
from src.core.llm_providers.provider_manager import ProviderManager
from src.core.llm_providers.base_provider import LLMMessage
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager
from datetime import datetime

def test_backend_directly():
    """Test the backend components directly without UI"""
    print("Testing Backend Functionality...")
    print("=" * 50)
    
    # Initialize components
    config = ConfigManager()
    db_path = config.get('database.path', 'test_backend.db')
    db = DatabaseManager(db_path)
    session_mgr = SessionManager(config, db)
    msg_store = MessageStore(db, session_mgr)
    provider_mgr = ProviderManager(config)
    
    # Create a session
    session_id = session_mgr.create_session(
        name=f"Test Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        project_type="test"
    )
    print(f"✓ Created session: {session_id}")
    
    # Test 1: Send a message with Claude
    print("\n1. Testing with Claude...")
    
    # Save user message
    msg_store.save_message(
        role=MessageRole.USER,
        content="Hello! Can you tell me what 2+2 equals?",
        session_id=session_id
    )
    
    # Build context
    context = msg_store.build_context(session_id)
    
    # Prepare messages for LLM
    llm_messages = []
    if context.system_prompt:
        llm_messages.append(LLMMessage(role="system", content=context.system_prompt))
    
    for msg in context.messages:
        llm_messages.append(LLMMessage(role=msg.role, content=msg.content))
    
    # Send to Claude
    try:
        response = provider_mgr.send_message(
            messages=llm_messages,
            model="claude-3-haiku-20240307",  # Use cheapest model
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"✓ Claude response: {response.content}")
        print(f"  Tokens: {response.total_tokens}")
        
        # Save assistant response
        msg_store.save_message(
            role=MessageRole.ASSISTANT,
            content=response.content,
            session_id=session_id,
            metadata={
                "model": response.model,
                "tokens": response.total_tokens
            }
        )
        
    except Exception as e:
        print(f"❌ Error with Claude: {e}")
    
    # Test 2: Switch to OpenAI
    print("\n2. Testing with OpenAI...")
    
    provider_mgr.switch_provider("openai")
    
    # Save another user message
    msg_store.save_message(
        role=MessageRole.USER,
        content="What's the capital of France?",
        session_id=session_id
    )
    
    # Get updated context
    context = msg_store.build_context(session_id)
    llm_messages = []
    for msg in context.messages:
        llm_messages.append(LLMMessage(role=msg.role, content=msg.content))
    
    # Send to OpenAI
    try:
        response = provider_mgr.send_message(
            messages=llm_messages,
            model="gpt-4o-mini",  # Use cheapest model
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"✓ OpenAI response: {response.content}")
        print(f"  Tokens: {response.total_tokens}")
        
        # Calculate cost
        cost = provider_mgr.calculate_cost(
            model=response.model,
            input_tokens=response.usage['prompt_tokens'],
            output_tokens=response.usage['completion_tokens']
        )
        print(f"  Cost: ${cost:.6f}")
        
    except Exception as e:
        print(f"❌ Error with OpenAI: {e}")
    
    # Show session stats
    print("\n3. Session Statistics:")
    stats = session_mgr.get_session_stats(session_id)
    print(f"  Total messages: {stats['message_count']}")
    print(f"  User messages: {stats['user_messages']}")
    print(f"  Assistant messages: {stats['assistant_messages']}")
    
    print("\n✅ Backend test complete!")

if __name__ == "__main__":
    test_backend_directly()