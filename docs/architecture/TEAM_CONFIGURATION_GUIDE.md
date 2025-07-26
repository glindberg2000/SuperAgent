# 👥 SuperAgent Team Configuration Guide

**How to create and manage teams for different Discord servers**

## 🎯 **Overview**

Teams allow you to deploy SuperAgent to multiple Discord servers with:
- Separate Discord bot tokens per team
- Different server configurations
- Isolated agent deployments
- Team-specific settings

## 📋 **Current Team Setup**

### Default Team (Current)
```json
{
  "server_id": "1395578178973597799",
  "gm_channel": "1398000953512296549",
  "bots": {
    "devops": "YOUR_TOKEN_HERE",
    "claude": "YOUR_TOKEN_HERE",
    "grok4": "YOUR_TOKEN_HERE",
    "gemini": "YOUR_TOKEN_HERE"
  }
}
```

## 🆕 **Creating a New Team**

### Step 1: Discord Server Setup

#### A. Create Discord Server
1. Create new Discord server (or use existing)
2. Note the Server ID: `Right-click server → Copy Server ID`
3. Create/identify GM channel for bot management
4. Note GM Channel ID: `Right-click channel → Copy Channel ID`

#### B. Create Discord Bots
For each team, create separate Discord bot applications:

1. **Go to:** https://discord.com/developers/applications
2. **Create Application** → Give it a team-specific name
3. **Bot Section** → Create Bot → Copy Token
4. **OAuth2 → URL Generator:**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Administrator` (or specific permissions)
5. **Invite bot to server** using generated URL

**Required Bots per Team:**
- DevOps Bot (for system management)
- Claude Bot (for Claude Code container)
- Agent Bots (Grok4, Gemini, etc. - optional)

### Step 2: Configuration Files

#### A. Update `agent_config.json`
```json
{
  "teams": {
    "default": {
      "description": "Main development team",
      "default_server_id": "1395578178973597799",
      "gm_channel": "1398000953512296549",
      "agents": ["grok4_agent", "claude_agent", "gemini_agent"],
      "auto_deploy": true
    },
    "production": {
      "description": "Production deployment team", 
      "default_server_id": "NEW_SERVER_ID_HERE",
      "gm_channel": "NEW_GM_CHANNEL_ID_HERE",
      "agents": ["grok4_agent", "claude_agent"],
      "auto_deploy": false,
      "claude_container": "claude-production-discord"
    },
    "client_team_alpha": {
      "description": "Client Alpha deployment",
      "default_server_id": "CLIENT_SERVER_ID",
      "gm_channel": "CLIENT_GM_CHANNEL_ID", 
      "agents": ["grok4_agent"],
      "auto_deploy": true,
      "claude_container": "claude-client-alpha"
    }
  }
}
```

#### B. Update `.env` File
```bash
# Team: Production
DISCORD_TOKEN_DEVOPS_PRODUCTION=your_production_devops_bot_token
DISCORD_TOKEN_CLAUDE_PRODUCTION=your_production_claude_bot_token
DISCORD_TOKEN_GROK4_PRODUCTION=your_production_grok4_bot_token
PRODUCTION_SERVER_ID=your_production_server_id
PRODUCTION_GM_CHANNEL=your_production_gm_channel_id

# Team: Client Alpha
DISCORD_TOKEN_DEVOPS_CLIENT_ALPHA=your_client_devops_bot_token
DISCORD_TOKEN_CLAUDE_CLIENT_ALPHA=your_client_claude_bot_token
CLIENT_ALPHA_SERVER_ID=your_client_server_id
CLIENT_ALPHA_GM_CHANNEL=your_client_gm_channel_id
```

### Step 3: Deploy New Team

#### A. Start DevOps Agent for Team
```bash
# Start DevOps agent for production team
python control_plane/mcp_devops_agent.py --team production &

# Start DevOps agent for client team
python control_plane/mcp_devops_agent.py --team client_team_alpha &
```

#### B. Start Claude Container for Team
```bash
# Production team Claude container
DISCORD_TOKEN_CLAUDE=$DISCORD_TOKEN_CLAUDE_PRODUCTION \
DEFAULT_SERVER_ID=$PRODUCTION_SERVER_ID \
./start_claude_container.sh claude-production-discord

# Client team Claude container  
DISCORD_TOKEN_CLAUDE=$DISCORD_TOKEN_CLAUDE_CLIENT_ALPHA \
DEFAULT_SERVER_ID=$CLIENT_ALPHA_SERVER_ID \
./start_claude_container.sh claude-client-alpha
```

#### C. Start Multi-Agent System for Team
```bash
# Production team agents
TEAM=production python multi_agent_launcher.py --agents grok4_agent claude_agent &

