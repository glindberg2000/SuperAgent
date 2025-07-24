#!/usr/bin/env python3
"""
DevOps Agent Specification and Skeleton Implementation
This special agent runs on the host with elevated privileges to manage the SuperAgent ecosystem
"""

import asyncio
import docker
import discord
from discord.ext import commands
import json
import logging
import os
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DevOpsAgent:
    """
    The DevOps Agent is a special host-level agent that:
    1. Manages all containerized agents
    2. Monitors system health
    3. Provides Discord interface for control
    4. Handles configuration management
    5. Orchestrates team operations
    """
    
    def __init__(self, config_path: str = "configs/devops_config.json"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize Docker client
        self.docker_client = self._init_docker()
        
        # Initialize Discord bot
        self.bot = self._init_discord_bot()
        
        # Agent registry
        self.agents = {}  # agent_name -> agent_info
        self.teams = {}   # team_name -> team_info
        
        # Metrics and monitoring
        self.metrics = {
            'start_time': datetime.now(),
            'agents_spawned': 0,
            'agents_stopped': 0,
            'errors': [],
            'health_checks': 0
        }
        
        # File system watcher for config changes
        self.config_watcher = None
        
        # Logging
        self.logger = self._setup_logging()
        
    def _load_config(self, config_path: str) -> dict:
        """Load DevOps agent configuration"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _init_docker(self) -> docker.DockerClient:
        """Initialize Docker client with proper socket detection"""
        # Similar to orchestrator_mvp.py logic
        return docker.from_env()
    
    def _init_discord_bot(self) -> commands.Bot:
        """Initialize Discord bot with DevOps commands"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        bot = commands.Bot(
            command_prefix='!',
            intents=intents,
            description='SuperAgent DevOps Controller'
        )
        
        # Register commands
        self._register_discord_commands(bot)
        
        return bot
    
    def _register_discord_commands(self, bot: commands.Bot):
        """Register all Discord commands for DevOps control"""
        
        @bot.command(name='status')
        async def status(ctx):
            """Show comprehensive system status"""
            embed = self._create_status_embed()
            await ctx.send(embed=embed)
        
        @bot.command(name='deploy')
        async def deploy(ctx, agent_type: str, *, args: str = ""):
            """Deploy a new agent: !deploy grok4 --team crypto"""
            result = await self.deploy_agent_async(agent_type, args)
            await ctx.send(result['message'])
        
        @bot.command(name='stop')
        async def stop(ctx, agent_name: str):
            """Stop a running agent"""
            result = self.stop_agent(agent_name)
            await ctx.send(result['message'])
        
        @bot.command(name='logs')
        async def logs(ctx, agent_name: str, lines: int = 20):
            """Show agent logs"""
            log_text = self.get_agent_logs(agent_name, lines)
            if len(log_text) > 1900:
                # Discord message limit
                log_text = log_text[-1900:]
            await ctx.send(f"```\n{log_text}\n```")
        
        @bot.command(name='team')
        async def team(ctx, action: str, *, args: str = ""):
            """Team management: !team create crypto-analysts"""
            if action == 'create':
                result = self.create_team(args)
            elif action == 'list':
                result = self.list_teams()
            elif action == 'assign':
                # Parse agent and team from args
                result = self.assign_to_team(args)
            else:
                result = {'message': 'Unknown team action'}
            
            await ctx.send(result['message'])
        
        @bot.command(name='health')
        async def health(ctx):
            """System health check"""
            health_info = self.comprehensive_health_check()
            embed = self._create_health_embed(health_info)
            await ctx.send(embed=embed)
        
        @bot.command(name='config')
        async def config(ctx, agent_name: str = None):
            """Show or edit agent configuration"""
            if agent_name:
                config_info = self.get_agent_config(agent_name)
                await ctx.send(f"```json\n{json.dumps(config_info, indent=2)}\n```")
            else:
                await ctx.send("Available agents: " + ", ".join(self.list_available_agents()))
    
    # Container Management Methods
    def spawn_agent(self, agent_type: str, config: dict) -> dict:
        """Spawn a new agent container"""
        try:
            # Load agent template
            template = self._load_agent_template(agent_type)
            
            # Merge with provided config
            final_config = {**template, **config}
            
            # Create container
            container = self.docker_client.containers.run(
                image=final_config.get('image', 'superagent/claude-code:latest'),
                name=final_config['name'],
                environment=final_config['environment'],
                volumes=final_config.get('volumes', {}),
                network='superagent-network',
                detach=True,
                auto_remove=False
            )
            
            # Register agent
            self.agents[final_config['name']] = {
                'container_id': container.id,
                'type': agent_type,
                'config': final_config,
                'status': 'running',
                'started_at': datetime.now()
            }
            
            self.metrics['agents_spawned'] += 1
            self.logger.info(f"Spawned agent: {final_config['name']}")
            
            return {
                'success': True,
                'message': f"Agent {final_config['name']} deployed successfully",
                'container_id': container.id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to spawn agent: {e}")
            self.metrics['errors'].append(str(e))
            return {
                'success': False,
                'message': f"Failed to spawn agent: {str(e)}"
            }
    
    def stop_agent(self, agent_name: str, remove: bool = False) -> dict:
        """Stop an agent container"""
        if agent_name not in self.agents:
            return {'success': False, 'message': f"Agent {agent_name} not found"}
        
        try:
            container = self.docker_client.containers.get(
                self.agents[agent_name]['container_id']
            )
            container.stop(timeout=30)
            
            if remove:
                container.remove()
                del self.agents[agent_name]
            else:
                self.agents[agent_name]['status'] = 'stopped'
            
            self.metrics['agents_stopped'] += 1
            return {'success': True, 'message': f"Agent {agent_name} stopped"}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_agent_logs(self, agent_name: str, lines: int = 100) -> str:
        """Retrieve agent container logs"""
        if agent_name not in self.agents:
            return f"Agent {agent_name} not found"
        
        try:
            container = self.docker_client.containers.get(
                self.agents[agent_name]['container_id']
            )
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return logs
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"
    
    # Health Monitoring Methods
    def comprehensive_health_check(self) -> dict:
        """Perform comprehensive system health check"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'docker': self._check_docker_health(),
            'agents': self._check_agents_health(),
            'discord': self._check_discord_health(),
            'postgres': self._check_postgres_health(),
            'system': self._check_system_resources()
        }
        
        self.metrics['health_checks'] += 1
        return health
    
    def _check_docker_health(self) -> dict:
        """Check Docker daemon health"""
        try:
            self.docker_client.ping()
            return {'status': 'healthy', 'message': 'Docker daemon responsive'}
        except:
            return {'status': 'unhealthy', 'message': 'Docker daemon not responding'}
    
    def _check_agents_health(self) -> dict:
        """Check health of all agents"""
        agent_health = {}
        for name, info in self.agents.items():
            try:
                container = self.docker_client.containers.get(info['container_id'])
                agent_health[name] = {
                    'status': container.status,
                    'health': container.attrs.get('State', {}).get('Health', {})
                }
            except:
                agent_health[name] = {'status': 'unknown', 'health': 'error'}
        
        return agent_health
    
    def _check_system_resources(self) -> dict:
        """Check system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg()
        }
    
    # Team Management Methods
    def create_team(self, team_name: str, agents: List[str] = None) -> dict:
        """Create a new team"""
        if team_name in self.teams:
            return {'success': False, 'message': f"Team {team_name} already exists"}
        
        self.teams[team_name] = {
            'created_at': datetime.now(),
            'agents': agents or [],
            'active_tasks': [],
            'status': 'active'
        }
        
        return {'success': True, 'message': f"Team {team_name} created"}
    
    def assign_to_team(self, agent_name: str, team_name: str) -> dict:
        """Assign an agent to a team"""
        if team_name not in self.teams:
            return {'success': False, 'message': f"Team {team_name} not found"}
        
        if agent_name not in self.agents:
            return {'success': False, 'message': f"Agent {agent_name} not found"}
        
        self.teams[team_name]['agents'].append(agent_name)
        self.agents[agent_name]['team'] = team_name
        
        return {'success': True, 'message': f"Agent {agent_name} assigned to team {team_name}"}
    
    # Configuration Management
    def watch_configs(self, config_dir: str = "configs/"):
        """Watch configuration directory for changes"""
        class ConfigHandler(FileSystemEventHandler):
            def __init__(self, devops_agent):
                self.devops = devops_agent
            
            def on_modified(self, event):
                if event.src_path.endswith('.json') or event.src_path.endswith('.yaml'):
                    self.devops.logger.info(f"Config changed: {event.src_path}")
                    self.devops.reload_configs()
        
        event_handler = ConfigHandler(self)
        self.config_watcher = Observer()
        self.config_watcher.schedule(event_handler, config_dir, recursive=True)
        self.config_watcher.start()
    
    def reload_configs(self):
        """Reload all agent configurations"""
        # Implementation for reloading configs
        pass
    
    # Discord Embed Creators
    def _create_status_embed(self) -> discord.Embed:
        """Create a status embed for Discord"""
        embed = discord.Embed(
            title="🤖 SuperAgent System Status",
            color=discord.Color.green() if self._is_system_healthy() else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # System overview
        embed.add_field(
            name="System Health",
            value="✅ Operational" if self._is_system_healthy() else "⚠️ Issues Detected",
            inline=False
        )
        
        # Agent summary
        running = sum(1 for a in self.agents.values() if a['status'] == 'running')
        total = len(self.agents)
        embed.add_field(
            name="Agents",
            value=f"{running}/{total} running",
            inline=True
        )
        
        # Teams
        embed.add_field(
            name="Teams",
            value=f"{len(self.teams)} active",
            inline=True
        )
        
        # Uptime
        uptime = datetime.now() - self.metrics['start_time']
        embed.add_field(
            name="Uptime",
            value=f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m",
            inline=True
        )
        
        # List agents
        if self.agents:
            agent_list = []
            for name, info in self.agents.items():
                status_emoji = "🟢" if info['status'] == 'running' else "🔴"
                agent_list.append(f"{status_emoji} {name} ({info['type']})")
            
            embed.add_field(
                name="Active Agents",
                value="\n".join(agent_list[:10]),  # Limit to 10
                inline=False
            )
        
        embed.set_footer(text="SuperAgent DevOps Controller")
        return embed
    
    def _is_system_healthy(self) -> bool:
        """Quick system health check"""
        # Simplified - implement full logic
        return True
    
    # Main run method
    async def run(self):
        """Main async run loop"""
        # Start config watcher
        self.watch_configs()
        
        # Start Discord bot
        await self.bot.start(self.config['discord_token'])
    
    def start(self):
        """Start the DevOps agent"""
        self.logger.info("Starting SuperAgent DevOps Controller...")
        
        try:
            # Run the async main loop
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.logger.info("Shutting down DevOps agent...")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        if self.config_watcher:
            self.config_watcher.stop()
        
        # Save metrics
        with open('devops_metrics.json', 'w') as f:
            json.dump(self.metrics, f, default=str)
        
        self.logger.info("DevOps agent shutdown complete")


# Example configuration file structure
EXAMPLE_DEVOPS_CONFIG = {
    "discord_token": "DEVOPS_BOT_TOKEN",
    "discord_server_id": "1395578178973597799",
    "docker_socket": "unix:///var/run/docker.sock",
    "agent_templates_dir": "configs/agents/",
    "team_configs_dir": "configs/teams/",
    "log_level": "INFO",
    "health_check_interval": 60,
    "auto_recovery": True,
    "max_agents": 20,
    "resource_limits": {
        "cpu_percent": 80,
        "memory_percent": 85,
        "disk_percent": 90
    }
}

# Example agent template
EXAMPLE_AGENT_TEMPLATE = {
    "grok4": {
        "image": "superagent/claude-code:latest",
        "environment": {
            "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
            "DISCORD_TOKEN": "${DISCORD_TOKEN_GROK}",
            "DISCORD_MCP_URL": "http://discord-stateless-api:3000",
            "AGENT_TYPE": "grok4",
            "AGENT_PERSONALITY": "Research expert focused on analysis"
        },
        "volumes": {
            "/workspace": "${WORKSPACE_PATH}"
        },
        "labels": {
            "superagent.type": "grok4",
            "superagent.managed": "true"
        }
    }
}

if __name__ == "__main__":
    # Example usage
    devops = DevOpsAgent()
    devops.start()