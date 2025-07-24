# MCP Discord Server Connection Issue - Problem Specification

## Problem Summary
Claude Code successfully detects and attempts to connect to a configured MCP Discord server, but the connection fails with "✗ Failed to connect" during the health check phase.

## Environment Details
- **Container**: Official Anthropic Claude Code container (Node.js 20 based)
- **MCP Server**: Discord MCP server written in Python using `mcp.server.stdio`
- **Transport**: STDIO (as expected by Claude Code)
- **Dependencies**: discord.py, mcp, python-dotenv installed globally in container

## Working Evidence
1. **MCP Server Runs Successfully**: When executed manually, the server:
   - Connects to Discord successfully
   - Logs in as the bot user
   - Shows "Discord bot is ready, starting MCP server"
   - Responds correctly to manual MCP protocol handshake (initialize message)

2. **Claude Code Detection**: Claude Code successfully:
   - Detects the configured MCP server
   - Shows it in `claude mcp list`
   - Attempts to connect during health check

## Failing Evidence
- **Claude Code Health Check**: Shows "✗ Failed to connect" consistently
- **No Error Details**: Claude Code doesn't provide verbose error information about why the connection fails

## Configuration
```json
{
  "discord-coderdev1": {
    "type": "stdio",
    "command": "/tmp/mcp-discord-start.sh",
    "args": [
      "--token", ""YOUR_TOKEN_HERE"",
      "--server-id", "1395578178973597799"
    ]
  }
}
```

## MCP Server Startup Script
```bash
#!/bin/bash
cd /home/node/mcp-discord
PYTHONPATH=src exec python3 -c "from discord_mcp import main; main()" "$@"
```

## MCP Server Implementation Details
- Uses `mcp.server.stdio.stdio_server()` for STDIO transport
- Follows MCP protocol version 2024-11-05
- Connects to Discord first, then starts MCP server with `app.run(read_stream, write_stream)`
- Server responds to initialize with proper JSON-RPC format

## Timing Observations
- Manual MCP handshake works immediately after server responds with initialization
- Discord connection takes ~2-3 seconds before MCP server starts
- Claude Code may have a shorter timeout for initial connection

## Questions for Investigation
1. What is Claude Code's expected timeout for MCP server connection?
2. Does Claude Code expect immediate response to MCP initialize, or can there be a delay?
3. Are there specific MCP capabilities or protocol requirements Claude Code expects?
4. Should the MCP server start before or after Discord connection?
5. Are there logging/debugging options in Claude Code to see detailed connection errors?
6. Does the server need to handle multiple initialization attempts?
7. Are there specific stdio buffering or flushing requirements?

## Reproduction Steps
1. Configure MCP server in Claude Code via `claude mcp add`
2. Run `claude mcp list` - shows server but with "✗ Failed to connect"
3. Manual test of same command with MCP protocol handshake works perfectly

## Expected Outcome
Claude Code should show "✓ Connected" for the MCP Discord server and allow access to Discord tools.