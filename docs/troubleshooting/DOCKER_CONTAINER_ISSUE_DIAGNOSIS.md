# Docker Container Code Mismatch - Root Cause Analysis & Resolution

## 🚨 **Issue Summary**
**Problem**: Discord API container was running different code (`discord_http_multi.py`) than what was in our codebase (`discord_http_stateless.py`).

**Impact**: 
- Bot identity information not returned properly (`bot_info: N/A`)
- Inconsistent API behavior vs. codebase expectations
- Confusion during debugging and testing

## 🔍 **Root Cause Analysis**

### **What Happened**
1. **Stale Container Image**: The Docker container was built 5+ hours ago with older code
2. **Different Entry Point**: Container was running `discord_http_multi.py` instead of `discord_http_stateless.py`
3. **Port Mismatch**: Container mapped `9090:9091` but new code runs on `9091:9091`
4. **API Structure Differences**: Different request/response formats between versions

### **Evidence Found**
```bash
# Container was running older code
docker history mcp-discord-discord-http-api:latest
# CMD ["python" "discord_http_multi.py"]  ← Wrong file!

# Container had different files
docker exec discord-stateless-api find /app -name "*.py"
# discord_http_multi.py, discord_http_api.py  ← Old files!

# Our codebase had
ls mcp-discord/
# discord_http_stateless.py  ← Correct file!
```

## 🛠️ **Resolution Steps Taken**

### **1. Container Rebuild** ✅
```bash
# Stopped old container
docker-compose down discord-http-api

# Rebuilt with --no-cache to ensure fresh build
docker-compose build --no-cache discord-http-api

# Verified correct files in new container
docker exec discord-stateless-api find /app -name "*.py"
# discord_http_stateless.py, test_mcp_http_client.py  ← Correct!
```

### **2. Port Mapping Fix** ✅
```yaml
# Fixed docker-compose.yml
ports:
  - "9091:9091"  # Was 9091:9090

healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9091/health"]  # Was 9090
```

### **3. Network Configuration** ✅
```bash
# Connected to proper network
docker network connect superagent-network discord-stateless-api
docker network disconnect mcp-discord_superagent-network discord-stateless-api
```

### **4. API Verification** ✅
```bash
# Confirmed correct API running
curl http://localhost:9091/health
# {"status":"healthy","stateless":true,"timestamp":"..."}  ← Correct response!

# Verified bot identities working
# GROK4_BOT: Grok4#9554
# CLAUDE_BOT: CryptoTax_CoderDev1#8967  ← Different identities confirmed!
```

## 🚫 **Prevention Measures**

### **1. Always Use --no-cache for Critical Rebuilds**
```bash
# Instead of:
docker-compose build discord-http-api

# Use:
docker-compose build --no-cache discord-http-api
```

### **2. Container Verification Script**
```bash
# Check what's actually running in container
docker exec <container> find /app -name "*.py" -exec basename {} \;
docker exec <container> cat /proc/1/cmdline
```

### **3. Version Tagging**
```yaml
# Add version tags to prevent confusion
services:
  discord-http-api:
    image: superagent/discord-api:v1.0.0
    build: .
```

### **4. Health Check Enhancement**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9091/health && echo 'API_VERSION: stateless'"]
```

## 📋 **Container Deployment Checklist**

### **Before Deployment**
- [ ] Verify Dockerfile CMD matches expected entry point
- [ ] Check port mapping in docker-compose.yml
- [ ] Ensure build context includes latest code changes
- [ ] Use `--no-cache` for critical rebuilds

### **After Deployment**
- [ ] Test health endpoint responds correctly
- [ ] Verify container is running expected code files
- [ ] Check logs for expected startup messages
- [ ] Test API functionality matches codebase expectations

### **Ongoing Monitoring**
- [ ] Compare container file checksums with codebase
- [ ] Monitor for unexpected API behavior
- [ ] Regular container rebuilds after code changes

## 🎯 **Key Lessons Learned**

1. **Docker Layer Caching**: Can cause issues when files change significantly
2. **Container Inspection**: Always verify what's actually running in production
3. **Port Consistency**: Ensure container ports match application ports
4. **API Testing**: Test actual container behavior, not just codebase
5. **Version Control**: Keep container versions aligned with code versions

## ✅ **Current Status**

- ✅ **Container Rebuilt**: Running correct `discord_http_stateless.py`
- ✅ **Port Mapping Fixed**: `9091:9091` mapping working
- ✅ **API Verified**: Health check and bot identity endpoints working
- ✅ **Multi-Bot Confirmed**: Different Discord bot identities detected
- ✅ **Documentation**: Issue analysis and prevention measures documented

---

**This diagnosis ensures the container deployment process is reliable and prevents similar code/container mismatches in the future.**