#!/usr/bin/env python3
"""
Test actual container deployments
"""

import asyncio
import os
import sys
import subprocess
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_real_container_deployment():
    """Test deploying actual Docker containers"""
    print("🐳 TESTING REAL CONTAINER DEPLOYMENTS")
    print("=" * 50)
    
    config = AgentConfig(
        name="ContainerTester",
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
    
    # Get initial container count
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    initial_containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
    print(f"Initial containers: {len(initial_containers)}")
    for container in initial_containers:
        print(f"  • {container}")
    
    # Test explicit container deployment
    print(f"\n1. Testing explicit container deployment...")
    response = await ai._process_with_function_calling("deploy a fullstackdev agent as a container", context)
    print(f"Response: {response}")
    
    # Wait for container startup
    await asyncio.sleep(5)
    
    # Check new containers
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    new_containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
    print(f"\nContainers after deployment: {len(new_containers)}")
    
    added_containers = [c for c in new_containers if c not in initial_containers]
    if added_containers:
        print(f"✅ New containers added:")
        for container in added_containers:
            print(f"  • {container}")
    else:
        print("❌ No new containers were created")
    
    # Test if new container is actually a Discord bot
    print(f"\n2. Checking if new containers are Discord bots...")
    for container in added_containers:
        try:
            # Check container logs for Discord connection
            result = subprocess.run(['docker', 'logs', '--tail', '10', container], 
                                 capture_output=True, text=True, timeout=10)
            logs = result.stdout + result.stderr
            
            if 'discord' in logs.lower() or 'connected' in logs.lower():
                print(f"✅ {container}: Discord connection detected")
                print(f"   Recent logs: {logs[:200]}...")
            else:
                print(f"❌ {container}: No Discord connection detected")
                print(f"   Recent logs: {logs[:200]}...")
                
        except Exception as e:
            print(f"⚠️  {container}: Could not check logs - {e}")

async def test_coderdev_container():
    """Test coderdev container deployment"""
    print(f"\n🔧 TESTING CODERDEV CONTAINER")
    print("=" * 30)
    
    config = AgentConfig(
        name="CoderdevTester",
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
    
    # Test coderdev1 container deployment
    response = await ai._process_with_function_calling("deploy a coderdev1 agent using container deployment", context)
    print(f"Coderdev1 container response: {response}")
    
    await asyncio.sleep(3)
    
    # Check if it's really a container
    result = subprocess.run(['docker', 'ps', '--filter', 'name=coderdev', '--format', '{{.Names}}'], 
                           capture_output=True, text=True)
    
    if result.stdout.strip():
        print(f"✅ Coderdev container found: {result.stdout.strip()}")
    else:
        print("❌ No coderdev container found")

async def main():
    print("🕵️ TESTING REAL CONTAINER DEPLOYMENT CAPABILITIES")
    print("=" * 60)
    
    await test_real_container_deployment()
    await test_coderdev_container()
    
    print("\n" + "=" * 60)
    print("🎯 Results show if container deployment actually works")

if __name__ == "__main__":
    asyncio.run(main())