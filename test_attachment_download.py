#!/usr/bin/env python3
"""
Test file download functionality with enhanced Discord agent
"""
import asyncio
import os
from enhanced_discord_agent import EnhancedDiscordAgent, AgentConfig
from dotenv import load_dotenv

load_dotenv()

async def test_agent_with_file():
    """Test that the agent can handle file attachments"""
    
    # Create agent config
    config = AgentConfig(
        name="TestFileAgent",
        bot_token=os.getenv("DISCORD_TOKEN_GROK", ""),
        server_id=os.getenv("DEFAULT_SERVER_ID", "1395578178973597799"),
        api_key=os.getenv("XAI_API_KEY", ""),
        llm_type="grok4",
        max_context_messages=5,
        max_turns_per_thread=10,
        response_delay=1.0,
        ignore_bots=True,
        bot_allowlist=[]
    )
    
    # Create agent
    agent = EnhancedDiscordAgent(config)
    
    print("🤖 Starting enhanced Discord agent with file capabilities...")
    print("💡 Upload a file in Discord and ask: 'can you download and read this file?'")
    print("🔍 The agent should now be able to download and process file attachments!")
    print("⚠️  Press Ctrl+C to stop")
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        print("\n✅ Agent stopped by user")
    except Exception as e:
        print(f"\n❌ Agent error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_agent_with_file())