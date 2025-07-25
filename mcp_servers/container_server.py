#!/usr/bin/env python3
"""
MCP Server for Container Management
Exposes container management tools via MCP protocol
"""

import asyncio
import docker
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContainerServer:
    """MCP Server for container management"""
    
    def __init__(self):
        self.server = Server("container-manager")
        self.docker_client = self._init_docker()
        self._setup_tools()
        
    def _init_docker(self) -> Optional[docker.DockerClient]:
        """Initialize Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            return None
            
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_containers",
                    description="List all Claude Code containers with bot descriptions and status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_stopped": {
                                "type": "boolean",
                                "description": "Include stopped containers",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="launch_container", 
                    description="Launch a Claude Code container with proper Discord token config",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "container_name": {
                                "type": "string",
                                "description": "Name of the container to launch"
                            },
                            "preserve_auth": {
                                "type": "boolean", 
                                "description": "Preserve Claude Code authentication if exists",
                                "default": True
                            }
                        },
                        "required": ["container_name"]
                    }
                ),
                Tool(
                    name="shutdown_container",
                    description="Stop a container, optionally remove it",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "container_name": {
                                "type": "string",
                                "description": "Name of the container to shutdown"
                            },
                            "remove": {
                                "type": "boolean",
                                "description": "Remove container after stopping",
                                "default": False
                            }
                        },
                        "required": ["container_name"]
                    }
                ),
                Tool(
                    name="test_container",
                    description="Test container functionality including Claude Code and Discord MCP",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "container_name": {
                                "type": "string",
                                "description": "Name of the container to test"
                            }
                        },
                        "required": ["container_name"]
                    }
                ),
                Tool(
                    name="get_container_config",
                    description="Get detailed container configuration including Discord token mapping",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "container_name": {
                                "type": "string", 
                                "description": "Name of the container"
                            }
                        },
                        "required": ["container_name"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            if name == "list_containers":
                result = await self._list_containers(arguments.get("include_stopped", False))
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "launch_container":
                result = await self._launch_container(
                    arguments["container_name"],
                    arguments.get("preserve_auth", True)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "shutdown_container":
                result = await self._shutdown_container(
                    arguments["container_name"],
                    arguments.get("remove", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "test_container":
                result = await self._test_container(arguments["container_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "get_container_config":
                result = await self._get_container_config(arguments["container_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
    async def _list_containers(self, include_stopped: bool) -> Dict[str, Any]:
        """List containers implementation"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available", "containers": []}
            
        try:
            containers = []
            token_registry = {
                "claude-isolated-discord": "DISCORD_TOKEN_CODERDEV1",
                "claude-fullstackdev-persistent": "DISCORD_TOKEN_CODERDEV2",
            }
            
            for container in self.docker_client.containers.list(all=include_stopped):
                labels = container.labels
                
                # Only include SuperAgent containers
                if "superagent.type" not in labels:
                    continue
                    
                container_info = {
                    "name": container.name,
                    "id": container.short_id,
                    "status": container.status,
                    "bot_identity": labels.get("superagent.agent", "Unknown"),
                    "discord_token_env": token_registry.get(container.name, "Unknown"),
                    "team": labels.get("superagent.team", "default"),
                    "type": labels.get("superagent.type", "unknown"),
                    "created": container.attrs['Created']
                }
                
                containers.append(container_info)
                
            return {"success": True, "containers": containers}
            
        except Exception as e:
            return {"success": False, "error": str(e), "containers": []}
            
    async def _launch_container(self, container_name: str, preserve_auth: bool) -> Dict[str, Any]:
        """Launch container implementation"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}
            
        try:
            # Check if container exists
            try:
                container = self.docker_client.containers.get(container_name)
                if container.status == "running":
                    return {"success": True, "message": f"Container {container_name} already running"}
                else:
                    container.start()
                    return {"success": True, "message": f"Started existing container {container_name}"}
            except docker.errors.NotFound:
                pass
                
            # For new containers, use the startup script
            # This ensures proper configuration and auth preservation
            script_path = Path(__file__).parent.parent / "start_claude_container.sh"
            if script_path.exists():
                import subprocess
                result = subprocess.run([str(script_path), container_name], capture_output=True, text=True)
                if result.returncode == 0:
                    return {"success": True, "message": f"Created container {container_name}"}
                else:
                    return {"success": False, "error": result.stderr}
            else:
                return {"success": False, "error": "Container startup script not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _shutdown_container(self, container_name: str, remove: bool) -> Dict[str, Any]:
        """Shutdown container implementation"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}
            
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=10)
            
            if remove:
                container.remove()
                return {"success": True, "message": f"Container {container_name} stopped and removed"}
            else:
                return {"success": True, "message": f"Container {container_name} stopped"}
                
        except docker.errors.NotFound:
            return {"success": False, "error": f"Container {container_name} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _test_container(self, container_name: str) -> Dict[str, Any]:
        """Test container implementation"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}
            
        try:
            container = self.docker_client.containers.get(container_name)
            
            if container.status != "running":
                return {"success": False, "error": "Container not running"}
                
            tests = {
                "claude_code": False,
                "mcp_connection": False,
                "discord_connection": False
            }
            
            # Test Claude Code
            result = container.exec_run("claude --version", user="node")
            if result.exit_code == 0 and b"Claude Code" in result.output:
                tests["claude_code"] = True
                
            # Test MCP
            result = container.exec_run("claude mcp list", user="node")
            if result.exit_code == 0:
                tests["mcp_connection"] = True
                if b"Connected" in result.output:
                    tests["discord_connection"] = True
                    
            return {"success": True, "tests": tests}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _get_container_config(self, container_name: str) -> Dict[str, Any]:
        """Get container config implementation"""
        try:
            config_path = Path(__file__).parent.parent / "claude_container_config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            container_config = config.get("containers", {}).get(container_name, {})
            
            # Add runtime status if container exists
            if self.docker_client:
                try:
                    container = self.docker_client.containers.get(container_name)
                    container_config["runtime_status"] = container.status
                except docker.errors.NotFound:
                    container_config["runtime_status"] = "not_created"
                    
            return {"success": True, "config": container_config}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server._get_capabilities()
            )


if __name__ == "__main__":
    server = ContainerServer()
    asyncio.run(server.run())