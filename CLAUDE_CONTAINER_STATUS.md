# Claude Code Container Status & Recovery Guide

**Last Updated:** July 24, 2025  
**Working Container:** `claude-fullstackdev-persistent`

## ✅ Current Working Setup

### Container Details
- **Name:** `claude-fullstackdev-persistent`
- **Image:** `superagent/official-claude-code:latest` 
- **Container ID:** `47b354af3748`
- **Status:** Running (with restart policy)
- **Created:** 2025-07-24T23:22:37

### Authentication
- **Method:** Anthropic API Key
- **Key:** `ANTHROPIC_API_KEY` from .env file
- **Status:** ✅ Working (Claude Code v1.0.59)

### Environment Variables
```bash
DISCORD_TOKEN="YOUR_TOKEN_HERE"
DEFAULT_SERVER_ID=1395578178973597799
POSTGRES_URL=postgresql://superagent:superagent@localhost:5433/superagent
ANTHROPIC_API_KEY=""sk-ant-api03-YOUR_ANTHROPIC_KEY_HERE""
AGENT_TYPE=fullstackdev
WORKSPACE_PATH=/workspace
```

### Volumes Mounted
- **Workspace:** `/Users/greg/repos/SuperAgent` → `/workspace` (rw)
- **MCP-Discord:** `/Users/greg/repos/SuperAgent/mcp-discord` → `/home/node/mcp-discord` (ro)

### Container Labels
```json
{
  "superagent.type": "claude-code",
  "superagent.agent": "fullstackdev", 
  "superagent.team": "development",
  "superagent.managed": "true",
  "superagent.persistent": "true"
}
```

## 🔧 Recovery Commands

### Check Container Status
```bash
docker ps -a | grep claude
docker exec claude-fullstackdev-persistent claude --version
```

### Restart Container if Stopped
```bash
docker start claude-fullstackdev-persistent
```

### Recreate Container if Lost
```bash
DISCORD_TOKEN_CLAUDE=$(grep "^DISCORD_TOKEN_CLAUDE=" .env | cut -d'=' -f2 | cut -d' ' -f1) \
ANTHROPIC_API_KEY=$(grep "^ANTHROPIC_API_KEY=" .env | cut -d'=' -f2) \
DEFAULT_SERVER_ID=$(grep "^DEFAULT_SERVER_ID=" .env | cut -d'=' -f2) \
python launch_claude_container.py
```

### Connect to Container
```bash
docker exec -it claude-fullstackdev-persistent /bin/bash
```

## 🐛 Current Issues & Solutions

### Issue 1: MCP Configuration Not Detected
**Problem:** Claude Code doesn't recognize MCP servers  
**Status:** In Progress  
**Config Location:** `/home/node/.claude/config.json`  
**Config Content:**
```json
{
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
        ""YOUR_TOKEN_HERE"",
        "--server-id",
        "1395578178973597799"
      ],
      "env": {}
    }
  }
}
```

**Next Steps:**
- Verify mcp-discord submodule is properly mounted
- Check Claude Code MCP configuration format
- Test MCP server connectivity

## 📋 Container Registry
Location: `/Users/greg/repos/SuperAgent/container_registry.json`

## 🚀 Launcher Script
Location: `/Users/greg/repos/SuperAgent/launch_claude_container.py`

## 🎯 Dashboard Integration
- Containers visible in detail dashboard (Press '8')  
- Container detection working in diagnostic dashboard
- Health monitoring available

## ⚠️ Critical Notes

1. **Don't lose this container!** It has working authentication
2. **Always use restart policy:** `unless-stopped` 
3. **Track in registry:** All containers logged to container_registry.json
4. **Environment variables:** Must be loaded from .env file
5. **MCP Integration:** Final piece needed for Discord functionality

## 🔄 Why Containers Get Lost

1. **Manual deletion** without documentation
2. **Docker system prune** operations  
3. **Image cleanup** removing authenticated layers
4. **Missing restart policies** 
5. **Lost environment variables**

## 🛡️ Prevention Strategy

1. **Persistent naming:** Use descriptive, memorable names
2. **Restart policies:** Always set `unless-stopped`
3. **Registry tracking:** Log all containers in registry.json
4. **Launcher scripts:** Automated recreation with proper config
5. **Dashboard monitoring:** Visual confirmation of container status