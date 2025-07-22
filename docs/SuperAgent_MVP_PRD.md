# SuperAgent MVP - Minimal Containerization PRD
## Product Requirements Document - Quick Win Version

**Version:** 1.0 MVP  
**Date:** 2025-07-22  
**Estimated Timeline:** 2-3 days  

## Executive Summary

Minimal viable containerization of SuperAgent focusing on getting Discord bots running in Claude Code containers with basic memory persistence. Cut all non-essential features for rapid deployment.

## Core Goal

Get 1-3 Discord bots running in Claude Code containers that can:
1. Connect to Discord via HTTP-based MCP
2. Access a shared Postgres vector memory
3. Mount local code repositories
4. Actually work end-to-end

## Phase 1: Discord MCP HTTP Bridge (Day 1)

### What We Need
A simple HTTP wrapper around the existing Discord MCP server since it only supports STDIO.

### Implementation
```python
# discord_mcp_http_bridge.py
from fastapi import FastAPI, Request
import subprocess
import json
import asyncio

app = FastAPI()

@app.post("/mcp")
async def mcp_proxy(request: Request):
    """Simple HTTP-to-STDIO bridge for Discord MCP"""
    body = await request.json()
    
    # Run the Discord MCP command
    proc = await asyncio.create_subprocess_exec(
        'node', '/path/to/mcp-discord-global/dist/index.js',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Send request and get response
    stdout, stderr = await proc.communicate(json.dumps(body).encode())
    
    if proc.returncode != 0:
        return {"error": stderr.decode()}
    
    return json.loads(stdout.decode())

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Quick Start
```bash
# Install deps
pip install fastapi uvicorn

# Run the bridge
uvicorn discord_mcp_http_bridge:app --host 0.0.0.0 --port 9090
```

## Phase 2: Postgres + pgvector (Day 1)

### Simple Setup
```bash
# Use port 5433 to avoid conflicts
docker run -d \
  --name superagent-postgres \
  -p 5433:5432 \
  -e POSTGRES_PASSWORD=superagent \
  -v superagent-pgdata:/var/lib/postgresql/data \
  ankane/pgvector:latest
```

### Minimal Schema
```sql
-- Just one table to start
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100),
    content TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops);
```

### Basic Memory Client
```python
# memory_client.py
import asyncpg
import numpy as np
from openai import OpenAI

