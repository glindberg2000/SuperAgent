# SuperAgent - Hybrid Multi-Agent Discord System

SuperAgent is a production-ready multi-agent system that provides intelligent Discord bot capabilities using various LLMs (Grok4, Claude, Gemini, O3) for different expertise areas. The system uses a hybrid architecture combining fast host process agents with powerful containerized Claude Code agents.

## 🏗️ Architecture

- **🎯 Manager Agent**: Orchestrates containers, coordinates files, delegates tasks
- **💻 Host Process Agents**: Fast responses (Grok4, Claude, Gemini, O3)  
- **🐳 Container Agents**: Full Claude Code development environment
- **📡 Discord HTTP API**: Stateless multi-bot support
- **🗄️ PostgreSQL + pgvector**: Shared vector memory across all agents
- **🔗 Docker Network**: Isolated container communication

## 🚨 **CRITICAL DEPENDENCY WARNING**

SuperAgent requires the `mcp-discord` submodule for Discord communication. **WITHOUT IT, THE SYSTEM WILL NOT FUNCTION.**

📖 **See [SUBMODULE_MANAGEMENT.md](docs/SUBMODULE_MANAGEMENT.md) for complete submodule documentation**

## 🚀 Quick Start

### 1. Prerequisites
- **Docker** (Docker Desktop or Colima)
- **Node.js** (for Claude Code CLI)
- **Python 3.11+**
- **Claude Max Plan** (for authenticated containers)
- **Git Submodules** (mcp-discord submodule is ESSENTIAL)

### 2. Environment Setup
```bash
# Clone repository with submodules
git clone --recursive <your-repo-url>
cd SuperAgent

# If you forgot --recursive, initialize submodules:
git submodule update --init --recursive

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and configure:

```env
# LLM API Keys
XAI_API_KEY=your-xai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_AI_API_KEY=your-google-key

# Discord Bot Tokens (separate applications)
DISCORD_TOKEN_GROK=manager-bot-token
DISCORD_TOKEN2=container-bot-1-token
DISCORD_TOKEN3=container-bot-2-token

# System Settings
DEFAULT_SERVER_ID=your-discord-server-id
POSTGRES_URL=postgresql://superagent:superagent@localhost:5433/superagent
```

### 4. Start Required Services

```bash
# Start PostgreSQL with pgvector
docker run -d --name superagent-postgres \
  -p 5433:5432 -e POSTGRES_PASSWORD=superagent \
  ankane/pgvector:latest

# Start Discord HTTP API (from mcp-discord directory)
cd mcp-discord
docker-compose up -d discord-http-api
cd ..
```

### 5. Create Authenticated Claude Code Container

**Important**: For Max plan integration, create a pre-authenticated container:

```bash
# Build writable container
cd docker/claude-code-writable
docker build -t superagent/claude-code-writable:latest .

# Create authenticated container
docker run -it -d --name claude-auth \
  -v $(pwd):/workspace -w /workspace \
  superagent/claude-code-writable:latest

# Authenticate (in new terminal)
docker exec -it claude-auth /bin/bash
claude login  # Choose Pro/Max plan
claude --print "Test authentication"
exit

# Save authenticated image
docker commit claude-auth superagent/claude-code-authenticated:latest
docker rm -f claude-auth
```

### 6. Launch Agents

```bash
# List available agents
python multi_agent_launcher_hybrid.py --list-agents

# Launch Manager Agent only
python multi_agent_launcher_hybrid.py --manager-only

# Launch full hybrid system
python multi_agent_launcher_hybrid.py --config agent_config_hybrid.json

# Launch specific agents
python multi_agent_launcher_hybrid.py --agents grok4_agent fullstackdev
```

## 🧪 Testing

```bash
# Validate Discord configuration
python tests/validate_discord_config.py

# Test Discord bot identities
python tests/test_discord_identities.py

# Test orchestrator
python orchestrator_mvp.py

