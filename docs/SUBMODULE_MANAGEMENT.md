# MCP-Discord Submodule Management Guide

## 🚨 **CRITICAL DEPENDENCY**

The `mcp-discord` submodule is **ABSOLUTELY ESSENTIAL** for SuperAgent functionality:

- **Discord Communication**: Provides the HTTP API server for Discord bot interactions
- **Multi-Bot Support**: Enables multiple Discord bot identities with stateless architecture  
- **Container Communication**: Allows Discord integration for containerized Claude Code agents
- **File Operations**: Handles file upload/download operations between Discord and agents

**⚠️ WITHOUT THIS SUBMODULE, THE ENTIRE SUPERAGENT SYSTEM WILL NOT FUNCTION**

## 📁 Current Configuration

```bash
# Submodule details
Repository: https://github.com/glindberg2000/mcp-discord.git
Path: mcp-discord/
Branch: main
Current Commit: e61462f (🚀 Implement stateless Discord HTTP API for multi-bot support)
```

## 🔧 Submodule Commands Reference

### **Checking Submodule Status**
```bash
# View submodule status
git submodule status

# View detailed submodule info
git submodule foreach git log --oneline -5
```

### **Updating Submodule**
```bash
# Update to latest commit from remote
git submodule update --remote mcp-discord

# Pull latest changes in submodule
cd mcp-discord && git pull origin main && cd ..
```

### **After Submodule Updates**
```bash
# Commit the submodule update in parent repo
git add mcp-discord
git commit -m "📦 Update mcp-discord submodule to latest version"
git push
```

### **Cloning Repository with Submodules**
```bash
# Clone with submodules (RECOMMENDED)
git clone --recursive https://github.com/glindberg2000/SuperAgent.git

# If already cloned without --recursive
cd SuperAgent
git submodule update --init --recursive
```

## 🚀 Submodule Restoration Process

If the submodule is ever missing or broken:

### **1. Remove Broken Submodule**
```bash
# Remove the submodule directory
rm -rf mcp-discord

# Remove from .gitmodules (if broken)
rm .gitmodules  # Only if corrupted
```

### **2. Re-add Submodule**
```bash
# Add the submodule fresh
git submodule add https://github.com/glindberg2000/mcp-discord.git mcp-discord

# Verify it was added correctly
git submodule status
```

### **3. Commit the Restoration**
```bash
# Stage the submodule changes
git add .gitmodules mcp-discord

# Commit with clear message
git commit -m "🔧 Restore critical mcp-discord submodule for Discord functionality"

# Push to remote
git push
```

## 🛡️ Prevention Measures

### **Never Delete These Files:**
- `.gitmodules` - Contains submodule configuration
- `mcp-discord/` directory - The actual submodule
- `.git/modules/mcp-discord/` - Git internal submodule data

### **Always Use --recursive:**
```bash
# When cloning
git clone --recursive <repo-url>

# When pulling updates
git pull --recurse-submodules
```

### **Development Workflow:**
```bash
# 1. Work on main SuperAgent code
git add . && git commit -m "Your changes"

# 2. If you made changes in mcp-discord submodule:
cd mcp-discord
git add . && git commit -m "Discord API changes"
git push origin main
cd ..

# 3. Update parent repo to reference new submodule commit
git add mcp-discord
git commit -m "📦 Update mcp-discord submodule"
git push
```

## 🧪 Testing Submodule Health

### **Quick Health Check:**
```bash
# Verify submodule exists and is accessible
[ -d "mcp-discord" ] && echo "✅ Submodule directory exists" || echo "❌ Submodule missing!"

# Check .gitmodules configuration
[ -f ".gitmodules" ] && echo "✅ .gitmodules exists" || echo "❌ .gitmodules missing!"

# Verify submodule is properly tracked
git ls-tree HEAD | grep mcp-discord && echo "✅ Submodule tracked in git" || echo "❌ Submodule not tracked!"
```

### **Full Verification:**
```bash
# Run comprehensive submodule test
python tests/test_submodule_health.py  # TODO: Create this test
```

## 📊 Integration Points

The mcp-discord submodule integrates with SuperAgent through:

1. **Docker Compose**: `mcp-discord/docker-compose.yml` runs the Discord HTTP API
2. **Agent Configuration**: `multi_agent_launcher_hybrid.py` connects to Discord API
3. **Port 9091**: Discord HTTP API endpoint for bot communications
4. **Environment Variables**: Discord tokens configured in `.env`

## 🚨 Emergency Recovery

If SuperAgent stops working and Discord bots are not responding:

### **Step 1: Check Submodule**
```bash
git submodule status
# Should show: e61462f9f99de627860f80146ab2f397185333a9 mcp-discord (heads/main)
```

### **Step 2: Verify Discord API**
```bash
cd mcp-discord
docker-compose up -d discord-http-api
curl http://localhost:9091/health
```

### **Step 3: Full Reset (Last Resort)**
```bash
# Save any local changes first!
git stash

# Reset submodule completely
git submodule deinit -f mcp-discord
rm -rf .git/modules/mcp-discord mcp-discord
git submodule add https://github.com/glindberg2000/mcp-discord.git mcp-discord
git add .gitmodules mcp-discord
git commit -m "🚨 Emergency restore of mcp-discord submodule"
git push
```

---

## ⚡ **REMEMBER**: 
- The mcp-discord submodule is THE critical dependency
- Never work without it properly configured  
- Always test Discord functionality after any git operations
- Document any changes to submodule configuration immediately

**This submodule provides the core Discord communication layer that enables the entire SuperAgent multi-bot ecosystem.**