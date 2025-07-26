#!/usr/bin/env python3
"""
Unified Agent Orchestrator
Consolidates all fragmented launch mechanisms into a single interface
Supports process-based, container-based, and hybrid deployments
"""

import asyncio
import docker
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Import existing components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig
from memory_client import MemoryClient
from agents.devops.devops_memory_manager import DevOpsMemoryManager
from orchestrator_mvp import MVPOrchestrator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-orchestrator")


@dataclass
class DeploymentRequest:
    """Unified deployment request structure"""
    agent_name: str
    agent_type: str  # 'grok4_agent', 'claude', 'fullstackdev', etc.
    deployment_type: str  # 'process', 'container', 'isolated_container'
    team: Optional[str] = None
    config_overrides: Optional[Dict[str, Any]] = None
    environment_overrides: Optional[Dict[str, str]] = None
    auto_start: bool = True


@dataclass
class DeploymentResult:
    """Result of a deployment operation"""
    success: bool
    agent_name: str
    deployment_type: str
    identifier: str  # process_id, container_id, etc.
    status: str
    message: str
    config: Dict[str, Any]
    discord_bot_name: Optional[str] = None
    channel_access: Optional[List[str]] = None


class AgentOrchestrator:
    """
    Unified Agent Orchestrator
    Consolidates all launch mechanisms into a single interface
    """

    def __init__(self, memory_client: Optional[MemoryClient] = None):
        """Initialize the orchestrator with optional memory client"""

        # Memory management
        if memory_client:
            self.memory_client = memory_client
        else:
            postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            self.memory_client = MemoryClient(postgres_url, openai_api_key)

        self.devops_memory = DevOpsMemoryManager(self.memory_client)

        # Docker client for container operations
        self.docker_client = self._init_docker_client()

        # Container orchestrator
        self.container_orchestrator = MVPOrchestrator()

        # Active deployments tracking
        self.active_deployments: Dict[str, DeploymentResult] = {}

        # Load configuration templates
        self.agent_configs = self._load_agent_configurations()

        logger.info("🎯 Unified Agent Orchestrator initialized")

    def _init_docker_client(self) -> Optional[docker.DockerClient]:
        """Initialize Docker client with robust connection handling"""
        try:
            client = docker.from_env()
            client.ping()
            logger.info("✅ Connected to Docker daemon")
            return client
        except Exception as e:
            logger.warning(f"⚠️ Docker connection failed: {e}")
            logger.info("Container deployments will be disabled")
            return None

    def _load_agent_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Load agent configuration templates from multiple sources"""
        configs = {}

        # Load from agent_config.json
        config_files = [
            "agent_config.json",
            "configs/devops_config.json",
            "agent_config_hybrid.json",
            "claude_container_config.json"
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        data = json.load(f)

                        # Handle different config file structures
                        if 'agents' in data:
                            configs.update(data['agents'])
                        elif 'container_agent_templates' in data:
                            configs.update(data['container_agent_templates'])
                        elif 'non_container_agents' in data:
                            configs.update(data['non_container_agents'])
                        else:
                            # Assume it's a flat config structure
                            configs.update(data)

                    logger.info(f"📋 Loaded configurations from {config_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load {config_file}: {e}")

        # Add default configurations if not present
        self._add_default_configurations(configs)

        logger.info(f"🎯 Loaded {len(configs)} agent type configurations")
        return configs

    def _add_default_configurations(self, configs: Dict[str, Dict[str, Any]]):
        """Add default configurations for common agent types"""

        defaults = {
            "grok4_agent": {
                "llm_type": "grok4",
                "deployment_type": "process",
                "script": "enhanced_discord_agent.py",
                "config_key": "grok4_agent",
                "token_env": "DISCORD_TOKEN_GROK4",
                "api_key_env": "XAI_API_KEY"
            },
            "claude_agent": {
                "llm_type": "claude",
                "deployment_type": "process",
                "script": "enhanced_discord_agent.py",
                "config_key": "claude_agent",
                "token_env": "DISCORD_TOKEN_CLAUDE",
                "api_key_env": "ANTHROPIC_API_KEY"
            },
            "fullstackdev": {
                "llm_type": "claude",
                "deployment_type": "container",
                "image": "superagent/official-claude-code:latest",
                "token_env": "DISCORD_TOKEN2",
                "api_key_env": "ANTHROPIC_API_KEY"
            }
        }

        for agent_type, config in defaults.items():
            if agent_type not in configs:
                configs[agent_type] = config

    async def deploy_agent(self, request: DeploymentRequest) -> DeploymentResult:
        """
        Deploy an agent using the appropriate mechanism

        Args:
            request: Deployment request with agent details

        Returns:
            DeploymentResult with success status and details
        """

        logger.info(f"🚀 Deploying {request.agent_type} agent: {request.agent_name}")

        try:
            # Ensure memory system is connected
            if not self.memory_client.pool:
                await self.memory_client.connect()

            # Get agent configuration
            if request.agent_type not in self.agent_configs:
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type=request.deployment_type,
                    identifier="",
                    status="failed",
                    message=f"Unknown agent type: {request.agent_type}",
                    config={}
                )

            agent_config = self.agent_configs[request.agent_type].copy()

            # Apply overrides
            if request.config_overrides:
                agent_config.update(request.config_overrides)

            # Determine deployment type
            deployment_type = request.deployment_type or agent_config.get('deployment_type', 'process')

            # Route to appropriate deployment method
            if deployment_type == 'container':
                result = await self._deploy_container_agent(request, agent_config)
            elif deployment_type == 'isolated_container':
                result = await self._deploy_isolated_container_agent(request, agent_config)
            elif deployment_type == 'process':
                result = await self._deploy_process_agent(request, agent_config)
            else:
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type=deployment_type,
                    identifier="",
                    status="failed",
                    message=f"Unsupported deployment type: {deployment_type}",
                    config={}
                )

            # Store deployment in memory system
            if result.success:
                await self._store_deployment_memory(request, result)
                self.active_deployments[request.agent_name] = result
                logger.info(f"✅ Successfully deployed {request.agent_name}")
            else:
                logger.error(f"❌ Failed to deploy {request.agent_name}: {result.message}")

            return result

        except Exception as e:
            logger.error(f"💥 Deployment error for {request.agent_name}: {e}")
            return DeploymentResult(
                success=False,
                agent_name=request.agent_name,
                deployment_type=request.deployment_type,
                identifier="",
                status="failed",
                message=str(e),
                config={}
            )

    async def _deploy_process_agent(self, request: DeploymentRequest, config: Dict[str, Any]) -> DeploymentResult:
        """Deploy agent as a host process using enhanced_discord_agent.py"""

        try:
            # Build command for process deployment
            script = config.get('script', 'enhanced_discord_agent.py')
            config_key = config.get('config_key', request.agent_type)

            cmd = [
                sys.executable, script,
                '--config-key', config_key
            ]

            # Set up environment
            env = os.environ.copy()

            # Add token and API key
            token_env = config.get('token_env', 'DISCORD_TOKEN_GROK4')
            api_key_env = config.get('api_key_env', 'XAI_API_KEY')

            if not env.get(token_env):
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type='process',
                    identifier="",
                    status="failed",
                    message=f"Missing environment variable: {token_env}",
                    config=config
                )

            # Apply environment overrides
            if request.environment_overrides:
                env.update(request.environment_overrides)

            # Start the process
            if request.auto_start:
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Give it a moment to start
                await asyncio.sleep(2)

                # Check if process is still running
                if process.poll() is None:
                    status = "running"
                    message = f"Process started successfully (PID: {process.pid})"
                    identifier = f"process_{process.pid}"
                else:
                    status = "failed"
                    stdout, stderr = process.communicate()
                    message = f"Process failed to start: {stderr or stdout}"
                    identifier = ""
            else:
                status = "configured"
                message = "Process configured but not started"
                identifier = f"process_configured_{request.agent_name}"

            return DeploymentResult(
                success=(status in ['running', 'configured']),
                agent_name=request.agent_name,
                deployment_type='process',
                identifier=identifier,
                status=status,
                message=message,
                config=config,
                discord_bot_name=self._get_discord_bot_name(config, request.agent_name)
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                agent_name=request.agent_name,
                deployment_type='process',
                identifier="",
                status="failed",
                message=f"Process deployment error: {e}",
                config=config
            )

    async def _deploy_container_agent(self, request: DeploymentRequest, config: Dict[str, Any]) -> DeploymentResult:
        """Deploy agent as a Docker container using existing working containers"""

        try:
            import docker
            # Use existing working containers instead of creating new ones
            # Based on the working shell script approach

            # Map agent types to existing working containers
            container_mapping = {
                'fullstackdev': 'claude-fullstackdev-persistent',
                'coderdev1': 'claude-fullstackdev-persistent', # Use same container for now
                'coderdev2': 'claude-isolated-discord',
                'claude': 'claude-fullstackdev-persistent'
            }

            # Get container name
            existing_container = container_mapping.get(request.agent_type)
            if not existing_container:
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type='container',
                    identifier="",
                    status="failed",
                    message=f"No container mapping for agent type: {request.agent_type}",
                    config=config
                )

            # Try to connect to Docker
            docker_client = None
            try:
                docker_client = docker.DockerClient(base_url='unix:///Users/greg/.colima/default/docker.sock')
                docker_client.ping()
            except Exception:
                try:
                    docker_client = docker.from_env()
                    docker_client.ping()
                except Exception:
                    pass

            if not docker_client:
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type='container',
                    identifier="",
                    status="failed",
                    message="No working Docker client available",
                    config=config
                )

            # Check if container exists and is running
            try:
                container = docker_client.containers.get(existing_container)

                if container.status != 'running':
                    # Start the container if it's stopped
                    container.start()
                    logger.info(f"Started existing container: {existing_container}")

                # Send a notification that the agent is now active
                # This simulates "deployment" by telling the container about the new agent role
                agent_personality = config.get('environment', {}).get('AGENT_PERSONALITY',
                    f'{request.agent_type} agent deployed via SuperAgent orchestrator')

                # Execute a command in the container to notify it of the new agent role
                try:
                    result = container.exec_run([
                        'claude', '--dangerously-skip-permissions', '--print',
                        f'🚀 New agent deployed: {request.agent_name} ({request.agent_type}) - {agent_personality[:100]}...'
                    ], user='node')

                    if result.exit_code == 0:
                        logger.info(f"Successfully notified container about new agent: {request.agent_name}")
                    else:
                        logger.warning(f"Container notification failed: {result.output.decode()}")

                except Exception as e:
                    logger.warning(f"Could not send container notification: {e}")

                # Return successful deployment
                return DeploymentResult(
                    success=True,
                    agent_name=request.agent_name,
                    deployment_type='container',
                    identifier=container.id,
                    status="running",
                    message=f"Using existing container {existing_container} - agent role activated",
                    config=config,
                    discord_bot_name=f"Claude{request.agent_type.title()}"
                )

            except docker.errors.NotFound:
                return DeploymentResult(
                    success=False,
                    agent_name=request.agent_name,
                    deployment_type='container',
                    identifier="",
                    status="failed",
                    message=f"Required container {existing_container} not found. Please run the container setup first.",
                    config=config
                )


        except Exception as e:
            return DeploymentResult(
                success=False,
                agent_name=request.agent_name,
                deployment_type='container',
                identifier="",
                status="failed",
                message=f"Container deployment error: {e}",
                config=config
            )

    async def _deploy_isolated_container_agent(self, request: DeploymentRequest, config: Dict[str, Any]) -> DeploymentResult:
        """Deploy agent as an isolated Docker container"""

        # For now, use the same container deployment but with isolation settings
        config_with_isolation = config.copy()
        config_with_isolation['volumes'] = {}  # No shared volumes for isolation

        result = await self._deploy_container_agent(request, config_with_isolation)
        result.deployment_type = 'isolated_container'

        return result

    def _get_discord_bot_name(self, config: Dict[str, Any], agent_name: str) -> str:
        """Extract Discord bot name from configuration or generate one"""

        # Check if config has a specific Discord name
        discord_name = config.get('discord_name')
        if discord_name:
            return discord_name

        # Generate based on agent type and name
        agent_type = config.get('llm_type', 'Agent')
        if agent_type == 'grok4':
            return f"Grok4{agent_name.title()}"
        elif agent_type == 'claude':
            return f"Claude{agent_name.title()}"
        elif agent_type == 'gemini':
            return f"Gemini{agent_name.title()}"
        else:
            return f"{agent_type.title()}{agent_name.title()}"

    async def _store_deployment_memory(self, request: DeploymentRequest, result: DeploymentResult):
        """Store deployment information in PostgreSQL memory system"""

        try:
            deployment_data = {
                'name': request.agent_name,
                'agent_type': request.agent_type,
                'deployment_type': result.deployment_type,
                'team': request.team or 'default',
                'identifier': result.identifier,
                'status': result.status,
                'discord_bot_name': result.discord_bot_name,
                'config': result.config,
                'timestamp': datetime.now().isoformat()
            }

            memory_id = await self.devops_memory.store_deployment_memory(deployment_data)
            logger.debug(f"📝 Stored deployment memory with ID: {memory_id}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to store deployment memory: {e}")

    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of all active agents"""

        active_agents = []

        # Check process-based agents
        for name, deployment in self.active_deployments.items():
            if deployment.deployment_type == 'process':
                # Check if process is still running
                if deployment.identifier.startswith('process_'):
                    try:
                        pid = int(deployment.identifier.split('_')[1])
                        if self._is_process_running(pid):
                            active_agents.append({
                                'name': name,
                                'type': deployment.deployment_type,
                                'status': 'running',
                                'discord_name': deployment.discord_bot_name,
                                'identifier': deployment.identifier
                            })
                    except (ValueError, IndexError):
                        pass

        # Check container-based agents
        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(
                    filters={'label': 'superagent.managed=true'}
                )

                for container in containers:
                    active_agents.append({
                        'name': container.name,
                        'type': 'container',
                        'status': container.status,
                        'discord_name': self._extract_discord_name_from_container(container),
                        'identifier': container.id
                    })
            except Exception as e:
                logger.warning(f"⚠️ Failed to get container list: {e}")

        return active_agents

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            # Fallback without psutil
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def _extract_discord_name_from_container(self, container) -> str:
        """Extract Discord bot name from container"""

        # Try to get from container labels
        labels = container.labels
        agent_type = labels.get('superagent.type', 'unknown')

        # Generate name based on container name and type
        container_name = container.name
        if agent_type == 'fullstackdev':
            return f"Claude_FullStackDev"
        elif agent_type == 'coderdev1':
            return f"CryptoTax_CoderDev1"
        else:
            return f"{agent_type.title()}Bot"

    async def stop_agent(self, agent_name: str) -> bool:
        """Stop a specific agent"""

        if agent_name not in self.active_deployments:
            logger.warning(f"⚠️ Agent {agent_name} not found in active deployments")
            return False

        deployment = self.active_deployments[agent_name]

        try:
            if deployment.deployment_type in ['container', 'isolated_container']:
                # Stop container
                if self.docker_client:
                    container = self.docker_client.containers.get(deployment.identifier)
                    container.stop()
                    container.remove()
                    logger.info(f"🛑 Stopped container agent: {agent_name}")

            elif deployment.deployment_type == 'process':
                # Stop process
                if deployment.identifier.startswith('process_'):
                    try:
                        pid = int(deployment.identifier.split('_')[1])
                        os.kill(pid, 9)  # SIGKILL
                        logger.info(f"🛑 Stopped process agent: {agent_name}")
                    except (ValueError, IndexError, OSError) as e:
                        logger.warning(f"⚠️ Failed to stop process {deployment.identifier}: {e}")

            # Remove from active deployments
            del self.active_deployments[agent_name]

            # Store stop event in memory
            await self.devops_memory.store_system_event(
                event_type='agent_stopped',
                event_data={
                    'agent_name': agent_name,
                    'deployment_type': deployment.deployment_type,
                    'identifier': deployment.identifier
                },
                severity='info'
            )

            return True

        except Exception as e:
            logger.error(f"💥 Error stopping agent {agent_name}: {e}")
            return False

    async def get_deployment_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent deployment history using vector search"""

        try:
            memories = await self.devops_memory.search_deployment_history(
                query="deployment agent started",
                limit=limit
            )

            history = []
            for memory in memories:
                metadata = memory.get('metadata', {})
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        continue

                history.append({
                    'agent_name': metadata.get('agent_target'),
                    'agent_type': metadata.get('agent_type'),
                    'team': metadata.get('team'),
                    'deployment_type': metadata.get('deployment_type'),
                    'timestamp': metadata.get('timestamp'),
                    'content': memory.get('content')
                })

            return history

        except Exception as e:
            logger.error(f"💥 Error getting deployment history: {e}")
            return []


# Factory functions for easy integration
async def create_orchestrator(memory_client: Optional[MemoryClient] = None) -> AgentOrchestrator:
    """Factory function to create and initialize orchestrator"""
    orchestrator = AgentOrchestrator(memory_client)

    # Ensure memory connection
    if not orchestrator.memory_client.pool:
        await orchestrator.memory_client.connect()

    return orchestrator


# Command-line interface for direct usage
async def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Unified Agent Orchestrator')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy an agent')
    deploy_parser.add_argument('agent_type', help='Type of agent to deploy')
    deploy_parser.add_argument('--name', required=True, help='Name for the agent')
    deploy_parser.add_argument('--deployment-type', choices=['process', 'container', 'isolated_container'], help='Deployment type')
    deploy_parser.add_argument('--team', help='Team name')
    deploy_parser.add_argument('--no-start', action='store_true', help="Don't start the agent automatically")

    # List command
    list_parser = subparsers.add_parser('list', help='List active agents')

    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop an agent')
    stop_parser.add_argument('agent_name', help='Name of agent to stop')

    # History command
    history_parser = subparsers.add_parser('history', help='Show deployment history')
    history_parser.add_argument('--limit', type=int, default=10, help='Number of entries to show')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create orchestrator
    orchestrator = await create_orchestrator()

    try:
        if args.command == 'deploy':
            request = DeploymentRequest(
                agent_name=args.name,
                agent_type=args.agent_type,
                deployment_type=args.deployment_type,
                team=args.team,
                auto_start=not args.no_start
            )

            result = await orchestrator.deploy_agent(request)

            if result.success:
                print(f"✅ Successfully deployed {result.agent_name}")
                print(f"   Type: {result.deployment_type}")
                print(f"   Status: {result.status}")
                print(f"   Discord Name: {result.discord_bot_name}")
                print(f"   Identifier: {result.identifier}")
            else:
                print(f"❌ Deployment failed: {result.message}")

        elif args.command == 'list':
            agents = await orchestrator.get_active_agents()

            if agents:
                print("🤖 Active Agents:")
                for agent in agents:
                    print(f"   • {agent['name']} ({agent['type']}) - {agent['status']}")
                    if agent.get('discord_name'):
                        print(f"     Discord: @{agent['discord_name']}")
            else:
                print("No active agents found")

        elif args.command == 'stop':
            success = await orchestrator.stop_agent(args.agent_name)

            if success:
                print(f"✅ Successfully stopped {args.agent_name}")
            else:
                print(f"❌ Failed to stop {args.agent_name}")

        elif args.command == 'history':
            history = await orchestrator.get_deployment_history(args.limit)

            if history:
                print(f"📜 Recent Deployment History ({len(history)} entries):")
                for entry in history:
                    print(f"   • {entry['agent_name']} ({entry['agent_type']}) - {entry['timestamp']}")
                    print(f"     Team: {entry['team']}, Type: {entry['deployment_type']}")
            else:
                print("No deployment history found")

    finally:
        # Clean up
        await orchestrator.memory_client.close()


if __name__ == "__main__":
    asyncio.run(main())
