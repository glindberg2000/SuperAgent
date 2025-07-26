#!/usr/bin/env python3
"""
MCP Container Management Tools Backend
Provides comprehensive container management functionality for Claude Code containers
"""

import asyncio
import docker
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPContainerManager:
    """Backend implementation for MCP container management tools"""
    
    def __init__(self):
        self.docker_client = self._init_docker()
        self.config = self._load_container_config()
        self.token_registry = self._load_token_registry()
        
    def _init_docker(self) -> Optional[docker.DockerClient]:
        """Initialize Docker client"""
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            return None
            
    def _load_container_config(self) -> Dict[str, Any]:
        """Load container configuration from claude_container_config.json"""
        config_path = Path(__file__).parent.parent / "claude_container_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load container config: {e}")
            return {"containers": {}}
            
    def _load_token_registry(self) -> Dict[str, str]:
        """Load Discord token registry mapping"""
        return {
            "claude-isolated-discord": "DISCORD_TOKEN_CODERDEV1",
            "claude-fullstackdev-persistent": "DISCORD_TOKEN_CODERDEV2",
        }
        
    async def list_containers(self, include_stopped: bool = False) -> Dict[str, Any]:
        """List all Claude Code containers with detailed information"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available", "containers": []}
            
        try:
            containers = []
            filters = {"label": "superagent.type"} if not include_stopped else {}
            
            for container in self.docker_client.containers.list(all=include_stopped, filters=filters):
                # Get container details
                labels = container.labels
                
                # Skip non-SuperAgent containers
                if "superagent.type" not in labels:
                    continue
                    
                # Get Discord token info
                discord_token_env = self.token_registry.get(container.name, "Unknown")
                
                # Get container health
                health_status = await self._check_container_health(container)
                
                container_info = {
                    "name": container.name,
                    "id": container.short_id,
                    "status": container.status,
                    "bot_identity": labels.get("superagent.agent", "Unknown"),
                    "discord_token_env": discord_token_env,
                    "team": labels.get("superagent.team", "default"),
                    "type": labels.get("superagent.type", "unknown"),
                    "workspace": labels.get("superagent.workspace", "unknown"),
                    "created": container.attrs['Created'],
                    "health": health_status,
                    "image": container.image.tags[0] if container.image.tags else "unknown"
                }
                
                # Add uptime if running
                if container.status == "running":
                    container_info["uptime"] = self._calculate_uptime(container.attrs['State']['StartedAt'])
                    
                containers.append(container_info)
                
            return {
                "success": True,
                "containers": containers,
                "total": len(containers)
            }
            
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return {"success": False, "error": str(e), "containers": []}
            
    async def launch_container(self, container_name: str, preserve_auth: bool = True) -> Dict[str, Any]:
        """Launch a Claude Code container with proper configuration"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}
            
        try:
            # Check if container already exists
            existing_container = None
            try:
                existing_container = self.docker_client.containers.get(container_name)
            except docker.errors.NotFound:
                pass
                
            if existing_container:
                if existing_container.status == "running":
                    return {"success": True, "message": f"Container {container_name} is already running", "container_id": existing_container.short_id}
                else:
                    # Start existing container (preserves auth)
                    existing_container.start()
                    await asyncio.sleep(2)  # Wait for startup
                    
                    # Configure MCP if needed
                    await self._configure_mcp(existing_container)
                    
                    return {"success": True, "message": f"Started existing container {container_name}", "container_id": existing_container.short_id}
                    
            # Create new container
            config = self.config.get("containers", {}).get(container_name, {})
            if not config:
                return {"success": False, "error": f"No configuration found for container {container_name}"}
                
            # Get Discord token
            discord_token_env = config.get("discord_token_env", self.token_registry.get(container_name))
            discord_token_value = os.environ.get(discord_token_env)
            
            if not discord_token_value:
                return {"success": False, "error": f"Discord token {discord_token_env} not found in environment"}
                
            # Clean token value (remove comments)
            discord_token_value = discord_token_value.split('#')[0].strip()
            
            # Prepare environment
            environment = {
                "DISCORD_TOKEN": discord_token_value,
                "DEFAULT_SERVER_ID": os.environ.get("DEFAULT_SERVER_ID", ""),
                "AGENT_TYPE": config.get("agent_type", "isolated_claude"),
                "AGENT_PERSONALITY": config.get("agent_personality", ""),
                "WORKSPACE_PATH": "/workspace"
            }
            
            # Prepare volumes
            volumes = {}
            workspace_path = os.path.expanduser(config.get("workspace_path", f"~/claude_workspaces/{container_name}"))
            os.makedirs(workspace_path, exist_ok=True)
            volumes[workspace_path] = {"bind": "/workspace", "mode": "rw"}
            
            # Add Git config mounts
            git_config = os.path.expanduser("~/.gitconfig")
            if os.path.exists(git_config):
                volumes[git_config] = {"bind": "/home/node/.gitconfig", "mode": "ro"}
                
            ssh_dir = os.path.expanduser("~/.ssh")
            if os.path.exists(ssh_dir):
                volumes[ssh_dir] = {"bind": "/home/node/.ssh", "mode": "ro"}
                
            # Add mcp-discord directory
            mcp_discord_path = Path(__file__).parent.parent / "mcp-discord"
            if mcp_discord_path.exists():
                volumes[str(mcp_discord_path)] = {"bind": "/home/node/mcp-discord", "mode": "rw"}
                
            # Create container
            container = self.docker_client.containers.run(
                image=config.get("image", "superagent/official-claude-code:latest"),
                name=container_name,
                detach=True,
                environment=environment,
                volumes=volumes,
                labels=config.get("labels", {}),
                restart_policy={"Name": config.get("restart_policy", "unless-stopped")},
                stdin_open=True,
                tty=True
            )
            
            # Wait for initialization
            await asyncio.sleep(5)
            
            # Configure MCP
            await self._configure_mcp(container)
            
            # Test container
            test_result = await self.test_container(container_name)
            
            return {
                "success": True,
                "message": f"Created new container {container_name}",
                "container_id": container.short_id,
                "test_result": test_result
            }
            
        except Exception as e:
            logger.error(f"Failed to launch container {container_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def shutdown_container(self, container_name: str, remove: bool = False) -> Dict[str, Any]:
        """Stop a container, optionally remove it"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available"}
            
        try:
            container = self.docker_client.containers.get(container_name)
            
            if remove:
                # Backup auth if present
                auth_backup = await self._backup_auth(container)
                
                container.stop(timeout=10)
                container.remove()
                
                return {
                    "success": True,
                    "message": f"Container {container_name} stopped and removed",
                    "auth_backed_up": auth_backup
                }
            else:
                container.stop(timeout=10)
                return {
                    "success": True,
                    "message": f"Container {container_name} stopped (preserved for restart)"
                }
                
        except docker.errors.NotFound:
            return {"success": False, "error": f"Container {container_name} not found"}
        except Exception as e:
            logger.error(f"Failed to shutdown container {container_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def test_container(self, container_name: str) -> Dict[str, Any]:
        """Test container functionality including Claude Code and Discord MCP"""
        if not self.docker_client:
            return {"success": False, "error": "Docker not available", "tests": {}}
            
        try:
            container = self.docker_client.containers.get(container_name)
            
            if container.status != "running":
                return {"success": False, "error": "Container not running", "tests": {}}
                
            tests = {
                "claude_code": False,
                "mcp_connection": False,
                "discord_connection": False,
                "workspace_access": False
            }
            
            # Test 1: Claude Code functionality
            try:
                result = container.exec_run("claude --version", user="node")
                if result.exit_code == 0 and b"Claude Code" in result.output:
                    tests["claude_code"] = True
            except Exception as e:
                logger.error(f"Claude Code test failed: {e}")
                
            # Test 2: MCP connection
            try:
                result = container.exec_run("claude mcp list", user="node")
                if result.exit_code == 0:
                    tests["mcp_connection"] = True
                    # Check for Discord connection
                    if b"✓ Connected" in result.output or b"discord" in result.output.lower():
                        tests["discord_connection"] = True
            except Exception as e:
                logger.error(f"MCP test failed: {e}")
                
            # Test 3: Workspace access
            try:
                result = container.exec_run("ls -la /workspace", user="node")
                if result.exit_code == 0:
                    tests["workspace_access"] = True
            except Exception as e:
                logger.error(f"Workspace test failed: {e}")
                
            # Overall success
            all_passed = all(tests.values())
            
            return {
                "success": all_passed,
                "tests": tests,
                "message": "All tests passed" if all_passed else "Some tests failed"
            }
            
        except docker.errors.NotFound:
            return {"success": False, "error": f"Container {container_name} not found", "tests": {}}
        except Exception as e:
            logger.error(f"Failed to test container {container_name}: {e}")
            return {"success": False, "error": str(e), "tests": {}}
            
    async def get_container_config(self, container_name: str) -> Dict[str, Any]:
        """Get detailed container configuration"""
        try:
            # Get config from file
            file_config = self.config.get("containers", {}).get(container_name, {})
            
            # Get runtime config if container exists
            runtime_config = {}
            if self.docker_client:
                try:
                    container = self.docker_client.containers.get(container_name)
                    runtime_config = {
                        "status": container.status,
                        "environment": container.attrs['Config']['Env'],
                        "volumes": container.attrs['Mounts'],
                        "labels": container.labels,
                        "created": container.attrs['Created']
                    }
                except docker.errors.NotFound:
                    runtime_config = {"status": "not_created"}
                    
            return {
                "success": True,
                "config": {
                    "file_config": file_config,
                    "runtime_config": runtime_config,
                    "discord_token_env": self.token_registry.get(container_name, "Unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get config for {container_name}: {e}")
            return {"success": False, "error": str(e)}
            
    async def _check_container_health(self, container) -> str:
        """Check container health status"""
        try:
            # Try to execute a simple command
            result = container.exec_run("claude --version", user="node")
            if result.exit_code == 0:
                return "healthy"
            else:
                return "unhealthy"
        except:
            return "unknown"
            
    async def _configure_mcp(self, container) -> bool:
        """Configure MCP Discord integration for container"""
        try:
            # Create __main__.py file
            container.exec_run(
                "sh -c 'echo \"from discord_mcp import main; main()\" > /home/node/mcp-discord/src/discord_mcp/__main__.py'",
                user="node"
            )
            
            # Get Discord token from environment
            env_vars = container.attrs['Config']['Env']
            discord_token = None
            server_id = None
            
            for env in env_vars:
                if env.startswith("DISCORD_TOKEN="):
                    discord_token = env.split("=", 1)[1]
                elif env.startswith("DEFAULT_SERVER_ID="):
                    server_id = env.split("=", 1)[1]
                    
            if not discord_token or not server_id:
                logger.error("Missing Discord token or server ID")
                return False
                
            # Add MCP server using claude mcp add
            cmd = f"""
            export PYTHONPATH=/home/node/mcp-discord/src
            claude mcp remove discord-isolated 2>/dev/null || true
            claude mcp add discord-isolated stdio -- python3 -m discord_mcp --token '{discord_token}' --server-id '{server_id}'
            """
            
            result = container.exec_run(["bash", "-c", cmd], user="node")
            return result.exit_code == 0
            
        except Exception as e:
            logger.error(f"Failed to configure MCP: {e}")
            return False
            
    async def _backup_auth(self, container) -> bool:
        """Backup Claude authentication before container removal"""
        try:
            # Copy .claude.json to backup location
            result = container.exec_run(
                "cp /home/node/.claude.json /workspace/.claude.json.backup 2>/dev/null",
                user="node"
            )
            return result.exit_code == 0
        except:
            return False
            
    def _calculate_uptime(self, started_at: str) -> str:
        """Calculate container uptime"""
        try:
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            uptime = datetime.now(start_time.tzinfo) - start_time
            
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "unknown"


# Singleton instance
container_manager = MCPContainerManager()