class SimpleMemory:
    def __init__(self, db_url):
        self.db_url = db_url
        self.openai = OpenAI()
    
    async def store(self, agent_id: str, content: str):
        # Get embedding
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )
        embedding = response.data[0].embedding
        
        # Store in DB
        conn = await asyncpg.connect(self.db_url)
        await conn.execute(
            "INSERT INTO memories (agent_id, content, embedding) VALUES ($1, $2, $3)",
            agent_id, content, embedding
        )
        await conn.close()
    
    async def search(self, query: str, limit: int = 5):
        # Get query embedding
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        embedding = response.data[0].embedding
        
        # Search
        conn = await asyncpg.connect(self.db_url)
        results = await conn.fetch(
            """
            SELECT content, 1 - (embedding <=> $1) as similarity
            FROM memories
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            embedding, limit
        )
        await conn.close()
        return results
```

## Phase 3: Minimal Orchestrator (Day 2)

### Simple Container Spawner
```python
# orchestrator_mvp.py
import docker
import os
import json

class MVPOrchestrator:
    def __init__(self):
        self.docker = docker.from_env()
        self.agents = {}
    
    def spawn_agent(self, name: str, workspace_path: str, discord_token: str):
        """Spawn a Claude Code container with minimal config"""
        
        # Basic environment
        env = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "DISCORD_TOKEN": discord_token,
            "DISCORD_MCP_URL": "http://host.docker.internal:9090",  # Bridge URL
            "POSTGRES_URL": "postgresql://postgres:superagent@host.docker.internal:5433/superagent"
        }
        
        # Simple volume mounts
        volumes = {
            workspace_path: {"bind": "/workspace", "mode": "rw"},
            f"{os.path.expanduser('~')}/.ssh": {"bind": "/root/.ssh", "mode": "ro"}
        }
        
        # Create container
        container = self.docker.containers.run(
            "anthropic/claude-code:latest",  # Use their image
            name=f"agent-{name}",
            environment=env,
            volumes=volumes,
            network_mode="bridge",  # Simple networking
            detach=True,
            restart_policy={"Name": "unless-stopped"}
        )
        
        self.agents[name] = container
        print(f"Started agent {name} - Container ID: {container.id[:12]}")
        
    def list_agents(self):
        for name, container in self.agents.items():
            print(f"{name}: {container.status}")
    
    def stop_all(self):
        for container in self.agents.values():
            container.stop()
            container.remove()

# Usage
if __name__ == "__main__":
    orchestrator = MVPOrchestrator()
    
    # Start a test agent
    orchestrator.spawn_agent(
        name="test-bot",
        workspace_path="/Users/greg/repos/CryptoTaxCalc",
        discord_token=os.getenv("DISCORD_TOKEN_TEST")
    )
```

## Phase 4: Basic Integration (Day 2-3)

### MCP Configuration in Container
Create a simple startup script that runs inside the container:

```bash
#!/bin/bash
# startup.sh - runs inside Claude Code container

# Configure MCP Discord connection
claude mcp add discord-http \
  --transport http \
  --url "${DISCORD_MCP_URL}" \
  --header "Authorization: Bearer ${DISCORD_TOKEN}"

# Start Claude Code
exec claude-code
```

### Simple Agent Config
```json
{
  "test-bot": {
    "workspace": "/Users/greg/repos/CryptoTaxCalc",
    "discord_token": "${DISCORD_TOKEN_TEST}",
    "personality": "Helpful coding assistant"
  }
}
```

## What We're NOT Doing (Yet)

1. **Complex workspace preparation** - Just mount existing repos
2. **Git configuration** - Use host SSH keys
3. **Document processing** - Basic memory only
4. **Multi-agent coordination** - Independent agents only
5. **Sophisticated memory ranking** - Simple vector search
6. **Health monitoring** - Docker restart policy only
7. **Custom CLAUDE.md generation** - Static files
8. **Advanced MCP tools** - Just Discord + basic memory

## Success Metrics

### Day 1
- [ ] Discord MCP HTTP bridge running locally
- [ ] Postgres with pgvector container running
- [ ] Basic memory store/search working

### Day 2
- [ ] One Claude Code container spawned successfully
- [ ] Container can connect to Discord via HTTP bridge
- [ ] Container can read/write to Postgres memory

### Day 3
- [ ] 2-3 agents running simultaneously
- [ ] Agents responding to Discord messages
- [ ] Basic memory persistence verified
- [ ] Can edit files in mounted workspace

## Quick Start Commands

```bash
# 1. Start Postgres
docker run -d --name superagent-postgres -p 5433:5432 \
  -e POSTGRES_PASSWORD=superagent ankane/pgvector

# 2. Start Discord MCP HTTP bridge
python discord_mcp_http_bridge.py

# 3. Test the orchestrator
python orchestrator_mvp.py

# 4. Check logs
docker logs agent-test-bot
```

## Next Steps After MVP

Once this is working:
1. Containerize the Discord MCP HTTP bridge
2. Add proper error handling and retries
3. Implement workspace preparation
4. Add memory context window management
5. Create multi-agent coordination

## Environment Variables Needed

```bash
# .env file
ANTHROPIC_API_KEY=your-key
DISCORD_TOKEN_TEST=your-discord-bot-token
OPENAI_API_KEY=your-openai-key  # For embeddings
```

## Estimated Effort

- **Day 1 Morning**: Discord MCP HTTP bridge
- **Day 1 Afternoon**: Postgres setup + basic memory
- **Day 2 Morning**: Minimal orchestrator
- **Day 2 Afternoon**: First agent running
- **Day 3**: Debug, test, get 2-3 agents stable

Total: 2-3 days to functional MVP

---

This MVP strips everything non-essential. The focus is purely on:
1. Getting Discord communication working via HTTP
2. Basic memory persistence
3. Spawning Claude Code containers that actually work

Everything else can be added incrementally once we have this foundation working.