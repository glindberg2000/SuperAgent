#!/usr/bin/env python3
"""
Enhanced Discord Agent with Chat History, Memory, and Multi-LLM Support
Based on MultiAgent Discord Listener PRD requirements
"""

import asyncio
import json
import pathlib
import logging
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
from memory_client import MemoryClient

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
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

class MemoryManagerWrapper:
    """Wrapper to make PostgreSQL MemoryClient compatible with existing MemoryManager API"""
    
    def __init__(self, memory_client: MemoryClient):
        self.client = memory_client
        self.conversation_stats = {}  # Simple in-memory tracking for compatibility
        
    def store_message(self, message_data: Dict[str, Any]):
        """Store a Discord message"""
        try:
            # Convert to memory format and store
            content = f"{message_data['author_name']}: {message_data['content']}"
            # Run async method synchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.client.store_memory(
                        agent_id=message_data.get('agent_name', 'discord'),
                        content=content,
                        metadata={
                            'message_id': message_data['id'],
                            'channel_id': message_data['channel_id'],
                            'thread_id': message_data.get('thread_id'),
                            'author_id': message_data['author_id'],
                            'author_name': message_data['author_name'],
                            'timestamp': str(message_data['timestamp']),
                            'is_bot': message_data['is_bot']
                        }
                    )
                )
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"Failed to store message in PostgreSQL: {e}")
    
    def get_context_messages(self, channel_id: str, thread_id: str = None, limit: int = 20) -> List[Dict]:
        """Get recent messages for context - simplified for now"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                memories = loop.run_until_complete(
                    self.client.get_recent_memories(limit=limit)
                )
                # Convert back to expected format
                context_messages = []
                for memory in memories[-limit:]:  # Get recent ones
                    # Parse the content format "author: message"
                    content = memory.get('content', '')
                    if ': ' in content:
                        author, message = content.split(': ', 1)
                        context_messages.append({
                            'author': author,
                            'content': message,
                            'timestamp': memory.get('created_at'),
                            'is_bot': author.endswith('Agent') or 'bot' in author.lower(),
                            'agent_name': None
                        })
                return context_messages
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"Failed to get context from PostgreSQL: {e}")
            return []
    
    def update_conversation_stats(self, thread_id: str, channel_id: str, increment_agent_turns: bool = False):
        """Update conversation statistics - simplified tracking"""
        key = f"{thread_id or channel_id}"
        if key not in self.conversation_stats:
            self.conversation_stats[key] = 0
        
        if increment_agent_turns:
            self.conversation_stats[key] += 1
            
        return self.conversation_stats[key]

# LLMProvider classes are now in llm_providers.py

class EnhancedDiscordAgent:
    """Enhanced Discord Agent with memory, context management, and multi-LLM support"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        # Initialize PostgreSQL memory client with wrapper
        postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
        memory_client = MemoryClient(postgres_url)
        self.memory = MemoryManagerWrapper(memory_client)
        self.llm_provider = self._create_llm_provider()
        
        # Configure MCP to use local mcp-discord with agent-specific token
        self.mcp_command = "python"
        self.mcp_args = [
            str(pathlib.Path(__file__).parent / "mcp-discord" / "src" / "discord_mcp" / "server.py"),
            "--token", config.bot_token,
            "--server-id", config.server_id
        ]
        
        # Include environment variables for the MCP process
        self.mcp_env = dict(os.environ)
        
        # Set up logging directory
        os.makedirs(f"logs/{config.name}", exist_ok=True)
        
        logger.info(f"Initialized {config.name} agent with {config.llm_type}")
    
    def _create_llm_provider(self) -> LLMProvider:
        """Create appropriate LLM provider based on config"""
        kwargs = {}
        if hasattr(self.config, 'model'):
            kwargs['model'] = self.config.model
        return create_llm_provider(self.config.llm_type, self.config.api_key, **kwargs)
    
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
        
        # Check if message mentions this bot (to prevent responding to everything)
        content = message_data.get('content', '')
        bot_mention = f"<@{os.getenv('DISCORD_BOT_USER_ID', '1396750004588253205')}>"  # Bot's user ID
        
        # Only respond if mentioned, unless it's a DM or special channel
        if bot_mention not in content and not channel_id.startswith('DM'):
            # Allow responses in certain channels or if configured to respond to all
            respond_to_all = getattr(self.config, 'respond_to_all', False)
            if not respond_to_all:
                return False, "not mentioned"
        
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
            
            # Check for file attachments and handle them
            attachments = message_data.get('attachments', [])
            attachment_info = ""
            
            # When processing files, reduce context to avoid pattern repetition
            context_limit = 3 if attachments else self.config.max_context_messages
            
            context_messages = self.memory.get_context_messages(
                channel_id, 
                thread_id, 
                limit=context_limit
            )
            
            if attachments:
                logger.info(f"Message has {len(attachments)} attachment(s)")
                logger.debug(f"Attachment data: {attachments}")
                attachment_info = f"\n\nATTACHMENT INFO: The user has uploaded {len(attachments)} file(s):\n"
                for att in attachments:
                    if isinstance(att, dict) and 'filename' in att:
                        attachment_info += f"- {att['filename']} ({att['size']} bytes, {att.get('content_type', 'unknown')} type)\n"
                    else:
                        logger.warning(f"Invalid attachment format: {att}")
                        attachment_info += f"- Invalid attachment format: {att}\n"
                
                # Try to download and process the first attachment
                content_lower = message_data['content'].lower()
                logger.info(f"Checking for download keywords in: '{content_lower}'")
                if attachments and ("download" in content_lower or "read" in content_lower or "file" in content_lower):
                    if len(attachments) > 0 and isinstance(attachments[0], dict) and 'filename' in attachments[0]:
                        try:
                            logger.info(f"Attempting to download attachment: {attachments[0]['filename']}")
                            download_params = {
                                "channel_id": channel_id,
                                "message_id": message_data['id'],
                                "attachment_filename": attachments[0]['filename']
                            }
                            logger.debug(f"Download params: {download_params}")
                            
                            download_result = await session.call_tool("download_attachment", download_params)
                            
                            if download_result and download_result.content:
                                download_response = download_result.content[0].text
                                logger.info(f"Download response: {download_response}")
                                if "downloaded successfully" in download_response:
                                    # Parse the absolute path from the response
                                    import re
                                    path_match = re.search(r'Absolute path: (.+?)\n', download_response)
                                    if path_match:
                                        file_path = path_match.group(1)
                                    else:
                                        # Fallback to parsing the regular save path
                                        save_match = re.search(r'Saved to: (.+?)\n', download_response)
                                        if save_match:
                                            file_path = save_match.group(1)
                                        else:
                                            file_path = f"downloads/{attachments[0]['filename']}"
                                    
                                    logger.info(f"Attempting to read file from: {file_path}")
                                    
                                    # Try to read the downloaded file
                                    try:
                                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                            file_content = f.read()[:2000]  # First 2000 chars
                                        attachment_info += f"\nFILE CONTENT (first 2000 chars):\n{file_content}\n"
                                        logger.info(f"Successfully read attachment: {attachments[0]['filename']}")
                                    except Exception as e:
                                        logger.error(f"Could not read file content: {e}")
                                        attachment_info += f"\nCould not read file content: {e}\n"
                                else:
                                    attachment_info += f"\nFailed to download attachment: {download_response}\n"
                            else:
                                logger.warning("No download result received")
                                attachment_info += f"\nNo download result received\n"
                        except Exception as e:
                            logger.error(f"Error downloading attachment: {e}")
                            attachment_info += f"\nError downloading attachment: {e}\n"
                    else:
                        logger.warning("First attachment is not valid or missing filename")
                        attachment_info += f"\nFirst attachment is not valid or missing filename\n"
            
            # Generate LLM response
            start_time = time.time()
            
            # Create a more explicit prompt when we have file content
            if attachment_info and "FILE CONTENT" in attachment_info:
                system_prompt = f"""You are {self.config.name}, a helpful Discord bot powered by {self.config.llm_type}.

IMPORTANT: The user has uploaded a file and you have SUCCESSFULLY downloaded and read it. The file content is provided below. You MUST analyze and respond about this specific file content.

DO NOT say you cannot read files - you have already successfully read the file.{attachment_info}

Based on the file content above, provide a helpful analysis of what the file contains. Be specific about what you found in the file."""
            else:
                system_prompt = f"""You are {self.config.name}, a helpful Discord bot powered by {self.config.llm_type}.
You're participating in a Discord conversation. Be conversational, helpful, and engaging.
Keep responses concise but informative. Avoid being repetitive or robotic.

IMPORTANT: Do NOT include your name or any prefixes like "{self.config.name}:" in your responses. Just respond naturally as if you're speaking directly to the user.

CAPABILITIES: You have access to file operations - you can download files uploaded by users and analyze their content. When users upload files and ask you to read them, you can download and process the files.{attachment_info}"""
            
            response_content = await self.llm_provider.generate_response(
                context_messages, 
                system_prompt
            )
            
            # Clean up the response - remove repeated bot name prefixes
            # Remove patterns like "Grok4Agent: Grok4Agent:" or "BotName: BotName:"
            import re
            bot_name = self.config.name
            # Remove multiple consecutive bot name prefixes 
            pattern = rf"^({re.escape(bot_name)}:\s*)+"
            response_content = re.sub(pattern, "", response_content, flags=re.IGNORECASE).strip()
            
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
                
                # Store audit log in PostgreSQL via memory system
                try:
                    audit_content = f"AUDIT: {self.config.name} responded ({processing_time:.2f}s) to: {message_data['content'][:100]}..."
                    self.memory.store_message({
                        'id': f"audit_{int(time.time())}",
                        'channel_id': channel_id,
                        'thread_id': thread_id,
                        'author_id': 'system',
                        'author_name': 'AUDIT',
                        'content': audit_content,
                        'timestamp': datetime.now(),
                        'is_bot': True,
                        'agent_name': self.config.name
                    })
                except Exception as e:
                    logger.warning(f"Failed to store audit log: {e}")
            
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
                    'is_bot': 'bot' in json_data.get('author', '').lower(),
                    'attachments': json_data.get('attachments', [])
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
        # Create server parameters with environment
        server_params = StdioServerParameters(
            command=self.mcp_command,
            args=self.mcp_args,
            env=self.mcp_env
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

def load_agent_config(config_key: str = "grok4_agent") -> AgentConfig:
    """Load agent configuration from environment and config files"""
    # Load from agent_config.json if available
    config_file = pathlib.Path(__file__).parent / "agent_config.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            agents = config_data.get('agents', {})
            if config_key in agents:
                agent_config = agents[config_key]
                
                # Map llm_type to appropriate token and API key
                token_map = {
                    "grok4": "DISCORD_TOKEN_GROK",
                    "claude": "DISCORD_TOKEN2", 
                    "gemini": "DISCORD_TOKEN3",
                    "openai": "DISCORD_TOKEN4"
                }
                
                api_key_map = {
                    "grok4": "XAI_API_KEY",
                    "claude": "ANTHROPIC_API_KEY",
                    "gemini": "GOOGLE_AI_API_KEY", 
                    "openai": "OPENAI_API_KEY"
                }
                
                llm_type = agent_config.get('llm_type', 'grok4')
                token_env = token_map.get(llm_type, "DISCORD_TOKEN_GROK")
                api_key_env = api_key_map.get(llm_type, "XAI_API_KEY")
                
                return AgentConfig(
                    name=agent_config.get('name', 'Agent'),
                    bot_token=os.getenv(token_env, ""),
                    server_id=os.getenv("DEFAULT_SERVER_ID", "1395578178973597799"),
                    api_key=os.getenv(api_key_env, ""),
                    llm_type=llm_type,
                    max_context_messages=agent_config.get('max_context_messages', 15),
                    max_turns_per_thread=agent_config.get('max_turns_per_thread', 30),
                    response_delay=agent_config.get('response_delay', 2.0),
                    ignore_bots=agent_config.get('ignore_bots', True),
                    bot_allowlist=agent_config.get('bot_allowlist', [])
                )
    
    # Fallback to default Grok4 config
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
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Discord Agent')
    parser.add_argument('--config-key', default='grok4_agent', help='Configuration key from agent_config.json')
    args = parser.parse_args()
    
    config = load_agent_config(args.config_key)
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