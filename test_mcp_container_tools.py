#!/usr/bin/env python3
"""
Test client for MCP Container Management Tools
Tests all container management functionality independently
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


class MCPContainerTestClient:
    """Test client for MCP container management tools"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "container_server.py"
        
    async def test_all_tools(self):
        """Run all container tool tests"""
        logger.info("🧪 Starting MCP Container Tools Test Suite")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        try:
            # Connect to MCP server
            logger.info("📡 Connecting to MCP container server...")
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()
                    logger.info("✅ Connected to MCP container server")
                    
                    # List available tools
                    tools = await session.list_tools()
                    logger.info(f"📋 Available tools: {[tool.name for tool in tools]}")
                    
                    # Run test suite
                    await self._test_list_containers(session)
                    await self._test_container_config(session)
                    await self._test_container_lifecycle(session)
                    await self._test_container_testing(session)
                    
                    logger.info("✅ All tests completed!")
                    
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
            
    async def _test_list_containers(self, session: ClientSession):
        """Test listing containers"""
        logger.info("\n🔍 TEST 1: List Containers")
        
        # Test 1.1: List running containers only
        logger.info("  1.1 List running containers...")
        result = await session.call_tool("list_containers", {"include_stopped": False})
        if result and result.content:
            data = json.loads(result.content[0].text)
            logger.info(f"  ✅ Found {len(data.get('containers', []))} running containers")
            for container in data.get('containers', []):
                logger.info(f"    - {container['name']} ({container['status']}) - Bot: {container['bot_identity']}")
        
        # Test 1.2: List all containers including stopped
        logger.info("  1.2 List all containers (including stopped)...")
        result = await session.call_tool("list_containers", {"include_stopped": True})
        if result and result.content:
            data = json.loads(result.content[0].text)
            logger.info(f"  ✅ Found {len(data.get('containers', []))} total containers")
            
    async def _test_container_config(self, session: ClientSession):
        """Test getting container configuration"""
        logger.info("\n📋 TEST 2: Get Container Configuration")
        
        # Test configs for known containers
        test_containers = ["claude-isolated-discord", "claude-fullstackdev-persistent"]
        
        for container_name in test_containers:
            logger.info(f"  Getting config for {container_name}...")
            result = await session.call_tool("get_container_config", {"container_name": container_name})
            if result and result.content:
                data = json.loads(result.content[0].text)
                if data['success']:
                    config = data['config']
                    logger.info(f"  ✅ Got config for {container_name}")
                    logger.info(f"    - Discord Token: {config.get('discord_token_env', 'Not set')}")
                    logger.info(f"    - Runtime Status: {config.get('runtime_status', 'Unknown')}")
                else:
                    logger.warning(f"  ⚠️  Failed to get config: {data.get('error')}")
                    
    async def _test_container_lifecycle(self, session: ClientSession):
        """Test container launch and shutdown"""
        logger.info("\n🔄 TEST 3: Container Lifecycle")
        
        # First, list containers to see what's available
        result = await session.call_tool("list_containers", {"include_stopped": True})
        if not result or not result.content:
            logger.error("  ❌ Could not list containers")
            return
            
        data = json.loads(result.content[0].text)
        if not data['success'] or not data['containers']:
            logger.warning("  ⚠️  No containers found to test lifecycle")
            return
            
        # Pick a test container
        test_container = None
        for container in data['containers']:
            if 'claude' in container['name'].lower():
                test_container = container
                break
                
        if not test_container:
            logger.warning("  ⚠️  No Claude containers found for testing")
            return
            
        container_name = test_container['name']
        logger.info(f"  Testing with container: {container_name}")
        
        # Test 3.1: Launch container
        logger.info(f"  3.1 Launching container {container_name}...")
        result = await session.call_tool("launch_container", {
            "container_name": container_name,
            "preserve_auth": True
        })
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                logger.info(f"  ✅ {data['message']}")
            else:
                logger.error(f"  ❌ Launch failed: {data['error']}")
                
        # Wait a bit for container to start
        await asyncio.sleep(3)
        
        # Test 3.2: Stop container (without removing)
        logger.info(f"  3.2 Stopping container {container_name}...")
        result = await session.call_tool("shutdown_container", {
            "container_name": container_name,
            "remove": False
        })
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                logger.info(f"  ✅ {data['message']}")
            else:
                logger.error(f"  ❌ Shutdown failed: {data['error']}")
                
    async def _test_container_testing(self, session: ClientSession):
        """Test container functionality testing"""
        logger.info("\n🧪 TEST 4: Container Testing")
        
        # First check for running containers
        result = await session.call_tool("list_containers", {"include_stopped": False})
        if not result or not result.content:
            logger.error("  ❌ Could not list containers")
            return
            
        data = json.loads(result.content[0].text)
        running_containers = [c for c in data.get('containers', []) if c['status'] == 'running']
        
        if not running_containers:
            logger.warning("  ⚠️  No running containers to test")
            # Try to start one for testing
            logger.info("  Attempting to start a container for testing...")
            result = await session.call_tool("launch_container", {
                "container_name": "claude-isolated-discord",
                "preserve_auth": True
            })
            await asyncio.sleep(5)  # Wait for startup
            
            # Check again
            result = await session.call_tool("list_containers", {"include_stopped": False})
            if result and result.content:
                data = json.loads(result.content[0].text)
                running_containers = [c for c in data.get('containers', []) if c['status'] == 'running']
                
        if running_containers:
            test_container = running_containers[0]
            container_name = test_container['name']
            
            logger.info(f"  Testing container: {container_name}")
            result = await session.call_tool("test_container", {"container_name": container_name})
            if result and result.content:
                data = json.loads(result.content[0].text)
                if data['success']:
                    logger.info("  ✅ Container tests:")
                    for test_name, passed in data['tests'].items():
                        status = "✅" if passed else "❌"
                        logger.info(f"    {status} {test_name}")
                else:
                    logger.error(f"  ❌ Test failed: {data['error']}")
        else:
            logger.warning("  ⚠️  Could not start any containers for testing")
            
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
                
                # Test with non-existent container
                logger.info("  Testing with non-existent container...")
                result = await session.call_tool("test_container", {"container_name": "non-existent-container"})
                if result and result.content:
                    data = json.loads(result.content[0].text)
                    if not data['success']:
                        logger.info(f"  ✅ Correctly handled error: {data['error']}")
                    else:
                        logger.error("  ❌ Should have failed for non-existent container")
                        
                # Test with missing parameters
                logger.info("  Testing with missing parameters...")
                try:
                    result = await session.call_tool("launch_container", {})
                    logger.error("  ❌ Should have failed for missing container_name")
                except Exception as e:
                    logger.info(f"  ✅ Correctly rejected missing parameter: {e}")


async def main():
    """Run all tests"""
    client = MCPContainerTestClient()
    
    # Run main test suite
    await client.test_all_tools()
    
    # Run error handling tests
    await client.test_error_handling()
    
    logger.info("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())