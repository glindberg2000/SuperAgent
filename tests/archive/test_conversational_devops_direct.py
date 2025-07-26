#!/usr/bin/env python3
"""
Direct testing of conversational DevOps AI without Discord
Test each function individually to see what actually works
"""

import asyncio
import json
import os
import sys
sys.path.append('.')

from conversational_devops_ai import ConversationalDevOpsAI, ConversationContext
from enhanced_discord_agent import AgentConfig

async def test_orchestrator_functions():
    """Test if orchestrator functions actually work"""
    print("🧪 Testing Orchestrator Functions")
    
    # Create test AI instance
    config = AgentConfig(
        name="TestDevOpsAI",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )
    
    ai = ConversationalDevOpsAI(config)
    
    # Test 1: Get active agents
    print("\n1. Testing get_active_agents()...")
    try:
        active_agents = await ai.orchestrator.get_active_agents()
        print(f"   Result: {active_agents}")
        print(f"   Type: {type(active_agents)}")
        print(f"   Length: {len(active_agents) if hasattr(active_agents, '__len__') else 'N/A'}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Get agent configs
    print("\n2. Testing agent_configs...")
    try:
        configs = ai.orchestrator.agent_configs
        print(f"   Result: {list(configs.keys()) if configs else 'None/Empty'}")
        print(f"   Type: {type(configs)}")
        
        if configs:
            print("   Available agent types:")
            for key, value in configs.items():
                print(f"     - {key}: {value.get('name', 'No name') if isinstance(value, dict) else value}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 3: Test individual tool functions
    print("\n3. Testing tool functions...")
    
    print("\n   3a. Testing _handle_check_status_tool()...")
    try:
        status_result = await ai._handle_check_status_tool()
        print(f"   Result: {status_result}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n   3b. Testing _handle_list_available_agents_tool()...")
    try:
        list_result = await ai._handle_list_available_agents_tool()
        print(f"   Result: {list_result}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n   3c. Testing _handle_deploy_agent_tool()...")
    try:
        deploy_result = await ai._handle_deploy_agent_tool("claude", "test", "test_agent")
        print(f"   Result: {deploy_result}")
    except Exception as e:
        print(f"   ERROR: {e}")

async def test_function_calling_loop():
    """Test the actual function calling loop"""
    print("\n🧪 Testing Function Calling Loop")
    
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
    
    test_messages = [
        "what is the system status?",
        "which agents are available?",
        "deploy a claude agent"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. Testing message: '{message}'")
        try:
            response = await ai._process_with_function_calling(message, context)
            print(f"   Response: {response}")
        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()

async def test_llm_provider():
    """Test the LLM provider directly"""
    print("\n🧪 Testing LLM Provider")
    
    from llm_providers import OpenAIProvider
    
    provider = OpenAIProvider(os.getenv('OPENAI_API_KEY'))
    print(f"Model being used: {provider.model}")
    
    # Test simple response
    print("\n1. Testing simple response...")
    try:
        response = await provider.generate_response(
            [],
            "You are a test assistant. Say 'Hello World'"
        )
        print(f"   Response type: {type(response)}")
        print(f"   Response: {response}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test function calling
    print("\n2. Testing function calling...")
    tools = [{
        "type": "function",
        "function": {
            "name": "test_function",
            "description": "A test function",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "A test message"}
                },
                "required": ["message"]
            }
        }
    }]
    
    try:
        response = await provider.generate_response(
            [{"role": "user", "content": "Call the test function with message 'hello'"}],
            "You are a helpful assistant. Use the available functions.",
            tools=tools
        )
        print(f"   Response type: {type(response)}")
        print(f"   Response: {response}")
        
        # Check if it's a completion object
        if hasattr(response, 'choices'):
            message = response.choices[0].message
            print(f"   Message content: {message.content}")
            print(f"   Tool calls: {message.tool_calls}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    async def main():
        print("🔍 DIRECT TESTING OF CONVERSATIONAL DEVOPS AI")
        print("=" * 50)
        
        await test_llm_provider()
        await test_orchestrator_functions()
        await test_function_calling_loop()
        
        print("\n" + "=" * 50)
        print("✅ Testing complete")

    asyncio.run(main())