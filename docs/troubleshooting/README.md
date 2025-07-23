# SuperAgent Troubleshooting Guides

This directory contains detailed troubleshooting guides for common SuperAgent issues.

## Available Guides

### `DOCKER_CONTAINER_ISSUE_DIAGNOSIS.md`
**Topic**: Docker container code mismatch diagnosis and resolution
**When to use**: When containers are running different code than expected

**Covers:**
- Container code vs. codebase mismatches
- Stale container image issues
- Port mapping problems
- Prevention measures and best practices

## Common Troubleshooting Categories

### 🐳 **Docker & Container Issues**
- Container running stale/wrong code
- Port mapping mismatches
- Network connectivity problems
- Build and deployment inconsistencies

### 🤖 **Discord & Bot Issues**
- Bot identity conflicts
- Multi-bot functionality failures
- Token configuration errors
- API connectivity problems

### 🔧 **Configuration Issues**
- Environment variable problems
- Service connectivity issues
- Authentication failures

### 🚀 **Performance Issues**
- Memory usage problems
- Container resource limits
- Network latency issues

## Diagnostic Commands

### Container Inspection
```bash
# Check what's running in container
docker exec <container> find /app -name "*.py" -exec basename {} \;
docker exec <container> cat /proc/1/cmdline

# Check container build history
docker history <image>:latest --no-trunc

# Verify port mappings
docker port <container>
```

### Service Health Checks
```bash
# Test API endpoints
curl http://localhost:9091/health

# Check service logs
docker logs <container> --tail 20

# Test network connectivity
docker network ls
docker network inspect <network>
```

### Configuration Validation
```bash
# Validate Discord configuration
python tests/validate_discord_config.py

# Test Discord identities
python tests/test_discord_identities.py
```

## When to Create New Guides

Create new troubleshooting guides when:
1. **Issue affects multiple users**
2. **Root cause analysis is complex**
3. **Resolution involves multiple steps**
4. **Prevention measures are important**

## Guide Template

```markdown
# Issue Title - Root Cause Analysis & Resolution

## 🚨 Issue Summary
**Problem**: Brief description
**Impact**: What breaks/fails
**Root Cause**: Technical explanation

## 🔍 Root Cause Analysis
### What Happened
### Evidence Found
### Why It Occurred

## 🛠️ Resolution Steps
### Step-by-step fix instructions

## 🚫 Prevention Measures
### How to avoid in future

## ✅ Verification
### How to confirm fix worked
```