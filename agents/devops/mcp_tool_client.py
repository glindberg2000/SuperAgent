#!/usr/bin/env python3
"""
Minimal MCP Tool Client
Provides clean interface for MCP tool discovery and execution
Following the blueprint from MCP_AGENT_REBUILD_GUIDE.md
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPToolClient:
    """Clean MCP client for tool discovery and execution"""

    def __init__(self):
        # MCP server configurations
        project_root = Path(__file__).parent.parent.parent
        # Use .venv python for MCP servers to ensure all dependencies are available
        venv_python = project_root / ".venv" / "bin" / "python"
        python_path = str(venv_python) if venv_python.exists() else "python"

        self.server_configs = {
            "discord": {
                "name": "discord",
                "description": "Discord communication and management tools",
                "command": python_path,
                "args": [
                    "-c",
                    f"import sys; sys.path.append('{project_root}/mcp-discord/src'); "
                    f"import os; os.environ['DISCORD_TOKEN'] = '{os.getenv('DISCORD_TOKEN_DEVOPS', '')}'; "
                    f"os.environ['DEFAULT_SERVER_ID'] = '{os.getenv('DEFAULT_SERVER_ID', '')}'; "
                    f"from discord_mcp import main; main()"
                ],
                "env": {
                    "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN_DEVOPS", ""),
                    "DEFAULT_SERVER_ID": os.getenv("DEFAULT_SERVER_ID", "")
                }
            },
            "chatbot": {
                "name": "chatbot",
                "description": "Agent management tools",
                "command": python_path,
                "args": [str(project_root / "mcp_servers" / "chatbot_server.py")]
            },
            "team": {
                "name": "team",
                "description": "Team coordination tools",
                "command": python_path,
                "args": [str(project_root / "mcp_servers" / "team_server.py")]
            },
            "container": {
                "name": "container",
                "description": "Container and DevOps tools",
                "command": python_path,
                "args": [str(project_root / "mcp_servers" / "container_server.py")]
            }
        }

    async def list_tools_on_server(self, server_name: str) -> Optional[List]:
        """List all tools available on a specific MCP server"""
        try:
            server_config = self.server_configs.get(server_name)
            if not server_config:
                logger.error(f"Unknown server: {server_name}")
                return None

            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env")
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    init_result = await session.initialize()
                    logger.debug(f"Initialized {server_name}: {init_result.serverInfo.name}")

                    # Discover tools
                    tools_response = await session.list_tools()

                    if hasattr(tools_response, 'tools'):
                        tools = []
                        for tool in tools_response.tools:
                            tools.append({
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema or {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            })

                        logger.info(f"Discovered {len(tools)} tools on {server_name} server")
                        return tools
                    else:
                        logger.warning(f"No tools found on {server_name} server")
                        return []

        except Exception as e:
            logger.error(f"Failed to list tools on {server_name}: {e}")
            return None

    async def call_tool_on_server(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Execute a tool on a specific MCP server"""
        try:
            server_config = self.server_configs.get(server_name)
            if not server_config:
                return f"Unknown server: {server_name}"

            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env")
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize session
                    await session.initialize()

                    # Call the tool
                    result = await session.call_tool(tool_name, args)

                    # Extract result content
                    if result and result.content:
                        if isinstance(result.content, list) and result.content:
                            return result.content[0].text
                        else:
                            return str(result.content)
                    else:
                        return f"Tool {tool_name} executed but returned no content"

        except Exception as e:
            logger.error(f"Failed to execute {tool_name} on {server_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def discover_all_tools(self) -> Dict[str, List]:
        """Discover all tools from all MCP servers"""
        all_tools = {}

        for server_name in self.server_configs.keys():
            tools = await self.list_tools_on_server(server_name)
            if tools is not None:
                all_tools[server_name] = tools
            else:
                logger.warning(f"Failed to discover tools on {server_name} server")
                all_tools[server_name] = []

        total_tools = sum(len(tools) for tools in all_tools.values())
        logger.info(f"Discovered {total_tools} total tools across {len(all_tools)} servers")

        return all_tools

    def get_server_for_tool_category(self, category: str) -> str:
        """Map tool categories to appropriate MCP servers"""
        category_mapping = {
            "agent": "chatbot",
            "chatbot": "chatbot",
            "deployment": "chatbot",
            "team": "team",
            "coordination": "team",
            "container": "container",
            "docker": "container",
            "devops": "container",
            "infrastructure": "container"
        }

        return category_mapping.get(category.lower(), "chatbot")  # Default to chatbot server


# Example usage and testing
async def test_mcp_client():
    """Test the MCP tool client"""
    print("🧪 Testing MCP Tool Client")
    print("=" * 50)

    client = MCPToolClient()

    # Test tool discovery
    print("\n1. Discovering all tools...")
    all_tools = await client.discover_all_tools()

    for server_name, tools in all_tools.items():
        print(f"\n📋 {server_name.upper()} SERVER ({len(tools)} tools):")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

    # Test tool execution
    print("\n2. Testing tool execution...")
    if all_tools.get("chatbot"):
        print("  Testing chatbot server...")
        result = await client.call_tool_on_server("chatbot", "list_chatbots", {"include_stopped": True})
        print(f"  Result: {result}")

    print("\n✅ MCP Tool Client test complete")


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
