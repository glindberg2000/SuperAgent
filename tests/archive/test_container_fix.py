#!/usr/bin/env python3
"""
Test the container deployment fix
"""

import asyncio
import os
import sys
import subprocess
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_container_deployment_fix():
    """Test that container deployment now works"""
    print("🐳 TESTING CONTAINER DEPLOYMENT FIX")
    print("=" * 40)
    
    config = AgentConfig(
        name="ContainerFixTester",
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
    initial_containers = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    print(f"Initial containers: {len(initial_containers)}")
    
    # Test 1: Direct container deployment via orchestrator
    print("\n1. Testing direct container deployment...")
    try:
        from agent_orchestrator import DeploymentRequest
        
        request = DeploymentRequest(
            agent_name="test_container_agent",
            agent_type="fullstackdev",
            deployment_type="container",
            team="test",
            auto_start=True
        )
        
        result = await ai.orchestrator.deploy_agent(request)
        print(f"✅ Direct deployment result:")
        print(f"   Success: {result.success}")
        print(f"   Agent: {result.agent_name}")
        print(f"   Status: {result.status}")
        print(f"   Identifier: {result.identifier}")
        print(f"   Message: {result.message}")
        
    except Exception as e:
        print(f"❌ Direct deployment error: {e}")
        import traceback
        traceback.print_exc()
    
    # Wait for container startup
    await asyncio.sleep(5)
    
    # Check for new containers
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    new_containers = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    added_containers = new_containers - initial_containers
    
    if added_containers:
        print(f"\n✅ New containers created:")
        for container in added_containers:
            print(f"  • {container}")
            
            # Check container status
            try:
                status_result = subprocess.run(['docker', 'inspect', '--format', '{{.State.Status}}', container],
                                              capture_output=True, text=True)
                if status_result.returncode == 0:
                    status = status_result.stdout.strip()
                    print(f"    Status: {status}")
            except:
                pass
    else:
        print(f"\n❌ No new containers created")
    
    # Test 2: Conversational deployment
    print(f"\n2. Testing conversational container deployment...")
    response = await ai._process_with_function_calling("deploy a coderdev1 agent as a container", context)
    print(f"Conversational response: {response}")
    
    # Check final containers
    await asyncio.sleep(3)
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
    final_containers = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    latest_added = final_containers - new_containers
    
    if latest_added:
        print(f"\n✅ Additional containers from conversational deployment:")
        for container in latest_added:
            print(f"  • {container}")
    else:
        print(f"\n❌ No additional containers from conversational deployment")

async def main():
    print("🕵️ TESTING CONTAINER DEPLOYMENT FIXES")
    print("=" * 50)
    
    await test_container_deployment_fix()
    
    print("\n" + "=" * 50)
    print("🎯 This shows if container deployment is now working")

if __name__ == "__main__":
    asyncio.run(main())