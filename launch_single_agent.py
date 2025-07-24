#!/usr/bin/env python3
"""
Single Agent Launcher - Deploy individual agents with PostgreSQL
Like the DevOps agent approach but simpler
"""

import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv
from enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig
from memory_client import MemoryClient

# Load environment variables
load_dotenv()

def create_agent_config(agent_type: str) -> AgentConfig:
    """Create agent configuration based on type"""
    
    # Token mapping for different agent types
    token_map = {
        "grok4_agent": "DISCORD_TOKEN_GROK",
        "claude_agent": "DISCORD_TOKEN2", 
        "gemini_agent": "DISCORD_TOKEN3",
        "o3_agent": "DISCORD_TOKEN4"
    }
    
    # API key mapping
    api_key_map = {
        "grok4_agent": "XAI_API_KEY",
        "claude_agent": "ANTHROPIC_API_KEY",
        "gemini_agent": "GOOGLE_AI_API_KEY", 
        "o3_agent": "OPENAI_API_KEY"
    }
    
    # LLM type mapping
    llm_map = {
        "grok4_agent": "grok4",
        "claude_agent": "claude",
        "gemini_agent": "gemini",
        "o3_agent": "openai"
    }
    
    # Agent name mapping
    name_map = {
        "grok4_agent": "Grok4Agent",
        "claude_agent": "ClaudeAgent", 
        "gemini_agent": "GeminiAgent",
        "o3_agent": "O3Agent"
    }
    
    # Personality mapping
    personality_map = {
        "grok4_agent": "Expert AI researcher and analyst with live web search capabilities",
        "claude_agent": "Thoughtful reasoning specialist and code analysis expert",
        "gemini_agent": "Creative collaborator and multimodal specialist",
        "o3_agent": "Logical reasoning specialist and mathematical analyst"
    }
    
    if agent_type not in token_map:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return AgentConfig(
        name=name_map[agent_type],
        bot_token=os.getenv(token_map[agent_type], ""),
        server_id=os.getenv("DEFAULT_SERVER_ID", "1395578178973597799"),
        api_key=os.getenv(api_key_map[agent_type], ""),
        llm_type=llm_map[agent_type],
        max_context_messages=15,
        max_turns_per_thread=30,
        response_delay=2.0,
        ignore_bots=True,
        bot_allowlist=[]
    )

async def test_postgres_connection():
    """Test PostgreSQL connection"""
    try:
        postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
        async with MemoryClient(postgres_url) as client:
            # Test basic functionality
            await client.store_memory(
                agent_id="test-connection",
                content="Connection test",
                metadata={"test": True}
            )
            print("✅ PostgreSQL connection successful")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Single Agent Launcher with PostgreSQL')
    parser.add_argument(
        'agent_type',
        choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'],
        help='Type of agent to launch'
    )
    parser.add_argument(
        '--test-postgres',
        action='store_true',
        help='Test PostgreSQL connection before launching'
    )
    
    args = parser.parse_args()
    
    # Test PostgreSQL if requested
    if args.test_postgres:
        if not await test_postgres_connection():
            print("Fix PostgreSQL connection before launching agent")
            sys.exit(1)
    
    # Create agent configuration
    try:
        config = create_agent_config(args.agent_type)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # Validate required environment variables
    if not config.bot_token:
        print(f"❌ Missing Discord token for {args.agent_type}")
        sys.exit(1)
        
    if not config.api_key:
        print(f"❌ Missing API key for {args.agent_type}")
        sys.exit(1)
    
    print(f"🚀 Starting {config.name} with PostgreSQL backend...")
    print(f"   LLM Type: {config.llm_type}")
    print(f"   Discord Token: {config.bot_token[:20]}...")
    print(f"   PostgreSQL: {os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')}")
    
    # Create and run agent
    agent = EnhancedDiscordAgent(config)
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Agent stopped by user")
    except Exception as e:
        print(f"\n❌ Agent error: {e}")
        sys.exit(1)