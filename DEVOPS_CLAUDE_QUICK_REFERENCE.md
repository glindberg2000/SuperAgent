# 🤖 DevOps Agent - Claude Container Quick Reference

This document provides the DevOps agent with quick access to Claude Code container management functions.

## 🎯 **WORKING CONTAINER: `claude-fullstackdev-persistent`**

**Status:** ✅ VERIFIED WORKING
- Discord bot `CryptoTax_CoderDev1#8967` active  
- Successfully sends Discord messages
- MCP connection functional
- Last confirmed test: Message ID 1398112458530357328

## 🚀 **DevOps-Accessible Functions**

### Python Interface (`devops_claude_manager.py`)

```python
# Import the functions
from devops_claude_manager import devops_claude_status, devops_claude_test, devops_claude_execute

# Get status
status = devops_claude_status()

# Test Discord connection  
test_result = devops_claude_test()

# Execute Claude command
result = devops_claude_execute("Send a status update to Discord")
```

### Command Line Interface

```bash
# Check status
python devops_claude_manager.py status

# Test Discord connection
python devops_claude_manager.py test

# Get health check
python devops_claude_manager.py health

# Execute Claude command
python devops_claude_manager.py execute "List available Discord tools"
```

### Direct Container Commands

```bash
# Start working container
docker start claude-fullstackdev-persistent

# Execute Claude command directly
docker exec claude-fullstackdev-persistent claude \
  --dangerously-skip-permissions \
  --print 'Your command here'

# Check container health
./manage_claude_containers.sh health claude-fullstackdev-persistent

# View container logs
docker logs claude-fullstackdev-persistent --tail 50
```

## 📋 **Common DevOps Tasks**

### 1. Check if Claude container is working
```python
status = devops_claude_status()
print(status)
```

### 2. Send test message to Discord
```python
test_result = devops_claude_test()
print(test_result)
```

### 3. Execute autonomous task
```python
result = devops_claude_execute("Monitor Discord for mentions and respond appropriately for the next 5 minutes")
print(result)
```

### 4. Get comprehensive health check
```bash
python devops_claude_manager.py health | jq
```

## 🔧 **Troubleshooting**

### Container not responding:
```bash
# Restart container
docker restart claude-fullstackdev-persistent

# Check MCP connection
docker exec claude-fullstackdev-persistent claude mcp list
```

### MCP Discord connection failed:
```bash
# Verify __main__.py exists
docker exec claude-fullstackdev-persistent ls -la /home/node/mcp-discord/src/discord_mcp/__main__.py

# Recreate if missing
docker exec claude-fullstackdev-persistent bash -c 'echo "from discord_mcp import main; main()" > /home/node/mcp-discord/src/discord_mcp/__main__.py'
```

## 📚 **Documentation References**

- **Complete Setup:** `CLAUDE_CODE_DISCORD_MCP_WORKING_SETUP.md`
- **Container Registry:** `container_registry.json`
- **Management Scripts:** `manage_claude_containers.sh`
- **Startup Scripts:** `start_claude_container.sh`

## ⚡ **Quick DevOps Bot Commands**

When the DevOps agent needs to manage Claude containers via Discord:

1. **Status Check:** Call `devops_claude_status()` and report results
2. **Health Test:** Call `devops_claude_test()` to verify Discord connectivity  
3. **Execute Task:** Call `devops_claude_execute(command)` for autonomous operations
4. **Restart if needed:** Use `docker restart claude-fullstackdev-persistent`

## 🎉 **Success Indicators**

- ✅ Container status shows "running"
- ✅ MCP connection shows "✓ Connected"  
- ✅ Discord test returns successful message send
- ✅ Bot responds in Discord as `CryptoTax_CoderDev1`

---
*Last Updated: July 25, 2025*
*Verified Working Container: `claude-fullstackdev-persistent`*