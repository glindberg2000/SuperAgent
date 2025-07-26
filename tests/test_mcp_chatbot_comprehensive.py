#!/usr/bin/env python3
"""
Comprehensive test for MCP Chatbot Management Tools
Tests all functionality including background launches, monitoring, and shutdown
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


class ComprehensiveChatbotTest:
    """Comprehensive chatbot management test"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "chatbot_server.py"
        
    async def run_comprehensive_test(self):
        """Run comprehensive test of all chatbot management functions"""
        logger.info("🚀 Starting Comprehensive MCP Chatbot Management Test")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info("✅ Connected to MCP chatbot server")
                    
                    # Test sequence
                    await self._test_initial_state(session)
                    await self._test_background_launch(session)
                    await self._test_monitoring(session)
                    await self._test_logs_and_status(session)
                    await self._test_shutdown(session)
                    await self._test_restart_functionality(session)
                    await self._test_cleanup(session)
                    
                    logger.info("🎉 Comprehensive test completed successfully!")
                    
        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            raise
            
    async def _test_initial_state(self, session: ClientSession):
        """Test 1: Check initial state"""
        logger.info("\n🔍 TEST 1: Initial State Check")
        
        # List all available chatbots
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        data = json.loads(result.content[0].text)
        
        logger.info(f"📋 Found {len(data['chatbots'])} total chatbots:")
        for bot in data['chatbots']:
            status = "🟢" if bot['status'] == 'running' else "🔴"
            logger.info(f"  {status} {bot['name']} ({bot['llm_type']}) - {bot['status']}")
            
        # Count running bots
        running_bots = [b for b in data['chatbots'] if b['status'] == 'running']
        logger.info(f"✅ Currently {len(running_bots)} bots running")
        
        return data['chatbots']
        
    async def _test_background_launch(self, session: ClientSession):
        """Test 2: Background launch functionality"""
        logger.info("\n🚀 TEST 2: Background Launch")
        
        # Pick first available bot to launch
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        data = json.loads(result.content[0].text)
        available_bots = [b for b in data['chatbots'] if b['status'] == 'stopped']
        
        if not available_bots:
            logger.warning("⚠️  No stopped bots available for launch test")
            return
            
        test_bot = available_bots[0]['name']
        logger.info(f"🎯 Testing background launch with: {test_bot}")
        
        # Launch in background
        result = await session.call_tool("launch_chatbot", {
            "agent_name": test_bot,
            "background": True
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"✅ Background launch successful: {data['message']}")
            if 'pid' in data:
                logger.info(f"📊 PID: {data['pid']}")
            if 'log_file' in data:
                logger.info(f"📝 Log file: {data['log_file']}")
        else:
            logger.error(f"❌ Background launch failed: {data['error']}")
            
        # Wait a moment for startup
        logger.info("⏱️  Waiting 5 seconds for bot to initialize...")
        await asyncio.sleep(5)
        
        return test_bot
        
    async def _test_monitoring(self, session: ClientSession):
        """Test 3: Monitor running bots"""
        logger.info("\n📊 TEST 3: Monitoring Running Bots")
        
        # Check running bots
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        
        running_bots = data['chatbots']
        logger.info(f"🔍 Found {len(running_bots)} running bots:")
        
        for bot in running_bots:
            logger.info(f"  🟢 {bot['name']}")
            logger.info(f"    PID: {bot.get('pid', 'N/A')}")
            logger.info(f"    Memory: {bot.get('memory_mb', 0)}MB")
            logger.info(f"    Uptime: {bot.get('uptime', 'N/A')}")
            logger.info(f"    CPU: {bot.get('cpu_percent', 0):.1f}%")
            
        return running_bots
        
    async def _test_logs_and_status(self, session: ClientSession):
        """Test 4: Check logs and detailed status"""
        logger.info("\n📝 TEST 4: Logs and Status")
        
        # Get running bots
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        running_bots = data['chatbots']
        
        if not running_bots:
            logger.warning("⚠️  No running bots to check logs/status")
            return
            
        test_bot = running_bots[0]['name']
        logger.info(f"🎯 Testing logs/status with: {test_bot}")
        
        # Test detailed status
        logger.info("  4.1 Getting detailed status...")
        result = await session.call_tool("get_chatbot_status", {"agent_name": test_bot})
        data = json.loads(result.content[0].text)
        
        if data['success']:
            status = data['status']
            config = data['config']
            logger.info(f"  ✅ Status: {status.get('status')}")
            logger.info(f"    LLM Type: {config.get('llm_type')}")
            logger.info(f"    Script: {config.get('script')}")
            if status.get('pid'):
                logger.info(f"    PID: {status['pid']}, Memory: {status.get('memory_mb')}MB")
        else:
            logger.error(f"  ❌ Status check failed: {data['error']}")
            
        # Test logs
        logger.info("  4.2 Getting recent logs...")
        result = await session.call_tool("get_chatbot_logs", {
            "agent_name": test_bot,
            "lines": 10
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ Retrieved {data['lines_returned']} log lines")
            logger.info(f"    Log file: {data['log_file']}")
            if data['logs']:
                logger.info(f"    Recent activity detected: {len(data['logs'])} chars")
            else:
                logger.info("    No recent log activity")
        else:
            logger.warning(f"  ⚠️  Could not get logs: {data['error']}")
            
    async def _test_shutdown(self, session: ClientSession):
        """Test 5: Shutdown functionality"""
        logger.info("\n🛑 TEST 5: Shutdown Functionality")
        
        # Get running bots
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        running_bots = data['chatbots']
        
        if not running_bots:
            logger.warning("⚠️  No running bots to shutdown")
            return
            
        # Test graceful shutdown
        for bot in running_bots[:2]:  # Test shutdown on first 2 bots
            bot_name = bot['name']
            logger.info(f"  5.1 Testing graceful shutdown: {bot_name}")
            
            result = await session.call_tool("stop_chatbot", {
                "agent_name": bot_name,
                "force": False
            })
            data = json.loads(result.content[0].text)
            
            if data['success']:
                logger.info(f"    ✅ {data['message']}")
                if 'killed_pids' in data:
                    logger.info(f"    Killed PIDs: {data['killed_pids']}")
            else:
                logger.warning(f"    ⚠️  Graceful shutdown failed: {data['error']}")
                
                # Try force shutdown
                logger.info(f"    Trying force shutdown...")
                result = await session.call_tool("stop_chatbot", {
                    "agent_name": bot_name,
                    "force": True
                })
                data = json.loads(result.content[0].text)
                
                if data['success']:
                    logger.info(f"    ✅ Force shutdown: {data['message']}")
                else:
                    logger.error(f"    ❌ Force shutdown failed: {data['error']}")
                    
        # Wait for shutdown to complete
        logger.info("⏱️  Waiting 3 seconds for shutdown to complete...")
        await asyncio.sleep(3)
        
    async def _test_restart_functionality(self, session: ClientSession):
        """Test 6: Restart functionality"""
        logger.info("\n🔄 TEST 6: Restart Functionality")
        
        # Get all bots (should be stopped now)
        result = await session.call_tool("list_chatbots", {"include_stopped": True})
        data = json.loads(result.content[0].text)
        all_bots = data['chatbots']
        
        if not all_bots:
            logger.warning("⚠️  No bots available for restart test")
            return
            
        # Pick first bot for restart test
        test_bot = all_bots[0]['name']
        logger.info(f"🎯 Testing restart with: {test_bot}")
        
        result = await session.call_tool("restart_chatbot", {"agent_name": test_bot})
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"✅ Restart successful: {data['message']}")
            logger.info(f"  Stop result: {'✅' if data['stop_result']['success'] else '❌'}")
            logger.info(f"  Start result: {'✅' if data['start_result']['success'] else '❌'}")
        else:
            logger.error(f"❌ Restart failed: {data['error']}")
            
        # Wait for restart to complete
        logger.info("⏱️  Waiting 5 seconds for restart to complete...")
        await asyncio.sleep(5)
        
        # Verify restart worked
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        running_after_restart = [b['name'] for b in data['chatbots']]
        
        if test_bot in running_after_restart:
            logger.info(f"✅ Restart verification successful - {test_bot} is running")
        else:
            logger.warning(f"⚠️  Restart verification failed - {test_bot} not running")
            
    async def _test_cleanup(self, session: ClientSession):
        """Test 7: Final cleanup"""
        logger.info("\n🧹 TEST 7: Final Cleanup")
        
        # Stop all running bots
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        running_bots = data['chatbots']
        
        if running_bots:
            logger.info(f"🛑 Stopping {len(running_bots)} running bots...")
            for bot in running_bots:
                result = await session.call_tool("stop_chatbot", {
                    "agent_name": bot['name'],
                    "force": True
                })
                data = json.loads(result.content[0].text)
                status = "✅" if data['success'] else "❌"
                logger.info(f"  {status} {bot['name']}: {data.get('message', data.get('error'))}")
        else:
            logger.info("✅ No running bots to clean up")
            
        # Final verification
        await asyncio.sleep(2)
        result = await session.call_tool("list_chatbots", {"include_stopped": False})
        data = json.loads(result.content[0].text)
        final_running = data['chatbots']
        
        if not final_running:
            logger.info("✅ Cleanup successful - no bots running")
        else:
            logger.warning(f"⚠️  {len(final_running)} bots still running after cleanup")
            
    async def test_error_cases(self):
        """Test error handling"""
        logger.info("\n🔧 ERROR HANDLING TESTS")
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test non-existent bot
                logger.info("  Testing non-existent bot operations...")
                
                operations = [
                    ("launch_chatbot", {"agent_name": "fake-bot"}),
                    ("stop_chatbot", {"agent_name": "fake-bot"}),
                    ("get_chatbot_status", {"agent_name": "fake-bot"}),
                    ("get_chatbot_logs", {"agent_name": "fake-bot"})
                ]
                
                for op_name, params in operations:
                    result = await session.call_tool(op_name, params)
                    data = json.loads(result.content[0].text)
                    
                    if not data['success']:
                        logger.info(f"    ✅ {op_name}: Correctly handled error")
                    else:
                        logger.warning(f"    ⚠️  {op_name}: Should have failed")


async def main():
    """Run comprehensive test"""
    test = ComprehensiveChatbotTest()
    
    # Run main comprehensive test
    await test.run_comprehensive_test()
    
    # Run error handling tests
    await test.test_error_cases()
    
    logger.info("\n🏆 All comprehensive tests completed!")


if __name__ == "__main__":
    asyncio.run(main())