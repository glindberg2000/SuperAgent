#!/usr/bin/env python3
"""
SuperAgent Hybrid Multi-Agent Launcher
Manages both host process agents and containerized Claude Code agents
Includes Manager Agent for container orchestration and file coordination
"""

import asyncio
import json
import os
import logging
from typing import Dict, List, Optional, Union
import argparse
from dotenv import load_dotenv
import docker
from pathlib import Path

# Import existing components
from enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig
from orchestrator_mvp import MVPOrchestrator
from memory_client import MemoryClient

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ManagerAgent(EnhancedDiscordAgent):
    """
    Manager Agent that handles container orchestration, file coordination, and task delegation
    Runs as a host process but can spawn and manage Claude Code containers
    """
    
    def __init__(self, config: AgentConfig, orchestrator: MVPOrchestrator):
        super().__init__(config)
        self.orchestrator = orchestrator
        self.container_agents = {}
        self.shared_memory = None
        self.is_manager = True
        
        # Initialize shared memory client
        self._init_shared_memory()
        
        # Add manager-specific system prompt additions
        manager_prompt = """
        
        MANAGER AGENT CAPABILITIES:
        - You can spawn and manage Claude Code containers for complex coding tasks
        - You coordinate file sharing and task delegation between agents
        - You have access to shared memory across all agents
        - You can assign coding tasks to fullstackdev, coderdev1, coderdev2 containers
        - Use @spawn-agent <name> <workspace> to create new container agents
        - Use @list-agents to see all active agents
        - Use @assign-task <agent> <task> to delegate tasks
        
        You are the orchestrator and coordinator of the SuperAgent system.
        """
        
        if hasattr(self.config, 'system_prompt_additions'):
            self.config.system_prompt_additions += manager_prompt
        else:
            self.config.system_prompt_additions = manager_prompt
    
    def _init_shared_memory(self):
        """Initialize shared memory client"""
        try:
            postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
            self.shared_memory = MemoryClient(postgres_url)
            logger.info("✅ Manager Agent: Shared memory initialized")
        except Exception as e:
            logger.error(f"❌ Manager Agent: Failed to initialize shared memory: {e}")
    
    async def spawn_container_agent(self, name: str, workspace_path: str, discord_token: str, personality: str = "Helpful coding assistant"):
        """Spawn a new container agent"""
        try:
            logger.info(f"🚀 Manager Agent: Spawning container agent '{name}'")
            
            container_id = self.orchestrator.spawn_agent(
                name=name,
                workspace_path=workspace_path,
                discord_token=discord_token,
                personality=personality
            )
            
            self.container_agents[name] = {
                'container_id': container_id,
                'workspace': workspace_path,
                'discord_token': discord_token,
                'personality': personality,
                'status': 'running'
            }
            
            await self.send_management_message(f"✅ Successfully spawned container agent '{name}' (ID: {container_id[:12]})")
            return container_id
            
        except Exception as e:
            logger.error(f"❌ Manager Agent: Failed to spawn container agent '{name}': {e}")
            await self.send_management_message(f"❌ Failed to spawn container agent '{name}': {e}")
            return None
    
    async def list_all_agents(self):
        """List all agents (host and container)"""
        try:
            # Get orchestrator agent status
            container_agents = self.orchestrator.list_agents()
            
            status_message = "📊 **SuperAgent System Status**\n\n"
            
            # Manager status
            status_message += "🎯 **Manager Agent**: Active (Host Process)\n"
            
            # Container agents
            if container_agents:
                status_message += f"\n🐳 **Container Agents** ({len(container_agents)}):\n"
                for name, info in container_agents.items():
                    status_message += f"  • {name}: {info['status']} (ID: {info.get('id', 'unknown')})\n"
            else:
                status_message += "\n🐳 **Container Agents**: None\n"
            
            # Host process agents (this would need to be tracked separately)
            status_message += f"\n💻 **Host Process Agents**: Manager + others\n"
            
            await self.send_management_message(status_message)
            
        except Exception as e:
            logger.error(f"❌ Manager Agent: Error listing agents: {e}")
            await self.send_management_message(f"❌ Error listing agents: {e}")
    
    async def send_management_message(self, content: str):
        """Send a management message to Discord"""
        try:
            # Find a suitable channel to send management messages
            for guild in self.client.guilds:
                for channel in guild.channels:
                    if hasattr(channel, 'send') and 'general' in channel.name.lower():
                        await channel.send(f"🎯 **Manager**: {content}")
                        return
        except Exception as e:
            logger.error(f"❌ Manager Agent: Failed to send management message: {e}")
    
    async def process_manager_commands(self, message):
        """Process special manager commands"""
        content = message.content.lower()
        
        if content.startswith('@spawn-agent'):
            # Parse spawn command: @spawn-agent <name> <workspace_path>
            parts = message.content.split()
            if len(parts) >= 3:
                name = parts[1]
                workspace = ' '.join(parts[2:])
                
                # Use a default Discord token or get from config
                discord_token = os.getenv('DISCORD_TOKEN2') or os.getenv('DISCORD_TOKEN')
                
                if discord_token:
                    await self.spawn_container_agent(name, workspace, discord_token)
                else:
                    await self.send_management_message("❌ No Discord token available for container agent")
            else:
                await self.send_management_message("❌ Usage: @spawn-agent <name> <workspace_path>")
                
        elif content.startswith('@list-agents'):
            await self.list_all_agents()
            
        elif content.startswith('@system-health'):
            health = self.orchestrator.health_check()
            health_msg = "🔍 **System Health**:\n"
            for service, status in health.items():
                emoji = "✅" if status else "❌"
                health_msg += f"  • {service}: {emoji}\n"
            await self.send_management_message(health_msg)


