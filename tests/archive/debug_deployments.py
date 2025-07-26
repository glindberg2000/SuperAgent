#!/usr/bin/env python3
"""
Debug deployment tracking
"""

import asyncio
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def debug_deployments():
    """Debug what's happening with deployment tracking"""
    print("🔍 DEBUGGING DEPLOYMENT TRACKING")
    print("=" * 40)
    
    config = AgentConfig(
        name="DebugTester",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    
    # Deploy an agent
    print("\n1. Deploying test agent...")
    from agent_orchestrator import DeploymentRequest
    
    request = DeploymentRequest(
        agent_name="debug_test_agent",
        agent_type="grok4_agent",
        deployment_type="process",
        team="debug",
        auto_start=True
    )
    
    result = await ai.orchestrator.deploy_agent(request)
    print(f"✅ Deployment result:")
    print(f"   Success: {result.success}")
    print(f"   Agent: {result.agent_name}")
    print(f"   Status: {result.status}")
    print(f"   Identifier: {result.identifier}")
    print(f"   Message: {result.message}")
    
    # Check active deployments storage
    print(f"\n2. Checking active_deployments storage...")
    active_deps = ai.orchestrator.active_deployments
    print(f"   Stored deployments: {len(active_deps)}")
    for name, dep in active_deps.items():
        print(f"   • {name}:")
        print(f"     - Type: {dep.deployment_type}")
        print(f"     - Status: {dep.status}")
        print(f"     - Identifier: {dep.identifier}")
        print(f"     - Success: {dep.success}")
    
    # Check get_active_agents
    print(f"\n3. Testing get_active_agents()...")
    active_agents = await ai.orchestrator.get_active_agents()
    print(f"   Active agents returned: {len(active_agents)}")
    for agent in active_agents:
        print(f"   • {agent}")
    
    # Check if PID parsing works
    print(f"\n4. Testing PID parsing...")
    for name, dep in active_deps.items():
        print(f"   Checking {name} with identifier: {dep.identifier}")
        
        if dep.identifier.startswith('process_'):
            try:
                pid = int(dep.identifier.split('_')[1])
                print(f"   ✅ Extracted PID: {pid}")
                
                # Check if process exists
                running = ai.orchestrator._is_process_running(pid)
                print(f"   Process running: {running}")
                
            except (ValueError, IndexError) as e:
                print(f"   ❌ PID extraction failed: {e}")
        else:
            print(f"   ⚠️  Identifier doesn't start with 'process_': {dep.identifier}")

async def main():
    await debug_deployments()

if __name__ == "__main__":
    asyncio.run(main())