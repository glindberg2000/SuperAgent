#!/usr/bin/env python3
"""
Comprehensive test for MCP Team Management Tools
Tests all 10 team management functions with real team operations
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


class ComprehensiveTeamTest:
    """Comprehensive team management test"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "team_server.py"
        self.test_team_name = "test_team_demo"
        
    async def run_comprehensive_test(self):
        """Run comprehensive test of all team management functions"""
        logger.info("🚀 Starting Comprehensive MCP Team Management Test")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info("✅ Connected to MCP team server")
                    
                    # Test sequence
                    await self._test_list_teams_initial(session)
                    await self._test_create_team(session)
                    await self._test_team_member_management(session)
                    await self._test_team_lifecycle(session)
                    await self._test_team_status_and_logs(session)
                    await self._test_team_restart(session)
                    await self._test_cleanup_and_delete(session)
                    
                    logger.info("🎉 Comprehensive team test completed successfully!")
                    
        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {e}")
            raise
            
    async def _test_list_teams_initial(self, session: ClientSession):
        """Test 1: List existing teams"""
        logger.info("\n🔍 TEST 1: List Existing Teams")
        
        # List all teams
        result = await session.call_tool("list_teams", {"include_inactive": True})
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"📋 Found {len(data['teams'])} existing teams:")
            for team in data['teams']:
                status = "🟢" if team['running_members'] > 0 else "🔴"
                logger.info(f"  {status} {team['name']} - {team['running_members']}/{team['total_members']} running")
                logger.info(f"    Mode: {team['coordination_mode']}, Auto-deploy: {team['auto_deploy']}")
        else:
            logger.error(f"❌ Failed to list teams: {data['error']}")
            
    async def _test_create_team(self, session: ClientSession):
        """Test 2: Create a new team"""
        logger.info("\n🆕 TEST 2: Create New Team")
        
        # Create test team
        result = await session.call_tool("create_team", {
            "team_name": self.test_team_name,
            "display_name": "Test Demo Team",
            "description": "Temporary team for testing team management functionality",
            "agents": ["grok4_agent", "claude_agent"],
            "coordination_mode": "parallel",
            "auto_deploy": False
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"✅ Created team: {data['message']}")
            logger.info(f"  Team config: {data['team_config']['name']}")
            logger.info(f"  Members: {data['team_config']['agents']}")
        else:
            logger.error(f"❌ Failed to create team: {data['error']}")
            
    async def _test_team_member_management(self, session: ClientSession):
        """Test 3: Add and remove team members"""
        logger.info("\n👥 TEST 3: Team Member Management")
        
        # Test add member
        logger.info("  3.1 Adding team member...")
        result = await session.call_tool("add_team_member", {
            "team_name": self.test_team_name,
            "agent_name": "gemini_agent"
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ {data['message']}")
            logger.info(f"    New member count: {data['new_member_count']}")
        else:
            logger.error(f"  ❌ Failed to add member: {data['error']}")
            
        # Test remove member
        logger.info("  3.2 Removing team member...")
        result = await session.call_tool("remove_team_member", {
            "team_name": self.test_team_name,
            "agent_name": "gemini_agent",
            "stop_agent": False
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ {data['message']}")
            logger.info(f"    New member count: {data['new_member_count']}")
        else:
            logger.error(f"  ❌ Failed to remove member: {data['error']}")
            
    async def _test_team_lifecycle(self, session: ClientSession):
        """Test 4: Team start and stop operations"""
        logger.info("\n🔄 TEST 4: Team Lifecycle Operations")
        
        # Test start team
        logger.info("  4.1 Starting team (parallel mode)...")
        result = await session.call_tool("start_team", {
            "team_name": self.test_team_name,
            "mode": "parallel"
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ {data['message']}")
            logger.info(f"    Started: {data['started_count']}/{data['total_count']} agents")
            for result_item in data['results']:
                status = "✅" if result_item['success'] else "❌"
                logger.info(f"      {status} {result_item['agent']}: {result_item['message']}")
        else:
            logger.error(f"  ❌ Failed to start team: {data['error']}")
            
        # Wait for agents to initialize
        logger.info("  ⏱️  Waiting 5 seconds for agents to initialize...")
        await asyncio.sleep(5)
        
        # Test stop team
        logger.info("  4.2 Stopping team...")
        result = await session.call_tool("stop_team", {
            "team_name": self.test_team_name,
            "force": False
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ {data['message']}")
            logger.info(f"    Stopped: {data['stopped_count']}/{data['total_count']} agents")
        else:
            logger.error(f"  ❌ Failed to stop team: {data['error']}")
            
    async def _test_team_status_and_logs(self, session: ClientSession):
        """Test 5: Team status and log retrieval"""
        logger.info("\n📊 TEST 5: Team Status and Logs")
        
        # Start team again for status testing
        logger.info("  5.1 Starting team for status testing...")
        await session.call_tool("start_team", {
            "team_name": self.test_team_name,
            "mode": "parallel"
        })
        
        # Wait for startup
        await asyncio.sleep(3)
        
        # Test get team status
        logger.info("  5.2 Getting team status...")
        result = await session.call_tool("get_team_status", {
            "team_name": self.test_team_name
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            health = data['health']
            logger.info(f"  ✅ Team health: {health['percentage']}% ({health['status']})")
            logger.info(f"    Running: {health['running_members']}/{health['total_members']}")
            logger.info(f"    Total memory: {health['total_memory_mb']}MB")
            
            logger.info("    Member details:")
            for member in data['members']:
                status = "🟢" if member['status'] == 'running' else "🔴"
                logger.info(f"      {status} {member['name']} ({member.get('llm_type', 'unknown')})")
                if member['status'] == 'running':
                    logger.info(f"        PID: {member.get('pid')}, Memory: {member.get('memory_mb')}MB")
        else:
            logger.error(f"  ❌ Failed to get team status: {data['error']}")
            
        # Test get team logs
        logger.info("  5.3 Getting team logs...")
        result = await session.call_tool("get_team_logs", {
            "team_name": self.test_team_name,
            "lines": 5,
            "merge": False
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ Retrieved logs from {data['member_count']} members")
            for member_log in data['member_logs']:
                status = "✅" if member_log['success'] else "❌"
                logger.info(f"    {status} {member_log['agent']}: {member_log.get('lines_returned', 0)} lines")
                if member_log.get('error'):
                    logger.info(f"      Error: {member_log['error']}")
        else:
            logger.error(f"  ❌ Failed to get team logs: {data['error']}")
            
    async def _test_team_restart(self, session: ClientSession):
        """Test 6: Team restart functionality"""
        logger.info("\n🔄 TEST 6: Team Restart")
        
        result = await session.call_tool("restart_team", {
            "team_name": self.test_team_name
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"✅ {data['message']}")
            
            stop_result = data['stop_result']
            start_result = data['start_result']
            
            logger.info(f"  Stop phase: {stop_result['stopped_count']}/{stop_result['total_count']} agents")
            logger.info(f"  Start phase: {start_result['started_count']}/{start_result['total_count']} agents")
        else:
            logger.error(f"❌ Failed to restart team: {data['error']}")
            
        # Wait for restart to complete
        logger.info("⏱️  Waiting 5 seconds for restart to complete...")
        await asyncio.sleep(5)
        
    async def _test_cleanup_and_delete(self, session: ClientSession):
        """Test 7: Cleanup and team deletion"""
        logger.info("\n🧹 TEST 7: Cleanup and Team Deletion")
        
        # Stop team before deletion
        logger.info("  7.1 Stopping team before deletion...")
        result = await session.call_tool("stop_team", {
            "team_name": self.test_team_name,
            "force": True
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ Stopped team: {data['stopped_count']} agents")
        else:
            logger.warning(f"  ⚠️  Stop team result: {data.get('error')}")
            
        # Wait for cleanup
        await asyncio.sleep(2)
        
        # Delete test team
        logger.info("  7.2 Deleting test team...")
        result = await session.call_tool("delete_team", {
            "team_name": self.test_team_name,
            "force": False
        })
        data = json.loads(result.content[0].text)
        
        if data['success']:
            logger.info(f"  ✅ {data['message']}")
        else:
            logger.error(f"  ❌ Failed to delete team: {data['error']}")
            
        # Verify team is gone
        logger.info("  7.3 Verifying team deletion...")
        result = await session.call_tool("list_teams", {"include_inactive": True})
        data = json.loads(result.content[0].text)
        
        if data['success']:
            team_names = [t['name'] for t in data['teams']]
            if self.test_team_name not in team_names:
                logger.info("  ✅ Test team successfully deleted")
            else:
                logger.warning("  ⚠️  Test team still exists after deletion")
        else:
            logger.error(f"  ❌ Failed to verify deletion: {data['error']}")
            
    async def test_error_cases(self):
        """Test error handling and edge cases"""
        logger.info("\n🔧 ERROR HANDLING TESTS")
        
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                error_tests = [
                    ("start_team", {"team_name": "non-existent-team"}),
                    ("stop_team", {"team_name": "fake-team"}),
                    ("get_team_status", {"team_name": "missing-team"}),
                    ("add_team_member", {"team_name": "fake-team", "agent_name": "fake-agent"}),
                    ("delete_team", {"team_name": "non-existent-team"})
                ]
                
                for tool_name, params in error_tests:
                    result = await session.call_tool(tool_name, params)
                    data = json.loads(result.content[0].text)
                    
                    if not data['success']:
                        logger.info(f"  ✅ {tool_name}: Correctly handled error")
                    else:
                        logger.warning(f"  ⚠️  {tool_name}: Should have failed for invalid input")


async def main():
    """Run comprehensive test"""
    test = ComprehensiveTeamTest()
    
    # Run main comprehensive test
    await test.run_comprehensive_test()
    
    # Run error handling tests
    await test.test_error_cases()
    
    logger.info("\n🏆 All comprehensive team tests completed!")


if __name__ == "__main__":
    asyncio.run(main())