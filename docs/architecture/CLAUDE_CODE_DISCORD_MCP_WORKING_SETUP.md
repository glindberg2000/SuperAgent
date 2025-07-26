# 🎉 WORKING Claude Code Discord MCP Setup - DO NOT LOSE THIS!

**CRITICAL:** This document contains the EXACT working configuration for Claude Code containers with Discord MCP integration. Do not delete or modify without testing!

**Last Verified:** July 24, 2025  
**Working Container:** `claude-fullstackdev-persistent`  
**Status:** ✅ FULLY WORKING

## 🔑 Critical Fix That Made It Work

The key missing piece was the `__main__.py` file in the `discord_mcp` package:

```bash
# Inside the container, create this file:
echo "from discord_mcp import main; main()" > /home/node/mcp-discord/src/discord_mcp/__main__.py
```

**Without this file:** `python3 -m discord_mcp` fails with "No module named discord_mcp.__main__"  
**With this file:** MCP connection works perfectly ✅

## 🐳 Working Container Configuration

### Container Setup
```bash
# Launch command (run from SuperAgent directory)
DISCORD_TOKEN_CLAUDE=$(grep "^DISCORD_TOKEN_CLAUDE=" .env | cut -d'=' -f2 | cut -d' ' -f1) \
ANTHROPIC_API_KEY=$(grep "^ANTHROPIC_API_KEY=" .env | cut -d'=' -f2) \
DEFAULT_SERVER_ID=$(grep "^DEFAULT_SERVER_ID=" .env | cut -d'=' -f2) \
python launch_claude_container.py
```

### Essential Volumes
```python
volumes = {
    workspace_path: {"bind": "/workspace", "mode": "rw"},
    mcp_discord_path: {"bind": "/home/node/mcp-discord", "mode": "rw"}  # MUST be rw!
}
```

### Environment Variables
```bash
DISCORD_TOKEN=YOUR_TOKEN_HERE
DEFAULT_SERVER_ID=1395578178973597799
ANTHROPIC_API_KEY=""sk-ant-api03-YOUR_ANTHROPIC_KEY_HERE""
```

## 🛠️ MCP Configuration

### Working MCP Setup Command
```bash
# Inside container
claude mcp add discord-fullstackdev stdio -- python3 -m discord_mcp \
  --token "YOUR_TOKEN_HERE" \
  --server-id "1395578178973597799"
```

### Working MCP Config File (`/home/node/.claude.json`)
```json
{
  "projects": {
    "/workspace": {
      "mcpServers": {
        "discord-fullstackdev": {
          "type": "stdio",
          "command": "python3",
          "args": [
            "-m", "discord_mcp",
            "--token", "YOUR_TOKEN_HERE",
            "--server-id", "1395578178973597799"
          ],
          "env": {
            "PYTHONPATH": "/home/node/mcp-discord/src"
          }
        }
      }
    }
  }
}
```

## ✅ Verification Steps

### 1. Container Health Check
```bash
docker ps | grep claude-fullstackdev-persistent
# Should show: Running status
```

### 2. Claude Code Authentication
```bash
docker exec claude-fullstackdev-persistent claude --version
# Should show: 1.0.59 (Claude Code)
```

### 3. MCP Connection Test
```bash
docker exec claude-fullstackdev-persistent claude mcp list
# Should show: discord-fullstackdev: ... - ✓ Connected
```

### 4. Discord Bot Login Test
```bash
docker exec claude-fullstackdev-persistent bash -c \
  'cd /home/node/mcp-discord && PYTHONPATH=/home/node/mcp-discord/src python3 -c "from discord_mcp import main; main()" --token "TOKEN" --server-id "SERVER_ID"'
# Should show: "Logged in as CryptoTax_CoderDev1" and "Discord bot is ready, starting MCP server"
```

## 🚨 CRITICAL - Do Not Lose This Setup!

### Why Containers Get Lost
1. Manual `docker rm` commands without documentation
2. `docker system prune` operations  
3. Missing restart policies
4. Lost environment variables
5. Missing the critical `__main__.py` file

### Recovery Commands
```bash
# If container stopped
docker start claude-fullstackdev-persistent

# If container deleted
python launch_claude_container.py

# If MCP not working, recreate __main__.py
docker exec claude-fullstackdev-persistent bash -c \
  'echo "from discord_mcp import main; main()" > /home/node/mcp-discord/src/discord_mcp/__main__.py'

# If MCP config lost
docker exec claude-fullstackdev-persistent claude mcp add discord-fullstackdev stdio -- python3 -m discord_mcp --token "TOKEN" --server-id "SERVER_ID"
```

## 📍 File Locations

- **Main Documentation:** `CLAUDE_CODE_DISCORD_MCP_WORKING_SETUP.md` (THIS FILE)
- **Container Launcher:** `launch_claude_container.py`
- **Container Registry:** `container_registry.json`
- **Status Documentation:** `CLAUDE_CONTAINER_STATUS.md`
- **Debug Specs:** `mcp_discord_debug_spec.md`
- **Working Config Examples:** `docker/container_mcp_config.json`

