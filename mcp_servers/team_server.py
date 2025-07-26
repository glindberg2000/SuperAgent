#!/usr/bin/env python3
"""
MCP Server for Team Management
Provides comprehensive team orchestration and management functionality
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TeamServer:
    """MCP Server for team management and orchestration"""
    
    def __init__(self):
        self.server = Server("team-manager")
        self.config = self._load_team_config()
        self.chatbot_server_script = Path(__file__).parent / "chatbot_server.py"
        self._setup_tools()
        
    def _load_team_config(self) -> Dict[str, Any]:
        """Load team and agent configuration"""
        config_files = [
            "agent_config.json",
            "agent_config_hybrid.json", 
            "agent_configs_mvp.json"
        ]
        
        # Try to load the most comprehensive config
        for config_file in config_files:
            config_path = Path(__file__).parent.parent / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        logger.info(f"Loaded team config from {config_file}")
                        return config
                except Exception as e:
                    logger.warning(f"Failed to load {config_file}: {e}")
                    
        # Default minimal config if no files found
        return {
            "agents": {},
            "teams": {},
            "global_settings": {}
        }
        
    def _save_team_config(self, config: Dict[str, Any]) -> bool:
        """Save updated configuration back to file"""
        try:
            config_path = Path(__file__).parent.parent / "agent_config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.config = config  # Update in-memory config
            logger.info("Team configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save team config: {e}")
            return False
            
    async def _get_chatbot_client(self):
        """Get a client connection to the chatbot server"""
        server_params = StdioServerParameters(
            command="python",
            args=[str(self.chatbot_server_script)]
        )
        return stdio_client(server_params)
        
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_teams",
                    description="List all teams with their members and status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_inactive": {
                                "type": "boolean",
                                "description": "Include teams with no running members",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="start_team",
                    description="Start all agents in a team (parallel or sequential)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team to start"
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["parallel", "sequential"],
                                "description": "Launch mode (parallel=all at once, sequential=one by one)",
                                "default": "parallel"
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="stop_team",
                    description="Stop all agents in a team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team to stop"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force kill all team members",
                                "default": False
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="restart_team",
                    description="Restart all agents in a team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team to restart"
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="get_team_status",
                    description="Get detailed status and health metrics for a team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team"
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="add_team_member",
                    description="Add an agent to an existing team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team"
                            },
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent to add"
                            }
                        },
                        "required": ["team_name", "agent_name"]
                    }
                ),
                Tool(
                    name="remove_team_member",
                    description="Remove an agent from a team",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team"
                            },
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent to remove"
                            },
                            "stop_agent": {
                                "type": "boolean",
                                "description": "Stop the agent when removing from team",
                                "default": False
                            }
                        },
                        "required": ["team_name", "agent_name"]
                    }
                ),
                Tool(
                    name="create_team",
                    description="Create a new team with specified configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the new team"
                            },
                            "display_name": {
                                "type": "string",
                                "description": "Display name for the team"
                            },
                            "description": {
                                "type": "string",
                                "description": "Team description"
                            },
                            "agents": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of agent names for the team"
                            },
                            "coordination_mode": {
                                "type": "string",
                                "enum": ["parallel", "sequential", "collaborative"],
                                "description": "How team members coordinate",
                                "default": "parallel"
                            },
                            "auto_deploy": {
                                "type": "boolean",
                                "description": "Auto-start team on system startup",
                                "default": False
                            }
                        },
                        "required": ["team_name", "display_name", "agents"]
                    }
                ),
                Tool(
                    name="delete_team",
                    description="Delete a team (stops all members first)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team to delete"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force delete even if members are running",
                                "default": False
                            }
                        },
                        "required": ["team_name"]
                    }
                ),
                Tool(
                    name="get_team_logs",
                    description="Get aggregated logs from all team members",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "team_name": {
                                "type": "string",
                                "description": "Name of the team"
                            },
                            "lines": {
                                "type": "integer",
                                "description": "Number of log lines per member",
                                "default": 20
                            },
                            "merge": {
                                "type": "boolean",
                                "description": "Merge logs by timestamp",
                                "default": False
                            }
                        },
                        "required": ["team_name"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            if name == "list_teams":
                result = await self._list_teams(arguments.get("include_inactive", True))
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "start_team":
                result = await self._start_team(
                    arguments["team_name"],
                    arguments.get("mode", "parallel")
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "stop_team":
                result = await self._stop_team(
                    arguments["team_name"],
                    arguments.get("force", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "restart_team":
                result = await self._restart_team(arguments["team_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "get_team_status":
                result = await self._get_team_status(arguments["team_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "add_team_member":
                result = await self._add_team_member(
                    arguments["team_name"],
                    arguments["agent_name"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "remove_team_member":
                result = await self._remove_team_member(
                    arguments["team_name"],
                    arguments["agent_name"],
                    arguments.get("stop_agent", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "create_team":
                result = await self._create_team(
                    arguments["team_name"],
                    arguments["display_name"],
                    arguments.get("description", ""),
                    arguments["agents"],
                    arguments.get("coordination_mode", "parallel"),
                    arguments.get("auto_deploy", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "delete_team":
                result = await self._delete_team(
                    arguments["team_name"],
                    arguments.get("force", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "get_team_logs":
                result = await self._get_team_logs(
                    arguments["team_name"],
                    arguments.get("lines", 20),
                    arguments.get("merge", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
    async def _list_teams(self, include_inactive: bool) -> Dict[str, Any]:
        """List all teams with member status"""
        try:
            teams_config = self.config.get("teams", {})
            teams_list = []
            
            # Get agent status from chatbot server  
            agent_statuses = {}
            try:
                async with self._get_chatbot_client() as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        # Get all agent statuses
                        agents_result = await session.call_tool("list_chatbots", {"include_stopped": True})
                        agents_data = json.loads(agents_result.content[0].text)
                        agent_statuses = {a["name"]: a for a in agents_data.get("chatbots", [])}
            except Exception as e:
                logger.warning(f"Could not connect to chatbot server: {e}")
                # Use default status for all agents
                agents_config = self.config.get("agents", {})
                agent_statuses = {name: {"status": "unknown"} for name in agents_config.keys()}
                    
            # Build team information
            for team_name, team_config in teams_config.items():
                team_agents = team_config.get("agents", [])
                running_count = 0
                member_details = []
                
                for agent_name in team_agents:
                    agent_info = agent_statuses.get(agent_name, {"status": "unknown"})
                    if agent_info["status"] == "running":
                        running_count += 1
                        
                    member_details.append({
                        "name": agent_name,
                        "status": agent_info["status"],
                        "pid": agent_info.get("pid"),
                        "memory_mb": agent_info.get("memory_mb"),
                        "uptime": agent_info.get("uptime")
                    })
                    
                team_info = {
                    "name": team_name,
                    "display_name": team_config.get("name", team_name),
                    "description": team_config.get("description", ""),
                    "total_members": len(team_agents),
                    "running_members": running_count,
                    "coordination_mode": team_config.get("coordination_mode", "parallel"),
                    "auto_deploy": team_config.get("auto_deploy", False),
                    "members": member_details
                }
                
                if include_inactive or running_count > 0:
                    teams_list.append(team_info)
                    
            return {
                "success": True,
                "teams": teams_list,
                "total_teams": len(teams_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return {"success": False, "error": str(e), "teams": []}
            
    async def _start_team(self, team_name: str, mode: str) -> Dict[str, Any]:
        """Start all agents in a team"""
        try:
            teams_config = self.config.get("teams", {})
            if team_name not in teams_config:
                available = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available}"
                }
                
            team_config = teams_config[team_name]
            team_agents = team_config.get("agents", [])
            
            if not team_agents:
                return {
                    "success": False,
                    "error": f"Team {team_name} has no members"
                }
                
            results = []
            async with self._get_chatbot_client() as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    if mode == "sequential":
                        # Start agents one by one
                        for agent_name in team_agents:
                            result = await session.call_tool("launch_chatbot", {
                                "agent_name": agent_name,
                                "background": True
                            })
                            agent_result = json.loads(result.content[0].text)
                            results.append({
                                "agent": agent_name,
                                "success": agent_result["success"],
                                "message": agent_result.get("message", agent_result.get("error"))
                            })
                            
                            # Wait between sequential starts
                            if agent_result["success"]:
                                await asyncio.sleep(2)
                    else:
                        # Start all agents in parallel
                        tasks = []
                        for agent_name in team_agents:
                            task = session.call_tool("launch_chatbot", {
                                "agent_name": agent_name,
                                "background": True
                            })
                            tasks.append((agent_name, task))
                            
                        # Wait for all to complete
                        for agent_name, task in tasks:
                            result = await task
                            agent_result = json.loads(result.content[0].text)
                            results.append({
                                "agent": agent_name,
                                "success": agent_result["success"],
                                "message": agent_result.get("message", agent_result.get("error"))
                            })
                            
            successful = sum(1 for r in results if r["success"])
            return {
                "success": successful > 0,
                "message": f"Started {successful}/{len(team_agents)} agents in team {team_name}",
                "team_name": team_name,
                "mode": mode,
                "results": results,
                "started_count": successful,
                "total_count": len(team_agents)
            }
            
        except Exception as e:
            logger.error(f"Failed to start team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _stop_team(self, team_name: str, force: bool) -> Dict[str, Any]:
        """Stop all agents in a team"""
        try:
            teams_config = self.config.get("teams", {})
            if team_name not in teams_config:
                available = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available}"
                }
                
            team_config = teams_config[team_name]
            team_agents = team_config.get("agents", [])
            
            if not team_agents:
                return {
                    "success": False,
                    "error": f"Team {team_name} has no members"
                }
                
            results = []
            async with self._get_chatbot_client() as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Stop all agents in parallel
                    tasks = []
                    for agent_name in team_agents:
                        task = session.call_tool("stop_chatbot", {
                            "agent_name": agent_name,
                            "force": force
                        })
                        tasks.append((agent_name, task))
                        
                    # Wait for all to complete
                    for agent_name, task in tasks:
                        result = await task
                        agent_result = json.loads(result.content[0].text)
                        results.append({
                            "agent": agent_name,
                            "success": agent_result["success"],
                            "message": agent_result.get("message", agent_result.get("error"))
                        })
                        
            successful = sum(1 for r in results if r["success"])
            return {
                "success": True,  # Team stop is successful if any agents were stopped
                "message": f"Stopped {successful}/{len(team_agents)} agents in team {team_name}",
                "team_name": team_name,
                "force": force,
                "results": results,
                "stopped_count": successful,
                "total_count": len(team_agents)
            }
            
        except Exception as e:
            logger.error(f"Failed to stop team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _restart_team(self, team_name: str) -> Dict[str, Any]:
        """Restart all agents in a team"""
        try:
            # Stop team first
            stop_result = await self._stop_team(team_name, force=False)
            
            if not stop_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to stop team {team_name}: {stop_result.get('error')}",
                    "stop_result": stop_result
                }
                
            # Wait a moment for cleanup
            await asyncio.sleep(3)
            
            # Start team again
            start_result = await self._start_team(team_name, "parallel")
            
            return {
                "success": start_result["success"],
                "message": f"Restarted team {team_name}",
                "team_name": team_name,
                "stop_result": stop_result,
                "start_result": start_result
            }
            
        except Exception as e:
            logger.error(f"Failed to restart team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_team_status(self, team_name: str) -> Dict[str, Any]:
        """Get detailed team status and health metrics"""
        try:
            teams_config = self.config.get("teams", {})
            if team_name not in teams_config:
                available = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available}"
                }
                
            team_config = teams_config[team_name]
            team_agents = team_config.get("agents", [])
            
            # Get detailed status for each agent
            member_statuses = []
            total_memory = 0
            running_count = 0
            
            async with self._get_chatbot_client() as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for agent_name in team_agents:
                        result = await session.call_tool("get_chatbot_status", {
                            "agent_name": agent_name
                        })
                        agent_result = json.loads(result.content[0].text)
                        
                        if agent_result["success"]:
                            status = agent_result["status"]
                            config = agent_result["config"]
                            
                            member_info = {
                                "name": agent_name,
                                "display_name": config.get("name", agent_name),
                                "status": status.get("status", "unknown"),
                                "llm_type": config.get("llm_type", "unknown"),
                                "pid": status.get("pid"),
                                "uptime": status.get("uptime"),
                                "memory_mb": status.get("memory_mb", 0),
                                "cpu_percent": status.get("cpu_percent", 0)
                            }
                            
                            if status.get("status") == "running":
                                running_count += 1
                                total_memory += status.get("memory_mb", 0)
                        else:
                            member_info = {
                                "name": agent_name,
                                "status": "error",
                                "error": agent_result.get("error")
                            }
                            
                        member_statuses.append(member_info)
                        
            # Calculate team health
            health_percentage = (running_count / len(team_agents) * 100) if team_agents else 0
            
            return {
                "success": True,
                "team_name": team_name,
                "team_config": team_config,
                "health": {
                    "percentage": round(health_percentage, 1),
                    "running_members": running_count,
                    "total_members": len(team_agents),
                    "total_memory_mb": total_memory,
                    "status": "healthy" if health_percentage >= 80 else "degraded" if health_percentage > 0 else "down"
                },
                "members": member_statuses
            }
            
        except Exception as e:
            logger.error(f"Failed to get team status for {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _add_team_member(self, team_name: str, agent_name: str) -> Dict[str, Any]:
        """Add an agent to a team"""
        try:
            teams_config = self.config.get("teams", {})
            agents_config = self.config.get("agents", {})
            
            if team_name not in teams_config:
                available_teams = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available_teams}"
                }
                
            if agent_name not in agents_config:
                available_agents = list(agents_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown agent: {agent_name}. Available: {available_agents}"
                }
                
            team_agents = teams_config[team_name].get("agents", [])
            
            if agent_name in team_agents:
                return {
                    "success": False,
                    "error": f"Agent {agent_name} is already a member of team {team_name}"
                }
                
            # Add agent to team
            updated_config = self.config.copy()
            updated_config["teams"][team_name]["agents"].append(agent_name)
            
            # Save configuration
            if self._save_team_config(updated_config):
                return {
                    "success": True,
                    "message": f"Added agent {agent_name} to team {team_name}",
                    "team_name": team_name,
                    "agent_name": agent_name,
                    "new_member_count": len(updated_config["teams"][team_name]["agents"])
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save configuration"
                }
                
        except Exception as e:
            logger.error(f"Failed to add {agent_name} to team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _remove_team_member(self, team_name: str, agent_name: str, stop_agent: bool) -> Dict[str, Any]:
        """Remove an agent from a team"""
        try:
            teams_config = self.config.get("teams", {})
            
            if team_name not in teams_config:
                available_teams = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available_teams}"
                }
                
            team_agents = teams_config[team_name].get("agents", [])
            
            if agent_name not in team_agents:
                return {
                    "success": False,
                    "error": f"Agent {agent_name} is not a member of team {team_name}"
                }
                
            # Stop agent if requested
            stop_result = None
            if stop_agent:
                async with self._get_chatbot_client() as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool("stop_chatbot", {
                            "agent_name": agent_name,
                            "force": False
                        })
                        stop_result = json.loads(result.content[0].text)
                        
            # Remove agent from team
            updated_config = self.config.copy()
            updated_config["teams"][team_name]["agents"].remove(agent_name)
            
            # Save configuration
            if self._save_team_config(updated_config):
                return {
                    "success": True,
                    "message": f"Removed agent {agent_name} from team {team_name}",
                    "team_name": team_name,
                    "agent_name": agent_name,
                    "new_member_count": len(updated_config["teams"][team_name]["agents"]),
                    "stop_result": stop_result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save configuration"
                }
                
        except Exception as e:
            logger.error(f"Failed to remove {agent_name} from team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _create_team(self, team_name: str, display_name: str, description: str, 
                          agents: List[str], coordination_mode: str, auto_deploy: bool) -> Dict[str, Any]:
        """Create a new team"""
        try:
            teams_config = self.config.get("teams", {})
            agents_config = self.config.get("agents", {})
            
            if team_name in teams_config:
                return {
                    "success": False,
                    "error": f"Team {team_name} already exists"
                }
                
            # Validate all agents exist
            invalid_agents = [a for a in agents if a not in agents_config]
            if invalid_agents:
                available_agents = list(agents_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown agents: {invalid_agents}. Available: {available_agents}"
                }
                
            # Create team configuration
            team_config = {
                "name": display_name,
                "description": description,
                "agents": agents,
                "coordination_mode": coordination_mode,
                "auto_deploy": auto_deploy,
                "default_server_id": self.config.get("global_settings", {}).get("default_server_id", ""),
                "gm_channel": self.config.get("global_settings", {}).get("gm_channel", "")
            }
            
            # Add team to configuration
            updated_config = self.config.copy()
            updated_config["teams"][team_name] = team_config
            
            # Save configuration
            if self._save_team_config(updated_config):
                return {
                    "success": True,
                    "message": f"Created team {team_name} with {len(agents)} members",
                    "team_name": team_name,
                    "team_config": team_config
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save configuration"
                }
                
        except Exception as e:
            logger.error(f"Failed to create team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _delete_team(self, team_name: str, force: bool) -> Dict[str, Any]:
        """Delete a team"""
        try:
            teams_config = self.config.get("teams", {})
            
            if team_name not in teams_config:
                available_teams = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available_teams}"
                }
                
            # Check if team has running members
            if not force:
                status_result = await self._get_team_status(team_name)
                if status_result["success"]:
                    running_count = status_result["health"]["running_members"]
                    if running_count > 0:
                        return {
                            "success": False,
                            "error": f"Team {team_name} has {running_count} running members. Stop them first or use force=true"
                        }
                        
            # Stop all team members if force is used
            stop_result = None
            if force:
                stop_result = await self._stop_team(team_name, force=True)
                
            # Remove team from configuration
            updated_config = self.config.copy()
            del updated_config["teams"][team_name]
            
            # Save configuration
            if self._save_team_config(updated_config):
                return {
                    "success": True,
                    "message": f"Deleted team {team_name}",
                    "team_name": team_name,
                    "stop_result": stop_result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save configuration"
                }
                
        except Exception as e:
            logger.error(f"Failed to delete team {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_team_logs(self, team_name: str, lines: int, merge: bool) -> Dict[str, Any]:
        """Get aggregated logs from all team members"""
        try:
            teams_config = self.config.get("teams", {})
            if team_name not in teams_config:
                available_teams = list(teams_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown team: {team_name}. Available: {available_teams}"
                }
                
            team_config = teams_config[team_name]
            team_agents = team_config.get("agents", [])
            
            if not team_agents:
                return {
                    "success": False,
                    "error": f"Team {team_name} has no members"
                }
                
            # Get logs from all team members
            member_logs = []
            
            async with self._get_chatbot_client() as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    for agent_name in team_agents:
                        result = await session.call_tool("get_chatbot_logs", {
                            "agent_name": agent_name,
                            "lines": lines
                        })
                        log_result = json.loads(result.content[0].text)
                        
                        member_logs.append({
                            "agent": agent_name,
                            "success": log_result["success"],
                            "logs": log_result.get("logs", ""),
                            "log_file": log_result.get("log_file", ""),
                            "lines_returned": log_result.get("lines_returned", 0),
                            "error": log_result.get("error")
                        })
                        
            if merge:
                # TODO: Implement timestamp-based log merging
                # For now, just concatenate logs
                merged_logs = ""
                for member in member_logs:
                    if member["success"] and member["logs"]:
                        merged_logs += f"\n=== {member['agent']} ===\n"
                        merged_logs += member["logs"]
                        
                return {
                    "success": True,
                    "team_name": team_name,
                    "merged_logs": merged_logs,
                    "member_count": len(team_agents),
                    "lines_per_member": lines
                }
            else:
                return {
                    "success": True,
                    "team_name": team_name,
                    "member_logs": member_logs,
                    "member_count": len(team_agents),
                    "lines_per_member": lines
                }
                
        except Exception as e:
            logger.error(f"Failed to get team logs for {team_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


if __name__ == "__main__":
    server = TeamServer()
    asyncio.run(server.run())