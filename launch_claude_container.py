#!/usr/bin/env python3
"""
Launch Claude Code Container with Persistent Authentication
Ensures we don't lose our working authenticated containers
"""

import docker
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

def launch_claude_container(
    container_name: str = "claude-fullstackdev-persistent",
    discord_token_env: str = "DISCORD_TOKEN_CLAUDE",  # Use Claude token
    use_official_image: bool = True
):
    """
    Launch a persistent Claude Code container with proper environment setup
    
    Args:
        container_name: Name for the container (should be persistent)
        discord_token_env: Which Discord token to use from environment
        use_official_image: Use superagent/official-claude-code vs authenticated
    """
    
    # Connect to Docker
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"❌ Docker connection failed: {e}")
        try:
            # Try Colima socket
            client = docker.DockerClient(base_url='unix:///Users/greg/.colima/default/docker.sock')
        except Exception as e2:
            print(f"❌ Colima Docker socket failed: {e2}")
            return False
    
    # Check if container already exists
    try:
        existing = client.containers.get(container_name)
        if existing.status == "running":
            print(f"✅ Container {container_name} is already running")
            print(f"   Container ID: {existing.id[:12]}")
            return True
        elif existing.status == "exited":
            print(f"🔄 Restarting existing container {container_name}")
            existing.start()
            print(f"✅ Container {container_name} restarted")
            return True
    except docker.errors.NotFound:
        print(f"📦 Creating new container {container_name}")
    
    # Load environment variables
    discord_token = os.getenv(discord_token_env)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    server_id = os.getenv("DEFAULT_SERVER_ID")
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://superagent:superagent@localhost:5433/superagent")
    
    if not discord_token:
        print(f"❌ Missing environment variable: {discord_token_env}")
        return False
    
    if not (anthropic_key or oauth_token):
        print("❌ Missing both ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN")
        return False
    
    if not server_id:
        print("❌ Missing DEFAULT_SERVER_ID")
        return False
    
    # Choose image
    if use_official_image:
        image = "superagent/official-claude-code:latest"
    else:
        image = "superagent/claude-code-authenticated:latest"
    
    print(f"🚀 Using image: {image}")
    
    # Container environment
    env = {
        "DISCORD_TOKEN": discord_token,
        "DEFAULT_SERVER_ID": server_id,
        "POSTGRES_URL": postgres_url,
        "AGENT_TYPE": "fullstackdev",
        "AGENT_PERSONALITY": "Full-stack developer specializing in Python, Docker, system architecture, and SuperAgent development. Expert in containerization and multi-agent systems.",
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
    
    # Volumes - bind current SuperAgent directory and mcp-discord
    workspace_path = str(Path(__file__).parent.absolute())
    mcp_discord_path = os.path.join(workspace_path, "mcp-discord")
    
    volumes = {
        workspace_path: {"bind": "/workspace", "mode": "rw"},
        mcp_discord_path: {"bind": "/home/node/mcp-discord", "mode": "rw"}  # Changed to rw for uv
    }
    
    # Check if mcp-discord exists
    if not os.path.exists(mcp_discord_path):
        print(f"⚠️  Warning: mcp-discord not found at {mcp_discord_path}")
        print("   Discord integration may not work properly")
    
    # Labels for identification
    labels = {
        "superagent.type": "claude-code",
        "superagent.agent": "fullstackdev",
        "superagent.team": "development",
        "superagent.managed": "true",
        "superagent.persistent": "true"
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
            restart_policy={"Name": "unless-stopped"},  # Auto-restart
            working_dir="/workspace",
            command="sleep infinity"  # Keep container running
        )
        
        print(f"✅ Container created successfully!")
        print(f"   Container ID: {container.id[:12]}")
        print(f"   Container Name: {container_name}")
        print(f"   Status: {container.status}")
        print(f"   Image: {image}")
        print(f"   Discord Token: {discord_token_env} (configured)")
        print(f"   Workspace: {workspace_path}")
        
        # Set up MCP Discord configuration
        print("\n🔧 Setting up MCP Discord configuration...")
        mcp_config = {
            "mcpServers": {
                "discord-fullstackdev": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "--directory",
                        "/home/node/mcp-discord",
                        "run",
                        "mcp-discord",
                        "--token",
                        discord_token,
                        "--server-id",
                        server_id
                    ],
                    "env": {}
                }
            }
        }
        
        # Create .claude directory and config file in container
        container.exec_run("mkdir -p /home/node/.claude")
        container.exec_run(f"echo '{json.dumps(mcp_config, indent=2)}' > /home/node/.claude/config.json")
        print("✅ MCP configuration created")
        
        # Test Claude authentication
        print("\n🔍 Testing Claude Code authentication...")
        try:
            exec_result = container.exec_run("claude --version", stdout=True, stderr=True)
            if exec_result.exit_code == 0:
                version = exec_result.output.decode().strip()
                print(f"✅ Claude Code working: {version}")
            else:
                print(f"⚠️  Claude Code test failed: {exec_result.output.decode()}")
        except Exception as e:
            print(f"⚠️  Could not test Claude Code: {e}")
        
        # Document the container
        container_info = {
            "container_id": container.id,
            "container_name": container_name,
            "image": image,
            "created_at": datetime.now().isoformat(),
            "discord_token_env": discord_token_env,
            "authentication": "oauth" if oauth_token else "api_key",
            "workspace": workspace_path,
            "status": "created_successfully"
        }
        
        # Save container info for tracking
        with open("container_registry.json", "w") as f:
            try:
                with open("container_registry.json", "r") as rf:
                    registry = json.load(rf)
            except (FileNotFoundError, json.JSONDecodeError):
                registry = {}
            
            registry[container_name] = container_info
            json.dump(registry, f, indent=2)
        
        print(f"\n📝 Container info saved to container_registry.json")
        print(f"\n🎯 Next steps:")
        print(f"   1. Connect to container: docker exec -it {container_name} /bin/bash")
        print(f"   2. Test Discord connection: claude mcp list")
        print(f"   3. Monitor via dashboard: Press '8' for containers view")
        print(f"   4. Container will auto-restart unless stopped manually")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create container: {e}")
        return False

