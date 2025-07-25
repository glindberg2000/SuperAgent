# MCP Container Management Testing Guide

This guide explains how to test the MCP container management tools independently before integrating with the DevOps agent.

## Test Scripts

### 1. Automated Test Suite (`test_mcp_container_tools.py`)

Runs a comprehensive test suite covering all container management functionality:

```bash
python test_mcp_container_tools.py
```

**Tests include:**
- ✅ List containers (running and all)
- ✅ Get container configurations
- ✅ Container lifecycle (launch/stop)
- ✅ Container functionality testing
- ✅ Error handling and edge cases

### 2. Interactive Test Client (`test_mcp_container_interactive.py`)

Provides an interactive command-line interface for manual testing:

```bash
python test_mcp_container_interactive.py
```

**Available commands:**
```
help              - Show help message
list [all]        - List containers (add 'all' to include stopped)
launch <name>     - Launch a container
stop <name> [rm]  - Stop a container (add 'rm' to remove)
test <name>       - Test container functionality
config <name>     - Get container configuration
tools             - List available MCP tools
exit              - Exit the client
```

**Example session:**
```
🤖 MCP> list all
📦 Listing containers (include_stopped=True)...
  Found 2 containers:

  🟢 claude-isolated-discord
     Bot: discord-managed
     Token: DISCORD_TOKEN_CODERDEV1
     Status: running
     Uptime: 2h 15m

  🔴 claude-fullstackdev-persistent
     Bot: fullstackdev
     Token: DISCORD_TOKEN_CODERDEV2
     Status: stopped

🤖 MCP> test claude-isolated-discord
🧪 Testing claude-isolated-discord...
  Test Results:
    ✅ claude_code
    ✅ mcp_connection
    ✅ discord_connection

  Overall: ✅ PASSED

🤖 MCP> exit
👋 Goodbye!
```

## MCP Server Architecture

The container management MCP server (`mcp_servers/container_server.py`) exposes these tools:

### Tools Available:

1. **list_containers**
   - Lists all Claude Code containers
   - Shows bot identity, Discord token mapping, status
   - Optional: include stopped containers

2. **launch_container**
   - Starts existing containers (preserves auth)
   - Returns error if container doesn't exist
   - Automatic post-launch testing

3. **shutdown_container**
   - Stops running containers
   - Optional: remove container completely
   - Preserves authentication by default

4. **test_container**
   - Tests Claude Code functionality
   - Tests MCP connection status
   - Tests Discord integration
   - Returns pass/fail for each test

5. **get_container_config**
   - Returns container configuration
   - Shows Discord token mapping
   - Includes runtime status

## Testing Workflow

1. **Start with automated tests:**
   ```bash
   python test_mcp_container_tools.py
   ```
   This ensures all basic functionality works.

2. **Use interactive client for specific scenarios:**
   ```bash
   python test_mcp_container_interactive.py
   ```
   Test edge cases and specific container operations.

3. **Verify container states:**
   - Check Docker directly: `docker ps -a`
   - Verify MCP connections: `docker exec <container> claude mcp list`
   - Test Discord: `docker exec <container> claude --print "test"`

## Integration Notes

Once testing is complete, the DevOps agent can use these tools by:

1. Connecting to the container MCP server
2. Using `session.call_tool()` to invoke container operations
3. Parsing JSON responses for status and error handling

The DevOps agent already has the code to handle these tools - it just needs the MCP server running.

## Troubleshooting

**Container not found:**
- Containers must be created first using the Python launcher
- The MCP server only manages existing containers

**Authentication issues:**
- Containers preserve auth when restarted (not recreated)
- Use `preserve_auth=True` when launching

**Discord token issues:**
- Ensure environment variables are set: DISCORD_TOKEN_CODERDEV1, etc.
- Check token mapping in DISCORD_BOT_REGISTRY.md

**MCP connection failures:**
- Verify Python path includes the project root
- Check that mcp_servers/__init__.py exists
- Ensure all dependencies are installed