class HybridMultiAgentLauncher:
    """
    Enhanced launcher that manages both host process agents and container agents
    Includes a Manager Agent for orchestration
    """
    
    def __init__(self, config_path: str = "agent_config.json"):
        self.config_path = config_path
        self.host_agents: Dict[str, EnhancedDiscordAgent] = {}
        self.container_agents: Dict[str, str] = {}  # agent_name -> container_id
        self.manager_agent: Optional[ManagerAgent] = None
        self.orchestrator: Optional[MVPOrchestrator] = None
        self.tasks: List[asyncio.Task] = []
        
        # Initialize orchestrator
        self._init_orchestrator()
    
    def _init_orchestrator(self):
        """Initialize the container orchestrator"""
        try:
            self.orchestrator = MVPOrchestrator()
            logger.info("✅ Container orchestrator initialized")
            
            # Check system health
            health = self.orchestrator.health_check()
            if not all(health.values()):
                logger.warning(f"⚠️  Some services are not healthy: {health}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize orchestrator: {e}")
            logger.info("🔄 Container functionality will be disabled")
    
    def load_config(self) -> dict:
        """Load agent configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Add default container agents if not present
        if 'container_agents' not in config:
            config['container_agents'] = {
                'fullstackdev': {
                    'type': 'container',
                    'workspace_path': '~/repos/SuperAgent',
                    'discord_token_env': 'DISCORD_TOKEN2',
                    'personality': 'Full-stack developer specializing in Python, Docker, and system architecture',
                    'capabilities': ['coding', 'file_operations', 'system_design']
                },
                'coderdev1': {
                    'type': 'container', 
                    'workspace_path': '~/repos/CryptoTaxCalc',
                    'discord_token_env': 'DISCORD_TOKEN3',
                    'personality': 'Backend developer focusing on data processing and API development',
                    'capabilities': ['coding', 'api_development', 'data_analysis']
                }
            }
        
        return config
    
    def create_agent_config(self, agent_name: str, agent_data: dict) -> AgentConfig:
        """Create AgentConfig from configuration data (existing logic)"""
        
        # Get API keys from environment
        api_keys = {
            'grok4': os.getenv('XAI_API_KEY'),
            'claude': os.getenv('ANTHROPIC_API_KEY'),
            'gemini': os.getenv('GOOGLE_AI_API_KEY'),
            'openai': os.getenv('OPENAI_API_KEY')
        }
        
        # Get bot tokens (try agent-specific first, then fall back to shared)
        bot_tokens = {
            'grok4': os.getenv('DISCORD_TOKEN_GROK'),
            'claude': os.getenv('DISCORD_TOKEN_CLAUDE') or os.getenv('DISCORD_TOKEN_GROK'),
            'gemini': os.getenv('DISCORD_TOKEN_GEMINI') or os.getenv('DISCORD_TOKEN_GROK'),
            'openai': os.getenv('DISCORD_TOKEN_O3') or os.getenv('DISCORD_TOKEN_GROK'),
            'manager': os.getenv('DISCORD_TOKEN_GROK')  # Manager uses primary token
        }
        
        llm_type = agent_data.get('llm_type', 'grok4')  # Default to grok4 for manager
        api_key = api_keys.get(llm_type)
        bot_token = bot_tokens.get(llm_type)
        
        if not api_key:
            raise ValueError(f"Missing API key for {llm_type}. Set environment variable.")
        
        if not bot_token:
            raise ValueError(f"Missing Discord bot token for {llm_type}. Set DISCORD_TOKEN_GROK or agent-specific token.")
        
        config = AgentConfig(
            name=agent_data.get('name', agent_name),
            bot_token=bot_token,
            server_id=os.getenv('DEFAULT_SERVER_ID', '1395578178973597799'),
            api_key=api_key,
            llm_type=llm_type,
            max_context_messages=agent_data.get('max_context_messages', 15),
            max_turns_per_thread=agent_data.get('max_turns_per_thread', 30),
            response_delay=agent_data.get('response_delay', 2.0),
            allowed_channels=agent_data.get('allowed_channels', []),
            ignore_bots=agent_data.get('ignore_bots', True),
            bot_allowlist=agent_data.get('bot_allowlist', [])
        )
        
        # Add model parameter for OpenAI
        if 'model' in agent_data:
            config.model = agent_data['model']
        
        # Add personality and system prompt additions
        if 'personality' in agent_data:
            config.personality = agent_data['personality']
        if 'system_prompt_additions' in agent_data:
            config.system_prompt_additions = agent_data['system_prompt_additions']
        
        return config
    
    async def launch_manager_agent(self):
        """Launch the Manager Agent"""
        if not self.orchestrator:
            logger.warning("⚠️  No orchestrator available, Manager Agent will have limited functionality")
        
        try:
            # Create manager agent config
            manager_config_data = {
                'name': 'SuperAgent Manager',
                'llm_type': 'grok4',  # Use Grok4 for manager
                'personality': 'Orchestrator and coordinator of the SuperAgent system',
                'system_prompt_additions': 'You manage containers, coordinate file sharing, and delegate tasks between agents.'
            }
            
            manager_config = self.create_agent_config('manager', manager_config_data)
            
            # Create manager agent with orchestrator
            self.manager_agent = ManagerAgent(manager_config, self.orchestrator)
            
            # Launch manager agent
            logger.info("🎯 Starting Manager Agent...")
            manager_task = asyncio.create_task(self.manager_agent.run())
            self.tasks.append(manager_task)
            
            logger.info("✅ Manager Agent launched successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to launch Manager Agent: {e}")
    
    async def launch_host_agent(self, agent_name: str, config: AgentConfig):
        """Launch a single host process agent (existing logic)"""
        try:
            logger.info(f"💻 Starting host agent: {agent_name}")
            agent = EnhancedDiscordAgent(config)
            self.host_agents[agent_name] = agent
            await agent.run()
        except Exception as e:
            logger.error(f"❌ Host agent {agent_name} failed: {e}")
    
    async def launch_container_agent(self, agent_name: str, agent_data: dict):
        """Launch a container agent via orchestrator"""
        if not self.orchestrator:
            logger.error(f"❌ Cannot launch container agent {agent_name}: No orchestrator available")
            return
        
        try:
            logger.info(f"🐳 Starting container agent: {agent_name}")
            
            workspace_path = os.path.expanduser(agent_data['workspace_path'])
            discord_token_env = agent_data.get('discord_token_env', 'DISCORD_TOKEN2')
            discord_token = os.getenv(discord_token_env)
            
            if not discord_token:
                logger.error(f"❌ Missing Discord token for {agent_name}: {discord_token_env}")
                return
            
            container_id = self.orchestrator.spawn_agent(
                name=agent_name,
                workspace_path=workspace_path,
                discord_token=discord_token,
                personality=agent_data.get('personality', 'Helpful coding assistant')
            )
            
            self.container_agents[agent_name] = container_id
            logger.info(f"✅ Container agent {agent_name} launched: {container_id[:12]}")
            
        except Exception as e:
            logger.error(f"❌ Failed to launch container agent {agent_name}: {e}")
    
    async def launch_all_agents(self, agent_names: List[str] = None):
        """Launch all configured agents (host and container) plus Manager Agent"""
        config_data = self.load_config()
        
        # Always launch Manager Agent first
        await self.launch_manager_agent()
        await asyncio.sleep(3)  # Give manager time to initialize
        
        # Determine which agents to launch
        host_agents_to_launch = agent_names or list(config_data['agents'].keys())
        container_agents_to_launch = list(config_data.get('container_agents', {}).keys())
        
        if agent_names:
            # Filter container agents if specific agents requested
            container_agents_to_launch = [name for name in container_agents_to_launch if name in agent_names]
        
        logger.info(f"🚀 Launching hybrid agent system:")
        logger.info(f"   💻 Host agents: {len(host_agents_to_launch)} ({', '.join(host_agents_to_launch)})")
        logger.info(f"   🐳 Container agents: {len(container_agents_to_launch)} ({', '.join(container_agents_to_launch)})")
        
        # Launch host process agents
        for agent_name in host_agents_to_launch:
            if agent_name not in config_data['agents']:
                logger.warning(f"⚠️  Agent {agent_name} not found in config")
                continue
            
            try:
                agent_config = self.create_agent_config(agent_name, config_data['agents'][agent_name])
                task = asyncio.create_task(self.launch_host_agent(agent_name, agent_config))
                self.tasks.append(task)
                await asyncio.sleep(2)  # Small delay between launches
            except Exception as e:
                logger.error(f"❌ Failed to create host agent {agent_name}: {e}")
        
        # Launch container agents
        for agent_name in container_agents_to_launch:
            if agent_name not in config_data['container_agents']:
                logger.warning(f"⚠️  Container agent {agent_name} not found in config")
                continue
            
            try:
                await self.launch_container_agent(agent_name, config_data['container_agents'][agent_name])
                await asyncio.sleep(3)  # Longer delay for container agents
            except Exception as e:
                logger.error(f"❌ Failed to create container agent {agent_name}: {e}")
        
        if not self.tasks and not self.container_agents:
            logger.error("❌ No agents were successfully created")
            return
        
        total_agents = len(self.tasks) + len(self.container_agents)
        logger.info(f"✅ SuperAgent hybrid system launched with {total_agents} agents")
        
        # Wait for host process tasks (containers run independently)
        if self.tasks:
            try:
                await asyncio.gather(*self.tasks)
            except KeyboardInterrupt:
                logger.info("🛑 Shutdown signal received")
            except Exception as e:
                logger.error(f"❌ Error in agent execution: {e}")
            finally:
                await self.shutdown_all_agents()
        else:
            # If only container agents, wait for interrupt
            try:
                while True:
                    await asyncio.sleep(10)
                    logger.info(f"🔄 System running with {len(self.container_agents)} container agents")
            except KeyboardInterrupt:
                logger.info("🛑 Shutdown signal received")
                await self.shutdown_all_agents()
    
    async def shutdown_all_agents(self):
        """Gracefully shutdown all agents (host and container)"""
        logger.info("🛑 Shutting down SuperAgent system...")
        
        # Cancel host process tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop container agents
        if self.orchestrator and self.container_agents:
            logger.info(f"🐳 Stopping {len(self.container_agents)} container agents...")
            for agent_name in list(self.container_agents.keys()):
                try:
                    self.orchestrator.stop_agent(agent_name)
                    self.orchestrator.remove_agent(agent_name)
                    logger.info(f"✅ Stopped container agent: {agent_name}")
                except Exception as e:
                    logger.error(f"❌ Error stopping container agent {agent_name}: {e}")
        
        logger.info("✅ All agents shut down")


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='SuperAgent Hybrid Multi-Agent Launcher')
    parser.add_argument(
        '--agents', 
        nargs='*',
        help='Specific agents to launch (default: all configured agents)'
    )
    parser.add_argument(
        '--config',
        default='agent_config.json',
        help='Path to agent configuration file'
    )
    parser.add_argument(
        '--list-agents',
        action='store_true',
        help='List available agents and exit'
    )
    parser.add_argument(
        '--manager-only',
        action='store_true',
        help='Launch only the Manager Agent'
    )
    
    args = parser.parse_args()
    
    launcher = HybridMultiAgentLauncher(args.config)
    
    if args.list_agents:
        try:
            config = launcher.load_config()
            print("📋 Available SuperAgent Agents:")
            print("\n💻 Host Process Agents:")
            for agent_name, agent_data in config['agents'].items():
                print(f"  - {agent_name} ({agent_data['llm_type']})")
            
            print("\n🐳 Container Agents:")
            for agent_name, agent_data in config.get('container_agents', {}).items():
                print(f"  - {agent_name} (container: {agent_data['workspace_path']})")
            
            print("\n🎯 Manager Agent: Always included (orchestrator + Discord identity)")
        except Exception as e:
            print(f"❌ Error loading config: {e}")
        return
    
    # Check required environment variables
    required_env_vars = ['DISCORD_TOKEN_GROK', 'DEFAULT_SERVER_ID']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Check Docker availability for container agents
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        logger.info("✅ Docker daemon available - container agents supported")
    except Exception as e:
        logger.warning(f"⚠️  Docker daemon not available - container agents disabled: {e}")
    
    # Check for at least one LLM API key
    llm_keys = {
        'XAI_API_KEY': 'grok4',
        'ANTHROPIC_API_KEY': 'claude', 
        'GOOGLE_AI_API_KEY': 'gemini'
    }
    
    available_llms = [name for env_var, name in llm_keys.items() if os.getenv(env_var)]
    
    if not available_llms:
        logger.error("❌ No LLM API keys found. Set at least one of: XAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY")
        return
    
    logger.info(f"✅ Available LLMs: {', '.join(available_llms)}")
    
    # Handle manager-only mode
    if args.manager_only:
        args.agents = []  # No host agents, just manager
    
    try:
        asyncio.run(launcher.launch_all_agents(args.agents))
    except KeyboardInterrupt:
        logger.info("🛑 SuperAgent launcher interrupted by user")
    except Exception as e:
        logger.error(f"❌ SuperAgent launcher error: {e}")


if __name__ == "__main__":
    main()