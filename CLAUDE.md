# SuperAgent - Multi-Agent Discord System

## Project Overview
SuperAgent is a multi-agent system that provides intelligent Discord bot capabilities using various LLMs (Grok4, Claude, Gemini) for different expertise areas. The system connects to Discord via MCP (Model Context Protocol) and can handle conversations, research, and eventually code execution.

## Current Status
- ✅ Basic MCP Discord connection working (`discord_mcp_agent.py`)
- ✅ Successfully sends messages to Discord channels
- ✅ Lists 25 available Discord tools via MCP
- ✅ Enhanced agent with memory, chat history, and context management (`enhanced_discord_agent.py`)
- ✅ SQLite-based conversation tracking and audit logging
- ✅ Thread-aware response rules to prevent bot loops
- ✅ Real LLM API integration (Grok4, Claude, Gemini)
- ✅ Multi-agent launcher for running multiple bots simultaneously
- ✅ Configurable agent personalities and response rules

## Architecture

### **Core Production Files** ✅
```
SuperAgent/
├── enhanced_discord_agent.py     # Primary Discord agent with memory & context
├── llm_providers.py              # LLM integrations (Grok4 w/Live Search, Claude, Gemini)
├── multi_agent_launcher.py       # Multi-agent orchestration system
├── agent_config.json             # Agent personalities & behavior configuration
├── mcp.json                      # MCP Discord server configuration
├── test_agent.py                 # Comprehensive agent testing suite
├── requirements.txt              # Python dependencies
├── memory.example.json           # Example memory configuration
└── .env.example                  # Environment variables template
```

### **Documentation & Guides** 📚
```
├── CLAUDE.md                     # This project documentation
├── DEVELOPER_GUIDE.md            # Developer customization guide  
├── MCP_DISCORD_ENHANCEMENTS.md   # File operations enhancement requirements
├── README.md                     # Project overview
├── MultiAgent_Discord_Listener_PRD.md  # System requirements
├── FMV_Research_PRD.md           # Generated analysis specification
└── NextGenDiscordChatbot_PRD.md  # Chatbot specification
```

### **Data Storage** 📁
```
├── data/                         # SQLite databases & user data (not committed)
│   ├── agent_memory.db          # Main conversation history & memory
│   ├── test_memory.db           # Test database
│   ├── 2024_tax_analysis.txt    # Tax analysis data (user data)
│   ├── 2024_transactions.csv    # Transaction data (user data)
│   ├── fmv_analysis_summary.txt # FMV analysis results
│   ├── missing_fmv_data.csv     # Missing data tracking
│   ├── 2Blue/                   # Crypto tax data folder
│   └── samples/                 # Sample data for testing
└── logs/                        # Agent logs (auto-generated)
    ├── discord_agent.log        # Main agent log
    ├── Grok4Agent/              # Grok4 agent logs
    └── TestAgent/               # Test agent logs
```

### **Generated Content & Responses** 📝
```
├── grok4_fmv_response.md         # Generated analysis response
├── grok4_responses/              # Archived Grok4 response files
│   ├── fmv_followup_*.md        # Follow-up analysis files
│   ├── fmv_research_*.md        # Research response files
│   └── fmv_followup_prompt_*.md # Prompt templates
└── workflow_prompt.md           # Workflow documentation
```

### **Legacy Files** (superseded by enhanced_discord_agent.py)
- discord_mcp_agent.py - Basic MCP agent (original working version)
- discord_mcp_async_agent.py - Async test version  
- discord_mcp_grok_agent.py - Grok-specific test version
- discord_mcp_improved_agent.py - Improved test version
- discord_mcp_simple_agent.py - Simple test version
- superagent_grok4.py - Old Grok4 integration
- analyze_memory.py - One-off memory analysis script

## Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and Discord tokens
# At minimum, set:
# - DISCORD_TOKEN_GROK
# - DEFAULT_SERVER_ID  
# - At least one LLM API key (XAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_AI_API_KEY)
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Test the System
```bash
# Run tests
python test_agent.py

# Test basic Discord connection
python discord_mcp_agent.py
```

### 4. Launch Agents
```bash
# List available agents
python multi_agent_launcher.py --list-agents

# Launch single agent
python multi_agent_launcher.py --agents grok4_agent

# Launch all agents
python multi_agent_launcher.py

# Launch specific agents
python multi_agent_launcher.py --agents grok4_agent claude_agent
```

## MCP Configuration
The system uses MCP to connect to Discord via the `mcp-discord-global` package. Configuration is in `mcp.json` with Discord token and server ID.

## Features

### 🧠 Memory & Context Management
- SQLite-based conversation history with thread awareness
- Configurable context window (N recent messages)
- Cross-conversation entity tracking and memory
- Audit logging for all interactions and responses

### 🤖 Multi-LLM Support
- **Grok4**: Research, analysis, detailed explanations
- **Claude**: Code analysis, writing, complex reasoning
- **Gemini**: Creative tasks, multimodal analysis, collaboration
- Easy API key configuration and provider switching

### 🛡️ Anti-Loop Protection
- Configurable max turns per thread/conversation
- Bot allowlist/blocklist functionality
- Response delay controls
- Channel restrictions and permissions

### 📊 Monitoring & Logging
- Per-agent log directories with structured logging
- Response time tracking and performance metrics
- Database storage for conversation analytics
- Error handling and recovery mechanisms

## Configuration

### Agent Configuration (`agent_config.json`)
```json
{
  "agents": {
    "grok4_agent": {
      "name": "Grok4Agent",
      "llm_type": "grok4",
      "max_context_messages": 15,
      "max_turns_per_thread": 30,
      "response_delay": 2.0,
      "personality": "helpful, analytical, and engaging"
    }
  }
}
```

### MCP Configuration (`mcp.json`)
- Discord server connection settings
- Bot token and server ID configuration  
- MCP Discord package integration

## Next Steps & Roadmap

### Phase 2: Enhanced Capabilities  
- ✅ Implement actual message listening with proper parsing
- ✅ Add support for Discord message processing and responses
- [ ] Enhanced personality system with dynamic prompt generation
- [ ] Add support for Discord threads and channel-specific responses
- [ ] Cross-agent knowledge sharing via MCP knowledge graph

### Phase 3: Advanced Features  
- [ ] Web dashboard for monitoring and controlling agents
- [ ] Dynamic agent enable/disable via Discord commands
- [ ] Integration with external tools and APIs
- [ ] Voice channel support and audio processing

### Phase 4: Code Execution Environment
- [ ] Containerized code execution (Docker integration)
- [ ] Git repository management and version control
- [ ] Automated testing and deployment pipelines
- [ ] Claude Code integration for development tasks

## Environment Variables Needed
- `DISCORD_TOKEN_GROK` - Discord bot token
- `XAI_API_KEY` - Grok API key
- `DEFAULT_SERVER_ID` - Discord server ID

## Notes
- Uses async MCP client for reliable Discord communication
- Server info is returned as text, not JSON (parsed manually)
- Currently targets #general channel, but can be configured

## 🎉 WORKING Claude Code Discord MCP Setup
**SEE:** `CLAUDE_CODE_DISCORD_MCP_WORKING_SETUP.md` for complete working configuration

- ✅ Container: `claude-fullstackdev-persistent` 
- ✅ Discord Bot: `CryptoTax_CoderDev1`
- ✅ MCP Connection: Working with `✓ Connected` status
- ✅ Critical Fix: `__main__.py` file required in `discord_mcp` package