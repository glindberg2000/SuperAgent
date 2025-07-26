#!/usr/bin/env python3
"""
Real MCP-Based DevOps Agent
Built following MCP_AGENT_REBUILD_GUIDE.md principles
Uses true MCP tool discovery and execution - no hardcoded functions
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Import MCP tool client and base agent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.devops.mcp_tool_client import MCPToolClient
from agents.enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig
from agents.llm_providers import create_llm_provider

# Load environment variables
load_dotenv()

logger = logging.getLogger("real-mcp-devops-agent")


@dataclass
class ToolMapping:
    """Maps user intents to MCP server and tool combinations"""
    server: str
    tool: str
    description: str


class RealMCPDevOpsAgent(EnhancedDiscordAgent):
    """
    Real MCP-based DevOps Agent
    - Discovers tools dynamically from MCP servers
    - Routes tool calls through MCP client (no hardcoded functions)
    - Exposes discovered tools as OpenAI functions for LLM orchestration
    """

    def __init__(self, config: AgentConfig):
        """Initialize real MCP DevOps agent"""

        # Initialize base Discord agent
        super().__init__(config)

        # Initialize MCP tool client
        self.mcp_client = MCPToolClient()

        # Cache discovered tools
        self.discovered_tools = {}
        self.openai_function_definitions = []

        # Tool routing mappings
        self.tool_mappings = self._build_tool_mappings()

        logger.info("🎯 Real MCP DevOps Agent initialized")

    def _build_tool_mappings(self) -> Dict[str, ToolMapping]:
        """Build mappings from common user intents to MCP tools"""
        return {
            # Agent management
            "list_agents": ToolMapping("chatbot", "list_chatbots", "List all available agents"),
            "deploy_agent": ToolMapping("chatbot", "launch_chatbot", "Deploy/launch a new agent"),
            "stop_agent": ToolMapping("chatbot", "stop_chatbot", "Stop a running agent"),
            "restart_agent": ToolMapping("chatbot", "restart_chatbot", "Restart an agent"),
            "agent_status": ToolMapping("chatbot", "get_chatbot_status", "Get agent status"),
            "agent_logs": ToolMapping("chatbot", "get_chatbot_logs", "Get agent logs"),

            # Team management
            "list_teams": ToolMapping("team", "list_teams", "List all teams"),
            "start_team": ToolMapping("team", "start_team", "Start all agents in a team"),
            "stop_team": ToolMapping("team", "stop_team", "Stop all agents in a team"),
            "create_team": ToolMapping("team", "create_team", "Create a new team"),
            "team_status": ToolMapping("team", "get_team_status", "Get team status"),

            # Container management
            "list_containers": ToolMapping("container", "list_containers", "List all containers"),
            "launch_container": ToolMapping("container", "launch_container", "Launch a container"),
            "stop_container": ToolMapping("container", "shutdown_container", "Stop a container"),
            "test_container": ToolMapping("container", "test_container", "Test container functionality")
        }

    async def initialize_mcp_tools(self):
        """Discover and cache all MCP tools at startup"""
        logger.info("🔄 Discovering MCP tools...")

        # Discover all tools from MCP servers
        self.discovered_tools = await self.mcp_client.discover_all_tools()

        # Convert to OpenAI function definitions
        self.openai_function_definitions = self._convert_to_openai_functions()

        total_tools = sum(len(tools) for tools in self.discovered_tools.values())
        logger.info(f"✅ Initialized with {total_tools} MCP tools")

        return total_tools > 0

    def _convert_to_openai_functions(self) -> List[Dict]:
        """Convert discovered MCP tools to OpenAI function definitions"""
        functions = []

        for server_name, tools in self.discovered_tools.items():
            for tool in tools:
                # Create OpenAI function definition
                function_def = {
                    "type": "function",
                    "function": {
                        "name": f"{server_name}_{tool['name']}",
                        "description": f"[{server_name} server] {tool['description']}",
                        "parameters": tool['parameters']
                    }
                }
                functions.append(function_def)

        return functions

    async def process_message(self, message: str, user_id: str = "user") -> str:
        """Process user message using MCP tools and OpenAI function calling"""
        try:
            # Build system prompt
            system_prompt = """
