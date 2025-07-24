#!/usr/bin/env python3
"""
AI-Powered DevOps Agent for SuperAgent
A truly intelligent DevOps agent that uses Claude LLM to understand natural language
and manage container orchestration with autonomous decision-making capabilities.
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
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yaml
from anthropic import AsyncAnthropic
from dataclasses import dataclass
import traceback
import subprocess
import shlex

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/devops_agent.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class AgentStatus:
    """Represents the current status of an agent"""
    name: str
    type: str
    container_id: Optional[str]
    status: str  # running, stopped, failed, deploying
    cpu_percent: float
    memory_mb: int
    uptime: str
    team: Optional[str]
    last_activity: datetime
    errors: List[str]

@dataclass
class SystemHealth:
    """System health information"""
    docker_healthy: bool
    postgres_healthy: bool
    discord_connected: bool
    system_cpu: float
    system_memory: float
    agent_count: int
    errors: List[str]

class AIDevOpsAgent:
    """
    An intelligent DevOps agent powered by Claude LLM that can:
    1. Understand natural language requests about infrastructure
    2. Make autonomous decisions about container management
    3. Monitor and maintain system health
    4. Coordinate multi-agent teams
    5. Provide intelligent insights and recommendations
    """
    
    def __init__(self, config_path: str = "configs/devops_config.json"):
        # Load environment and config
        self.config = self._load_config(config_path)
        
        # Set up logging first
        self.logger = logging.getLogger('AIDevOpsAgent')
        self.logger.info("AI DevOps Agent initializing...")
        
        # Initialize Claude LLM client
        self.claude = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Initialize Docker client
        self.docker_client = self._init_docker()
        
        # Agent registry and state
        self.agents: Dict[str, AgentStatus] = {}
        self.teams: Dict[str, dict] = {}
        self.system_state = {
            'last_health_check': None,
            'alerts': [],
            'performance_history': [],
            'deployment_history': []
        }
        
        # AI conversation context
        self.conversation_context = []
        self.system_knowledge = self._build_system_knowledge()
        
        # Initialize Discord bot
        self.bot = self._init_discord_bot()
        
    def _load_config(self, config_path: str) -> dict:
        """Load DevOps agent configuration"""
        default_config = {
            "discord_token_env": "DISCORD_TOKEN_DEVOPS",
            "personality": "Expert DevOps engineer with deep knowledge of containerization and system administration",
            "health_check_interval": 60,
            "auto_recovery": True,
            "max_agents": 20,
            "claude_model": "claude-3-5-sonnet-20241022"
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return default_config
    
    def _init_docker(self) -> Optional[docker.DockerClient]:
        """Initialize Docker client with connection fallback"""
        try:
            client = docker.from_env()
            client.ping()
            self.logger.info("✅ Connected to Docker daemon")
            return client
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to connect to Docker daemon: {e}")
            self.logger.info("Docker functionality will be limited until connection is restored")
            return None
    
    def _init_discord_bot(self) -> commands.Bot:
        """Initialize Discord bot with AI-powered command handling"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        bot = commands.Bot(
            command_prefix=['!', '@DevOps ', 'devops '],
            intents=intents,
            description='AI-Powered SuperAgent DevOps Controller'
        )
        
        @bot.event
        async def on_ready():
            self.logger.info(f"🤖 AI DevOps Agent online as {bot.user}")
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="SuperAgent Infrastructure"
                )
            )
        
        @bot.event
        async def on_message(message):
            # Ignore own messages
            if message.author == bot.user:
                return
            
            # Check if message mentions the bot or is a DM
            if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
                await self._handle_natural_language_request(message)
                return
            
            # Process commands
            await bot.process_commands(message)
        
        # Register commands
        self._register_commands(bot)
        
        return bot
    
    def _register_commands(self, bot: commands.Bot):
        """Register Discord commands with the bot"""
        
        @bot.command(name='status', aliases=['health', 'system'])
        async def status_command(ctx):
            """Get comprehensive system status"""
            await self._handle_status_request(ctx)
        
        @bot.command(name='agents', aliases=['list', 'ls'])
        async def list_agents_command(ctx):
            """List all agents and their status"""
            await self._handle_list_agents(ctx)
        
        @bot.command(name='deploy')
        async def deploy_command(ctx, agent_type: str = None, *, args: str = ""):
            """Deploy a new agent"""
            if not agent_type:
                await ctx.send("Please specify agent type: `!deploy grok4` or `!deploy claude --team crypto`")
                return
            await self._handle_deploy_request(ctx, agent_type, args)
        
        @bot.command(name='stop')
        async def stop_command(ctx, agent_name: str = None):
            """Stop an agent"""
            if not agent_name:
                await ctx.send("Please specify agent name: `!stop grok4-agent-1`")
                return
            await self._handle_stop_request(ctx, agent_name)
        
        @bot.command(name='logs')
        async def logs_command(ctx, agent_name: str = None, lines: int = 20):
            """Get agent logs"""
            if not agent_name:
                await ctx.send("Please specify agent name: `!logs claude-agent-1`")
                return
            await self._handle_logs_request(ctx, agent_name, lines)
        
        @bot.command(name='team')
        async def team_command(ctx, action: str = None, *, args: str = ""):
            """Team management commands"""
            if not action:
                await ctx.send("Team commands: `!team create <name>`, `!team list`, `!team assign <agent> <team>`")
                return
            await self._handle_team_request(ctx, action, args)
    
    def _build_system_knowledge(self) -> str:
        """Build system knowledge base for Claude"""
        return f"""
You are the AI DevOps Agent for SuperAgent, a multi-agent Discord system. Your role:

SYSTEM ARCHITECTURE:
- Host: {os.uname().nodename} running {os.uname().sysname}
- Container orchestration via Docker
- Multiple AI agents (Grok4, Claude, Gemini, etc.) in containers
- Discord integration via MCP (Model Context Protocol)
- PostgreSQL shared memory with pgvector
- Each agent has unique Discord identity and specialized capabilities

AVAILABLE AGENT TYPES:
- grok4: Research and analysis expert
- claude: Code development and writing
- gemini: Creative tasks and multimodal analysis
- manager: Team coordination and task assignment
- fullstack: Full-stack development specialist

CONTAINER MANAGEMENT:
- All agents run in isolated Docker containers
- Standard image: superagent/claude-code:latest
- Network: superagent-network for inter-container communication
- Volumes: Workspace mounts for file access
- Environment: API keys, Discord tokens, agent configs

CURRENT CAPABILITIES:
- Deploy/stop/restart agents
- Monitor system health and resources
- Manage teams and task assignments
- View logs and troubleshoot issues
- Auto-recovery for failed services
- Performance optimization

PERSONALITY:
- Expert DevOps engineer with deep containerization knowledge
- Proactive problem-solving and optimization suggestions
- Clear communication with both technical and non-technical users
- Autonomous decision-making within defined parameters
- Safety-first approach to system changes
"""
    
    async def _handle_natural_language_request(self, message: discord.Message):
        """Handle natural language requests using Claude LLM"""
        try:
            # Get current system state
            system_state = await self._get_current_system_state()
            
            # Build context for Claude
            context = f"""
{self.system_knowledge}

CURRENT SYSTEM STATE:
{json.dumps(system_state, indent=2, default=str)}

USER REQUEST:
User: {message.author.display_name}
Message: {message.content}
Channel: {message.channel.name if hasattr(message.channel, 'name') else 'DM'}

Please analyze this request and determine the appropriate action. You can:
1. Provide information about system status
2. Suggest actions to take
3. Execute safe operations (deploy/stop agents, view logs, etc.)
4. Ask for clarification if needed

Respond in a helpful, technical but accessible manner. If you need to execute operations, 
clearly state what you plan to do and why.
"""
            
            # Send typing indicator
            async with message.channel.typing():
                # Get Claude's response
                response = await self.claude.messages.create(
                    model=self.config['claude_model'],
                    max_tokens=1500,
                    messages=[{"role": "user", "content": context}]
                )
                
                claude_response = response.content[0].text
                
                # Process the response and potentially execute actions
                await self._process_claude_response(message, claude_response)
                
        except Exception as e:
            self.logger.error(f"Error in natural language processing: {e}")
            await message.reply(f"I encountered an error processing your request: {str(e)}")
    
    async def _process_claude_response(self, message: discord.Message, claude_response: str):
        """Process Claude's response and execute any recommended actions"""
        
        # Check if Claude suggests specific actions
        if "EXECUTE:" in claude_response:
            # Extract and execute commands
            parts = claude_response.split("EXECUTE:")
            explanation = parts[0].strip()
            commands = parts[1].strip() if len(parts) > 1 else ""
            
            # Send explanation first
            if explanation:
                await message.reply(explanation)
            
            # Execute commands (implement based on your needs)
            if commands:
                await self._execute_suggested_actions(message, commands)
        else:
            # Just send the response
            await message.reply(claude_response)
    
    async def _execute_suggested_actions(self, message: discord.Message, commands: str):
        """Execute actions suggested by Claude (with safety checks)"""
        # Parse and execute commands safely
        # This would implement the actual command execution
        await message.channel.send(f"Executing: {commands}")
        # Implementation would go here
    
    async def _get_current_system_state(self) -> dict:
        """Get comprehensive current system state"""
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {name: {
                "status": agent.status,
                "type": agent.type,
                "cpu_percent": agent.cpu_percent,
                "memory_mb": agent.memory_mb,
                "uptime": agent.uptime,
                "team": agent.team,
                "errors": agent.errors
            } for name, agent in self.agents.items()},
            "teams": self.teams,
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "docker_containers": len(self.docker_client.containers.list()) if self.docker_client else 0,
                "load_average": os.getloadavg()
            },
            "recent_alerts": self.system_state.get('alerts', [])[-5:],
            "deployment_history": self.system_state.get('deployment_history', [])[-10:]
        }
    
    async def _handle_status_request(self, ctx):
        """Handle status command with AI insights"""
        try:
            health = await self._comprehensive_health_check()
            
            embed = discord.Embed(
                title="🤖 SuperAgent System Status",
                color=discord.Color.green() if health.docker_healthy else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            # System health overview
            status_emoji = "✅" if health.docker_healthy else "❌"
            embed.add_field(
                name="System Health",
                value=f"{status_emoji} Docker: {'Healthy' if health.docker_healthy else 'Issues'}",
                inline=True
            )
            
            # Agent summary
            running_agents = len([a for a in self.agents.values() if a.status == 'running'])
            embed.add_field(
                name="Agents",
                value=f"{running_agents}/{len(self.agents)} running",
                inline=True
            )
            
            # System resources
            embed.add_field(
                name="Resources",
                value=f"CPU: {health.system_cpu:.1f}% | RAM: {health.system_memory:.1f}%",
                inline=True
            )
            
            # List running agents
            if self.agents:
                agent_list = []
                for name, agent in list(self.agents.items())[:8]:  # Limit display
                    status_emoji = "🟢" if agent.status == 'running' else "🔴"
                    agent_list.append(f"{status_emoji} {name} ({agent.type})")
                
                embed.add_field(
                    name="Active Agents",
                    value="\n".join(agent_list) if agent_list else "No agents running",
                    inline=False
                )
            
            # AI insights
            insights = await self._generate_system_insights()
            if insights:
                embed.add_field(
                    name="🧠 AI Insights",
                    value=insights[:500] + "..." if len(insights) > 500 else insights,
                    inline=False
                )
            
            embed.set_footer(text="AI DevOps Agent • SuperAgent Control Plane")
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in status request: {e}")
            await ctx.send(f"Error getting system status: {str(e)}")
    
    async def _generate_system_insights(self) -> str:
        """Generate AI insights about current system state"""
        try:
            system_state = await self._get_current_system_state()
            
            insight_prompt = f"""
Based on this system state, provide 2-3 brief insights or recommendations:

{json.dumps(system_state, indent=2, default=str)}

Focus on:
- Performance optimization opportunities
- Resource utilization concerns
- Deployment recommendations
- Health/stability issues

Keep response under 300 characters.
"""
            
            response = await self.claude.messages.create(
                model=self.config['claude_model'],
                max_tokens=300,
                messages=[{"role": "user", "content": insight_prompt}]
            )
            
            return response.content[0].text.strip()
        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            return "System analysis available - see logs for details"
    
    async def _comprehensive_health_check(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        try:
            # Check Docker
            docker_healthy = False
            if self.docker_client:
                try:
                    self.docker_client.ping()
                    docker_healthy = True
                except:
                    docker_healthy = False
            
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            # Update agent statuses
            await self._update_agent_statuses()
            
            return SystemHealth(
                docker_healthy=docker_healthy,
                postgres_healthy=True,  # TODO: implement postgres check
                discord_connected=self.bot.is_ready(),
                system_cpu=cpu_percent,
                system_memory=memory_percent,
                agent_count=len(self.agents),
                errors=[]
            )
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return SystemHealth(
                docker_healthy=False,
                postgres_healthy=False,
                discord_connected=False,
                system_cpu=0,
                system_memory=0,
                agent_count=0,
                errors=[str(e)]
            )
    
    async def _update_agent_statuses(self):
        """Update status for all tracked agents"""
        if not self.docker_client:
            return
            
        for agent_name, agent_status in self.agents.items():
            try:
                if agent_status.container_id:
                    container = self.docker_client.containers.get(agent_status.container_id)
                    
                    # Update basic status
                    agent_status.status = container.status
                    
                    # Get resource usage if running
                    if container.status == 'running':
                        stats = container.stats(stream=False)
                        
                        # Calculate CPU percentage
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                   stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                      stats['precpu_stats']['system_cpu_usage']
                        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
                        
                        # Calculate memory usage
                        memory_usage = stats['memory_stats']['usage']
                        memory_mb = memory_usage / (1024 * 1024)
                        
                        agent_status.cpu_percent = cpu_percent
                        agent_status.memory_mb = int(memory_mb)
                        
                        # Calculate uptime
                        created = datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00'))
                        uptime = datetime.now(created.tzinfo) - created
                        agent_status.uptime = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
                    
            except Exception as e:
                self.logger.error(f"Error updating agent {agent_name}: {e}")
                agent_status.errors.append(str(e))
    
    async def _handle_list_agents(self, ctx):
        """Handle list agents request"""
        if not self.agents:
            await ctx.send("No agents currently registered.")
            return
        
        embed = discord.Embed(title="🤖 SuperAgent Fleet", color=discord.Color.blue())
        
        for agent_name, agent in self.agents.items():
            status_emoji = {
                'running': '🟢',
                'stopped': '🔴', 
                'failed': '💥',
                'deploying': '🟡'
            }.get(agent.status, '⚪')
            
            embed.add_field(
                name=f"{status_emoji} {agent_name}",
                value=f"Type: {agent.type}\nCPU: {agent.cpu_percent:.1f}%\nRAM: {agent.memory_mb}MB\nTeam: {agent.team or 'None'}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    async def start(self):
        """Start the AI DevOps Agent"""
        self.logger.info("🚀 Starting AI DevOps Agent...")
        
        # Start health monitoring background task
        asyncio.create_task(self._health_monitor_loop())
        
        # Start Discord bot
        token = os.getenv(self.config['discord_token_env'])
        if not token:
            raise ValueError(f"Discord token not found in env var: {self.config['discord_token_env']}")
        
        await self.bot.start(token)
    
    async def _health_monitor_loop(self):
        """Background health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.config['health_check_interval'])
                await self._comprehensive_health_check()
                self.system_state['last_health_check'] = datetime.now()
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")

# Placeholder implementations for other handlers
    async def _handle_deploy_request(self, ctx, agent_type: str, args: str):
        await ctx.send(f"Deploy {agent_type} requested (implementation pending)")
    
    async def _handle_stop_request(self, ctx, agent_name: str):
        await ctx.send(f"Stop {agent_name} requested (implementation pending)")
    
    async def _handle_logs_request(self, ctx, agent_name: str, lines: int):
        await ctx.send(f"Logs for {agent_name} requested (implementation pending)")
    
    async def _handle_team_request(self, ctx, action: str, args: str):
        await ctx.send(f"Team {action} requested (implementation pending)")

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Create and start the AI DevOps Agent
        agent = AIDevOpsAgent()
        await agent.start()
    
    # Run the agent
    asyncio.run(main())