#!/usr/bin/env python3
"""
Multi-Agent Discord Bot Launcher
Launches multiple Discord agents with different LLM providers
"""

import asyncio
import json
import os
import logging
from typing import Dict, List
import argparse
from dotenv import load_dotenv
from enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiAgentLauncher:
    """Manages multiple Discord agents"""
    
    def __init__(self, config_path: str = "agent_config.json"):
        self.config_path = config_path
        self.agents: Dict[str, EnhancedDiscordAgent] = {}
        self.tasks: List[asyncio.Task] = []
        
    def load_config(self) -> dict:
        """Load agent configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def create_agent_config(self, agent_name: str, agent_data: dict) -> AgentConfig:
        """Create AgentConfig from configuration data"""
        
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
            'openai': os.getenv('DISCORD_TOKEN_O3') or os.getenv('DISCORD_TOKEN_GROK')
        }
        
        llm_type = agent_data['llm_type']
        api_key = api_keys.get(llm_type)
        bot_token = bot_tokens.get(llm_type)
        
        if not api_key:
            raise ValueError(f"Missing API key for {llm_type}. Set environment variable.")
        
        if not bot_token:
            raise ValueError(f"Missing Discord bot token for {llm_type}. Set DISCORD_TOKEN_GROK or agent-specific token.")
        
        config = AgentConfig(
            name=agent_data['name'],
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
        
        return config
    
    async def launch_agent(self, agent_name: str, config: AgentConfig):
        """Launch a single agent"""
        try:
            logger.info(f"Starting agent: {agent_name}")
            agent = EnhancedDiscordAgent(config)
            self.agents[agent_name] = agent
            await agent.run()
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
    
    async def launch_all_agents(self, agent_names: List[str] = None):
        """Launch all configured agents or specified ones"""
        config_data = self.load_config()
        agents_to_launch = agent_names or list(config_data['agents'].keys())
        
        logger.info(f"Launching {len(agents_to_launch)} agents: {', '.join(agents_to_launch)}")
        
        # Create tasks for each agent
        for agent_name in agents_to_launch:
            if agent_name not in config_data['agents']:
                logger.warning(f"Agent {agent_name} not found in config")
                continue
            
            try:
                agent_config = self.create_agent_config(agent_name, config_data['agents'][agent_name])
                task = asyncio.create_task(self.launch_agent(agent_name, agent_config))
                self.tasks.append(task)
                
                # Small delay between agent launches
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to create {agent_name}: {e}")
        
        if not self.tasks:
            logger.error("No agents were successfully created")
            return
        
        logger.info("All agents launched. Running...")
        
        # Wait for all tasks to complete (they should run indefinitely)
        try:
            await asyncio.gather(*self.tasks)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        except Exception as e:
            logger.error(f"Error in agent execution: {e}")
        finally:
            await self.shutdown_all_agents()
    
    async def shutdown_all_agents(self):
        """Gracefully shutdown all agents"""
        logger.info("Shutting down all agents...")
        
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("All agents shut down")

def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Multi-Agent Discord Bot Launcher')
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
    
    args = parser.parse_args()
    
    launcher = MultiAgentLauncher(args.config)
    
    if args.list_agents:
        try:
            config = launcher.load_config()
            print("Available agents:")
            for agent_name, agent_data in config['agents'].items():
                print(f"  - {agent_name} ({agent_data['llm_type']})")
        except Exception as e:
            print(f"Error loading config: {e}")
        return
    
    # Check required environment variables
    required_env_vars = ['DISCORD_TOKEN_GROK', 'DEFAULT_SERVER_ID']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Check for at least one LLM API key
    llm_keys = {
        'XAI_API_KEY': 'grok4',
        'ANTHROPIC_API_KEY': 'claude', 
        'GOOGLE_AI_API_KEY': 'gemini'
    }
    
    available_llms = [name for env_var, name in llm_keys.items() if os.getenv(env_var)]
    
    if not available_llms:
        logger.error("No LLM API keys found. Set at least one of: XAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY")
        return
    
    logger.info(f"Available LLMs: {', '.join(available_llms)}")
    
    try:
        asyncio.run(launcher.launch_all_agents(args.agents))
    except KeyboardInterrupt:
        logger.info("Launcher interrupted by user")
    except Exception as e:
        logger.error(f"Launcher error: {e}")

if __name__ == "__main__":
    main()