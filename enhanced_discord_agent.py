#!/usr/bin/env python3
"""
Enhanced Discord Agent with Chat History, Memory, and Multi-LLM Support
Based on MultiAgent Discord Listener PRD requirements
"""

import asyncio
import json
import pathlib
import logging
import sqlite3
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import re
from dotenv import load_dotenv
from llm_providers import create_llm_provider, LLMProvider

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/discord_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    bot_token: str
    server_id: str
    api_key: str
    llm_type: str  # 'grok4', 'claude', 'gemini'
    max_context_messages: int = 20
    max_turns_per_thread: int = 50
    response_delay: float = 1.0  # seconds
    allowed_channels: List[str] = None
    ignore_bots: bool = True
    bot_allowlist: List[str] = None

class MemoryManager:
    """Handles conversation memory and context using SQLite"""
    
    def __init__(self, db_path: str = "data/agent_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                channel_id TEXT,
                thread_id TEXT,
                author_id TEXT,
                author_name TEXT,
                content TEXT,
                timestamp DATETIME,
                is_bot BOOLEAN,
                agent_name TEXT
            )
        ''')
        
        # Conversations table for thread tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE,
                channel_id TEXT,
                title TEXT,
                participant_count INTEGER,
                message_count INTEGER,
                last_activity DATETIME,
                agent_turn_count INTEGER DEFAULT 0
            )
        ''')
        
        # Agent responses for audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT,
                agent_name TEXT,
                llm_type TEXT,
                prompt_context TEXT,
                response_content TEXT,
                timestamp DATETIME,
                processing_time FLOAT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_message(self, message_data: Dict[str, Any]):
        """Store a Discord message"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO messages 
            (message_id, channel_id, thread_id, author_id, author_name, content, timestamp, is_bot, agent_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_data['id'],
            message_data['channel_id'],
            message_data.get('thread_id'),
            message_data['author_id'],
            message_data['author_name'],
            message_data['content'],
            message_data['timestamp'],
            message_data['is_bot'],
            message_data.get('agent_name')
        ))
        
        conn.commit()
        conn.close()
    
    def get_context_messages(self, channel_id: str, thread_id: str = None, limit: int = 20) -> List[Dict]:
        """Get recent messages for context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if thread_id:
            cursor.execute('''
                SELECT author_name, content, timestamp, is_bot, agent_name
                FROM messages 
                WHERE thread_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (thread_id, limit))
        else:
            cursor.execute('''
                SELECT author_name, content, timestamp, is_bot, agent_name
                FROM messages 
                WHERE channel_id = ? AND thread_id IS NULL
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (channel_id, limit))
        
        messages = cursor.fetchall()
        conn.close()
        
        # Convert to dict and reverse to chronological order
        return [{
            'author': msg[0],
            'content': msg[1],
            'timestamp': msg[2],
            'is_bot': bool(msg[3]),
            'agent_name': msg[4]
        } for msg in reversed(messages)]
    
    def update_conversation_stats(self, thread_id: str, channel_id: str, increment_agent_turns: bool = False):
        """Update conversation statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute('SELECT agent_turn_count FROM conversations WHERE thread_id = ?', (thread_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing
            new_agent_turns = result[0] + (1 if increment_agent_turns else 0)
            cursor.execute('''
                UPDATE conversations 
                SET last_activity = ?, agent_turn_count = ?
                WHERE thread_id = ?
            ''', (datetime.now(), new_agent_turns, thread_id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO conversations 
                (thread_id, channel_id, last_activity, agent_turn_count)
                VALUES (?, ?, ?, ?)
            ''', (thread_id, channel_id, datetime.now(), 1 if increment_agent_turns else 0))
        
        conn.commit()
        conn.close()
        
        # Return current agent turn count
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT agent_turn_count FROM conversations WHERE thread_id = ?', (thread_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

# LLMProvider classes are now in llm_providers.py

class EnhancedDiscordAgent:
    """Enhanced Discord Agent with memory, context management, and multi-LLM support"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.memory = MemoryManager()
        self.llm_provider = self._create_llm_provider()
        
        # Load MCP configuration
        mcp_config_path = pathlib.Path(__file__).parent / "mcp.json"
        with open(mcp_config_path, "r") as f:
            mcp_config = json.load(f)
        
        discord_config = mcp_config.get("mcpServers", {}).get("discord-grok", {})
        self.mcp_command = discord_config.get("command", "uv")
        self.mcp_args = discord_config.get("args", [])
        
        # Set up logging directory
        os.makedirs(f"logs/{config.name}", exist_ok=True)
        
        logger.info(f"Initialized {config.name} agent with {config.llm_type}")
    
    def _create_llm_provider(self) -> LLMProvider:
        """Create appropriate LLM provider based on config"""
        return create_llm_provider(self.config.llm_type, self.config.api_key)
    
    def _should_respond(self, message_data: Dict[str, Any]) -> tuple[bool, str]:
        """Determine if agent should respond to message"""
        author_name = message_data['author_name']
        content = message_data['content']
        is_bot = message_data['is_bot']
        
        # Don't respond to self
        if (author_name == self.config.name or 
            author_name.startswith('Grok4') or 
            message_data.get('agent_name') == self.config.name):
            return False, "own message"
        
        # Check if bot message should be ignored
        if is_bot and self.config.ignore_bots:
            if self.config.bot_allowlist and author_name not in self.config.bot_allowlist:
                return False, "bot not in allowlist"
        
        # Check channel restrictions
        channel_id = message_data['channel_id']
        if self.config.allowed_channels and channel_id not in self.config.allowed_channels:
            return False, "channel not allowed"
        
        # Check max turns per thread
        thread_id = message_data.get('thread_id', channel_id)
        agent_turns = self.memory.update_conversation_stats(thread_id, channel_id, increment_agent_turns=False)
        if agent_turns >= self.config.max_turns_per_thread:
            return False, f"max turns reached ({agent_turns})"
        
        return True, "should respond"
    
    async def process_message(self, session: ClientSession, message_data: Dict[str, Any]):
        """Process incoming Discord message"""
        # Store message in memory
        self.memory.store_message(message_data)
        
        # Check if should respond
        should_respond, reason = self._should_respond(message_data)
        logger.info(f"Message from {message_data['author_name']}: {should_respond} ({reason})")
        
        if not should_respond:
            return
        
        # Add response delay to prevent rapid-fire responses
        await asyncio.sleep(self.config.response_delay)
        
        try:
            # Get context messages
            thread_id = message_data.get('thread_id')
            channel_id = message_data['channel_id']
            
            context_messages = self.memory.get_context_messages(
                channel_id, 
                thread_id, 
                limit=self.config.max_context_messages
            )
            
            # Generate LLM response
            start_time = time.time()
            system_prompt = f"""You are {self.config.name}, a helpful Discord bot powered by {self.config.llm_type}.
You're participating in a Discord conversation. Be conversational, helpful, and engaging.
Keep responses concise but informative. Avoid being repetitive or robotic."""
            
            response_content = await self.llm_provider.generate_response(
                context_messages, 
                system_prompt
            )
            
            processing_time = time.time() - start_time
            
            # Send response to Discord
            result = await session.call_tool(
                "send_message",
                {
                    "channel_id": channel_id,
                    "content": response_content
                }
            )
            
            if result:
                # Log successful response
                logger.info(f"Sent response to {channel_id}: {response_content[:100]}...")
                
                # Store our response in memory
                response_message_data = {
                    'id': f"agent_{int(time.time())}",  # Generate ID
                    'channel_id': channel_id,
                    'thread_id': thread_id,
                    'author_id': 'agent',
                    'author_name': self.config.name,
                    'content': response_content,
                    'timestamp': datetime.now(),
                    'is_bot': True,
                    'agent_name': self.config.name
                }
                self.memory.store_message(response_message_data)
                
                # Update conversation stats
                self.memory.update_conversation_stats(
                    thread_id or channel_id, 
                    channel_id, 
                    increment_agent_turns=True
                )
                
                # Store audit log
                conn = sqlite3.connect(self.memory.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO agent_responses 
                    (message_id, agent_name, llm_type, prompt_context, response_content, timestamp, processing_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message_data['id'],
                    self.config.name,
                    self.config.llm_type,
                    json.dumps([msg['content'] for msg in context_messages[-5:]]),  # Last 5 messages
                    response_content,
                    datetime.now(),
                    processing_time
                ))
                conn.commit()
                conn.close()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def send_startup_message(self, session: ClientSession):
        """Send a startup message to announce the agent is online"""
        try:
            # Get server info to find a channel
            result = await session.call_tool(
                "get_server_info",
                {"server_id": self.config.server_id}
            )
            
            if result and result.content:
                content = result.content[0].text
                
                # Parse channels from response
                channels = []
                if "Text Channels:" in content:
                    lines = content.split('\n')
                    in_text_channels = False
                    for line in lines:
                        if "Text Channels:" in line:
                            in_text_channels = True
                            continue
                        if in_text_channels and "Voice Channels:" in line:
                            break
                        if in_text_channels and "#" in line and "ID:" in line:
                            import re
                            match = re.search(r'#(\S+)\s+\(ID:\s*(\d+)', line)
                            if match:
                                channels.append({
                                    'name': match.group(1),
                                    'id': match.group(2)
                                })
                
                # Find preferred channel or use first available
                target_channel = None
                for channel in channels:
                    if channel.get('name') in ['general', 'bot', 'bots', 'test', 'bot-test', 'grok-test']:
                        target_channel = channel
                        break
                
                if not target_channel and channels:
                    target_channel = channels[0]
                
                if target_channel:
                    startup_message = f"🤖 {self.config.name} is now online and ready to chat! Powered by {self.config.llm_type.upper()}. Say hello!"
                    
                    await session.call_tool(
                        "send_message",
                        {
                            "channel_id": target_channel.get('id'),
                            "content": startup_message
                        }
                    )
                    
                    logger.info(f"Sent startup message to #{target_channel.get('name')}")
                else:
                    logger.warning("No suitable channel found for startup message")
                    
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")

    async def listen_for_messages(self, session: ClientSession):
        """Listen for new Discord messages"""
        logger.info(f"{self.config.name} is listening for messages...")
        
        while True:
            try:
                # Wait for new message with shorter timeout
                result = await session.call_tool(
                    "wait_for_message",
                    {"timeout": 10}  # 10 second timeout
                )
                
                if result and result.content:
                    content = result.content[0].text
                    logger.info(f"Received message: {content[:200]}...")  # Log first 200 chars
                    
                    # Try parsing as JSON first, then as text
                    message_data = self._parse_message_content(content)
                    if message_data:
                        logger.info(f"Processing message from {message_data['author_name']}: {message_data['content'][:50]}...")
                        await self.process_message(session, message_data)
                    else:
                        logger.debug("Could not parse message data")
                else:
                    # No message received in timeout period - this is normal
                    logger.debug("No messages in timeout period, continuing to listen...")
                
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def _parse_message_content(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse message from either JSON or text format"""
        # Clean up the content - remove prefix like "Received message: "
        if "Received message: " in content:
            content = content.split("Received message: ", 1)[1]
        
        # Try parsing as JSON/dict first
        try:
            # Find dict/JSON part of the content
            if '{' in content and '}' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                dict_part = content[start:end]
                
                # Try JSON first
                try:
                    import json as json_module
                    json_data = json_module.loads(dict_part)
                except:
                    # If JSON fails, try eval (for Python dict format with single quotes)
                    json_data = eval(dict_part)
                
                logger.debug(f"Parsed dict: {json_data}")
                
                # Convert to our expected format
                message_data = {
                    'id': json_data.get('id', f"parsed_{int(time.time())}"),
                    'author_id': json_data.get('author', 'unknown'),
                    'author_name': json_data.get('author', 'unknown'),
                    'content': json_data.get('content', ''),
                    'channel_id': json_data.get('channel_id', 'unknown'),
                    'timestamp': datetime.now(),
                    'thread_id': json_data.get('thread_id'),
                    'is_bot': 'bot' in json_data.get('author', '').lower()
                }
                if message_data['content']:
                    logger.debug(f"Successfully parsed message data: {message_data}")
                    return message_data
        except Exception as e:
            logger.debug(f"Failed to parse as dict/JSON: {e}")
        
        # Fall back to text parsing
        return self._parse_message_text(content)
    
    def _parse_message_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse message information from MCP text response"""
        # Handle different possible message formats from MCP Discord server
        
        # Try parsing as structured text
        message_data = {}
        
        # Look for key-value patterns
        patterns = [
            (r'Author[:\s]+(.+)', 'author_name'),
            (r'Content[:\s]+(.+)', 'content'),
            (r'Channel ID[:\s]+(\d+)', 'channel_id'),
            (r'Message ID[:\s]+(\d+)', 'id'),
            (r'Thread ID[:\s]+(\d+)', 'thread_id'),
            (r'User[:\s]+(.+)', 'author_name'),  # Alternative format
            (r'Message[:\s]+(.+)', 'content'),   # Alternative format
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                message_data[key] = match.group(1).strip()
        
        # If structured parsing failed, try to extract from natural language
        if not message_data.get('content'):
            # Look for patterns like "New message from USER: content"
            new_msg_pattern = r'New message from\s+([^:]+):\s*(.+)'
            match = re.search(new_msg_pattern, text, re.IGNORECASE)
            if match:
                message_data['author_name'] = match.group(1).strip()
                message_data['content'] = match.group(2).strip()
        
        # Set defaults and derived values
        if message_data.get('author_name'):
            message_data['author_id'] = message_data['author_name']
            message_data['timestamp'] = datetime.now()
            message_data['is_bot'] = (
                'bot' in message_data['author_name'].lower() or
                message_data['author_name'].endswith('Bot') or
                message_data['author_name'] == self.config.name
            )
            
            # Default channel ID if not found
            if not message_data.get('channel_id'):
                message_data['channel_id'] = 'unknown'
            
            # Generate message ID if not found
            if not message_data.get('id'):
                message_data['id'] = f"parsed_{int(time.time())}"
            
            return message_data
        
        logger.warning(f"Could not parse message format: {text[:100]}...")
        return None
    
    async def run(self):
        """Main run method"""
        # Create server parameters
        server_params = StdioServerParameters(
            command=self.mcp_command,
            args=self.mcp_args
        )
        
        logger.info(f"Starting {self.config.name} Discord agent...")
        
        # Use the MCP client
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                logger.info("Initializing MCP session...")
                
                # Initialize the session
                await session.initialize()
                logger.info("MCP session initialized successfully!")
                
                # Send startup message
                await self.send_startup_message(session)
                
                # Start listening for messages
                await self.listen_for_messages(session)

def load_agent_config() -> AgentConfig:
    """Load agent configuration from environment and config files"""
    return AgentConfig(
        name="Grok4Agent",
        bot_token=os.getenv("DISCORD_TOKEN_GROK", ""),
        server_id=os.getenv("DEFAULT_SERVER_ID", "1395578178973597799"),
        api_key=os.getenv("XAI_API_KEY", ""),
        llm_type="grok4",
        max_context_messages=15,
        max_turns_per_thread=30,
        response_delay=2.0,
        ignore_bots=True,
        bot_allowlist=[]
    )

async def main():
    """Main entry point"""
    config = load_agent_config()
    agent = EnhancedDiscordAgent(config)
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent shutdown requested")
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise