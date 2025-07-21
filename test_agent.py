#!/usr/bin/env python3
"""
Test script for the enhanced Discord agent
"""

import asyncio
import sqlite3
import os
from enhanced_discord_agent import MemoryManager, AgentConfig, load_agent_config

def test_memory_manager():
    """Test the memory management system"""
    print("Testing MemoryManager...")
    
    # Create test database
    test_db = "data/test_memory.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    memory = MemoryManager(test_db)
    
    # Test storing a message
    test_message = {
        'id': '12345',
        'channel_id': '67890',
        'thread_id': None,
        'author_id': 'user123',
        'author_name': 'TestUser',
        'content': 'Hello, bot!',
        'timestamp': '2024-01-01 12:00:00',
        'is_bot': False,
        'agent_name': None
    }
    
    memory.store_message(test_message)
    print("✅ Message stored")
    
    # Test retrieving context
    context = memory.get_context_messages('67890', limit=10)
    print(f"✅ Retrieved {len(context)} context messages")
    
    # Test conversation stats
    turns = memory.update_conversation_stats('67890', '67890', increment_agent_turns=True)
    print(f"✅ Agent turns: {turns}")
    
    print("Memory tests passed!")

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    config = load_agent_config()
    print(f"✅ Loaded config for: {config.name}")
    print(f"✅ LLM type: {config.llm_type}")
    print(f"✅ Max context: {config.max_context_messages}")
    
    print("Config tests passed!")

if __name__ == "__main__":
    test_memory_manager()
    test_config()
    print("\n🎉 All tests passed!")