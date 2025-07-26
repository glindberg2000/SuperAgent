#!/usr/bin/env python3
"""
Interactive test client for MCP Container Management Tools
Allows manual testing of container management commands
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InteractiveMCPClient:
    """Interactive client for testing MCP container tools"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "container_server.py"
        self.session = None
        
    async def start(self):
        """Start the interactive client"""
        logger.info("🚀 Starting Interactive MCP Container Client")
        logger.info("Type 'help' for available commands, 'exit' to quit\n")
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.server_script)]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.session = session
                    logger.info("✅ Connected to MCP container server\n")
                    
                    # Interactive loop
                    await self.interactive_loop()
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            
    async def interactive_loop(self):
        """Main interactive command loop"""
        commands = {
            'help': self.show_help,
            'list': self.list_containers,
            'launch': self.launch_container,
            'stop': self.stop_container,
            'test': self.test_container,
            'config': self.get_config,
            'tools': self.list_tools,
            'exit': self.exit_client
        }
        
        while True:
            try:
                # Get user input
                command = input("\n🤖 MCP> ").strip().lower()
                
                if not command:
                    continue
                    
                # Parse command
                parts = command.split()
                cmd = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                # Execute command
                if cmd in commands:
                    result = await commands[cmd](args)
                    if result == 'exit':
                        break
                else:
                    print(f"❌ Unknown command: {cmd}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                
    async def show_help(self, args):
        """Show available commands"""
        print("\n📚 Available Commands:")
        print("  help              - Show this help message")
        print("  list [all]        - List containers (add 'all' to include stopped)")
        print("  launch <name>     - Launch a container")
        print("  stop <name> [rm]  - Stop a container (add 'rm' to remove)")
        print("  test <name>       - Test container functionality")
        print("  config <name>     - Get container configuration")
        print("  tools             - List available MCP tools")
        print("  exit              - Exit the client")
        print("\nExamples:")
        print("  list all")
        print("  launch claude-isolated-discord")
        print("  test claude-isolated-discord")
        print("  stop claude-isolated-discord rm")
        
    async def list_containers(self, args):
        """List containers"""
        include_stopped = 'all' in args
        
        print(f"\n📦 Listing containers (include_stopped={include_stopped})...")
        result = await self.session.call_tool("list_containers", {"include_stopped": include_stopped})
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                containers = data['containers']
                if not containers:
                    print("  No containers found")
                else:
                    print(f"  Found {len(containers)} containers:\n")
                    for c in containers:
                        status = "🟢" if c['status'] == 'running' else "🔴"
                        print(f"  {status} {c['name']}")
                        print(f"     Bot: {c['bot_identity']}")
                        print(f"     Token: {c['discord_token_env']}")
                        print(f"     Status: {c['status']}")
                        if 'uptime' in c:
                            print(f"     Uptime: {c['uptime']}")
                        print()
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def launch_container(self, args):
        """Launch a container"""
        if not args:
            print("❌ Usage: launch <container_name>")
            return
            
        container_name = args[0]
        print(f"\n🚀 Launching {container_name}...")
        
        result = await self.session.call_tool("launch_container", {
            "container_name": container_name,
            "preserve_auth": True
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ {data['message']}")
                if 'test_result' in data:
                    print(f"  Test results: {data['test_result']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def stop_container(self, args):
        """Stop a container"""
        if not args:
            print("❌ Usage: stop <container_name> [rm]")
            return
            
        container_name = args[0]
        remove = 'rm' in args or 'remove' in args
        
        action = "removing" if remove else "stopping"
        print(f"\n🛑 {action.title()} {container_name}...")
        
        result = await self.session.call_tool("shutdown_container", {
            "container_name": container_name,
            "remove": remove
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ {data['message']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def test_container(self, args):
        """Test container functionality"""
        if not args:
            print("❌ Usage: test <container_name>")
            return
            
        container_name = args[0]
        print(f"\n🧪 Testing {container_name}...")
        
        result = await self.session.call_tool("test_container", {
            "container_name": container_name
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if 'tests' in data:
                print("  Test Results:")
                for test_name, passed in data['tests'].items():
                    status = "✅" if passed else "❌"
                    print(f"    {status} {test_name}")
                print(f"\n  Overall: {'✅ PASSED' if data['success'] else '❌ FAILED'}")
            else:
                print(f"  ❌ Error: {data.get('error', 'Unknown error')}")
                
    async def get_config(self, args):
        """Get container configuration"""
        if not args:
            print("❌ Usage: config <container_name>")
            return
            
        container_name = args[0]
        print(f"\n📋 Getting config for {container_name}...")
        
        result = await self.session.call_tool("get_container_config", {
            "container_name": container_name
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                config = data['config']
                print(f"\n  Configuration for {container_name}:")
                print(json.dumps(config, indent=2))
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def list_tools(self, args):
        """List available MCP tools"""
        print("\n🔧 Available MCP Tools:")
        tools_response = await self.session.list_tools()
        tools = tools_response.tools if hasattr(tools_response, 'tools') else tools_response
        for tool in tools:
            print(f"\n  📌 {tool.name}")
            print(f"     {tool.description}")
            if tool.inputSchema.get('properties'):
                print("     Parameters:")
                for param, schema in tool.inputSchema['properties'].items():
                    required = param in tool.inputSchema.get('required', [])
                    req_marker = "*" if required else ""
                    print(f"       - {param}{req_marker}: {schema.get('description', 'No description')}")
                    
    async def exit_client(self, args):
        """Exit the client"""
        print("\n👋 Goodbye!")
        return 'exit'


async def main():
    """Run the interactive client"""
    client = InteractiveMCPClient()
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")