def list_claude_containers():
    """List all Claude-related containers"""
    try:
        client = docker.from_env()
    except:
        try:
            client = docker.DockerClient(base_url='unix:///Users/greg/.colima/default/docker.sock')
        except Exception as e:
            print(f"❌ Docker connection failed: {e}")
            return
    
    print("🐳 Claude Code Containers:")
    print("=" * 60)
    
    containers = client.containers.list(all=True)
    claude_containers = []
    
    for container in containers:
        if any(tag in container.image.tags[0] if container.image.tags else "" 
               for tag in ["claude-code", "official-claude-code"]) or \
           "claude" in container.name.lower():
            claude_containers.append(container)
    
    if not claude_containers:
        print("❌ No Claude Code containers found")
        return
    
    for container in claude_containers:
        status_icon = "🟢" if container.status == "running" else "🔴" if container.status == "exited" else "🟡"
        print(f"{status_icon} {container.name}")
        print(f"   ID: {container.id[:12]}")
        print(f"   Image: {container.image.tags[0] if container.image.tags else 'Unknown'}")
        print(f"   Status: {container.status}")
        print(f"   Created: {container.attrs['Created'][:19]}")
        
        # Check labels
        labels = container.labels or {}
        if labels.get('superagent.type'):
            print(f"   Type: {labels.get('superagent.type')}")
            print(f"   Agent: {labels.get('superagent.agent', 'Unknown')}")
            print(f"   Team: {labels.get('superagent.team', 'Unknown')}")
        print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_claude_containers()
    else:
        print("🚀 SuperAgent Claude Code Container Launcher")
        print("=" * 50)
        
        # Launch the container
        success = launch_claude_container()
        
        if success:
            print("\n✅ Container launched successfully!")
            print("\n📊 Current Claude containers:")
            list_claude_containers()
        else:
            print("\n❌ Container launch failed!")
            sys.exit(1)