## 🎯 Success Indicators

When everything is working correctly:
1. ✅ Container shows "Running" status
2. ✅ `claude --version` works in container  
3. ✅ `claude mcp list` shows "✓ Connected"
4. ✅ Discord bot logs show "Logged in as CryptoTax_CoderDev1"
5. ✅ MCP server logs show "Discord bot is ready, starting MCP server"

## 🔧 Discord Bot Details

- **Bot Name:** `CryptoTax_CoderDev1` 
- **Bot Token:** `DISCORD_TOKEN_CLAUDE` (from .env)
- **Server ID:** `1395578178973597799`
- **Bot User ID:** Available in Discord logs

## 🚀 Full Autonomous Operation Setup

### ✅ **VERIFIED WORKING CONTAINER: `claude-fullstackdev-persistent`**

**🎉 ACTUAL TEST RESULTS:**
- ✅ Discord bot `CryptoTax_CoderDev1#8967` connected and working
- ✅ MCP Discord connection active and functional
- ✅ Successfully sends messages to #general channel
- ✅ Message ID tracking working (e.g., Message ID: 1398112458530357328)
- ✅ Full tool access with `--dangerously-skip-permissions`

### 🔥 Production Command Pattern (RECOMMENDED)
```bash
# Full autonomous operation with all tools and MCP servers
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Your autonomous AI command here'
```

### ⚠️ **CRITICAL DISCOVERY: Broken vs Working Containers**

**✅ WORKING:** `claude-fullstackdev-persistent`
- Mount: SuperAgent project directory (not isolated)
- MCP: Properly configured with working `__main__.py`
- Status: **ACTUALLY SENDS DISCORD MESSAGES**

**❌ BROKEN:** `claude-isolated-discord` 
- Mount: Isolated workspace (clean but broken)
- MCP: Shows "Connected" but crashes on tool usage
- Status: **JavaScript errors on MCP tool execution**

**Key Lesson: Isolated workspace approach introduced bugs. Original shared workspace works perfectly.**

### Alternative Permission Patterns
```bash
# Allow specific Discord tools only
docker exec claude-fullstackdev-persistent claude \
  --allowedTools "mcp__discord-fullstackdev__send_message,mcp__discord-fullstackdev__get_server_info,mcp__discord-fullstackdev__wait_for_message" \
  --print 'Your Discord command here'

# Allow all Discord tools
docker exec claude-fullstackdev-persistent claude \
  --allowedTools "mcp__discord-fullstackdev__*" \
  --print 'Your Discord command here'

# Allow all MCP tools (when multiple MCP servers added)
docker exec claude-fullstackdev-persistent claude \
  --allowedTools "mcp__*" \
  --print 'Your command here'
```

### ✅ Verified Working Tests

**Test 1: Basic Message Send**
```bash
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Send a test message saying "🎉 SUCCESS!" to Discord and wait 60 seconds for responses.'
```
**Result:** ✅ Message sent successfully to #general channel - **USER CONFIRMED MESSAGE RECEIVED**

**Test 2: Extended Response Waiting** ✅
```bash
# Send message first
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Send a message saying "Step 1: Testing response waiting functionality" to Discord.'

# Then wait for responses
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Use the wait_for_message function to wait 45 seconds for any new messages in the Discord channel, then report what you found.'
```
**Result:** ✅ Successfully captured user response: "Found a new message from user `.cryptoplato` saying 'how are you?' with a mention (@1395875361354547200)"

**Test 3: Conversation Pattern**
```bash
# For autonomous conversation handling, use this pattern:
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Send a greeting message to Discord, wait for responses using wait_for_message with a 60 second timeout, then engage in conversation based on what you receive.'
```

### 🎯 Best Practices for Discord Response Waiting

**Key Findings:**
1. **Step-by-Step Approach**: Send message first, then wait separately works better than combined operations
2. **Timeout Management**: 45-60 seconds is optimal for interactive responses  
3. **MCP Tool Usage**: Use `wait_for_message` function directly for reliable response collection
4. **Error Handling**: If Claude Code session hangs, break operations into smaller steps

**Recommended Patterns:**
```bash
# Interactive conversation pattern
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Send message "Hello! How can I help?" then wait 45 seconds for responses and engage naturally.'

# Monitoring pattern  
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Check for any new messages in the last 5 minutes using get_unread_messages and report findings.'

# Autonomous operation pattern
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Monitor Discord for mentions or questions, respond appropriately, and continue monitoring.'
```

---

**⚠️ WARNING:** This setup took significant time to get working. The critical `__main__.py` file fix is not obvious and will be lost if the container is recreated without documentation. Always verify the MCP connection with `claude mcp list` before assuming it works!