# DevOps Agent Startup Flow

## 🚀 How to Start the Main DevOps Agent

### Method 1: Direct Launcher (Recommended)
```bash
# Set environment variables (if not in .env)
export OPENAI_API_KEY="your-openai-api-key"
export DISCORD_TOKEN_DEVOPS="your-discord-bot-token"
export DEFAULT_SERVER_ID="your-discord-server-id"

# Activate virtual environment
source .venv/bin/activate

# Start the conversational DevOps AI
python launchers/start_conversational_devops.py
```

### Method 2: Control Script
```bash
# Start using the control script
python devops_control.py start

# Check status
python devops_control.py status

# Stop all DevOps agents
python devops_control.py stop
```

## 📋 Startup Flow Details

### 1. **Environment Check**
- ✅ Validates `OPENAI_API_KEY` is set
- ✅ Validates `DISCORD_TOKEN_DEVOPS` is set
- ✅ Validates `DEFAULT_SERVER_ID` is set

### 2. **Agent Initialization**
```
🤖 ConversationalDevOpsAI initialized
├── 🛡️ Input validator (60 security patterns)
├── 🧠 Enhanced Discord Agent (OpenAI provider)
├── 💾 DevOps Memory Manager (PostgreSQL backend)
├── 🐳 Agent Orchestrator (Docker + container management)
└── 📋 Configuration loader (11 agent types)
```

### 3. **Discord Connection**
```
🎧 Starting message listener...
├── 🔌 Connects to Discord via MCP
├── 👂 Starts listening for mentions and DMs
└── 🎯 Ready to process natural language commands
```

### 4. **Message Processing Flow**
```
User Message → Input Validation → OpenAI Analysis → Tool Selection → Execution → Response
```

## 🛠️ Available Tools (OpenAI Function Calling)

1. **`deploy_agent`** - Deploy new AI agents (grok4, claude, gemini, etc.)
2. **`check_status`** - Get system and agent status
3. **`list_available_agents`** - Show available agent types
4. **`troubleshoot_agent`** - Debug and fix agent issues

## 🎯 Natural Language Examples

**Agent Deployment:**
- "Deploy a claude agent for coding tasks"
- "Start a grok4 agent for research"
- "Launch a fullstack developer bot"

**System Management:**
- "What's the system status?"
- "Show me all running agents"
- "How much memory is being used?"

**Troubleshooting:**
- "The claude agent isn't responding"
- "Check why the container deployment failed"
- "Restart the grok4 agent"

## 🔧 Architecture Components

### Core Files:
- **`agents/devops/conversational_devops_ai.py`** - Main OpenAI-based agent
- **`agents/devops/agent_orchestrator.py`** - Container/process management
- **`agents/devops/devops_memory_manager.py`** - PostgreSQL memory system
- **`agents/devops/input_validator.py`** - Security validation
- **`agents/enhanced_discord_agent.py`** - Base Discord functionality
- **`agents/llm_providers.py`** - OpenAI provider with function calling

### Configuration:
- **`agent_config.json`** - Agent type definitions
- **`configs/devops_config.json`** - DevOps-specific settings
- **`.env`** - Environment variables and API keys

## ✅ Success Indicators

When successfully started, you'll see:
```
✅ Environment variables configured
✅ Conversational DevOps AI initialized
🎧 Starting message listener...
INFO: 🛡️ Input validator initialized with 60 security patterns
INFO: 🎯 Unified Agent Orchestrator initialized
INFO: 🤖 Conversational DevOps AI initialized with input validation
```

## 🚨 Troubleshooting

**Missing API Key:**
```bash
# Add to .env file:
OPENAI_API_KEY=your-key-here
```

**Discord Connection Issues:**
```bash
# Check Discord token:
DISCORD_TOKEN_DEVOPS=your-bot-token-here
```

**Import Errors:**
```bash
# Ensure virtual environment is activated:
source .venv/bin/activate
pip install -r requirements.txt
```
