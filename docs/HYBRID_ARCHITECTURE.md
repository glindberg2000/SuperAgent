# SuperAgent Hybrid Multi-Agent Architecture

A comprehensive guide to the SuperAgent hybrid system that combines host process agents with containerized Claude Code agents, orchestrated by a Manager Agent.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SuperAgent Hybrid System                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎯 Manager Agent (Host Process)                                │
│  ├─ Container Orchestration                                     │
│  ├─ File Coordination                                          │
│  ├─ Task Delegation                                            │
│  └─ Discord Identity & Communication                           │
│                                                                 │
│  💻 Host Process Agents                                        │
│  ├─ grok4_agent (Research & Analysis)                         │
│  ├─ claude_agent (Reasoning & Writing)                        │
│  ├─ gemini_agent (Creative & Multimodal)                      │
│  └─ o3_agent (Logic & Mathematics)                            │
│                                                                 │
│  🐳 Container Agents (Claude Code)                             │
│  ├─ fullstackdev (SuperAgent Development)                     │
│  ├─ coderdev1 (CryptoTaxCalc Backend)                         │
│  └─ coderdev2 (Frontend & Integrations)                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     Shared Services                             │
│  📡 Discord HTTP API (Stateless)                              │
│  🗄️ PostgreSQL + pgvector (Shared Memory)                     │
│  🔗 Docker Network (superagent-network)                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Manager Agent: The Orchestrator

The **Manager Agent** is a special host process agent that serves as the system orchestrator:

### **Primary Responsibilities:**
- **🐳 Container Management**: Spawn, monitor, and manage Claude Code containers
- **📁 File Coordination**: Handle file sharing and synchronization between agents
- **📋 Task Delegation**: Assign complex coding tasks to appropriate container agents
- **💬 Discord Communication**: Maintain own Discord identity for system management
- **📊 System Monitoring**: Health checks and status reporting

### **Special Commands:**
- `@spawn-agent <name> <workspace>` - Create new container agent
- `@list-agents` - Show all active agents (host + container)
- `@system-health` - Check system status
- `@assign-task <agent> <task>` - Delegate task to specific agent
- `@share-file <source> <target> <file>` - Coordinate file sharing

## 💻 Host Process Agents: Fast & Reliable

Host process agents run directly on the system for **fast response times** and **simple tasks**:

### **Capabilities:**
- ✅ **Lightning fast responses** (no container overhead)
- ✅ **Shared PostgreSQL memory** access
- ✅ **Individual Discord identities**
- ✅ **Specialized LLM expertise** (Grok4, Claude, Gemini, O3)
- ✅ **Easy debugging and monitoring**

### **Best For:**
- Quick chat responses
- Research and analysis
- Reasoning and explanations  
- Creative tasks
- Mathematical calculations

## 🐳 Container Agents: Full Development Power

Container agents run in **Claude Code containers** for **complex development tasks**:

### **Capabilities:**
- ✅ **Full Claude Code environment**
- ✅ **File system access** (mounted workspaces)
- ✅ **Individual Discord identities**
- ✅ **Code execution and editing**
- ✅ **Git repository access**
- ✅ **Isolated development environments**

### **Best For:**
- Complex coding projects
- File operations and editing
- System architecture design
- Multi-file development tasks
- Testing and deployment

## 📋 Configuration Structure

### **agent_config_hybrid.json Structure:**

```json
{
  "agents": {
    "grok4_agent": {
      "name": "Grok4Agent",
      "llm_type": "grok4",
      "personality": "Expert AI researcher...",
      // Host process agent settings
    }
  },
  
  "container_agents": {
    "fullstackdev": {
      "type": "container",
      "workspace_path": "~/repos/SuperAgent",
      "discord_token_env": "DISCORD_TOKEN2",
      "personality": "Full-stack developer...",
      "capabilities": ["coding", "file_operations"]
    }
  },
  
  "manager_agent": {
    "name": "SuperAgent Manager",
    "llm_type": "grok4",
    "personality": "Orchestrator and coordinator...",
    "capabilities": ["container_management", "file_coordination"]
  }
}
```

## 🚀 Usage Examples

### **1. Launch Full System:**
```bash
# Launch all agents (Manager + Host + Container)
python multi_agent_launcher_hybrid.py --config agent_config_hybrid.json

# Launch specific agents only
python multi_agent_launcher_hybrid.py --agents grok4_agent fullstackdev

# Manager Agent only (for testing)
python multi_agent_launcher_hybrid.py --manager-only
```

### **2. List Available Agents:**
```bash
python multi_agent_launcher_hybrid.py --list-agents
```

