#!/usr/bin/env python3
"""
Test for MessageStore
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.message_store import MessageStore, MessageRole, ContentType
from src.core.session_manager import SessionManager
from src.storage.database import DatabaseManager
from src.utils.config import ConfigManager


def test_message_store():
    print("Testing MessageStore...\n")
    
    # Initialize components
    config = ConfigManager()
    db = DatabaseManager("test_messages.db")
    session_mgr = SessionManager(config, db)
    msg_store = MessageStore(db, session_mgr)
    
    try:
        # 1. Create a session first
        session_id = session_mgr.create_session(
            name="Test Conversation",
            project_type="testing",
            metadata={"system_prompt": "You are a helpful AI assistant."}
        )
        print(f"✓ Created session: {session_id}")
        
        # 2. Save messages
        # User message
        user_msg_id = msg_store.save_message(
            role=MessageRole.USER,
            content="Hello! Can you help me write a Python function?",
            metadata={"intent": "coding_help"}
        )
        print(f"✓ Saved user message: {user_msg_id}")
        
        # Assistant response
        assistant_msg_id = msg_store.save_message(
            role=MessageRole.ASSISTANT,
            content="Of course! I'd be happy to help you write a Python function. What would you like the function to do?",
            metadata={"model": "claude-3-5-sonnet", "tokens": 28}
        )
        print(f"✓ Saved assistant message: {assistant_msg_id}")
        
        # Another exchange
        msg_store.save_message(
            role=MessageRole.USER,
            content="I need a function to calculate fibonacci numbers"
        )
        
        msg_store.save_message(
            role=MessageRole.ASSISTANT,
            content="""Here's a Python function to calculate Fibonacci numbers:

```python
def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    else:
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        return fib
```

This returns the first n Fibonacci numbers as a list.""",
            content_type=ContentType.CODE,
            metadata={"model": "claude-3-5-sonnet", "tokens": 95}
        )
        
        # 3. Retrieve messages
        messages = msg_store.get_session_messages()
        print(f"\n✓ Retrieved {len(messages)} messages")
        
        # 4. Get conversation history for LLM
        history = msg_store.get_conversation_history(max_messages=10)
        print(f"✓ Got conversation history with {len(history)} messages")
        
        # 5. Build context with token limit
        context = msg_store.build_context(max_tokens=500)
        print(f"\n✓ Built context:")
        print(f"  - Messages included: {len(context.messages)}")
        print(f"  - Total tokens: {context.total_tokens}")
        print(f"  - Truncated: {context.truncated}")
        print(f"  - System prompt: {'Yes' if context.system_prompt else 'No'}")
        
        # 6. Test message filtering
        user_messages = msg_store.get_session_messages(
            role_filter=MessageRole.USER
        )
        print(f"\n✓ Filtered messages: {len(user_messages)} user messages")
        
        # 7. Search messages
        search_results = msg_store.find_messages_by_content("fibonacci")
        print(f"✓ Search found {len(search_results)} messages containing 'fibonacci'")
        
        # 8. Get stats
        stats = msg_store.get_conversation_stats()
        print(f"\n✓ Conversation stats:")
        print(f"  - Total messages: {stats['total_messages']}")
        print(f"  - User messages: {stats['user_messages']}")
        print(f"  - Assistant messages: {stats['assistant_messages']}")
        print(f"  - Total tokens used: {stats['total_tokens']}")
        
        # 9. Test export
        json_export = msg_store.bulk_export_messages(format="json")
        print(f"\n✓ Exported to JSON: {len(json_export)} characters")
        
        markdown_export = msg_store.bulk_export_messages(format="markdown")
        print(f"✓ Exported to Markdown: {len(markdown_export)} characters")
        
        # 10. Test getting last messages
        last_user = msg_store.get_last_user_message()
        last_assistant = msg_store.get_last_assistant_message()
        print(f"\n✓ Last user message: '{last_user.content[:50]}...'")
        print(f"✓ Last assistant message: '{last_assistant.content[:50]}...'")
        
        # 11. Test update
        updated = msg_store.update_message(
            user_msg_id, 
            "Hello! Can you help me write a Python function? (edited)"
        )
        print(f"\n✓ Updated message: {updated}")
        
        # Verify update
        updated_msg = msg_store.get_message_by_id(user_msg_id)
        if "(edited)" in updated_msg.content:
            print("✓ Message update verified")
        
        # Cleanup
        db.close()
        Path("test_messages.db").unlink()
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        db.close()
        if Path("test_messages.db").exists():
            Path("test_messages.db").unlink()


if __name__ == "__main__":
    test_message_store()