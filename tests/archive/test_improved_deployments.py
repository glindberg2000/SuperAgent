#!/usr/bin/env python3
"""
Test improved deployments with better agent type mapping
"""

import asyncio
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_deployments():
    """Test various agent deployments"""
    print("🔍 TESTING IMPROVED AGENT DEPLOYMENTS")
    print("=" * 50)
    
    config = AgentConfig(
        name="TestDevOpsAI",
        bot_token="test",
        server_id="test", 
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    context = ConversationContext(
        user_id="test_user",
        channel_id="test_channel",
        thread_id=None,
        conversation_history=[]
    )
    
    test_cases = [
        "deploy a grok4 agent for research",
        "deploy a fullstackdev container agent",  
        "deploy a coderdev1 agent",
        "what is the system status?",
        "list available agents"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{message}'")
        try:
            response = await ai._process_with_function_calling(message, context)
            print(f"   ✅ Response: {response}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ Improved deployment testing complete")

if __name__ == "__main__":
    asyncio.run(test_deployments())