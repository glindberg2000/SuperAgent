#!/usr/bin/env python3
"""
Conversational DevOps AI Launcher
Uses the modern OpenAI-based conversational DevOps system
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

def check_environment():
    """Check that required environment variables are set"""
    print("🔍 Checking environment...")

    required_vars = [
        'DISCORD_TOKEN_DEVOPS',
        'OPENAI_API_KEY',
        'DEFAULT_SERVER_ID'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print("Please set these in your .env file")
        return False

    print("✅ Environment variables configured")
    return True

async def start_conversational_devops():
    """Start the Conversational DevOps AI"""
    print("🚀 Starting Conversational DevOps AI...")

    try:
        from agents.devops.conversational_devops_ai import RealMCPDevOpsAgent
        from agents.enhanced_discord_agent import AgentConfig

        # Create agent config
        config = AgentConfig(
            name="RealMCPDevOpsAgent",
            bot_token=os.getenv('DISCORD_TOKEN_DEVOPS'),
            server_id=os.getenv('DEFAULT_SERVER_ID'),
            api_key=os.getenv('OPENAI_API_KEY'),
            llm_type="openai"
        )

        # Create and start the agent
        agent = RealMCPDevOpsAgent(config)

        # Initialize MCP tools
        success = await agent.initialize_mcp_tools()
        if not success:
            print("❌ Failed to initialize MCP tools - check that MCP servers are available")
            return

        print("✅ Real MCP DevOps AI initialized with MCP tools")
        print("🎧 Starting message listener...")

        await agent.run()

    except KeyboardInterrupt:
        print("\n👋 Shutting down Conversational DevOps AI...")
    except Exception as e:
        print(f"❌ Error starting agent: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    print("🤖 SuperAgent Real MCP DevOps AI")
    print("=" * 50)

    if not check_environment():
        sys.exit(1)

    # Create required directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    # Start the agent
    asyncio.run(start_conversational_devops())

if __name__ == "__main__":
    main()
