#!/usr/bin/env python3
"""
Debug config types to find the string vs dict issue
"""

import asyncio
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def debug_config_types():
    """Debug what configs are being loaded and their types"""
    print("🔍 DEBUGGING CONFIG TYPES")
    print("=" * 30)
    
    config = AgentConfig(
        name="ConfigDebugger",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    
    # Check all agent configs
    print("\n1. Checking all agent configs...")
    configs = ai.orchestrator.agent_configs
    
    for agent_type, agent_config in configs.items():
        print(f"\n{agent_type}:")
        print(f"  Type: {type(agent_config)}")
        print(f"  Value: {agent_config}")
        
        if isinstance(agent_config, str):
            print(f"  ❌ WARNING: {agent_type} config is a string, not a dict!")
        elif isinstance(agent_config, dict):
            print(f"  ✅ {agent_type} config is a proper dict")
            # Check a few key fields
            for key in ['deployment_type', 'token_env', 'api_key_env', 'image']:
                if key in agent_config:
                    value = agent_config[key]
                    print(f"    {key}: {value} ({type(value)})")
        else:
            print(f"  ⚠️  {agent_type} config is type: {type(agent_config)}")
    
    # Test specific configs that might be problematic
    print(f"\n2. Testing specific problematic configs...")
    problem_agents = ['fullstackdev', 'coderdev1', 'coderdev2']
    
    for agent_type in problem_agents:
        if agent_type in configs:
            agent_config = configs[agent_type]
            print(f"\n{agent_type} detailed analysis:")
            print(f"  Type: {type(agent_config)}")
            print(f"  Repr: {repr(agent_config)}")
            
            if isinstance(agent_config, dict):
                print("  Dict keys:", list(agent_config.keys()))
            elif isinstance(agent_config, str):
                print(f"  String content (first 100 chars): {agent_config[:100]}")

async def main():
    await debug_config_types()

if __name__ == "__main__":
    asyncio.run(main())