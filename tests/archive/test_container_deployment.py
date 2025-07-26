#!/usr/bin/env python3
"""
Test containerized deployments specifically
"""

import asyncio
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_container_deployments():
    """Test container-specific deployments"""
    print("🐳 TESTING CONTAINERIZED AGENT DEPLOYMENTS")
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
    
    # Test container deployment by requesting specific deployment type
    test_cases = [
        "deploy a fullstackdev agent using container deployment",
        "deploy a coderdev2 agent as a container",
        "what containers are running?",
        "check system status"
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
    
    print("\n🔍 CHECKING ORCHESTRATOR CONFIGS")
    print("=" * 30)
    
    # Check what deployment types are available
    try:
        configs = ai.orchestrator.agent_configs
        
        print("Available agent configs:")
        for agent_type, config in list(configs.items())[:7]:  # Show first 7
            deployment_type = config.get('deployment_type', 'process')
            script = config.get('script', 'N/A')
            print(f"  • {agent_type}: {deployment_type} ({script})")
        
        # Check if Docker is available
        docker_available = ai.orchestrator.docker_client is not None
        print(f"\nDocker client available: {docker_available}")
        
        if docker_available:
            try:
                # Test Docker connection
                version = ai.orchestrator.docker_client.version()
                print(f"Docker version: {version.get('Version', 'Unknown')}")
            except Exception as e:
                print(f"Docker connection error: {e}")
        
    except Exception as e:
        print(f"Config check error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Container deployment testing complete")

if __name__ == "__main__":
    asyncio.run(test_container_deployments())