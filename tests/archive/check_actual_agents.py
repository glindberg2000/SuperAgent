#!/usr/bin/env python3
"""
Actually check what agents are running and verify Discord connectivity
"""

import asyncio
import os
import sys
import subprocess
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def check_real_agent_status():
    """Check what's actually running, not just what the system thinks"""
    print("🔍 CHECKING ACTUAL AGENT STATUS")
    print("=" * 50)
    
    # 1. Check system processes
    print("\n1. Checking running Python processes...")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        agent_processes = []
        for line in lines:
            if 'python' in line and ('discord' in line or 'agent' in line):
                agent_processes.append(line)
        
        if agent_processes:
            print(f"Found {len(agent_processes)} potential agent processes:")
            for proc in agent_processes:
                print(f"  • {proc}")
        else:
            print("❌ No agent processes found in system")
            
    except Exception as e:
        print(f"Error checking processes: {e}")
    
    # 2. Check Docker containers
    print("\n2. Checking Docker containers...")
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            containers = result.stdout
            print("Docker containers:")
            print(containers)
        else:
            print("❌ Docker not available or no containers running")
    except Exception as e:
        print(f"Docker check failed: {e}")
    
    # 3. Check orchestrator status
    print("\n3. Checking orchestrator status...")
    try:
        config = AgentConfig(
            name="StatusChecker",
            bot_token="test",
            server_id="test",
            api_key=os.getenv('OPENAI_API_KEY'),
            llm_type="openai"
        )
        
        ai = ConversationalDevOpsAI(config)
        active_agents = await ai.orchestrator.get_active_agents()
        
        print(f"Orchestrator reports {len(active_agents)} active agents:")
        for agent in active_agents:
            print(f"  • {agent['name']}: {agent['status']} (PID: {agent.get('identifier', 'unknown')})")
            
    except Exception as e:
        print(f"Orchestrator check failed: {e}")
    
    # 4. Try to stop the broken Claude agent
    print("\n4. Attempting to stop broken Claude agent...")
    try:
        # Find Claude processes
        result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"Found Claude processes: {pids}")
            
            for pid in pids:
                if pid.strip():
                    print(f"Killing PID {pid}")
                    subprocess.run(['kill', pid.strip()])
        else:
            print("No Claude processes found")
            
    except Exception as e:
        print(f"Error stopping Claude: {e}")

async def test_actual_deployment():
    """Test deployment and verify it actually works"""
    print("\n🚀 TESTING ACTUAL DEPLOYMENT")
    print("=" * 30)
    
    config = AgentConfig(
        name="DeploymentTester",
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
    
    # Deploy a Grok4 agent and verify it goes online
    print("\n1. Deploying Grok4 agent...")
    response = await ai._process_with_function_calling("deploy a grok4 agent for testing", context)
    print(f"Deployment response: {response}")
    
    # Wait a bit for startup
    print("\n2. Waiting 10 seconds for agent startup...")
    await asyncio.sleep(10)
    
    # Check if it's actually running
    print("\n3. Checking if agent is actually online...")
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    grok_processes = [line for line in result.stdout.split('\n') if 'grok' in line.lower() and 'python' in line]
    
    if grok_processes:
        print("✅ Grok agent process found:")
        for proc in grok_processes:
            print(f"  {proc}")
    else:
        print("❌ No Grok agent process found")
    
    # Try fullstack container deployment
    print("\n4. Attempting fullstack container deployment...")
    response = await ai._process_with_function_calling("deploy a fullstackdev container agent", context)
    print(f"Container deployment response: {response}")
    
    # Check Docker containers
    await asyncio.sleep(5)
    print("\n5. Checking Docker containers after deployment...")
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Docker containers:")
            print(result.stdout)
        else:
            print("❌ No Docker containers found")
    except Exception as e:
        print(f"Docker check failed: {e}")

async def main():
    print("🕵️ ACTUAL AGENT STATUS VERIFICATION")
    print("=" * 60)
    
    await check_real_agent_status()
    await test_actual_deployment()
    
    print("\n" + "=" * 60)
    print("🎯 Use this information to fix what's actually broken")

if __name__ == "__main__":
    asyncio.run(main())