# Test memory client
python memory_client.py
```

## 📁 Project Structure

### **Core Application Files**
```
SuperAgent/
├── README.md                          # Main project documentation
├── CLAUDE.md                          # Claude Code specific instructions
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore patterns (keeps secrets safe)
```

### **Python Core Modules**
```
├── enhanced_discord_agent.py          # 🤖 Main Discord agent with memory & context
├── llm_providers.py                   # 🧠 LLM API integrations (Grok4, Claude, Gemini, O3)
├── multi_agent_launcher_hybrid.py     # 🚀 Primary launcher - hybrid host/container system
├── multi_agent_launcher.py            # 📦 Legacy launcher - host process only
├── orchestrator_mvp.py                # 🐳 Container orchestration and management
├── memory_client.py                   # 🗄️ PostgreSQL + pgvector memory client
├── setup_postgres_vector.sh           # 🛠️ PostgreSQL setup utility
```

### **Configuration Files**
```
├── agent_config.json                  # 🔧 Basic agent configurations (grok4, claude, gemini, o3)
├── agent_config_hybrid.json           # 🔧 Enhanced hybrid system config with containers
├── agent_configs_mvp.json             # 🔧 Container-specific MVP configuration
├── example_custom_configs.json        # 📝 User customization examples
├── mcp.json                          # 🔒 MCP Discord server config (ignored - contains tokens)
├── memory.example.json               # 💾 Memory system example
```

### **Docker & Containers**
```
├── docker/                           # 🐳 Docker configurations
│   ├── claude-code-writable/         # Writable Claude Code container setup
│   │   ├── Dockerfile
│   │   └── create_authenticated_image.py
│   ├── claude-code-authenticated/    # Pre-authenticated container scripts  
│   │   ├── Dockerfile
│   │   └── setup.sh
│   └── claude-code-max/              # Max plan container (legacy)
│       └── Dockerfile
```

### **Discord Integration (Submodule)**
```
├── mcp-discord/                      # 📡 Discord HTTP API server (CRITICAL SUBMODULE)
│   ├── discord_http_stateless.py    # Main Discord HTTP API server
│   ├── docker-compose.yml           # Discord API container orchestration
│   ├── README.md                     # Discord setup documentation
│   ├── src/discord_mcp/             # MCP Discord source code
│   └── [see SUBMODULE_MANAGEMENT.md for complete details]
```

### **Testing & Validation**
```
├── tests/                           # 🧪 Test suite and validation tools
│   ├── test_discord_identities.py  # Discord bot identity regression tests
│   ├── validate_discord_config.py  # Configuration validator  
│   ├── discord_identity_test_report.json # Test results
│   └── README.md                    # Testing documentation
```

### **Documentation**
```
├── docs/                            # 📚 Comprehensive documentation
│   ├── SUBMODULE_MANAGEMENT.md      # 🚨 CRITICAL: mcp-discord submodule guide
│   ├── HYBRID_ARCHITECTURE.md       # System architecture details
│   ├── DEVELOPER_GUIDE.md           # Developer customization guide
│   ├── ORCHESTRATOR_README.md       # Container orchestration guide
│   ├── SuperAgent_MVP_PRD.md        # MVP requirements specification
│   ├── CONTAINER_SETUP.md           # Container setup instructions
│   ├── SuperAgent_Modernization_Roadmap.md # Development roadmap
│   └── troubleshooting/             # 🛠️ Troubleshooting guides
│       ├── DOCKER_CONTAINER_ISSUE_DIAGNOSIS.md
│       └── README.md
```

### **Issues & Resolution Tracking**
```
├── issues/                          # 🐛 Known issues and resolutions
│   ├── DISCORD_IDENTITY_ISSUE.md   # Discord bot identity regression fix
│   └── README.md                    # Issues documentation
```

### **Generated Content (Ignored by Git)**
```
├── PRD/                             # 📋 Product Requirements Documents (local only)
├── grok4_responses/                 # 🤖 Generated AI responses (local only)
├── data/                           # 🗄️ SQLite databases and user data (local only)
│   └── agent_memory.db             # Main conversation history
├── logs/                           # 📝 Agent logs (auto-generated, local only)
│   ├── discord_agent.log          # Main agent log
│   ├── Grok4Agent/                 # Per-agent log directories
│   ├── ClaudeAgent/
│   └── [other agent logs]
```

### **Key File Purposes:**

- **Launchers**: `multi_agent_launcher_hybrid.py` (current) vs `multi_agent_launcher.py` (legacy)
- **Container Orchestration**: `orchestrator_mvp.py` - standalone class imported by hybrid launcher
- **Configs**: `agent_config_hybrid.json` (production) vs `agent_config.json` (basic)
- **Security**: `mcp.json` contains Discord tokens - kept in .gitignore for cursor IDE
- **Memory**: All conversation data stored in `data/agent_memory.db` (SQLite + local files)
- **Submodule**: `mcp-discord/` is ESSENTIAL - provides Discord HTTP API server

## 🤖 Agent Types

### Host Process Agents (Fast)
- **Grok4Agent**: Research, analysis, live web search
- **ClaudeAgent**: Writing, reasoning, code analysis  
- **GeminiAgent**: Creative tasks, multimodal analysis
- **O3Agent**: Mathematical reasoning, logical analysis

### Container Agents (Full Development)
- **FullStackDev**: SuperAgent architecture & infrastructure
- **CoderDev1**: CryptoTaxCalc backend & financial analysis
- **CoderDev2**: Frontend, UI, Discord integrations

### Manager Agent (Orchestrator)
- **Container Management**: Spawn, monitor, manage Claude Code containers
- **File Coordination**: Handle file sharing between agents
- **Task Delegation**: Assign tasks to appropriate agents
- **System Monitoring**: Health checks and status reporting

## 💬 Manager Agent Commands

Use these commands in Discord:

- `@spawn-agent <name> <workspace>` - Create new container agent
- `@list-agents` - Show all active agents
- `@system-health` - Check system status
- `@assign-task <agent> <task>` - Delegate task to specific agent

## 🎯 Features

### Memory & Context Management
- SQLite-based conversation history with thread awareness
- Configurable context window
- Cross-conversation entity tracking
- Vector similarity search with PostgreSQL + pgvector

### Multi-LLM Support
- **Grok4**: Research, analysis, detailed explanations
- **Claude**: Code analysis, writing, complex reasoning (via API or Max plan)
- **Gemini**: Creative tasks, multimodal analysis
- **O3**: Logic, mathematics, structured reasoning

### Anti-Loop Protection
- Configurable max turns per thread/conversation
- Bot allowlist/blocklist functionality
- Response delay controls
- Channel restrictions and permissions

### Container Orchestration
- Docker-based Claude Code agents
- Pre-authenticated containers using Max plan
- Automatic health checks and recovery
- Isolated workspaces with file mounting

## 🔧 Troubleshooting

### Docker Issues
```bash
# Check Docker daemon
docker ps

