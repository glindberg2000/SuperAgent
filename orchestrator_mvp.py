#!/usr/bin/env python3
"""
SuperAgent MVP Container Orchestrator
Spawns Claude Code containers with Discord and PostgreSQL access
"""

import docker
import os
import json
import time
import logging
from typing import Dict, Optional, List
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator-mvp")


class MVPOrchestrator:
    """Minimal orchestrator for spawning Claude Code containers"""
    
    def __init__(self):
        try:
            # Try to connect to Docker using environment settings
            self.docker = docker.from_env()
            # Test the connection
            self.docker.ping()
            logger.info("✅ Connected to Docker daemon")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Docker daemon: {e}")
            logger.info("💡 Make sure Docker is running (Docker Desktop or Colima)")
            # Try common socket paths for debugging
            import os
            socket_paths = [
                "/var/run/docker.sock",
                "/Users/greg/.colima/default/docker.sock",
                os.path.expanduser("~/.colima/default/docker.sock")
            ]
            for path in socket_paths:
                if os.path.exists(path):
                    logger.info(f"   Found Docker socket at: {path}")
            raise
        
        self.agents: Dict[str, docker.models.containers.Container] = {}
        self.network_name = "superagent-network"
        self._ensure_network()
    
    def _ensure_network(self):
        """Ensure Docker network exists for container communication"""
        try:
            self.docker.networks.get(self.network_name)
            logger.info(f"✅ Network '{self.network_name}' already exists")
        except docker.errors.NotFound:
            network = self.docker.networks.create(
                self.network_name,
                driver="bridge"
            )
            logger.info(f"✅ Created Docker network: {network.name}")
    
    def _validate_workspace(self, workspace_path: str) -> str:
        """Validate and resolve workspace path"""
        path = Path(workspace_path).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Workspace path does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Workspace path is not a directory: {path}")
        return str(path)
    
    def spawn_agent(
        self, 
        name: str, 
        workspace_path: str, 
        discord_token: str,
        anthropic_api_key: Optional[str] = None,
        personality: str = "Helpful coding assistant"
    ) -> str:
        """
        Spawn a Claude Code container with Discord and PostgreSQL access
        
        Args:
            name: Unique agent name
            workspace_path: Local path to mount as workspace
            discord_token: Discord bot token for this agent
            anthropic_api_key: Claude API key (defaults to env var)
            personality: Agent personality description
        
        Returns:
            Container ID
        """
        
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already exists")
        
        # Validate inputs
        workspace_path = self._validate_workspace(workspace_path)
        anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not discord_token:
            raise ValueError("discord_token is required")
        
        # Container environment
        env = {
            "ANTHROPIC_API_KEY": anthropic_api_key,
            "DISCORD_TOKEN": discord_token,
            "DISCORD_MCP_URL": "http://discord-stateless-api:9091",  # Internal network
            "POSTGRES_URL": "postgresql://superagent:superagent@postgres:5432/superagent",
            "AGENT_NAME": name,
            "AGENT_PERSONALITY": personality,
            "WORKSPACE_PATH": "/workspace"
        }
        
        # Volume mounts
        volumes = {
            workspace_path: {"bind": "/workspace", "mode": "rw"},
        }
        
        # Add SSH keys if they exist
        ssh_path = Path.home() / ".ssh"
        if ssh_path.exists():
            volumes[str(ssh_path)] = {"bind": "/root/.ssh", "mode": "ro"}
        
        logger.info(f"🚀 Spawning agent '{name}'...")
        logger.info(f"   Workspace: {workspace_path}")
        logger.info(f"   Discord Token: ...{discord_token[-8:]}")
        logger.info(f"   Personality: {personality}")
        
        try:
            # Create and start container
            # For now, use a simple test image until we get the Claude Code image
            container = self.docker.containers.run(
                "python:3.11-slim",  # Test with Python image first
                name=f"agent-{name}",
                environment=env,
                volumes=volumes,
                network=self.network_name,  # Connect to our network
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                remove=False,  # Keep container for debugging
                tty=True,  # Allocate TTY for interactive sessions
                stdin_open=True,  # Keep STDIN open
                command=["sleep", "3600"]  # Keep container running for testing
            )
            
            self.agents[name] = container
            
            logger.info(f"✅ Agent '{name}' started successfully!")
            logger.info(f"   Container ID: {container.id[:12]}")
            logger.info(f"   Status: {container.status}")
            
            return container.id
            
        except Exception as e:
            logger.error(f"❌ Failed to spawn agent '{name}': {e}")
            raise
    
    def list_agents(self) -> Dict[str, Dict]:
        """List all agents with their status"""
        agent_info = {}
        
        for name, container in self.agents.items():
            try:
                container.reload()  # Refresh status
                agent_info[name] = {
                    "id": container.id[:12],
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "created": container.attrs["Created"],
                    "workspace": container.attrs["Mounts"][0]["Source"] if container.attrs["Mounts"] else "none"
                }
            except Exception as e:
                agent_info[name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return agent_info
    
    def get_agent_logs(self, name: str, lines: int = 50) -> str:
        """Get recent logs from an agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        
        try:
            container = self.agents[name]
            logs = container.logs(tail=lines, timestamps=True)
            return logs.decode('utf-8')
        except Exception as e:
            return f"Error getting logs: {e}"
    
    def stop_agent(self, name: str) -> None:
        """Stop a specific agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        
        try:
            container = self.agents[name]
            logger.info(f"🛑 Stopping agent '{name}'...")
            container.stop(timeout=10)
            logger.info(f"✅ Agent '{name}' stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping agent '{name}': {e}")
            raise
    
    def remove_agent(self, name: str) -> None:
        """Remove a stopped agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        
        try:
            container = self.agents[name]
            logger.info(f"🗑️  Removing agent '{name}'...")
            container.remove(force=True)
            del self.agents[name]
            logger.info(f"✅ Agent '{name}' removed")
        except Exception as e:
            logger.error(f"❌ Error removing agent '{name}': {e}")
            raise
    
    def stop_all(self) -> None:
        """Stop all agents"""
        logger.info(f"🛑 Stopping all {len(self.agents)} agents...")
        
        for name in list(self.agents.keys()):
            try:
                self.stop_agent(name)
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    def remove_all(self) -> None:
        """Remove all agents (stops them first if needed)"""
        logger.info(f"🗑️  Removing all {len(self.agents)} agents...")
        
        for name in list(self.agents.keys()):
            try:
                self.remove_agent(name)
            except Exception as e:
                logger.error(f"Error removing {name}: {e}")
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of required services"""
        health = {}
        
        # Check Docker daemon
        try:
            self.docker.ping()
            health["docker"] = True
        except:
            health["docker"] = False
        
        # Check for Discord API container
        try:
            discord_container = self.docker.containers.get("discord-stateless-api")
            health["discord_api"] = discord_container.status == "running"
        except:
            health["discord_api"] = False
        
        # Check for PostgreSQL container  
        try:
            postgres_container = self.docker.containers.get("superagent-postgres")
            health["postgres"] = postgres_container.status == "running"
        except:
            health["postgres"] = False
        
        return health


def main():
    """Example usage of the orchestrator"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    orchestrator = MVPOrchestrator()
    
    # Check system health
    logger.info("🔍 Checking system health...")
    health = orchestrator.health_check()
    for service, is_healthy in health.items():
        status = "✅" if is_healthy else "❌"
        logger.info(f"   {service}: {status}")
    
    if not all(health.values()):
        logger.error("❌ Some required services are not running!")
        logger.info("💡 Make sure Discord API and PostgreSQL containers are running:")
        logger.info("   docker-compose -f mcp-discord/docker-compose.yml up -d")
        return
    
    # Example agent configurations
    example_agents = [
        {
            "name": "grok4-agent",
            "workspace_path": "~/repos/SuperAgent",
            "discord_token": os.getenv("DISCORD_TOKEN"),
            "personality": "Expert AI researcher and Discord bot focused on analysis and explanations"
        },
        {
            "name": "crypto-agent", 
            "workspace_path": "~/repos/CryptoTaxCalc",
            "discord_token": os.getenv("DISCORD_TOKEN2"),
            "personality": "Cryptocurrency tax calculation specialist and financial analyst"
        }
    ]
    
    try:
        # Spawn example agents
        for agent_config in example_agents:
            if agent_config["discord_token"]:
                try:
                    orchestrator.spawn_agent(**agent_config)
                    time.sleep(2)  # Brief pause between spawns
                except Exception as e:
                    logger.error(f"Failed to spawn {agent_config['name']}: {e}")
            else:
                logger.warning(f"Skipping {agent_config['name']} - no Discord token")
        
        # Show status
        logger.info("\n📊 Agent Status:")
        agents = orchestrator.list_agents()
        for name, info in agents.items():
            logger.info(f"   {name}: {info['status']} (ID: {info.get('id', 'unknown')})")
        
        # Show logs for first agent
        if agents:
            first_agent = list(agents.keys())[0]
            logger.info(f"\n📋 Recent logs for {first_agent}:")
            logs = orchestrator.get_agent_logs(first_agent, lines=10)
            for line in logs.split('\n')[-10:]:
                if line.strip():
                    logger.info(f"   {line}")
        
        logger.info("\n✅ MVP Orchestrator setup complete!")
        logger.info("🎯 Check Discord to see if agents are responding")
        logger.info("🔍 Monitor agents with: docker ps")
        logger.info("📋 View logs with: docker logs agent-<name>")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        # Uncomment to auto-cleanup on exit
        # orchestrator.stop_all()
        pass


if __name__ == "__main__":
    main()