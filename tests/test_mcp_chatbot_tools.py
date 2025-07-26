#!/usr/bin/env python3
"""
Test client for MCP Chatbot Management Tools
Tests all chatbot management functionality independently
"""

import asyncio
import json
import logging
from typing import Dict, Any
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPChatbotTestClient:
    """Test client for MCP chatbot management tools"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "chatbot_server.py"
        
    async def test_all_tools(self):
        """Run all chatbot tool tests"""
        logger.info("🤖 Starting MCP Chatbot Tools Test Suite")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        try:
            # Connect to MCP server
            logger.info("📡 Connecting to MCP chatbot server...")
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()
                    logger.info("✅ Connected to MCP chatbot server")
                    
                    # List available tools
                    tools_response = await session.list_tools()
                    if hasattr(tools_response, 'tools'):
                        tools = tools_response.tools
                        logger.info(f"📋 Available tools: {[tool.name for tool in tools]}")
                    else:
                        logger.info(f"📋 Tools response: {tools_response}")
                    
                    # Run test suite
                    await self._test_list_chatbots(session)
                    await self._test_chatbot_status(session)
                    await self._test_chatbot_lifecycle(session)
                    await self._test_chatbot_logs(session)
                    
                    logger.info("✅ All chatbot tests completed!")
                    
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
            
    async def _test_list_chatbots(self, session: ClientSession):
        """Test listing chatbots"""
        logger.info("\n🔍 TEST 1: List Chatbots")
        
        # Test 1.1: List all chatbots (including stopped)
        logger.info("  1.1 List all chatbots...")
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        if result and result.content:
            data = json.loads(result.content[0].text)
            logger.info(f"  ✅ Found {len(data.get('chatbots', []))} total chatbots")
            for chatbot in data.get('chatbots', []):
                status_emoji = "🟢" if chatbot['status'] == 'running' else "🔴"
                logger.info(f"    {status_emoji} {chatbot['name']} ({chatbot['llm_type']}) - Token: {chatbot['discord_token_env']}")
                
        # Test 1.2: List only running chatbots
        logger.info("  1.2 List running chatbots...")
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        if result and result.content:
            data = json.loads(result.content[0].text)
            running_count = len([c for c in data.get('chatbots', []) if c['status'] == 'running'])
            logger.info(f"  ✅ Found {running_count} running chatbots")
            
    async def _test_chatbot_status(self, session: ClientSession):
        """Test getting chatbot status"""
        logger.info("\n📋 TEST 2: Get Chatbot Status")
        
        # Get list of available chatbots first
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        if not result or not result.content:
            logger.warning("  ⚠️  Could not get chatbot list")
            return
            
        data = json.loads(result.content[0].text)
        chatbots = data.get('chatbots', [])
        
        if not chatbots:
            logger.warning("  ⚠️  No chatbots found")
            return
            
        # Test status for first chatbot
        test_chatbot = chatbots[0]
        agent_name = test_chatbot['name']
        
        logger.info(f"  Getting status for {agent_name}...")
        result = await session.call_tool("get_chatbot_status", {"agent_name": agent_name})
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                status = data['status']
                config = data['config']
                logger.info(f"  ✅ Status: {status.get('status', 'unknown')}")
                logger.info(f"    LLM Type: {config.get('llm_type', 'unknown')}")
                logger.info(f"    Script: {config.get('script', 'unknown')}")
                if status.get('pid'):
                    logger.info(f"    PID: {status['pid']}, Memory: {status.get('memory_mb', 0)}MB")
            else:
                logger.error(f"  ❌ Failed to get status: {data['error']}")
                
    async def _test_chatbot_lifecycle(self, session: ClientSession):
        """Test chatbot launch and stop"""
        logger.info("\n🔄 TEST 3: Chatbot Lifecycle")
        
        # Get available chatbots
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        if not result or not result.content:
            logger.error("  ❌ Could not list chatbots")
            return
            
        data = json.loads(result.content[0].text)
        chatbots = data.get('chatbots', [])
        
        if not chatbots:
            logger.warning("  ⚠️  No chatbots available for testing")
            return
            
        # Pick a stopped chatbot to test with
        test_chatbot = None
        for chatbot in chatbots:
            if chatbot['status'] == 'stopped':
                test_chatbot = chatbot
                break
                
        if not test_chatbot:
            # Use the first one
            test_chatbot = chatbots[0]
            
        agent_name = test_chatbot['name']
        logger.info(f"  Testing with chatbot: {agent_name}")
        
        # Test 3.1: Launch chatbot (in foreground for testing)
        logger.info(f"  3.1 Launching chatbot {agent_name} (foreground test)...")
        result = await session.call_tool("launch_chatbot", {
            "agent_name": agent_name,
            "background": False
        })
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                logger.info(f"  ✅ {data['message']}")
                if 'stdout' in data and data['stdout']:
                    logger.info(f"    Output preview: {data['stdout'][:200]}...")
            else:
                logger.error(f"  ❌ Launch failed: {data['error']}")
                
        # Test 3.2: Stop chatbot (if it was running)
        if test_chatbot['status'] == 'running':
            logger.info(f"  3.2 Stopping chatbot {agent_name}...")
            result = await session.call_tool("stop_chatbot", {
                "agent_name": agent_name,
                "force": False
            })
            if result and result.content:
                data = json.loads(result.content[0].text)
                if data['success']:
                    logger.info(f"  ✅ {data['message']}")
                else:
                    logger.error(f"  ❌ Stop failed: {data['error']}")
                    
    async def _test_chatbot_logs(self, session: ClientSession):
        """Test getting chatbot logs"""
        logger.info("\n📝 TEST 4: Chatbot Logs")
        
        # Get available chatbots
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        if not result or not result.content:
            logger.error("  ❌ Could not list chatbots")
            return
            
        data = json.loads(result.content[0].text)
        chatbots = data.get('chatbots', [])
        
        if not chatbots:
            logger.warning("  ⚠️  No chatbots available")
            return
            
        # Test logs for first chatbot
        agent_name = chatbots[0]['name']
        logger.info(f"  Getting logs for {agent_name}...")
        
        result = await session.call_tool("get_chatbot_logs", {
            "agent_name": agent_name,
            "lines": 10
        })
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                logger.info(f"  ✅ Retrieved {data['lines_returned']} log lines")
                logger.info(f"    Log file: {data['log_file']}")
                if data['logs']:
                    logger.info(f"    Recent logs preview: {data['logs'][:200]}...")
                else:
                    logger.info("    No log content found")
            else:
                logger.warning(f"  ⚠️  Could not get logs: {data['error']}")
                
    async def test_error_handling(self):
        """Test error handling and edge cases"""
        logger.info("\n🔧 Testing Error Handling")
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test with non-existent chatbot
                logger.info("  Testing with non-existent chatbot...")
                result = await session.call_tool("get_chatbot_status", {"agent_name": "non-existent-bot"})
                if result and result.content:
                    data = json.loads(result.content[0].text)
                    if not data['success']:
                        logger.info(f"  ✅ Correctly handled error: {data['error']}")
                    else:
                        logger.error("  ❌ Should have failed for non-existent chatbot")
                        
                # Test launching non-existent chatbot
                logger.info("  Testing launch of non-existent chatbot...")
                result = await session.call_tool("launch_chatbot", {"agent_name": "fake-agent"})
                if result and result.content:
                    data = json.loads(result.content[0].text)
                    if not data['success']:
                        logger.info(f"  ✅ Correctly handled error: {data['error']}")
                    else:
                        logger.error("  ❌ Should have failed for non-existent agent")


async def main():
    """Run all tests"""
    client = MCPChatbotTestClient()
    
    # Run main test suite
    await client.test_all_tools()
    
    # Run error handling tests
    await client.test_error_handling()
    
    logger.info("\n🎉 All chatbot tests completed!")


if __name__ == "__main__":
    asyncio.run(main())