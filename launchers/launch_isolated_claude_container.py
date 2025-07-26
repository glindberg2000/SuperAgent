#!/usr/bin/env python3
"""
Launch Claude Code Container with ISOLATED workspace
Creates a clean environment separate from SuperAgent project
"""

import docker
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

def launch_isolated_claude_container(
    container_name: str = "claude-isolated-discord",
    discord_token_env: str = "DISCORD_TOKEN_CLAUDE",
    use_official_image: bool = True
):
    """
    Launch Claude Code container with isolated clean workspace
    """
    
    # Connect to Docker
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"❌ Docker connection failed: {e}")
        try:
            client = docker.DockerClient(base_url='unix:///Users/greg/.colima/default/docker.sock')
        except Exception as e2:
            print(f"❌ Colima Docker socket failed: {e2}")
            return False
    
    # Check if container already exists
    try:
        existing = client.containers.get(container_name)
        if existing.status == "running":
            print(f"✅ Container {container_name} is already running")
            return True
        elif existing.status == "exited":
            print(f"🔄 Restarting existing container {container_name}")
            existing.start()
            return True
    except docker.errors.NotFound:
        print(f"📦 Creating new isolated container {container_name}")
    
    # Load environment variables
    discord_token = os.getenv(discord_token_env)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    server_id = os.getenv("DEFAULT_SERVER_ID")
    
    if not discord_token:
        print(f"❌ Missing environment variable: {discord_token_env}")
        return False
    
    if not (anthropic_key or oauth_token):
        print("❌ Missing both ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN")
        return False
    
    if not server_id:
        print("❌ Missing DEFAULT_SERVER_ID")
        return False
    
    # Create isolated workspace directory
    isolated_workspace = Path.home() / "claude_workspaces" / container_name
    isolated_workspace.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Using isolated workspace: {isolated_workspace}")
    
    # Choose image
    image = "superagent/official-claude-code:latest" if use_official_image else "superagent/claude-code-authenticated:latest"
    print(f"🚀 Using image: {image}")
    
    # Container environment
    env = {
        "DISCORD_TOKEN": discord_token,
        "DEFAULT_SERVER_ID": server_id,
        "AGENT_TYPE": "isolated_claude",
        "AGENT_PERSONALITY": "Claude Code container with isolated workspace. I am a separate bot from the SuperAgent system, operating independently for Discord-managed tasks.",
        "WORKSPACE_PATH": "/workspace"
    }
    
    # Add authentication
    if oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
        env["ANTHROPIC_AUTH_TOKEN"] = oauth_token
        print("   Using OAuth token for Claude authentication")
    elif anthropic_key:
        env["ANTHROPIC_API_KEY"] = anthropic_key
        print("   Using API key for Claude authentication")
    
    # Volumes - ONLY isolated workspace and mcp-discord
    superagent_path = str(Path(__file__).parent.absolute())
    mcp_discord_path = os.path.join(superagent_path, "mcp-discord")
    
    volumes = {
        str(isolated_workspace): {"bind": "/workspace", "mode": "rw"},
        mcp_discord_path: {"bind": "/home/node/mcp-discord", "mode": "rw"}
    }
    
    # Check if mcp-discord exists
    if not os.path.exists(mcp_discord_path):
        print(f"⚠️  Warning: mcp-discord not found at {mcp_discord_path}")
        print("   Discord integration may not work properly")
    
    # Labels for identification
    labels = {
        "superagent.type": "claude-code-isolated",
        "superagent.agent": "discord-managed",
        "superagent.team": "autonomous",
        "superagent.managed": "discord",
        "superagent.workspace": "isolated"
    }
    
    try:
        # Create container
        container = client.containers.run(
            image=image,
            name=container_name,
            environment=env,
            volumes=volumes,
            labels=labels,
            detach=True,
            stdin_open=True,
            tty=True,
            restart_policy={"Name": "unless-stopped"},
            working_dir="/workspace",
            command="sleep infinity"
        )
        
        print(f"✅ Isolated container created successfully!")
        print(f"   Container ID: {container.id[:12]}")
        print(f"   Container Name: {container_name}")
        print(f"   Isolated Workspace: {isolated_workspace}")
        print(f"   Discord Token: {discord_token_env}")
        
        # Create clean workspace structure
        container.exec_run("mkdir -p /workspace/projects")
        container.exec_run("mkdir -p /workspace/logs")
        container.exec_run("mkdir -p /workspace/temp")
        
        # Create identification file
        container.exec_run(f'echo "Claude Code Isolated Container\\nCreated: {datetime.now().isoformat()}\\nPurpose: Discord-managed autonomous operations\\nWorkspace: Isolated from SuperAgent project" > /workspace/README.txt')
        
        # Set up MCP Discord configuration
        print("🔧 Setting up MCP Discord configuration...")
        mcp_config = {
            "mcpServers": {
                "discord-isolated": {
                    "type": "stdio",
                    "command": "python3",
                    "args": [
                        "-m", "discord_mcp",
                        "--token", discord_token,
                        "--server-id", server_id
                    ],
                    "env": {
                        "PYTHONPATH": "/home/node/mcp-discord/src"
                    }
                }
            }
        }
        
        # Create MCP config in container
        container.exec_run("mkdir -p /home/node/.claude")
        mcp_config_str = json.dumps(mcp_config, indent=2)
        container.exec_run(f"echo '{mcp_config_str}' > /home/node/.claude/config.json")
        
        # Create the critical __main__.py file
        container.exec_run('echo "from discord_mcp import main; main()" > /home/node/mcp-discord/src/discord_mcp/__main__.py')
        print("✅ Created critical __main__.py file")
        
        # Test Claude authentication
        print("🔍 Testing Claude Code authentication...")
        exec_result = container.exec_run("claude --version", stdout=True, stderr=True)
        if exec_result.exit_code == 0:
            version = exec_result.output.decode().strip()
            print(f"✅ Claude Code working: {version}")
        else:
            print(f"⚠️  Claude Code test failed: {exec_result.output.decode()}")
        
        # Test MCP connection
        print("🔍 Testing MCP Discord connection...")
        exec_result = container.exec_run("claude mcp list", stdout=True, stderr=True)
        if "Connected" in exec_result.output.decode():
            print("✅ MCP Discord connection working")
        else:
            print(f"⚠️  MCP connection issue: {exec_result.output.decode()}")
        
        # Document the container
        container_info = {
            "container_id": container.id,
            "container_name": container_name,
            "image": image,
            "created_at": datetime.now().isoformat(),
            "discord_token_env": discord_token_env,
            "workspace": str(isolated_workspace),
            "type": "isolated",
            "purpose": "discord-managed-autonomous",
            "status": "created_successfully"
        }
        
        # Save container info
        registry_file = "isolated_container_registry.json"
        try:
            with open(registry_file, "r") as f:
                registry = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            registry = {}
        
        registry[container_name] = container_info
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        
        print(f"📝 Container info saved to {registry_file}")
        print(f"\n🎯 Next steps:")
        print(f"   1. Test identity: docker exec {container_name} claude --dangerously-skip-permissions --print 'Send message identifying myself as isolated Claude Code bot'")
        print(f"   2. Monitor workspace: ls {isolated_workspace}")
        print(f"   3. Container logs: docker logs {container_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create isolated container: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SuperAgent Isolated Claude Code Container Launcher")
    print("=" * 60)
    
    success = launch_isolated_claude_container()
    
    if success:
        print("\n✅ Isolated container launched successfully!")
    else:
        print("\n❌ Container launch failed!")
        sys.exit(1)