#!/usr/bin/env python3
"""
Interactive test client for MCP Chatbot Management Tools
Allows manual testing of chatbot management commands
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


class InteractiveChatbotClient:
    """Interactive client for testing MCP chatbot tools"""
    
    def __init__(self):
        self.server_script = Path(__file__).parent / "mcp_servers" / "chatbot_server.py"
        self.session = None
        
    async def start(self):
        """Start the interactive client"""
        logger.info("🤖 Starting Interactive MCP Chatbot Client")
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
                    logger.info("✅ Connected to MCP chatbot server\n")
                    
                    # Interactive loop
                    await self.interactive_loop()
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            
    async def interactive_loop(self):
        """Main interactive command loop"""
        commands = {
            'help': self.show_help,
            'list': self.list_chatbots,
            'launch': self.launch_chatbot,
            'stop': self.stop_chatbot,
            'restart': self.restart_chatbot,
            'status': self.get_status,
            'logs': self.get_logs,
            'tools': self.list_tools,
            'exit': self.exit_client
        }
        
        while True:
            try:
                # Get user input
                command = input("\n🤖 ChatBot> ").strip().lower()
                
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
        print("  help                - Show this help message")
        print("  list [all|running]  - List chatbots (all=default, running=only active)")
        print("  launch <name> [bg]  - Launch a chatbot (bg=background, default=foreground)")
        print("  stop <name> [force] - Stop a chatbot (force=kill immediately)")
        print("  restart <name>      - Restart a chatbot")
        print("  status <name>       - Get detailed status of a chatbot")
        print("  logs <name> [N]     - Get recent logs (N=number of lines, default=20)")
        print("  tools               - List available MCP tools")
        print("  exit                - Exit the client")
        print("\nExamples:")
        print("  list all")
        print("  launch grok4_agent bg")
        print("  status grok4_agent")
        print("  logs grok4_agent 50")
        print("  stop grok4_agent force")
        
    async def list_chatbots(self, args):
        """List chatbots"""
        filter_type = args[0] if args else 'all'
        include_stopped = filter_type != 'running'
        
        print(f"\n🤖 Listing chatbots (filter: {filter_type})...")
        result = await self.session.call_tool("list_chatbots", {"include_stopped": include_stopped})
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                chatbots = data['chatbots']
                if not chatbots:
                    print("  No chatbots found")
                else:
                    print(f"  Found {len(chatbots)} chatbots:\n")
                    for c in chatbots:
                        status = "🟢" if c['status'] == 'running' else "🔴"
                        print(f"  {status} {c['name']} ({c['display_name']})")
                        print(f"     LLM: {c['llm_type']}")
                        print(f"     Token: {c['discord_token_env']}")
                        print(f"     Script: {c['script']}")
                        if c['status'] == 'running':
                            print(f"     PID: {c.get('pid', 'N/A')}, Memory: {c.get('memory_mb', 0)}MB")
                            print(f"     Uptime: {c.get('uptime', 'N/A')}")
                        print()
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def launch_chatbot(self, args):
        """Launch a chatbot"""
        if not args:
            print("❌ Usage: launch <chatbot_name> [bg]")
            return
            
        agent_name = args[0]
        background = len(args) > 1 and args[1] == 'bg'
        
        mode = "background" if background else "foreground"
        print(f"\n🚀 Launching {agent_name} in {mode} mode...")
        
        result = await self.session.call_tool("launch_chatbot", {
            "agent_name": agent_name,
            "background": background
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ {data['message']}")
                if 'pid' in data:
                    print(f"  PID: {data['pid']}")
                if 'log_file' in data:
                    print(f"  Log file: {data['log_file']}")
                if 'stdout' in data and data['stdout']:
                    print(f"  Output preview:\n{data['stdout']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def stop_chatbot(self, args):
        """Stop a chatbot"""
        if not args:
            print("❌ Usage: stop <chatbot_name> [force]")
            return
            
        agent_name = args[0]
        force = len(args) > 1 and args[1] == 'force'
        
        action = "force stopping" if force else "stopping"
        print(f"\n🛑 {action.title()} {agent_name}...")
        
        result = await self.session.call_tool("stop_chatbot", {
            "agent_name": agent_name,
            "force": force
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ {data['message']}")
                if 'killed_pids' in data:
                    print(f"  Killed PIDs: {data['killed_pids']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def restart_chatbot(self, args):
        """Restart a chatbot"""
        if not args:
            print("❌ Usage: restart <chatbot_name>")
            return
            
        agent_name = args[0]
        print(f"\n🔄 Restarting {agent_name}...")
        
        result = await self.session.call_tool("restart_chatbot", {
            "agent_name": agent_name
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ {data['message']}")
                print(f"  Stop result: {data['stop_result']['success']}")
                print(f"  Start result: {data['start_result']['success']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def get_status(self, args):
        """Get chatbot status"""
        if not args:
            print("❌ Usage: status <chatbot_name>")
            return
            
        agent_name = args[0]
        print(f"\n📋 Getting status for {agent_name}...")
        
        result = await self.session.call_tool("get_chatbot_status", {
            "agent_name": agent_name
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                status = data['status']
                config = data['config']
                log_info = data.get('log_info')
                
                print(f"\n  📊 Status for {agent_name}:")
                print(f"    Status: {status.get('status', 'unknown')}")
                if status.get('pid'):
                    print(f"    PID: {status['pid']}")
                    print(f"    Uptime: {status.get('uptime', 'unknown')}")
                    print(f"    Memory: {status.get('memory_mb', 0)}MB")
                    print(f"    CPU: {status.get('cpu_percent', 0):.1f}%")
                    
                print(f"\n  ⚙️  Configuration:")
                print(f"    Display Name: {config.get('name', 'N/A')}")
                print(f"    LLM Type: {config.get('llm_type', 'N/A')}")
                print(f"    Script: {config.get('script', 'N/A')}")
                print(f"    Discord Token: {config.get('discord_token_env', 'N/A')}")
                print(f"    Personality: {config.get('personality', 'N/A')}")
                
                if log_info:
                    print(f"\n  📝 Log Info:")
                    print(f"    Path: {log_info['path']}")
                    print(f"    Size: {log_info['size_mb']}MB")
                    print(f"    Modified: {log_info['modified']}")
            else:
                print(f"  ❌ Error: {data['error']}")
                
    async def get_logs(self, args):
        """Get chatbot logs"""
        if not args:
            print("❌ Usage: logs <chatbot_name> [lines]")
            return
            
        agent_name = args[0]
        lines = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
        
        print(f"\n📝 Getting {lines} lines of logs for {agent_name}...")
        
        result = await self.session.call_tool("get_chatbot_logs", {
            "agent_name": agent_name,
            "lines": lines
        })
        
        if result and result.content:
            data = json.loads(result.content[0].text)
            if data['success']:
                print(f"  ✅ Retrieved {data['lines_returned']} lines from {data['log_file']}")
                if data['logs']:
                    print(f"\n  📋 Recent logs:")
                    print("  " + "="*50)
                    print(data['logs'])
                    print("  " + "="*50)
                else:
                    print("  No log content found")
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
    client = InteractiveChatbotClient()
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")