# Client team agents
TEAM=client_team_alpha python multi_agent_launcher.py --agents grok4_agent &
```

## 🛠️ **Team Management Scripts**

### Team Startup Script
```bash
#!/bin/bash
# start_team.sh <team_name>

TEAM_NAME=${1:-default}

echo "🚀 Starting SuperAgent team: $TEAM_NAME"

# Load team-specific environment
if [[ -f ".env.$TEAM_NAME" ]]; then
    source ".env.$TEAM_NAME"
fi

# Start DevOps agent
echo "Starting DevOps agent for $TEAM_NAME..."
python control_plane/mcp_devops_agent.py --team "$TEAM_NAME" &

# Start Claude container
echo "Starting Claude container for $TEAM_NAME..."
./start_claude_container.sh "claude-${TEAM_NAME}-discord"

# Start agents
echo "Starting agents for $TEAM_NAME..."
TEAM="$TEAM_NAME" python multi_agent_launcher.py &

echo "✅ Team $TEAM_NAME started successfully"
```

### Team Status Script
```bash
#!/bin/bash
# team_status.sh <team_name>

TEAM_NAME=${1:-default}

echo "📊 Status for team: $TEAM_NAME"
echo "================================"

# Check DevOps agent
if pgrep -f "mcp_devops_agent.py --team $TEAM_NAME" > /dev/null; then
    echo "✅ DevOps Agent: Running"
else
    echo "❌ DevOps Agent: Stopped"
fi

# Check Claude container
if docker ps --format "{{.Names}}" | grep -q "claude-${TEAM_NAME}"; then
    echo "✅ Claude Container: Running"
else
    echo "❌ Claude Container: Stopped"
fi

# Check agents
if pgrep -f "TEAM=$TEAM_NAME.*multi_agent_launcher" > /dev/null; then
    echo "✅ Multi-Agent System: Running"
else
    echo "❌ Multi-Agent System: Stopped"
fi
```

## 🔧 **Team-Specific DevOps Management**

### Updated `devops_claude_manager.py` for Teams
```python
class TeamAwareDevOpsManager:
    def __init__(self, team_name: str = "default"):
        self.team_name = team_name
        self.container_name = f"claude-{team_name}-discord"
        
    def get_team_config(self):
        """Load team-specific configuration"""
        with open("agent_config.json") as f:
            config = json.load(f)
        return config.get("teams", {}).get(self.team_name, {})
    
    def start_team_container(self):
        """Start Claude container for specific team"""
        team_config = self.get_team_config()
        
        # Set team-specific environment variables
        env_vars = {
            "DISCORD_TOKEN": os.getenv(f"DISCORD_TOKEN_CLAUDE_{self.team_name.upper()}"),
            "DEFAULT_SERVER_ID": team_config.get("default_server_id"),
            "GM_CHANNEL": team_config.get("gm_channel")
        }
        
        # Start container with team-specific config
        # ... container creation logic
```

## 📊 **Multi-Team Dashboard**

### Team Selection in Dashboard
```python
# Enhanced agent_dashboard.py with team support
class MultiTeamDashboard:
    def __init__(self):
        self.current_team = "default"
        self.teams = self.load_teams()
    
    def switch_team(self, team_name: str):
        """Switch dashboard view to different team"""
        self.current_team = team_name
        self.refresh_team_data()
    
    def show_team_selector(self):
        """Show team selection menu"""
        print("Available Teams:")
        for i, team in enumerate(self.teams.keys(), 1):
            print(f"  {i}. {team}")
```

## ✅ **Team Verification Checklist**

For each new team, verify:

- [ ] Discord server created/configured
- [ ] All bot tokens generated and added to `.env`
- [ ] Team configuration added to `agent_config.json`
- [ ] DevOps agent starts and connects to Discord
- [ ] Claude container starts with team-specific token
- [ ] Agents deploy and show online in Discord
- [ ] DevOps commands work in team Discord server
- [ ] Team isolation verified (no cross-team interference)

## 🚨 **Security Considerations**

### Token Management
- **Never commit tokens** to version control
- **Use separate tokens** for each team/environment
- **Rotate tokens** regularly for production teams
- **Limit bot permissions** to minimum required

### Team Isolation
- **Separate containers** per team prevent data leakage
- **Team-specific logs** and data directories
- **Independent deployments** for stability
- **Access control** via Discord permissions

---
**Last Updated:** July 25, 2025  
**Status:** Template ready for team expansion