### **3. Manager Agent Commands in Discord:**
```
@spawn-agent mybot ~/repos/MyProject
@list-agents
@system-health
@assign-task fullstackdev "Implement user authentication system"
```

## 🔧 System Requirements

### **Required Services:**
1. **Docker** (Docker Desktop or Colima)
2. **Discord HTTP API** container (port 9091)
3. **PostgreSQL with pgvector** (port 5433)

### **Environment Variables:**
```bash
# LLM API Keys
ANTHROPIC_API_KEY=your-anthropic-key
XAI_API_KEY=your-xai-key
GOOGLE_AI_API_KEY=your-google-key

# Discord Bot Tokens (separate applications)
DISCORD_TOKEN_GROK=manager-bot-token
DISCORD_TOKEN2=container-bot-1-token  
DISCORD_TOKEN3=container-bot-2-token

# System Settings
DEFAULT_SERVER_ID=your-discord-server-id
POSTGRES_URL=postgresql://superagent:superagent@localhost:5433/superagent
```

### **Start Required Services:**
```bash
# Start Discord API (from mcp-discord directory)
docker-compose up -d discord-http-api

# Start PostgreSQL
docker run -d --name superagent-postgres \
  -p 5433:5432 -e POSTGRES_PASSWORD=superagent \
  ankane/pgvector:latest
```

## 🎯 Agent Coordination Patterns

### **1. Task Delegation Pattern:**
```
User → Manager Agent → Container Agent → Response
```

### **2. File Coordination Pattern:**
```
Agent A → Manager Agent → Shared Storage → Agent B
```

### **3. Memory Sharing Pattern:**
```
All Agents → Shared PostgreSQL → Vector Similarity Search
```

### **4. Hybrid Response Pattern:**
```
Simple Query → Host Agent (Fast Response)
Complex Task → Container Agent (Full Development)
```

## 📊 Agent Roles & Specializations

### **Host Process Specialists:**
- **🧠 Grok4Agent**: Research, analysis, live web search
- **✍️ ClaudeAgent**: Writing, reasoning, code analysis  
- **🎨 GeminiAgent**: Creative tasks, multimodal analysis
- **🔢 O3Agent**: Mathematical reasoning, logical analysis

### **Container Development Teams:**
- **🏗️ FullStackDev**: SuperAgent architecture & infrastructure
- **💰 CoderDev1**: CryptoTaxCalc backend & financial analysis
- **🎨 CoderDev2**: Frontend, UI, Discord integrations

### **🎯 Manager Agent**: System orchestrator and coordinator

## 🔄 Lifecycle Management

### **System Startup:**
1. **Manager Agent** initializes first (container orchestration)
2. **Host Process Agents** launch in parallel (fast startup)
3. **Container Agents** spawn via Manager (slower, but full power)
4. **All agents** connect to shared services (Discord API, PostgreSQL)

### **Task Execution:**
1. **Discord message** received by appropriate agent
2. **Simple tasks** handled by host process agents
3. **Complex tasks** delegated to container agents via Manager
4. **Results** shared back through Discord and memory

### **System Shutdown:**
1. **Graceful shutdown signal** sent to all agents
2. **Host process agents** stop their tasks
3. **Container agents** stopped and removed via orchestrator
4. **Shared services** remain running for next session

## 🧪 Testing & Debugging

### **Test the System:**
```bash
# Run test suite
python test_hybrid_launcher.py

# Check configuration
python multi_agent_launcher_hybrid.py --list-agents

# Test Manager Agent only
python multi_agent_launcher_hybrid.py --manager-only
```

### **Debug Individual Components:**
```bash
# Test orchestrator
python orchestrator_mvp.py

# Test Discord API
curl http://localhost:9091/health

# Test PostgreSQL
python memory_client.py
```

## 🚀 Next Steps

### **Phase 1: Current MVP**
- ✅ Hybrid architecture working
- ✅ Manager Agent orchestration
- ✅ Host process agents
- ✅ Container agent support

### **Phase 2: Enhanced Coordination**
- 🔄 Inter-agent communication protocols
- 🔄 Advanced file sharing systems
- 🔄 Task queue and priority management
- 🔄 Dynamic agent scaling

### **Phase 3: Advanced Features**
- 🔄 Multi-repository workspace management
- 🔄 Automated testing and deployment
- 🔄 Advanced memory context management
- 🔄 Cross-agent learning and optimization

---

**The SuperAgent Hybrid Architecture provides the perfect balance of speed and power, enabling both lightning-fast responses and complex development capabilities within a single coordinated system.** 🚀