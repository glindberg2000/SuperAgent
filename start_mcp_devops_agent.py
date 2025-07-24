#!/usr/bin/env python3
"""
MCP DevOps Agent Startup Script
Launcher for the MCP-based AI DevOps agent with environment validation
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

def check_environment():
    """Check that required environment variables are set"""
    print("🔍 Checking environment...")
    
    required_vars = [
        'DISCORD_TOKEN_DEVOPS',
        'ANTHROPIC_API_KEY',
        'DEFAULT_SERVER_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set these in your .env file or environment:")
        for var in missing:
            print(f"  export {var}=your_value_here")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_dependencies():
    """Check that required Python packages are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import anthropic
        import docker
        import psutil
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        print("✅ Core dependencies and MCP available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install -r control_plane/requirements.txt")
        print("Also ensure MCP client is installed: pip install mcp")
        return False

def check_docker():
    """Check Docker daemon status"""
    print("🔍 Checking Docker...")
    
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✅ Docker daemon running")
        return True
    except Exception as e:
        print(f"⚠️ Docker daemon not available: {e}")
        print("Agent will run with limited container management capabilities")
        return False

def check_mcp_config():
    """Check MCP configuration exists"""
    print("🔍 Checking MCP configuration...")
    
    mcp_config_path = Path(__file__).parent / "mcp.json"
    if mcp_config_path.exists():
        print("✅ MCP configuration found")
        return True
    else:
        print("⚠️ MCP configuration not found at mcp.json")
        print("Agent will use fallback MCP configuration")
        return False

def create_directories():
    """Create required directories"""
    dirs = ['logs', 'data', 'configs']
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    print("✅ Required directories created")

async def start_agent():
    """Start the MCP DevOps Agent"""
    print("🚀 Starting MCP DevOps Agent...")
    
    # Add control_plane to Python path
    sys.path.insert(0, str(Path(__file__).parent / 'control_plane'))
    
    try:
        from mcp_devops_agent import MCPDevOpsAgent
        
        agent = MCPDevOpsAgent()
        await agent.start()
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down MCP DevOps Agent...")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main startup routine"""
    print("🤖 SuperAgent MCP DevOps Agent Startup")
    print("=" * 45)
    
    # Environment checks
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    check_docker()  # Non-blocking check
    check_mcp_config()  # Non-blocking check
    
    # Setup
    create_directories()
    
    print("\n🎯 All checks passed! Starting MCP agent...")
    print("The agent will connect to Discord via MCP for consistency")
    print("Press Ctrl+C to stop\n")
    
    # Start the agent
    try:
        asyncio.run(start_agent())
    except KeyboardInterrupt:
        print("\n👋 Agent stopped by user")
    except Exception as e:
        print(f"\n❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()