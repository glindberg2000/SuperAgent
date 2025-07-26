#!/usr/bin/env python3
"""
MCP Server for Chatbot Management
Provides comprehensive chatbot management functionality for Python Discord agents
"""

import asyncio
import json
import logging
import os
import subprocess
import psutil
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatbotServer:
    """MCP Server for chatbot management"""
    
    def __init__(self):
        self.server = Server("chatbot-manager")
        self.processes = {}  # Store running processes
        self.config = self._load_chatbot_config()
        self._setup_tools()
        
    def _load_chatbot_config(self) -> Dict[str, Any]:
        """Load chatbot configuration"""
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
                        logger.info(f"Loaded chatbot config from {config_file}")
                        return config
                except Exception as e:
                    logger.warning(f"Failed to load {config_file}: {e}")
                    
        # Default config if no files found
        return {
            "agents": {
                "grok4_agent": {
                    "name": "Grok4Agent",
                    "script": "enhanced_discord_agent.py",
                    "llm_type": "grok4",
                    "discord_token_env": "DISCORD_TOKEN_GROK4",
                    "personality": "Research and analysis expert with live search"
                },
                "gemini_agent": {
                    "name": "GeminiAgent", 
                    "script": "enhanced_discord_agent.py",
                    "llm_type": "gemini",
                    "discord_token_env": "DISCORD_TOKEN_GEMINI",
                    "personality": "Creative tasks and multimodal analysis"
                }
            }
        }
        
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_chatbots",
                    description="List all available chatbots with their status and configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_stopped": {
                                "type": "boolean",
                                "description": "Include stopped/available chatbots",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="launch_chatbot",
                    description="Launch a chatbot agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the chatbot agent to launch"
                            },
                            "background": {
                                "type": "boolean",
                                "description": "Run in background (detached)",
                                "default": True
                            }
                        },
                        "required": ["agent_name"]
                    }
                ),
                Tool(
                    name="stop_chatbot",
                    description="Stop a running chatbot agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the chatbot agent to stop"
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force kill the process",
                                "default": False
                            }
                        },
                        "required": ["agent_name"]
                    }
                ),
                Tool(
                    name="restart_chatbot",
                    description="Restart a chatbot agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string", 
                                "description": "Name of the chatbot agent to restart"
                            }
                        },
                        "required": ["agent_name"]
                    }
                ),
                Tool(
                    name="get_chatbot_status",
                    description="Get detailed status of a specific chatbot",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the chatbot agent"
                            }
                        },
                        "required": ["agent_name"]
                    }
                ),
                Tool(
                    name="get_chatbot_logs",
                    description="Get recent logs from a chatbot agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the chatbot agent"
                            },
                            "lines": {
                                "type": "integer",
                                "description": "Number of log lines to retrieve",
                                "default": 50
                            }
                        },
                        "required": ["agent_name"]
                    }
                )
            ]
            
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            if name == "list_chatbots":
                result = await self._list_chatbots(arguments.get("include_stopped", True))
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "launch_chatbot":
                result = await self._launch_chatbot(
                    arguments["agent_name"],
                    arguments.get("background", True)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "stop_chatbot":
                result = await self._stop_chatbot(
                    arguments["agent_name"],
                    arguments.get("force", False)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "restart_chatbot":
                result = await self._restart_chatbot(arguments["agent_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "get_chatbot_status":
                result = await self._get_chatbot_status(arguments["agent_name"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "get_chatbot_logs":
                result = await self._get_chatbot_logs(
                    arguments["agent_name"],
                    arguments.get("lines", 50)
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
                
    async def _list_chatbots(self, include_stopped: bool) -> Dict[str, Any]:
        """List all chatbots with their status"""
        try:
            chatbots = []
            agents_config = self.config.get("agents", {})
            
            for agent_name, agent_config in agents_config.items():
                # Get runtime status
                status = await self._get_process_status(agent_name)
                
                chatbot_info = {
                    "name": agent_name,
                    "display_name": agent_config.get("name", agent_name),
                    "status": status["status"],
                    "llm_type": agent_config.get("llm_type", "unknown"),
                    "discord_token_env": agent_config.get("discord_token_env", "unknown"),
                    "personality": agent_config.get("personality", ""),
                    "script": agent_config.get("script", "enhanced_discord_agent.py"),
                    "pid": status.get("pid"),
                    "uptime": status.get("uptime"),
                    "memory_mb": status.get("memory_mb"),
                    "cpu_percent": status.get("cpu_percent")
                }
                
                if include_stopped or status["status"] == "running":
                    chatbots.append(chatbot_info)
                    
            return {
                "success": True,
                "chatbots": chatbots,
                "total": len(chatbots)
            }
            
        except Exception as e:
            logger.error(f"Failed to list chatbots: {e}")
            return {"success": False, "error": str(e), "chatbots": []}
            
    async def _launch_chatbot(self, agent_name: str, background: bool) -> Dict[str, Any]:
        """Launch a chatbot agent"""
        try:
            # Check if already running
            status = await self._get_process_status(agent_name)
            if status["status"] == "running":
                return {
                    "success": True,
                    "message": f"Chatbot {agent_name} is already running",
                    "pid": status.get("pid")
                }
                
            # Get agent configuration
            agents_config = self.config.get("agents", {})
            if agent_name not in agents_config:
                available = list(agents_config.keys())
                return {
                    "success": False,
                    "error": f"Unknown agent: {agent_name}. Available: {available}"
                }
                
            agent_config = agents_config[agent_name]
            script = agent_config.get("script", "enhanced_discord_agent.py")
            script_path = Path(__file__).parent.parent / script
            
            if not script_path.exists():
                return {
                    "success": False,
                    "error": f"Script not found: {script_path}"
                }
                
            # Prepare environment variables
            env = os.environ.copy()
            
            # Set agent-specific environment variables
            env["AGENT_NAME"] = agent_name
            env["AGENT_TYPE"] = agent_config.get("llm_type", "grok4")
            env["AGENT_PERSONALITY"] = agent_config.get("personality", "")
            
            # Check Discord token
            discord_token_env = agent_config.get("discord_token_env")
            if discord_token_env and discord_token_env in env:
                logger.info(f"Using Discord token: {discord_token_env}")
            else:
                logger.warning(f"Discord token {discord_token_env} not found in environment")
                
            # Create logs directory
            logs_dir = Path(__file__).parent.parent / "logs" / agent_name
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / f"{agent_name}.log"
            
            # Launch process
            if background:
                # Run in background with log redirection
                with open(log_file, "a") as f:
                    process = subprocess.Popen([
                        "python", str(script_path)
                    ], 
                    env=env,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=script_path.parent
                    )
                    
                self.processes[agent_name] = process
                logger.info(f"Started {agent_name} with PID {process.pid}")
                
                return {
                    "success": True,
                    "message": f"Launched chatbot {agent_name}",
                    "pid": process.pid,
                    "log_file": str(log_file)
                }
            else:
                # Run in foreground (for testing)
                result = subprocess.run([
                    "python", str(script_path)
                ], env=env, capture_output=True, text=True, cwd=script_path.parent)
                
                return {
                    "success": result.returncode == 0,
                    "message": f"Executed {agent_name}",
                    "stdout": result.stdout[-1000:],  # Last 1000 chars
                    "stderr": result.stderr[-1000:] if result.stderr else None
                }
                
        except Exception as e:
            logger.error(f"Failed to launch chatbot {agent_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _stop_chatbot(self, agent_name: str, force: bool) -> Dict[str, Any]:
        """Stop a chatbot agent"""
        try:
            # Check if we have the process
            if agent_name in self.processes:
                process = self.processes[agent_name]
                if process.poll() is None:  # Still running
                    if force:
                        process.kill()
                    else:
                        process.terminate()
                    
                    # Wait for termination
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        if not force:
                            process.kill()
                            process.wait(timeout=5)
                            
                    del self.processes[agent_name]
                    return {
                        "success": True,
                        "message": f"Stopped chatbot {agent_name}"
                    }
                    
            # Look for process by name pattern
            killed_pids = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if (cmdline and 
                        'python' in cmdline[0] and 
                        any(agent_name in arg for arg in cmdline)):
                        
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        killed_pids.append(proc.info['pid'])
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            if killed_pids:
                return {
                    "success": True,
                    "message": f"Stopped chatbot {agent_name}",
                    "killed_pids": killed_pids
                }
            else:
                return {
                    "success": False,
                    "error": f"No running process found for {agent_name}"
                }
                
        except Exception as e:
            logger.error(f"Failed to stop chatbot {agent_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _restart_chatbot(self, agent_name: str) -> Dict[str, Any]:
        """Restart a chatbot agent"""
        try:
            # Stop first
            stop_result = await self._stop_chatbot(agent_name, force=False)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Start again
            start_result = await self._launch_chatbot(agent_name, background=True)
            
            return {
                "success": start_result["success"],
                "message": f"Restarted chatbot {agent_name}",
                "stop_result": stop_result,
                "start_result": start_result
            }
            
        except Exception as e:
            logger.error(f"Failed to restart chatbot {agent_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_chatbot_status(self, agent_name: str) -> Dict[str, Any]:
        """Get detailed status of a chatbot"""
        try:
            # Get process status
            status = await self._get_process_status(agent_name)
            
            # Get configuration
            agent_config = self.config.get("agents", {}).get(agent_name, {})
            
            # Get log file info
            logs_dir = Path(__file__).parent.parent / "logs" / agent_name
            log_file = logs_dir / f"{agent_name}.log"
            log_info = None
            
            if log_file.exists():
                stat = log_file.stat()
                log_info = {
                    "path": str(log_file),
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                
            return {
                "success": True,
                "agent_name": agent_name,
                "config": agent_config,
                "status": status,
                "log_info": log_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for {agent_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_chatbot_logs(self, agent_name: str, lines: int) -> Dict[str, Any]:
        """Get recent logs from a chatbot"""
        try:
            logs_dir = Path(__file__).parent.parent / "logs" / agent_name
            log_file = logs_dir / f"{agent_name}.log"
            
            if not log_file.exists():
                return {
                    "success": False,
                    "error": f"Log file not found: {log_file}"
                }
                
            # Read last N lines
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
            return {
                "success": True,
                "agent_name": agent_name,
                "log_file": str(log_file),
                "lines_requested": lines,
                "lines_returned": len(recent_lines),
                "logs": "".join(recent_lines)
            }
            
        except Exception as e:
            logger.error(f"Failed to get logs for {agent_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _get_process_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a process"""
        try:
            # Check our tracked processes first
            if agent_name in self.processes:
                process = self.processes[agent_name]
                if process.poll() is None:  # Still running
                    try:
                        ps_process = psutil.Process(process.pid)
                        return {
                            "status": "running",
                            "pid": process.pid,
                            "uptime": self._calculate_uptime(ps_process.create_time()),
                            "memory_mb": round(ps_process.memory_info().rss / 1024 / 1024, 1),
                            "cpu_percent": ps_process.cpu_percent()
                        }
                    except psutil.NoSuchProcess:
                        del self.processes[agent_name]
                        
            # Look for process by command line pattern
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline = proc.info['cmdline']
                    if (cmdline and 
                        'python' in cmdline[0] and 
                        any(agent_name in arg for arg in cmdline)):
                        
                        ps_process = psutil.Process(proc.info['pid'])
                        return {
                            "status": "running",
                            "pid": proc.info['pid'],
                            "uptime": self._calculate_uptime(proc.info['create_time']),
                            "memory_mb": round(ps_process.memory_info().rss / 1024 / 1024, 1),
                            "cpu_percent": ps_process.cpu_percent()
                        }
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            return {"status": "stopped"}
            
        except Exception as e:
            logger.error(f"Failed to get process status for {agent_name}: {e}")
            return {"status": "error", "error": str(e)}
            
    def _calculate_uptime(self, create_time: float) -> str:
        """Calculate process uptime"""
        try:
            uptime_seconds = datetime.now().timestamp() - create_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "unknown"
            
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


if __name__ == "__main__":
    server = ChatbotServer()
    asyncio.run(server.run())