# For Colima users
export DOCKER_HOST=unix:///Users/$(whoami)/.colima/default/docker.sock
```

### Claude Code Authentication
```bash
# Re-authenticate host installation
claude login

# Rebuild authenticated container if needed
cd docker/claude-code-writable
docker build --no-cache -t superagent/claude-code-writable:latest .
```

### Discord Issues
```bash
# Check Discord API health
curl http://localhost:9091/health

# Restart Discord API
cd mcp-discord && docker-compose restart discord-http-api
```

## 📚 Documentation

- **[SUBMODULE_MANAGEMENT.md](docs/SUBMODULE_MANAGEMENT.md)** - **CRITICAL: mcp-discord submodule setup**
- **[HYBRID_ARCHITECTURE.md](docs/HYBRID_ARCHITECTURE.md)** - Complete architecture guide
- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** - Customization and development
- **[CLAUDE.md](CLAUDE.md)** - Project overview and status

## 🚀 Production Deployment

1. **Environment Variables**: Set all required API keys and tokens
2. **Service Dependencies**: Ensure PostgreSQL and Discord API are running
3. **Container Images**: Build and authenticate Claude Code containers
4. **Monitor Logs**: Check `logs/` directory for agent activity
5. **Health Checks**: Use Manager Agent `@system-health` command

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

---

**SuperAgent provides the perfect balance of speed and power, enabling both lightning-fast responses and complex development capabilities within a single coordinated system.** 🚀