#!/usr/bin/env python3
"""
MCP-Based AI DevOps Agent for SuperAgent
Uses MCP Discord integration for consistency with other agents
"""

import asyncio
import docker
import json
import logging
import os
import psutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel
from dataclasses import dataclass
import traceback

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for troubleshooting
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_devops_agent.log'),
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

class DevOpsResponse(BaseModel):
    """Structured response from DevOps agent"""
    message: str
    action_taken: Optional[str] = None
    needs_followup: bool = False
    command_suggestions: List[str] = []

class MCPDevOpsAgent:
    """
    MCP-based AI DevOps Agent that uses Claude LLM and MCP Discord integration
    for managing SuperAgent infrastructure with natural language understanding.
    """
    
    def __init__(self, config_path: str = "configs/devops_config.json"):
        # Load environment and config
        self.config = self._load_config(config_path)
        
        # Set up logging
        self.logger = logging.getLogger('MCPDevOpsAgent')
        self.logger.info("MCP DevOps Agent initializing...")
        
        # Initialize LLM clients (prefer OpenAI for structured outputs)
        self.openai = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
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
        
        # Memory management (SQLite-based like other agents)
        self.memory_db_path = "data/devops_memory.db"
        self._init_memory_db()
        
        # Message deduplication
        self.processed_messages = set()
        self.last_response_time = {}
        
        # Cache for dynamic agent discovery (initialize before system knowledge)
        self._agent_types_cache = None
        self._cache_timestamp = None
        
        # MCP Discord configuration
        self.mcp_command, self.mcp_args = self._load_mcp_config()
        
        # AI conversation context
        self.system_knowledge = self._build_system_knowledge()
        
    def _load_config(self, config_path: str) -> dict:
        """Load DevOps agent configuration"""
        default_config = {
            "personality": "Expert DevOps engineer with deep knowledge of containerization and system administration",
            "health_check_interval": 60,
            "auto_recovery": True,
            "max_agents": 20,
            "claude_model": "claude-3-5-sonnet-20241022",
            "max_context_messages": 15,
            "response_delay": 2.0
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return default_config
    
    def _load_mcp_config(self) -> Tuple[str, List[str]]:
        """Load MCP Discord configuration"""
        try:
            mcp_config_path = Path(__file__).parent.parent / "mcp.json"
            with open(mcp_config_path, "r") as f:
                mcp_config = json.load(f)
            
            # Use the existing Discord MCP server config
            discord_config = mcp_config.get("mcpServers", {}).get("discord-grok", {})
            command = discord_config.get("command", "uv")
            args = discord_config.get("args", [])
            
            # Update token to use DevOps token
            if "--token" in args:
                token_index = args.index("--token") + 1
                if token_index < len(args):
                    args[token_index] = os.getenv('DISCORD_TOKEN_DEVOPS', args[token_index])
            
            self.logger.info(f"MCP Discord config loaded: {command} {args}")
            return command, args
            
        except Exception as e:
            self.logger.error(f"Failed to load MCP config: {e}")
            # Fallback configuration
            return "python3", ["-m", "discord_mcp", 
                             "--token", os.getenv('DISCORD_TOKEN_DEVOPS', ''),
                             "--server-id", os.getenv('DEFAULT_SERVER_ID', '')]
    
    def _init_docker(self) -> Optional[docker.DockerClient]:
        """Initialize Docker client with connection fallback"""
        docker_client = None
        connection_error = None
        
        try:
            # First try from environment
            docker_client = docker.from_env()
            docker_client.ping()
            self.logger.info("✅ Connected to Docker daemon via environment")
            return docker_client
        except Exception as e1:
            connection_error = e1
            
            # Try common socket paths
            socket_paths = [
                "/var/run/docker.sock",
                "/Users/greg/.colima/default/docker.sock",
                os.path.expanduser("~/.colima/default/docker.sock")
            ]
            
            for socket_path in socket_paths:
                if os.path.exists(socket_path):
                    try:
                        docker_client = docker.DockerClient(base_url=f"unix://{socket_path}")
                        docker_client.ping()
                        self.logger.info(f"✅ Connected to Docker daemon via {socket_path}")
                        return docker_client
                    except Exception as e2:
                        self.logger.debug(f"Failed to connect via {socket_path}: {e2}")
                        continue
            
            self.logger.warning(f"⚠️ Failed to connect to Docker daemon: {connection_error}")
            self.logger.info("Docker functionality will be limited until connection is restored")
            return None
    
    def _init_memory_db(self):
        """Initialize SQLite memory database like other agents"""
        os.makedirs(os.path.dirname(self.memory_db_path), exist_ok=True)
        
        with sqlite3.connect(self.memory_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    thread_id TEXT,
                    user_id TEXT,
                    username TEXT,
                    message_content TEXT,
                    response_content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    agent_name TEXT DEFAULT 'DevOpsAgent'
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state_type TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_registry (
                    agent_name TEXT PRIMARY KEY,
                    agent_type TEXT,
                    container_id TEXT,
                    status TEXT,
                    config TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
        
        self.logger.info("Memory database initialized")
    
    async def _register_agent(self, name: str, agent_type: str, identifier: str, status: str, config: Dict[str, Any]):
        """Register an agent in the registry"""
        with sqlite3.connect(self.memory_db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO agent_registry 
                (agent_name, agent_type, container_id, status, config, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, agent_type, identifier, status, json.dumps(config)))
            conn.commit()
    
    def _get_available_agent_types(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically discover available agent types from configuration files"""
        # Cache for 5 minutes to avoid constant file reads
        if (self._agent_types_cache and self._cache_timestamp and 
            (datetime.now() - self._cache_timestamp).seconds < 300):
            return self._agent_types_cache
        
        available_types = {}
        
        # 1. Load from DevOps config (container agents)
        container_templates = self.config.get('container_agent_templates', {})
        for agent_type, template in container_templates.items():
            available_types[agent_type] = {
                'source': 'devops_container_config',
                'type': 'container',
                'image': template.get('image', 'unknown'),
                'capabilities': template.get('capabilities', []),
                'personality': template.get('environment', {}).get('AGENT_PERSONALITY', 'General AI assistant'),
                'labels': template.get('labels', {}),
                'deployable': template.get('deployable', True)
            }
        
        # 2. Load from DevOps config (non-container agents)
        non_container_templates = self.config.get('non_container_agents', {})
        for agent_type, template in non_container_templates.items():
            available_types[agent_type] = {
                'source': 'devops_non_container_config',
                'type': 'non_container',
                'script': template.get('script', 'unknown'),
                'capabilities': template.get('capabilities', []),  
                'personality': template.get('description', 'General AI assistant'),
                'deployable': template.get('deployable', True)
            }
        
        # 3. Load from main agent config (for reference)
        try:
            agent_config_path = Path(__file__).parent.parent / "agent_config.json"
            if agent_config_path.exists():
                with open(agent_config_path, 'r') as f:
                    agent_config = json.load(f)
                    
                agents = agent_config.get('agents', {})
                for agent_key, agent_data in agents.items():
                    # Extract agent type from key (e.g., "grok4_agent" -> "grok4") 
                    agent_type = agent_key.replace('_agent', '')
                    
                    if agent_type not in available_types:
                        available_types[agent_type] = {
                            'source': 'agent_config',
                            'image': 'N/A - Config only',
                            'capabilities': [],
                            'personality': agent_data.get('personality', ''),
                            'llm_type': agent_data.get('llm_type', 'unknown'),
                            'deployable': False  # Config only, no deployment template
                        }
                    else:
                        # Merge additional info
                        available_types[agent_type]['llm_type'] = agent_data.get('llm_type', 'unknown')
                        if not available_types[agent_type]['personality']:
                            available_types[agent_type]['personality'] = agent_data.get('personality', '')
        except Exception as e:
            self.logger.debug(f"Could not load agent_config.json: {e}")
        
        # 4. Check available Docker images (only for container agents)
        if self.docker_client:
            try:
                images = self.docker_client.images.list()
                
                for agent_type, agent_info in available_types.items():
                    if agent_info.get('type') == 'container':
                        # Check if there's a suitable image available
                        required_image = agent_info.get('image', '')
                        image_available = any(required_image in (tag for tag in img.tags or []) 
                                            for img in images)
                        available_types[agent_type]['image_available'] = image_available
                    else:
                        # Non-container agents don't need Docker images
                        available_types[agent_type]['image_available'] = True
                    
            except Exception as e:
                self.logger.debug(f"Could not check Docker images: {e}")
        
        # Update cache
        self._agent_types_cache = available_types
        self._cache_timestamp = datetime.now()
        
        return available_types
    
    def _get_available_agent_types_description(self) -> str:
        """Generate description of available agent types"""
        agent_types = self._get_available_agent_types()
        
        if not agent_types:
            return "- No agent types currently configured"
        
        descriptions = []
        for agent_type, info in agent_types.items():
            # Determine status
            deployable = info.get('deployable', False)
            image_available = info.get('image_available', True)
            agent_type_icon = "🐳" if info.get('type') == 'container' else "🧠"
            
            if deployable and image_available:
                status = "✅"
            elif deployable and not image_available:
                status = "⚠️"  # Deployable but missing image
            else:
                status = "❌"  # Not deployable
            
            capabilities = ", ".join(info.get('capabilities', [])) or "general"
            personality = info.get('personality', 'AI assistant')
            
            # Show container vs non-container type
            type_info = f"({info.get('type', 'unknown')})"
            
            descriptions.append(f"- {status} {agent_type_icon} **{agent_type}**: {personality} {type_info}")
        
        return "\n".join(descriptions)
    
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
{self._get_available_agent_types_description()}

CONTAINER MANAGEMENT:
- All agents run in isolated Docker containers
- Standard image: superagent/claude-code:latest
- Network: superagent-network for inter-container communication
- Volumes: Workspace mounts for file access
- Environment: API keys, Discord tokens, agent configs

DISCORD INTEGRATION:
- Uses MCP Discord server for consistent messaging
- Responds to mentions and direct messages
- Can execute commands and provide system insights
- Supports file uploads for logs and configurations

CURRENT CAPABILITIES:
- Deploy/stop/restart agents
- Monitor system health and resources
- Manage teams and task assignments
- View logs and troubleshoot issues
- Auto-recovery for failed services
- Performance optimization recommendations

PERSONALITY:
- Expert DevOps engineer with deep containerization knowledge
- Proactive problem-solving and optimization suggestions
- Clear communication with both technical and non-technical users
- Autonomous decision-making within defined parameters
- Safety-first approach to system changes

COMMAND PATTERNS:
- "deploy grok4 agent for crypto analysis"
- "show me system status"
- "what agents are running?"
- "stop the claude agent"
- "show logs for grok4-agent-1"
- "create a development team"
"""
    
    async def _should_respond(self, message_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if agent should respond to message"""
        content = message_data.get('content', '').lower()
        username = message_data.get('username', '')
        
        # Don't respond to own messages
        if username == 'DevOps':
            return False, "own_message"
        
        # Respond to direct mentions (DevOps bot ID: 1397754394950373428)
        if '<@1397754394950373428>' in content or '@devops' in content:
            return True, "mentioned"
        
        # Also respond to common agent management queries even without mention
        # This makes the bot more helpful for follow-up questions
        if any(keyword in content for keyword in [
            'which agents', 'list agents', 'running agents', 'agent status',
            'deploy agent', 'stop agent', 'system status', 'available agents',
            'agents running', 'show agents'
        ]):
            return True, "management_query"
        
        # Don't respond to other messages - require explicit mention
        return False, "no_mention"
    
    async def _generate_response(self, message_data: Dict[str, Any], context_messages: List[Dict]) -> str:
        """Generate AI response using OpenAI with structured outputs"""
        try:
            content = message_data.get('content', '').lower()
            
            # Get available agent types dynamically
            available_agents = self._get_available_agent_types()
            available_agent_names = list(available_agents.keys())
            
            # Check for direct commands first
            if 'deploy' in content and any(agent_type in content for agent_type in available_agent_names):
                # Extract agent type
                agent_type = None
                for atype in available_agent_names:
                    if atype in content:
                        agent_type = atype
                        break
                
                if agent_type:
                    return await self.execute_command("deploy", agent_type=agent_type)
            
            elif 'stop' in content and 'agent' in content:
                return "To stop an agent, please specify the exact agent name. Use `list agents` to see running agents first."
            
            elif ('list' in content or 'show' in content) and 'agent' in content:
                return await self.execute_command("list")
            
            elif 'status' in content and ('system' in content or 'server' in content):
                # Get REAL system status with real data
                return await self._get_real_system_status()
            
            elif 'available' in content and 'agent' in content:
                # List actual available agent types from dynamic discovery
                return f"🤖 **Available Agent Types:**\n{self._get_available_agent_types_description()}"
            
            elif 'logs' in content and ('agent' in content or 'container' in content):
                return "To view logs, please specify the exact agent name: `show logs for agent-name`"
            
            # Get current system state for context
            system_state = await self._get_current_system_state()
            
            # Use Claude with proper system context and strict instructions  
            deployable_agents = [name for name, info in available_agents.items() if info.get('deployable', False)]
            all_agent_names = list(available_agents.keys())
            
            response = await self.claude.messages.create(
                model=self.config['claude_model'],
                max_tokens=400,
                messages=[{
                    "role": "user", 
                    "content": f"""You are the SuperAgent DevOps Agent managing a multi-agent Discord system.

AVAILABLE AGENT TYPES: {', '.join(all_agent_names)}
DEPLOYABLE AGENTS: {', '.join(deployable_agents)}
CURRENT SYSTEM: CPU {system_state['system']['cpu_percent']:.1f}%, Memory {system_state['system']['memory_percent']:.1f}%, {len(system_state['agents'])} active agents
DOCKER STATUS: {"Connected" if self.docker_client else "Not available"}

COMMANDS YOU CAN EXECUTE:
- deploy [{'/'.join(deployable_agents)}] agent
- list active agents  
- stop agent [name]
- show system status
- get agent logs

User {message_data.get('username')} asks: "{message_data.get('content', '')}"

If they ask about deployable agents, list the actual types: {', '.join(deployable_agents)}.
If they ask about all agents, include config-only ones: {', '.join(all_agent_names)}.
If they ask to deploy something, only deploy from deployable list.
If they ask about containers, explain you manage Docker containers for the agent types above.

Respond with ONLY your final Discord message. No thinking or analysis. Be helpful and accurate about what you actually can do."""
                }]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return f"Error processing request: {str(e)}"
    
    def _format_context_messages(self, messages: List[Dict]) -> str:
        """Format context messages for Claude"""
        formatted = []
        for msg in messages[-5:]:  # Last 5 messages for context
            formatted.append(f"{msg.get('username', 'User')}: {msg.get('message_content', '')}")
        return "\n".join(formatted)
    
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
    
    def _store_conversation(self, message_data: Dict[str, Any], response: str):
        """Store conversation in memory database"""
        try:
            with sqlite3.connect(self.memory_db_path) as conn:
                conn.execute('''
                    INSERT INTO conversations 
                    (channel_id, thread_id, user_id, username, message_content, response_content, agent_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_data.get('channel_id'),
                    message_data.get('thread_id'),
                    message_data.get('user_id'),
                    message_data.get('username'),
                    message_data.get('content'),
                    response,
                    'DevOpsAgent'
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error storing conversation: {e}")
    
    def _get_context_messages(self, channel_id: str, thread_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        try:
            with sqlite3.connect(self.memory_db_path) as conn:
                cursor = conn.cursor()
                
                if thread_id:
                    cursor.execute('''
                        SELECT user_id, username, message_content, response_content, timestamp
                        FROM conversations 
                        WHERE channel_id = ? AND thread_id = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (channel_id, thread_id, limit))
                else:
                    cursor.execute('''
                        SELECT user_id, username, message_content, response_content, timestamp
                        FROM conversations 
                        WHERE channel_id = ? AND thread_id IS NULL
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (channel_id, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        'user_id': row[0],
                        'username': row[1],
                        'message_content': row[2],
                        'response_content': row[3],
                        'timestamp': row[4]
                    } for row in reversed(rows)
                ]
        except Exception as e:
            self.logger.error(f"Error getting context messages: {e}")
            return []
    
    def _parse_message_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse message content from MCP Discord format (robust version)"""
        try:
            # First try JSON parsing
            try:
                message_data = json.loads(content)
                if isinstance(message_data, dict):
                    # Map to expected field names
                    result = {
                        'username': message_data.get('author_name', message_data.get('author', {}).get('username', 'Unknown')),
                        'user_id': message_data.get('author_id', message_data.get('author', {}).get('id', '')),
                        'content': message_data.get('content', ''),
                        'channel_id': message_data.get('channel_id', ''),
                        'channel_name': message_data.get('channel_name', ''),
                        'thread_id': message_data.get('thread_id'),
                        'message_id': message_data.get('id', message_data.get('message_id', ''))
                    }
                    return result
            except json.JSONDecodeError:
                pass
            
            # Try Python dict eval parsing (fallback)
            try:
                message_data = eval(content)
                if isinstance(message_data, dict):
                    result = {
                        'username': message_data.get('author_name', message_data.get('author', {}).get('username', 'Unknown')),
                        'user_id': message_data.get('author_id', message_data.get('author', {}).get('id', '')),
                        'content': message_data.get('content', ''),
                        'channel_id': message_data.get('channel_id', ''),
                        'channel_name': message_data.get('channel_name', ''),
                        'thread_id': message_data.get('thread_id'),
                        'message_id': message_data.get('id', message_data.get('message_id', ''))
                    }
                    return result
            except:
                pass
            
            # Try text-based parsing patterns
            return self._parse_message_text(content)
            
        except Exception as e:
            self.logger.error(f"Error parsing message content: {e}")
            return None
    
    def _parse_message_text(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse text-based message formats"""
        try:
            # Handle "Received message: {json}" format specifically
            if content.startswith("Received message: "):
                json_part = content.replace("Received message: ", "").strip()
                
                # Handle truncated JSON (ends with ...)
                if json_part.endswith('...'):
                    # Try to extract what we can from the partial JSON
                    try:
                        # Find key-value pairs using regex
                        import re
                        author_match = re.search(r"'author':\s*'([^']+)'", json_part)
                        content_match = re.search(r"'content':\s*'([^']+)'", json_part)
                        id_match = re.search(r"'id':\s*'([^']+)'", json_part)
                        channel_match = re.search(r"'channel_id':\s*'([^']+)'", json_part)
                        
                        if author_match and content_match:
                            return {
                                'username': author_match.group(1),
                                'user_id': '',
                                'content': content_match.group(1),
                                'channel_id': channel_match.group(1) if channel_match else '',
                                'channel_name': '',
                                'thread_id': None,
                                'message_id': id_match.group(1) if id_match else ''
                            }
                    except Exception as e:
                        self.logger.debug(f"Regex parsing failed: {e}")
                
                # Try full JSON parsing
                try:
                    message_data = json.loads(json_part)
                    if isinstance(message_data, dict):
                        return {
                            'username': message_data.get('author', 'Unknown'),
                            'user_id': message_data.get('author_id', ''),
                            'content': message_data.get('content', ''),
                            'channel_id': message_data.get('channel_id', ''),
                            'channel_name': message_data.get('channel_name', ''),
                            'thread_id': message_data.get('thread_id'),
                            'message_id': message_data.get('id', '')
                        }
                except json.JSONDecodeError as e:
                    self.logger.debug(f"JSON decode failed: {e}")
                    # Try parsing the truncated message with eval (unsafe but works for partial dicts)
                    try:
                        # Add closing braces if missing
                        if not json_part.rstrip().endswith('}') and not json_part.endswith('...'):
                            json_part += "}"
                        message_data = eval(json_part.replace('...', ''))
                        if isinstance(message_data, dict):
                            return {
                                'username': message_data.get('author', 'Unknown'),
                                'user_id': message_data.get('author_id', ''),
                                'content': message_data.get('content', ''),
                                'channel_id': message_data.get('channel_id', ''),
                                'channel_name': message_data.get('channel_name', ''),
                                'thread_id': message_data.get('thread_id'),
                                'message_id': message_data.get('id', '')
                            }
                    except Exception as e:
                        self.logger.debug(f"Eval parsing failed: {e}")
            
            # Skip timeout messages
            if content.startswith("Timeout:"):
                return None
            
            message_data = {}
            
            # Pattern 1: "New message:" format
            if "New message:" in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith("User:"):
                        message_data['username'] = line.replace("User:", "").strip()
                    elif line.startswith("Author:"):
                        message_data['username'] = line.replace("Author:", "").strip()
                    elif line.startswith("Channel:"):
                        message_data['channel_name'] = line.replace("Channel:", "").strip()
                    elif line.startswith("Message:"):
                        message_data['content'] = line.replace("Message:", "").strip()
                    elif line.startswith("Content:"):
                        message_data['content'] = line.replace("Content:", "").strip()
                    elif line.startswith("Channel ID:"):
                        message_data['channel_id'] = line.replace("Channel ID:", "").strip()
                    elif line.startswith("User ID:"):  
                        message_data['user_id'] = line.replace("User ID:", "").strip()
                    elif line.startswith("Author ID:"):
                        message_data['user_id'] = line.replace("Author ID:", "").strip()
                    elif line.startswith("Message ID:"):
                        message_data['message_id'] = line.replace("Message ID:", "").strip()
                
                return message_data if message_data else None
            
            # Pattern 2: Direct message format
            if content.startswith("Message from"):
                import re
                # Extract: "Message from @username in #channel: message text"
                pattern = r"Message from @?(\w+) in #?(\w+): (.*)"
                match = re.match(pattern, content)
                if match:
                    return {
                        'username': match.group(1),
                        'channel_name': match.group(2), 
                        'content': match.group(3),
                        'user_id': '',
                        'channel_id': ''
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing text message: {e}")
            return None
    
    async def _process_message(self, session: ClientSession, message_data: Dict[str, Any]):
        """Process incoming message and generate response"""
        try:
            # Create message hash for deduplication
            message_hash = hash(f"{message_data.get('user_id', '')}-{message_data.get('content', '')}-{message_data.get('channel_id', '')}")
            
            # Check if already processed
            if message_hash in self.processed_messages:
                self.logger.debug("Skipping duplicate message")
                return
            
            # Rate limiting per user
            user_id = message_data.get('user_id', '')
            now = datetime.now()
            if user_id in self.last_response_time:
                time_diff = (now - self.last_response_time[user_id]).total_seconds()
                if time_diff < 3.0:  # 3 second cooldown
                    self.logger.debug(f"Rate limiting user {user_id}")
                    return
            
            # Check if should respond
            should_respond, reason = await self._should_respond(message_data)
            if not should_respond:
                self.logger.debug(f"Not responding to message: {reason}")
                return
            
            self.logger.info(f"Processing message from {message_data.get('username')}: {message_data.get('content', '')[:100]}...")
            
            # Mark as processed
            self.processed_messages.add(message_hash)
            self.last_response_time[user_id] = now
            
            # Clean up old processed messages (keep last 100)
            if len(self.processed_messages) > 100:
                self.processed_messages = set(list(self.processed_messages)[-50:])
            
            # Get conversation context
            context_messages = self._get_context_messages(
                message_data.get('channel_id', ''),
                message_data.get('thread_id'),
                limit=self.config['max_context_messages']
            )
            
            # Generate AI response
            response_content = await self._generate_response(message_data, context_messages)
            
            # Send response via MCP
            result = await session.call_tool("send_message", {
                "channel_id": message_data['channel_id'],
                "content": response_content
            })
            
            self.logger.info(f"Sent response: {response_content[:100]}...")
            
            # Store conversation
            self._store_conversation(message_data, response_content)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            traceback.print_exc()
    
    async def _listen_for_messages(self, session: ClientSession):
        """Listen for Discord messages via MCP"""
        self.logger.info("🎧 Starting message listener...")
        
        while True:
            try:
                # Try get_unread_messages first (might give us full content)
                try:
                    unread_result = await session.call_tool("get_unread_messages", {
                        "channel_id": os.getenv('DEFAULT_CHANNEL_ID', '1395578179531309089'),  # Use general channel
                        "limit": 1
                    })
                    
                    if unread_result and unread_result.content:
                        unread_content = unread_result.content[0].text
                        self.logger.info(f"📬 Unread messages: {unread_content[:200]}...")
                        
                        # Process unread messages if any
                        if "No unread messages" not in unread_content:
                            message_data = self._parse_message_content(unread_content)
                            if message_data:
                                self.logger.info(f"✅ Parsed unread message: {message_data}")
                                await self._process_message(session, message_data)
                                continue
                
                except Exception as e:
                    self.logger.debug(f"get_unread_messages failed: {e}")
                
                # Fallback to wait_for_message
                self.logger.debug("⏳ Waiting for messages...")
                result = await session.call_tool("wait_for_message", {"timeout": 10})
                
                if result and result.content:
                    content = result.content[0].text
                    self.logger.info(f"📨 Received raw message: {content[:400]}...")  # Show more content
                    
                    message_data = self._parse_message_content(content)
                    
                    if message_data:
                        self.logger.info(f"✅ Parsed message data: {message_data}")
                        await self._process_message(session, message_data)
                    else:
                        self.logger.warning(f"❌ Failed to parse message: {content[:400]}...")
                else:
                    self.logger.debug("⏸️ No message received (timeout)")
                        
            except Exception as e:
                self.logger.error(f"Error in message listener: {e}")
                await asyncio.sleep(5)
    
    # Docker Management Tools
    async def deploy_agent(self, agent_type: str, team: str = None, name: str = None) -> Dict[str, Any]:
        """Deploy a new agent (container or non-container)"""
        try:
            # Get agent info from dynamic discovery
            available_agents = self._get_available_agent_types()
            if agent_type not in available_agents:
                return {"success": False, "error": f"Unknown agent type: {agent_type}"}
            
            agent_info = available_agents[agent_type]
            
            # Route to appropriate deployment method
            if agent_info.get('type') == 'container':
                return await self._deploy_container_agent(agent_type, agent_info, team, name)
            elif agent_info.get('type') == 'non_container':
                return await self._deploy_non_container_agent(agent_type, agent_info, team, name)
            else:
                return {"success": False, "error": f"Unknown agent deployment type: {agent_info.get('type')}"}
            
        except Exception as e:
            self.logger.error(f"Error deploying agent {agent_type}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _deploy_container_agent(self, agent_type: str, agent_info: Dict[str, Any], team: str = None, name: str = None) -> Dict[str, Any]:
        """Deploy a container-based agent"""
        if not self.docker_client:
            return {"success": False, "error": "Docker daemon not available for container deployment"}
        
        try:
            # Get template from config
            templates = self.config.get('container_agent_templates', {})
            if agent_type not in templates:
                return {"success": False, "error": f"Container template not found for: {agent_type}"}
            
            template = templates[agent_type]
            
            # Generate unique container name
            if not name:
                name = f"{agent_type}-agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare environment variables
            env_vars = template.get('environment', {}).copy()
            for key, value in env_vars.items():
                if value.startswith('${') and value.endswith('}'):
                    env_name = value[2:-1]
                    env_vars[key] = os.getenv(env_name, value)
            
            # Create container
            container = self.docker_client.containers.run(
                image=template['image'],
                name=name,
                environment=env_vars,
                volumes=template.get('volumes', {}),
                labels={**template.get('labels', {}), 'superagent.team': team or 'default'},
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Register agent
            self.agents[name] = AgentStatus(
                name=name,
                type=agent_type,
                container_id=container.id,
                status='running',
                cpu_percent=0.0,
                memory_mb=0,
                uptime='0s',
                team=team,
                last_activity=datetime.now(),
                errors=[]
            )
            
            self.logger.info(f"✅ Deployed {agent_type} container agent: {name}")
            return {"success": True, "container_id": container.id, "name": name, "type": "container"}
            
        except Exception as e:
            self.logger.error(f"Failed to deploy {agent_type} container agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def _deploy_non_container_agent(self, agent_type: str, agent_info: Dict[str, Any], team: str = None, name: str = None) -> Dict[str, Any]:
        """Deploy a non-container agent (like enhanced_discord_agent.py)"""
        try:
            # Get template from config  
            templates = self.config.get('non_container_agents', {})
            if agent_type not in templates:
                return {"success": False, "error": f"Non-container template not found for: {agent_type}"}
            
            template = templates[agent_type]
            
            # Generate unique process name
            if not name:
                name = f"{agent_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Get script path
            script = template.get('script', 'enhanced_discord_agent.py')
            script_path = Path(__file__).parent.parent / script
            
            if not script_path.exists():
                return {"success": False, "error": f"Agent script not found: {script_path}"}
            
            # Prepare environment variables
            env_vars = template.get('environment', {}).copy()
            for key, value in env_vars.items():
                if value.startswith('${') and value.endswith('}'):
                    env_name = value[2:-1]
                    env_vars[key] = os.getenv(env_name, value)
            
            # Actually start the process
            venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python"
            if not venv_python.exists():
                # Fallback to system python
                venv_python = "python"
            
            # Set up environment
            proc_env = os.environ.copy()
            proc_env.update(env_vars)
            
            # Add config key for enhanced_discord_agent.py
            config_key = template.get('config_key', agent_type)
            
            # Start the process with better logging
            self.logger.info(f"Starting non-container agent: {script_path} with config key: {config_key}")
            
            # Create a log file for this specific agent instance
            log_dir = Path(__file__).parent.parent / "logs" / "deployed_agents"
            log_dir.mkdir(exist_ok=True)  
            log_file = log_dir / f"{name}.log"
            
            import subprocess
            with open(log_file, 'w') as log_handle:
                process = subprocess.Popen(
                    [str(venv_python), str(script_path), "--config-key", config_key],
                    env=proc_env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,  # Redirect stderr to stdout so we capture all output
                    cwd=str(script_path.parent)
                )
            
            # Give it a moment to start
            await asyncio.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                # Store process info in registry  
                await self._register_agent(name, agent_type, str(process.pid), "running", template)
                
                self.logger.info(f"✅ Non-container agent {agent_type} started successfully (PID: {process.pid})")
                self.logger.info(f"📋 Agent logs: {log_file}")
                
                # Store the process object for monitoring
                if not hasattr(self, '_deployed_processes'):
                    self._deployed_processes = {}
                self._deployed_processes[name] = process
                
                return {
                    "success": True,
                    "name": name,
                    "type": "non_container", 
                    "script": str(script_path),
                    "pid": process.pid,
                    "status": "running",
                    "config_key": config_key,
                    "log_file": str(log_file)
                }
            else:
                # Process failed to start - read the log file for errors
                try:
                    with open(log_file, 'r') as f:
                        error_output = f.read()
                except:
                    error_output = "Could not read log file"
                    
                error_msg = f"Process failed to start. Exit code: {process.returncode}"
                self.logger.error(f"{error_msg}\nOutput: {error_output}")
                return {
                    "success": False,
                    "error": error_msg,
                    "output": error_output,
                    "log_file": str(log_file)
                }
            
        except Exception as e:
            self.logger.error(f"Failed to prepare {agent_type} non-container agent: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_non_container_agents(self) -> Dict[str, Any]:
        """Check status of deployed non-container agents"""
        if not hasattr(self, '_deployed_processes'):
            return {"active_agents": [], "dead_agents": []}
        
        active_agents = []
        dead_agents = []
        
        for name, process in self._deployed_processes.items():
            if process.poll() is None:
                # Process is still running
                active_agents.append({
                    "name": name,
                    "pid": process.pid,
                    "status": "running"
                })
            else:
                # Process has died
                dead_agents.append({
                    "name": name,
                    "pid": process.pid,
                    "status": "dead",
                    "exit_code": process.returncode
                })
                
        return {
            "active_agents": active_agents,
            "dead_agents": dead_agents,
            "total_deployed": len(self._deployed_processes)
        }
    
    async def stop_agent(self, agent_name: str) -> Dict[str, Any]:
        """Stop an agent container"""
        if not self.docker_client:
            return {"success": False, "error": "Docker daemon not available"}
        
        try:
            # Find container
            containers = self.docker_client.containers.list(all=True)
            container = None
            for c in containers:
                if c.name == agent_name:
                    container = c
                    break
            
            if not container:
                return {"success": False, "error": f"Agent {agent_name} not found"}
            
            # Stop container
            container.stop()
            
            # Update agent status
            if agent_name in self.agents:
                self.agents[agent_name].status = 'stopped'
            
            self.logger.info(f"🛑 Stopped agent: {agent_name}")
            return {"success": True, "message": f"Agent {agent_name} stopped"}
            
        except Exception as e:
            self.logger.error(f"Failed to stop agent {agent_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_agent_logs(self, agent_name: str, lines: int = 50) -> Dict[str, Any]:
        """Get logs from an agent container"""
        if not self.docker_client:
            return {"success": False, "error": "Docker daemon not available"}
        
        try:
            container = self.docker_client.containers.get(agent_name)
            logs = container.logs(tail=lines).decode('utf-8')
            
            return {"success": True, "logs": logs}
            
        except Exception as e:
            self.logger.error(f"Failed to get logs for {agent_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_active_agents(self) -> Dict[str, Any]:
        """List all active agents (both containers and processes)"""
        try:
            agents = []
            
            # Get container-based agents
            if self.docker_client:
                try:
                    containers = self.docker_client.containers.list(
                        filters={"label": "superagent.managed=true"}
                    )
                    
                    for container in containers:
                        labels = container.labels
                        agents.append({
                            "name": container.name,
                            "type": labels.get('superagent.type', 'unknown'),
                            "status": container.status,
                            "team": labels.get('superagent.team', 'default'),
                            "created": container.attrs['Created'],
                            "deployment": "container",
                            "pid": None,
                            "uptime": None
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to get container agents: {e}")
            
            # Get process-based agents (like launch_single_agent.py)
            import psutil
            import time
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline_list = proc.info.get('cmdline', [])
                    if not cmdline_list:
                        continue
                    
                    cmdline = ' '.join(cmdline_list)
                    
                    if 'launch_single_agent.py' in cmdline:
                        parts = cmdline.split()
                        agent_type = parts[-1] if len(parts) > 0 and parts[-1] in ['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'] else 'unknown'
                        
                        if agent_type != 'unknown':
                            uptime_seconds = time.time() - proc.info['create_time']
                            uptime_str = f"{uptime_seconds/60:.1f}m" if uptime_seconds < 3600 else f"{uptime_seconds/3600:.1f}h"
                            
                            agents.append({
                                "name": agent_type.replace('_agent', '').title() + 'Agent',
                                "type": agent_type,
                                "status": "running",
                                "team": "default",
                                "created": proc.info['create_time'],
                                "deployment": "process",
                                "pid": proc.info['pid'],
                                "uptime": uptime_str
                            })
                    
                    elif 'mcp_devops_agent.py' in cmdline:
                        uptime_seconds = time.time() - proc.info['create_time']
                        uptime_str = f"{uptime_seconds/60:.1f}m" if uptime_seconds < 3600 else f"{uptime_seconds/3600:.1f}h"
                        
                        agents.append({
                            "name": "DevOps Agent",
                            "type": "devops_agent",
                            "status": "running",
                            "team": "system",
                            "created": proc.info['create_time'],
                            "deployment": "process",
                            "pid": proc.info['pid'],
                            "uptime": uptime_str
                        })
                        
                except Exception:
                    continue
            
            return {"success": True, "agents": agents}
            
        except Exception as e:
            self.logger.error(f"Failed to list agents: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_command(self, command_type: str, **kwargs) -> str:
        """Execute DevOps commands and return formatted response"""
        try:
            if command_type == "deploy":
                result = await self.deploy_agent(kwargs.get('agent_type'), kwargs.get('team'), kwargs.get('name'))
                if result['success']:
                    return f"✅ Successfully deployed {kwargs.get('agent_type')} agent: {result['name']}"
                else:
                    return f"❌ Failed to deploy agent: {result['error']}"
            
            elif command_type == "stop":
                result = await self.stop_agent(kwargs.get('agent_name'))
                if result['success']:
                    return f"🛑 {result['message']}"
                else:
                    return f"❌ Failed to stop agent: {result['error']}"
            
            elif command_type == "logs":
                result = await self.get_agent_logs(kwargs.get('agent_name'), kwargs.get('lines', 20))
                if result['success']:
                    logs = result['logs'][-1000:]  # Limit to 1000 chars for Discord
                    return f"📋 Logs for {kwargs.get('agent_name')}:\n```\n{logs}\n```"
                else:
                    return f"❌ Failed to get logs: {result['error']}"
            
            elif command_type == "list":
                result = await self.list_active_agents()
                if result['success']:
                    if not result['agents']:
                        return "📋 No active agents currently running"
                    
                    agent_list = []
                    for agent in result['agents']:
                        status_emoji = "🟢" if agent['status'] == 'running' else "🔴"
                        deployment_info = f"(PID: {agent['pid']}, {agent['uptime']})" if agent.get('deployment') == 'process' else "(Container)"
                        agent_list.append(f"{status_emoji} **{agent['name']}** ({agent['type']}) - Team: {agent['team']} {deployment_info}")
                    
                    return f"📋 **Active Agents ({len(result['agents'])} running):**\n" + "\n".join(agent_list)
                else:
                    return f"❌ Failed to list agents: {result['error']}"
            
            else:
                return f"❌ Unknown command type: {command_type}"
                
        except Exception as e:
            self.logger.error(f"Error executing command {command_type}: {e}")
            return f"❌ Error executing command: {str(e)}"
    
    async def _get_real_system_status(self) -> str:
        """Get real system status with actual data"""
        try:
            # Get actual system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = os.getloadavg()
            
            # Get Docker container count
            container_count = 0
            docker_status = "❌ Not Available"
            if self.docker_client:
                try:
                    containers = self.docker_client.containers.list()
                    container_count = len(containers)
                    docker_status = "✅ Connected"
                except Exception as e:
                    docker_status = f"❌ Error: {str(e)[:50]}"
            
            # Get agent count from our registry
            running_agents = len([a for a in self.agents.values() if a.status == 'running'])
            
            status_msg = f"""📊 **Real System Status:**
            
**System Resources:**
• CPU Usage: {cpu_percent:.1f}%
• Memory: {memory.percent:.1f}% ({memory.used//1024//1024//1024:.1f}GB / {memory.total//1024//1024//1024:.1f}GB)
• Disk Usage: {disk.percent:.1f}% ({disk.free//1024//1024//1024:.1f}GB free)
• Load Average: {load_avg[0]:.2f} (1m), {load_avg[1]:.2f} (5m), {load_avg[2]:.2f} (15m)

**SuperAgent Status:**
• Docker: {docker_status}
• Total Containers: {container_count}
• Managed Agents: {running_agents}
• Agent Registry: {len(self.agents)} tracked

**Available Agent Types:** {', '.join(self._get_available_agent_types().keys())}"""
            
            return status_msg
            
        except Exception as e:
            return f"❌ Error getting system status: {str(e)}"
    
    def _get_agent_description(self, agent_type: str) -> str:
        """Get description for an agent type from actual configuration"""
        agent_types = self._get_available_agent_types()
        
        if agent_type in agent_types:
            info = agent_types[agent_type]
            capabilities = ", ".join(info.get('capabilities', [])) or "general tasks"
            personality = info.get('personality', 'AI assistant')
            return f"{personality} - Specializes in {capabilities}"
            
        # OBVIOUSLY FAKE fallbacks so we know when discovery is broken
        fake_descriptions = {
            'grok4': '🦄 FAKE: Unicorn-powered rainbow generator',
            'claude': '🤖 FAKE: Sentient toaster with PhD in philosophy', 
            'gemini': '👽 FAKE: Alien communication specialist from Mars',
            'manager': '🎪 FAKE: Circus ringmaster managing digital elephants',
            'fullstack': '🧙 FAKE: Wizard casting JavaScript spells'
        }
        return fake_descriptions.get(agent_type, '💀 ERROR: Unknown agent type - config missing!')
    
    async def _health_monitor_loop(self):
        """Background health monitoring"""
        while True:
            try:
                await asyncio.sleep(self.config['health_check_interval'])
                
                # Update system state
                system_state = await self._get_current_system_state()
                
                # Store in database
                with sqlite3.connect(self.memory_db_path) as conn:
                    conn.execute('''
                        INSERT INTO system_state (state_type, state_data)
                        VALUES (?, ?)
                    ''', ('health_check', json.dumps(system_state, default=str)))
                    conn.commit()
                
                self.system_state['last_health_check'] = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
    
    async def start(self):
        """Start the MCP DevOps Agent"""
        self.logger.info("🚀 Starting MCP DevOps Agent...")
        
        try:
            # Create MCP server parameters
            server_params = StdioServerParameters(
                command=self.mcp_command,
                args=self.mcp_args
            )
            
            # Connect to MCP Discord server
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize MCP session
                    await session.initialize()
                    self.logger.info("✅ Connected to MCP Discord server")
                    
                    # Set agent status
                    try:
                        await session.call_tool("set_agent_status", {
                            "status": "available",
                            "details": "AI DevOps Agent - SuperAgent Infrastructure Management"
                        })
                    except Exception as e:
                        self.logger.warning(f"Could not set agent status: {e}")
                    
                    # Start background tasks
                    health_task = asyncio.create_task(self._health_monitor_loop())
                    
                    # Start message listener (this will run indefinitely)
                    await self._listen_for_messages(session)
        
        except Exception as e:
            self.logger.error(f"Failed to start MCP DevOps Agent: {e}")
            traceback.print_exc()
            raise

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    # Load environment
    load_dotenv()
    
    async def main():
        # Ensure required directories exist
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Create and start the MCP DevOps Agent
        agent = MCPDevOpsAgent()
        await agent.start()
    
    # Run the agent
    asyncio.run(main())