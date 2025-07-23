# SuperAgent MVP Container Orchestrator

A minimal container orchestrator for spawning and managing Claude Code containers with Discord and PostgreSQL integration.

## 🚀 Features

- **🐳 Container Management**: Spawn, monitor, and manage multiple agent containers
- **🤖 Multi-Agent Support**: Run multiple agents with different Discord identities
- **📡 Discord Integration**: Connects agents to Discord via stateless HTTP API
- **🗄️ PostgreSQL Memory**: Shared vector memory storage across agents
- **🔗 Network Isolation**: Secure container networking with automatic setup
- **📊 Health Monitoring**: System health checks for all dependencies
- **🛠️ Easy Cleanup**: Graceful container stop and removal

## 📋 Prerequisites

1. **Docker** running (Docker Desktop or Colima)
2. **Discord HTTP API** container running (`discord-stateless-api`)
3. **PostgreSQL** with pgvector running (`superagent-postgres`)
4. **Python 3.11+** with required dependencies

## 🔧 Installation

```bash
# Install dependencies
pip install docker python-dotenv

# Or use the requirements file
pip install -r requirements_orchestrator.txt
```

## 🚀 Quick Start

### 1. Start Required Services

```bash
# Start Discord API (from mcp-discord directory)
docker-compose up -d discord-http-api

# Start PostgreSQL with pgvector
docker run -d \
  --name superagent-postgres \
  -p 5433:5432 \
  -e POSTGRES_PASSWORD=superagent \
  -e POSTGRES_USER=superagent \
  -e POSTGRES_DB=superagent \
  ankane/pgvector:latest
```

### 2. Basic Usage

```python
from orchestrator_mvp import MVPOrchestrator

# Create orchestrator
orchestrator = MVPOrchestrator()

# Check system health
health = orchestrator.health_check()
print(f"System health: {health}")

# Spawn an agent
container_id = orchestrator.spawn_agent(
    name="my-agent",
    workspace_path="/path/to/workspace",
    discord_token="your_discord_bot_token",
    personality="Helpful coding assistant"
)

# List all agents
agents = orchestrator.list_agents()
print(f"Active agents: {list(agents.keys())}")

# View agent logs
logs = orchestrator.get_agent_logs("my-agent", lines=20)
print(logs)

# Stop and remove agent
orchestrator.stop_agent("my-agent")
orchestrator.remove_agent("my-agent")
```

### 3. Command Line Usage

```bash
# Set environment variables
export ANTHROPIC_API_KEY="your-api-key"
export DISCORD_TOKEN="your-discord-token"
export DOCKER_HOST="unix:///Users/greg/.colima/default/docker.sock"  # For Colima

# Run the orchestrator
python orchestrator_mvp.py

# Or test with minimal setup
python test_orchestrator.py
```

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Orchestrator      │    │  Discord HTTP API   │    │   PostgreSQL        │
│   (Host Machine)    │    │   (Container)       │    │   (Container)       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                           │                           │
           └─────────── superagent-network ────────────────────────┘
                              │
                    ┌─────────────────────┐
                    │   Agent Container   │
                    │   (Claude Code)     │
                    │                     │
                    │  - Discord Token    │
                    │  - Workspace Mount  │
                    │  - Postgres Access  │
                    └─────────────────────┘
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your-anthropic-api-key
DISCORD_TOKEN=your-primary-bot-token
DISCORD_TOKEN2=your-secondary-bot-token  # Optional

# Docker (auto-detected, but can override)
DOCKER_HOST=unix:///var/run/docker.sock  # or Colima path
```

### Agent Configuration (agent_configs_mvp.json)

```json
{
  "agents": {
    "grok4-agent": {
      "workspace_path": "~/repos/SuperAgent",
      "discord_token_env": "DISCORD_TOKEN",
      "personality": "Expert AI researcher focused on analysis and explanations"
    },
    "crypto-agent": {
      "workspace_path": "~/repos/CryptoTaxCalc", 
      "discord_token_env": "DISCORD_TOKEN2",
      "personality": "Cryptocurrency tax specialist and financial analyst"
    }
  }
}
```

## 📊 Monitoring

### Health Check

```python
health = orchestrator.health_check()
# Returns: {'docker': True, 'discord_api': True, 'postgres': True}
```

### Agent Status

```python
agents = orchestrator.list_agents()
# Returns detailed info about each agent:
# {
#   'agent-name': {
#     'id': 'container_id',
#     'status': 'running',
#     'image': 'python:3.11-slim',
#     'workspace': '/path/to/workspace'
#   }
# }
```

### Retrieve Logs

```python
logs = orchestrator.get_agent_logs("agent-name", lines=50)
print(logs)
```

## 🐳 Container Details

Each spawned agent container includes:

- **Environment Variables**:
  - `ANTHROPIC_API_KEY`: Claude API access
  - `DISCORD_TOKEN`: Bot-specific Discord token
  - `DISCORD_MCP_URL`: Internal Discord API URL
  - `POSTGRES_URL`: PostgreSQL connection string
  - `AGENT_NAME`: Unique agent identifier
  - `AGENT_PERSONALITY`: Agent behavior description

- **Volume Mounts**:
  - Workspace directory (read/write)
  - SSH keys (read-only, if available)

- **Network**: Connected to `superagent-network` for service communication

## 🛠️ Troubleshooting

### Docker Connection Issues

```bash
# Check Docker daemon
docker version

# For Colima users
export DOCKER_HOST=unix:///Users/$USER/.colima/default/docker.sock

# For Docker Desktop users
export DOCKER_HOST=unix:///var/run/docker.sock
```

### Service Health Issues

```bash
# Check running containers
docker ps | grep -E "(discord|postgres)"

# Start Discord API
cd mcp-discord && docker-compose up -d discord-http-api

# Start PostgreSQL
docker run -d --name superagent-postgres -p 5433:5432 \
  -e POSTGRES_PASSWORD=superagent ankane/pgvector:latest
```

### Network Issues

```bash
# List Docker networks
docker network ls | grep superagent

# Recreate network if needed
docker network rm superagent-network
# Orchestrator will recreate it automatically
```

## 🧪 Testing

```bash
# Run basic orchestrator test
python test_orchestrator.py

# Manual testing
python -c "
from orchestrator_mvp import MVPOrchestrator
o = MVPOrchestrator()
print('Health:', o.health_check())
"
```

## 🚀 Next Steps

1. **Claude Code Integration**: Replace test containers with actual Claude Code images
2. **MCP Configuration**: Auto-configure MCP settings in containers
3. **Agent Coordination**: Add inter-agent communication capabilities
4. **Persistent Storage**: Add volume management for agent persistence
5. **Load Balancing**: Distribute workload across multiple agents

## 📄 Files

- `orchestrator_mvp.py`: Main orchestrator class
- `test_orchestrator.py`: Basic functionality tests
- `agent_configs_mvp.json`: Agent configuration templates
- `requirements_orchestrator.txt`: Python dependencies

## 🤝 Integration

This orchestrator integrates with:
- **Discord HTTP API** (`discord_http_stateless.py`)
- **PostgreSQL Memory Client** (`memory_client.py`)
- **SuperAgent Multi-Agent System** (main project)

---

**Built for the SuperAgent MVP** 🤖  
**Enabling containerized multi-agent Discord interactions** 🚀