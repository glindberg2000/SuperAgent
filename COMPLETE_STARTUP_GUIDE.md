# 🚀 SuperAgent Complete Startup Guide

**How to start the entire SuperAgent ecosystem with DevOps online**

## 🎯 **Quick Start (TL;DR)**

```bash
# 1. Start DevOps agent
python control_plane/mcp_devops_agent.py &

# 2. Start Claude Code container with Git access
./start_claude_container.sh claude-isolated-discord

# 3. Verify everything is working
python devops_claude_manager.py status
```

## 📋 **Complete Startup Process**

### Step 1: Environment Setup
```bash
# Ensure you're in the SuperAgent directory
cd /Users/greg/repos/SuperAgent

# Load environment variables
source .env  # or ensure .env is properly configured

# Verify required tokens are set
echo "DevOps Token: ${DISCORD_TOKEN_DEVOPS:0:10}..."
echo "Claude Token: ${DISCORD_TOKEN_CLAUDE:0:10}..."
echo "Server ID: $DEFAULT_SERVER_ID"
```

### Step 2: Start Core Services

#### A. PostgreSQL Database (if needed)
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if not running
docker-compose up -d postgres
```

#### B. DevOps Agent (Critical - Must Start First)
```bash
# Start DevOps MCP agent with proper Discord token
python control_plane/mcp_devops_agent.py &

# Verify it's running
ps aux | grep mcp_devops_agent

# Check logs
tail -f logs/devops_agent.log  # if log file exists
```

#### C. Claude Code Container (For Discord Management)
```bash
# Start isolated Claude container with Git SSH keys
./start_claude_container.sh claude-isolated-discord

# Verify container is working
docker exec claude-isolated-discord claude --print "Container startup test"

# Test Discord connection
python devops_claude_manager.py test
```

### Step 3: Optional Additional Agents

#### Multi-Agent Discord Bots (if needed)
```bash
# Start individual agents
python launch_single_agent.py grok4_agent &
python launch_single_agent.py claude_agent &
python launch_single_agent.py gemini_agent &

# Or start all at once
python multi_agent_launcher.py &
```

### Step 4: Verification

#### Check System Status
```bash
# 1. DevOps agent status
python devops_claude_manager.py status

# 2. Container health
./manage_claude_containers.sh health claude-isolated-discord

# 3. Discord bot connections
python agent_dashboard.py  # Interactive dashboard

# 4. Check all running processes
ps aux | grep -E "(devops|agent|claude)"
```

#### Test Discord Integration
```bash
# Test DevOps agent Discord connection
python devops_claude_manager.py test

# Test Claude container Discord
docker exec claude-isolated-discord claude \
  --dangerously-skip-permissions \
  --print 'Send startup verification message to Discord'
```

## 🤖 **DevOps Agent Configuration**

### Environment Variables Required
```bash
DISCORD_TOKEN_DEVOPS=YOUR_TOKEN_HERE
DEFAULT_SERVER_ID=1395578178973597799
ANTHROPIC_API_KEY=""sk-ant-api03-YOUR_ANTHROPIC_KEY_HERE""
```

### DevOps Agent Features
- ✅ Discord command processing
- ✅ Container management  
- ✅ Agent deployment control
- ✅ System monitoring
- ✅ Claude Code container integration

### DevOps Discord Commands (via DevOps bot)
```
!devops status          - System status check
!devops deploy <agent>  - Deploy specific agent
!devops stop <agent>    - Stop specific agent  
!devops claude start    - Start Claude container
!devops claude test     - Test Claude container
!devops logs <service>  - Show service logs
```

## 🏗️ **Team Configuration**

### Create New Team
1. **Edit `agent_config.json`:**
```json
{
  "teams": {
    "new_team_name": {
      "description": "Team description",
      "default_server_id": "YOUR_DISCORD_SERVER_ID",
      "gm_channel": "YOUR_GM_CHANNEL_ID", 
      "agents": ["agent1", "agent2"],
      "auto_deploy": true,
      "discord_tokens": {
        "devops": "DISCORD_TOKEN_DEVOPS_NEW_TEAM",
        "claude": "DISCORD_TOKEN_CLAUDE_NEW_TEAM"
      }
    }
  }
}
```

2. **Add Environment Variables:**
```bash
# Add to .env file
DISCORD_TOKEN_DEVOPS_NEW_TEAM=your_devops_bot_token
DISCORD_TOKEN_CLAUDE_NEW_TEAM=your_claude_bot_token
NEW_TEAM_SERVER_ID=your_server_id
NEW_TEAM_GM_CHANNEL=your_gm_channel_id
```

3. **Deploy Team:**
```bash
# Start DevOps agent for new team
python control_plane/mcp_devops_agent.py --team new_team_name &

# Start Claude container for new team  
./start_claude_container.sh claude-new-team --team new_team_name
```

## 🛠️ **Troubleshooting**

### DevOps Agent Not Responding
```bash
# Check process
ps aux | grep mcp_devops_agent

# Restart DevOps agent
pkill -f mcp_devops_agent
python control_plane/mcp_devops_agent.py &

# Check Discord connection
python -c "
import os
print('DevOps Token:', os.getenv('DISCORD_TOKEN_DEVOPS', 'NOT SET'))
print('Server ID:', os.getenv('DEFAULT_SERVER_ID', 'NOT SET'))
"
```

### Claude Container Issues
```bash
# Check container status
docker ps | grep claude

# Recreate container
docker stop claude-isolated-discord
docker rm claude-isolated-discord
./start_claude_container.sh claude-isolated-discord

# Check authentication
docker exec claude-isolated-discord claude mcp list
```

### Git Access Issues
```bash
# Verify SSH keys in container
docker exec claude-isolated-discord ls -la /home/node/.ssh

# Test Git access
docker exec claude-isolated-discord ssh -T git@github.com

# Fix SSH permissions
docker exec claude-isolated-discord chmod 600 /home/node/.ssh/id_rsa
```

## 📊 **System Architecture**

```
┌─────────────────────────────────────────┐
│           SuperAgent Host               │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │        DevOps Agent                 │ │
│  │  • Discord: DISCORD_TOKEN_DEVOPS    │ │
│  │  • Commands: !devops status, etc.   │ │
│  │  • Process: mcp_devops_agent.py     │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │     Multi-Agent System              │ │
│  │  • Grok4, Claude, Gemini agents     │ │
│  │  • Each with own Discord token      │ │
│  │  • Process: launch_single_agent.py  │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      Claude Code Container              │
│  • Name: claude-isolated-discord        │
│  • Discord: DISCORD_TOKEN_CLAUDE        │
│  • Git: SSH keys mounted                │
│  • Workspace: Isolated                  │
│  • Managed by: DevOps agent             │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│            Discord Server               │
│  • DevOps Bot (DEVOPS token)           │
│  • Claude Bot (CLAUDE token)           │  
│  • Multi-Agent Bots (various tokens)   │
└─────────────────────────────────────────┘
```

## ✅ **Success Indicators**

- DevOps agent responds to Discord commands
- Claude container sends messages with correct bot identity
- Git operations work in Claude container
- All agents show "online" status in Discord
- Dashboard shows all services running

---
**Last Updated:** July 25, 2025  
**Status:** Ready for full deployment