You are a DevOps AI assistant with access to real MCP tools for managing AI agents and infrastructure.

Available capabilities:
- Agent Management: list, deploy, stop, restart agents; get status and logs
- Team Coordination: manage teams of agents working together
- Container Operations: launch, manage, and monitor containers

IMPORTANT:
- Use the available MCP tools to fulfill user requests
- Provide clear, helpful responses based on actual tool results
- If a tool fails, explain the error and suggest alternatives
- Be conversational and informative in your responses
"""

            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]

            # Process with function calling
            return await self._process_with_function_calling(messages)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error processing your request: {str(e)}"

    async def _process_with_function_calling(self, messages: List[Dict]) -> str:
        """Process messages using OpenAI function calling with MCP tool execution"""

        try:
            # Ensure tools are initialized
            if not self.openai_function_definitions:
                await self.initialize_mcp_tools()

            if not self.openai_function_definitions:
                return "❌ No MCP tools available. Please check that MCP servers are running."

            # Tool calling loop
            max_iterations = 3
            for iteration in range(max_iterations):

                # Get LLM response with available tools
                response = await self.llm_provider.generate_response(
                    messages,
                    system_prompt="",  # Already in messages
                    tools=self.openai_function_definitions
                )

                # Handle string responses (errors)
                if isinstance(response, str):
                    return response

                assistant_message = response.choices[0].message

                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": assistant_message.tool_calls
                })

                # If no tool calls, return response
                if not assistant_message.tool_calls:
                    return assistant_message.content or "I couldn't generate a response."

                # Execute tool calls via MCP
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    logger.info(f"🔧 Executing MCP tool: {function_name}")

                    # Execute via MCP client
                    result = await self._execute_mcp_tool(function_name, function_args)

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            return "Reached maximum iterations in conversation loop."

        except Exception as e:
            logger.error(f"Function calling failed: {e}")
            return "I'm having trouble processing your request. Please try again."

    async def _execute_mcp_tool(self, function_name: str, args: Dict[str, Any]) -> str:
        """Execute MCP tool by routing to appropriate server"""
        try:
            # Parse server and tool name
            if '_' not in function_name:
                return f"Invalid function name format: {function_name}"

            server_name, tool_name = function_name.split('_', 1)

            # Validate server exists
            if server_name not in self.discovered_tools:
                return f"Unknown MCP server: {server_name}"

            # Validate tool exists on server
            server_tools = [tool['name'] for tool in self.discovered_tools[server_name]]
            if tool_name not in server_tools:
                return f"Tool '{tool_name}' not found on {server_name} server. Available: {server_tools}"

            # Execute via MCP client
            result = await self.mcp_client.call_tool_on_server(server_name, tool_name, args)

            logger.info(f"✅ MCP tool {function_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to execute MCP tool {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"


# Testing and demonstration
async def test_real_mcp_agent():
    """Test the real MCP DevOps agent"""
    print("🎯 Testing Real MCP DevOps Agent")
    print("=" * 50)

    # Create agent config
    config = AgentConfig(
        name="RealMCPDevOpsAgent",
        bot_token="test",
        server_id="test",
        api_key=os.getenv('OPENAI_API_KEY'),
        llm_type="openai"
    )

    # Initialize agent
    agent = RealMCPDevOpsAgent(config)

    # Initialize MCP tools
    success = await agent.initialize_mcp_tools()
    if not success:
        print("❌ Failed to initialize MCP tools")
        return

    print(f"✅ Agent initialized with {len(agent.openai_function_definitions)} OpenAI functions")

    # Test queries
    test_queries = [
        "What agents are currently available?",
        "Show me the system status",
        "List all teams"
    ]

    for query in test_queries:
        print(f"\n🤔 User: {query}")
        try:
            response = await agent.process_message(query)
            print(f"🤖 Agent: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n✅ Real MCP DevOps Agent test complete")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Test the agent
    asyncio.run(test_real_mcp_agent())
