# SuperAgent Container Setup

This document covers the new containerization features for SuperAgent, including HTTP Discord API and PostgreSQL memory storage.

## Architecture Overview

The containerized SuperAgent consists of:
1. **Discord HTTP API** - Provides HTTP endpoints for Discord operations
2. **PostgreSQL with pgvector** - Vector database for memory storage
3. **Memory Client** - Async client for storing/retrieving memories
4. **Claude Code Containers** - Spawned containers for agent execution

## Quick Setup

### 1. Prerequisites
```bash
# Ensure Docker is running
docker --version

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn asyncpg openai numpy discord.py python-dotenv
```

### 3. Environment Configuration
```bash
# Copy and edit environment file
cp .env.example .env

# Required variables:
# DISCORD_TOKEN=your-discord-bot-token
# DEFAULT_SERVER_ID=your-discord-server-id
# OPENAI_API_KEY=your-openai-key (for embeddings)
# ANTHROPIC_API_KEY=your-anthropic-key (for Claude Code containers)
```

### 4. Start Infrastructure

#### PostgreSQL with pgvector
```bash
# Start PostgreSQL container on port 5433
./setup_postgres_vector.sh
```

This creates:
- Container: `superagent-postgres`
- Port: `5433` (to avoid conflicts)
- Database: `superagent`
- User/Password: `superagent/superagent`
- Tables: `memories` (with vector embeddings), `info`

#### Discord HTTP API
```bash
# Start Discord HTTP server
python discord_http_api.py

# Server starts on http://localhost:9090
```

### 5. Test the Setup

#### Test Discord API
```bash
# Health check
curl http://localhost:9090/health

# List channels
curl http://localhost:9090/channels

# Send test message
curl -X POST http://localhost:9090/test
```

#### Test Memory System
```bash
# Run memory client test
python memory_client.py
```

## API Endpoints

### Discord HTTP API (Port 9090)

- `GET /health` - Server health and Discord connection status
- `GET /channels` - List all accessible Discord channels
- `POST /messages` - Send message to channel
- `GET /messages/{channel_id}` - Get recent messages from channel
- `POST /test` - Send test message to #general

#### Example Usage
```bash
# Send a message
curl -X POST http://localhost:9090/messages \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "1395578179531309089",
    "content": "Hello from HTTP API!"
  }'
```

## Memory System

### Database Schema
```sql
-- Main memories table with vector embeddings
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100),
    content TEXT,
    embedding vector(1536),     -- OpenAI text-embedding-3-small
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX memories_embedding_idx ON memories 
USING ivfflat (embedding vector_cosine_ops);
```

### Memory Client Usage
```python
from memory_client import MemoryClient

async with MemoryClient("postgresql://superagent:superagent@localhost:5433/superagent") as client:
    # Store memory
    memory_id = await client.store_memory(
        agent_id="test-agent",
        content="User prefers Python for backend development",
        metadata={"source": "conversation", "importance": 0.8}
    )
    
    # Search similar memories
    results = await client.search_memories(
        "What programming language does the user prefer?",
        agent_id="test-agent"
    )
```

## Container Integration

### For Claude Code Containers
```python
# Environment variables for containers
environment = {
    "DISCORD_HTTP_URL": "http://host.docker.internal:9090",
    "POSTGRES_URL": "postgresql://superagent:superagent@host.docker.internal:5433/superagent",
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
}
```

### Docker Network Access
```bash
# From inside containers, access services via:
# Discord API: http://host.docker.internal:9090
# PostgreSQL: postgresql://superagent:superagent@host.docker.internal:5433/superagent
```

## Troubleshooting

### Port Conflicts
- Discord API: Port 9090 (configurable)
- PostgreSQL: Port 5433 (avoids default 5432)

### Check Running Services
```bash
# Check containers
docker ps | grep superagent

# Check ports
lsof -i :9090  # Discord API
lsof -i :5433  # PostgreSQL
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
docker exec -it superagent-postgres psql -U superagent -d superagent -c "SELECT 'Connection OK'"

# Check logs
docker logs superagent-postgres
```

### Discord API Issues
```bash
# Check Discord bot permissions in server
# Verify DISCORD_TOKEN is valid
# Check server logs for connection errors
```

## Migration from Legacy System

The HTTP API complements the existing MCP-based agents:
- **Legacy agents** continue using STDIO MCP transport
- **New containers** use HTTP API for Discord access
- **Memory system** is shared between both approaches
- **No breaking changes** to existing functionality

## Next Steps

After basic setup is working:
1. Create the orchestrator for spawning Claude Code containers
2. Add workspace mounting and repository access
3. Implement multi-agent coordination
4. Add monitoring and health checks