#!/usr/bin/env python3
"""
Test specific deployments: Grok4 agent and containerized agents
"""

import asyncio
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_grok_deployment():
    """Test Grok4 agent deployment"""
    print("🧪 Testing Grok4 Agent Deployment")
    
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
    
    try:
        # Test Grok4 deployment
        print("\n1. Testing Grok4 deployment...")
        response = await ai._process_with_function_calling("deploy a grok4 agent", context)
        print(f"   Response: {response}")
        
        # Check system status
        print("\n2. Checking system status after Grok4 deployment...")
        response = await ai._process_with_function_calling("what is the system status?", context)
        print(f"   Response: {response}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

async def test_container_deployment():
    """Test containerized agent deployment"""
    print("\n🧪 Testing Containerized Agent Deployment")
    
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
    
    try:
        # Test fullstack container deployment
        print("\n1. Testing fullstack container deployment...")
        response = await ai._process_with_function_calling("deploy a fullstack container agent", context)
        print(f"   Response: {response}")
        
        # Test coderdev1 container deployment
        print("\n2. Testing coderdev1 container deployment...")
        response = await ai._process_with_function_calling("deploy a coderdev1 agent", context)
        print(f"   Response: {response}")
        
        # Check final status
        print("\n3. Checking final system status...")
        response = await ai._process_with_function_calling("what is the system status?", context)
        print(f"   Response: {response}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

async def stop_claude_agent():
    """Stop the problematic Claude agent"""
    print("\n🛑 Stopping Claude Agent (API Issues)")
    
    config = AgentConfig(
        name="TestDevOpsAI",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    
    try:
        # Get active agents first
        active_agents = await ai.orchestrator.get_active_agents()
        print(f"Active agents before shutdown: {[agent['name'] for agent in active_agents]}")
        
        # Find and stop Claude agent
        for agent in active_agents:
            if 'claude' in agent['name'].lower():
                print(f"Stopping {agent['name']} (PID: {agent.get('identifier', 'unknown')})")
                try:
                    result = await ai.orchestrator.stop_agent(agent['name'])
                    print(f"Stop result: {result}")
                except Exception as e:
                    print(f"Error stopping {agent['name']}: {e}")
        
        # Check status after shutdown
        active_agents_after = await ai.orchestrator.get_active_agents()
        print(f"Active agents after shutdown: {[agent['name'] for agent in active_agents_after]}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("🔍 TESTING SPECIFIC AGENT DEPLOYMENTS")
    print("=" * 50)
    
    # Step 1: Stop problematic Claude agent
    await stop_claude_agent()
    
    # Step 2: Test Grok4 deployment
    await test_grok_deployment()
    
    # Step 3: Test container deployments
    await test_container_deployment()
    
    print("\n" + "=" * 50)
    print("✅ Deployment testing complete")

if __name__ == "__main__":
    asyncio.run(main())