#!/usr/bin/env python3
"""
Test MCP tools directly, then through agent, then check Discord
"""

import asyncio
import os
import sys
import subprocess
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_mcp_tools_direct():
    """Test MCP tools directly via orchestrator"""
    print("🔧 TESTING MCP TOOLS DIRECTLY")
    print("=" * 40)
    
    config = AgentConfig(
        name="MCPTester",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    
    # Test 1: Direct orchestrator call
    print("\n1. Testing direct orchestrator.get_active_agents()...")
    try:
        active_agents = await ai.orchestrator.get_active_agents()
        print(f"✅ Active agents: {len(active_agents)}")
        for agent in active_agents:
            print(f"  • {agent['name']}: {agent['status']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Direct deployment via orchestrator
    print("\n2. Testing direct orchestrator.deploy_agent()...")
    try:
        from agent_orchestrator import DeploymentRequest
        
        request = DeploymentRequest(
            agent_name="direct_test_grok",
            agent_type="grok4_agent",
            deployment_type="process",
            team="test",
            auto_start=True
        )
        
        result = await ai.orchestrator.deploy_agent(request)
        print(f"✅ Deployment result: {result.success}")
        print(f"   Agent: {result.agent_name}")
        print(f"   Status: {result.status}")
        print(f"   Message: {result.message}")
        print(f"   PID: {result.identifier}")
        
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()

async def test_agent_calls_mcp():
    """Test if agent properly calls MCP tools"""
    print("\n🤖 TESTING AGENT CALLS TO MCP TOOLS")
    print("=" * 45)
    
    config = AgentConfig(
        name="AgentMCPTester",
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
    
    # Test 3: Agent tool calling
    print("\n3. Testing agent _handle_check_status_tool()...")
    try:
        result = await ai._handle_check_status_tool()
        print(f"✅ Status tool result: {result}")
    except Exception as e:
        print(f"❌ Status tool error: {e}")
    
    # Test 4: Agent deployment tool
    print("\n4. Testing agent _handle_deploy_agent_tool()...")
    try:
        result = await ai._handle_deploy_agent_tool("grok4", "test", "agent_test_grok")
        print(f"✅ Deploy tool result: {result}")
    except Exception as e:
        print(f"❌ Deploy tool error: {e}")
        import traceback
        traceback.print_exc()

async def test_discord_routing():
    """Test if Discord can see the agents"""
    print("\n💬 TESTING DISCORD ROUTING")
    print("=" * 30)
    
    # Check running processes that look like Discord bots
    print("\n5. Checking Discord bot processes...")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        discord_processes = []
        
        for line in result.stdout.split('\n'):
            if 'mcp-discord' in line or ('discord' in line and 'python' in line):
                discord_processes.append(line.strip())
        
        print(f"Found {len(discord_processes)} Discord-related processes:")
        for proc in discord_processes[:5]:  # Show first 5
            # Extract the relevant part
            parts = proc.split()
            if len(parts) > 10:
                pid = parts[1]
                command = ' '.join(parts[10:])
                print(f"  • PID {pid}: {command[:80]}...")
            
    except Exception as e:
        print(f"❌ Process check error: {e}")
    
    # Check Docker containers with Claude Code
    print("\n6. Checking Claude Code containers...")
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=claude', '--format', '{{.Names}}\t{{.Status}}'], 
                               capture_output=True, text=True)
        
        if result.stdout.strip():
            containers = result.stdout.strip().split('\n')
            print(f"✅ Found {len(containers)} Claude containers:")
            for container in containers:
                name, status = container.split('\t')
                print(f"  • {name}: {status}")
                
                # Check if container is responding
                try:
                    logs_result = subprocess.run(['docker', 'logs', '--tail', '3', name], 
                                               capture_output=True, text=True, timeout=5)
                    recent_logs = logs_result.stdout + logs_result.stderr
                    if recent_logs.strip():
                        print(f"    Recent activity: {recent_logs.strip()[:100]}...")
                except:
                    print(f"    Could not get recent logs")
        else:
            print("❌ No Claude containers found")
            
    except Exception as e:
        print(f"❌ Container check error: {e}")

async def main():
    print("🕵️ COMPREHENSIVE MCP AND DISCORD TESTING")
    print("=" * 60)
    
    await test_mcp_tools_direct()
    await test_agent_calls_mcp()
    await test_discord_routing()
    
    print("\n" + "=" * 60)
    print("🎯 This shows exactly where the issue is in the chain")

if __name__ == "__main__":
    asyncio.run(main())