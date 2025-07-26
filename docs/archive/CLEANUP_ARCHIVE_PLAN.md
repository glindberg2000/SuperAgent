# SuperAgent Legacy Code Cleanup & Archive Plan

## 🎯 Current Production System (KEEP)

### **✅ Active PostgreSQL Multi-Agent System**
```
multi_agent_launcher_hybrid.py     # Main production launcher
agent_config_hybrid.json          # Production configuration
memory_client.py                   # PostgreSQL + pgvector client
orchestrator_mvp.py               # Container orchestration
enhanced_discord_agent.py         # Core agent implementation
setup_postgres_vector.sh          # Database initialization
```

### **✅ Supporting Infrastructure (KEEP)**
```
llm_providers.py                   # LLM integrations
mcp.json                          # MCP Discord configuration
requirements.txt                  # Dependencies
.env                              # Environment configuration
logs/                             # Log directory
data/                             # Database directory (if needed)
```

## 📁 Legacy Code to Archive

### **Phase 1: SQLite-Based Legacy (Archive to `legacy/sqlite/`)**
```
multi_agent_launcher.py           # Old basic launcher (no PostgreSQL)
agent_config.json                 # Old config without PostgreSQL
test_agent.py                     # SQLite-based test agent
devops_control.py                 # Old control script
start_devops_agent.py             # Old startup script
test_ai_devops.py                 # Old test file
```

### **Phase 2: Legacy Docker HTTP Discord (Archive to `legacy/docker_http/`)**
```
mcp-discord/discord_http_stateless.py    # HTTP Docker Discord API
mcp-discord/docker-compose.yml           # Docker Discord services
mcp-discord/setup_discord_http.sh        # HTTP setup script
discord_*.py files in root               # Old Discord implementations
```

### **Phase 3: DevOps Agent System (Archive to `legacy/devops_system/`)**
```
control_plane/mcp_devops_agent.py        # MCP DevOps agent
control_plane/ai_devops_agent.py         # AI DevOps agent  
control_plane/devops_agent_spec.py       # DevOps specification
control_plane/devops_config.json         # DevOps configuration
start_mcp_devops_agent.py               # DevOps startup
```

### **Phase 4: Experimental/Test Files (Archive to `legacy/experimental/`)**
```
discord_mcp_*.py                   # Old MCP Discord experiments
superagent_grok4.py               # Old Grok4 implementation
analyze_memory.py                 # One-off analysis script
memory_client_test.py             # Old memory tests
validate_discord_config.py        # Config validation (move to tools/)
```

## 🗂️ Archive Directory Structure

```
SuperAgent/
├── legacy/
│   ├── sqlite/                   # SQLite-based old system
│   ├── docker_http/             # Docker HTTP Discord system  
│   ├── devops_system/           # DevOps agent system
│   ├── experimental/            # Test and experimental files
│   └── README.md                # Archive documentation
├── tools/                       # Utility scripts (keep)
│   ├── validate_discord_config.py
│   └── setup_postgres_vector.sh
└── [production files remain in root]
```

## 🚀 Archive Command Script

```bash
#!/bin/bash
# SuperAgent Legacy Archive Script

# Create archive directories
mkdir -p legacy/{sqlite,docker_http,devops_system,experimental}
mkdir -p tools

echo "📁 Archiving SuperAgent legacy code..."

# Phase 1: SQLite Legacy
mv multi_agent_launcher.py legacy/sqlite/
mv agent_config.json legacy/sqlite/
mv test_agent.py legacy/sqlite/
mv devops_control.py legacy/sqlite/
mv start_devops_agent.py legacy/sqlite/
mv test_ai_devops.py legacy/sqlite/

# Phase 2: Docker HTTP Discord
mv mcp-discord/discord_http_stateless.py legacy/docker_http/
mv mcp-discord/docker-compose.yml legacy/docker_http/
mv mcp-discord/setup_discord_http.sh legacy/docker_http/
mv discord_mcp_*.py legacy/docker_http/ 2>/dev/null || true

# Phase 3: DevOps System  
mv control_plane/ legacy/devops_system/
mv start_mcp_devops_agent.py legacy/devops_system/

# Phase 4: Experimental
mv discord_mcp_*.py legacy/experimental/ 2>/dev/null || true
mv superagent_grok4.py legacy/experimental/ 2>/dev/null || true
mv analyze_memory.py legacy/experimental/ 2>/dev/null || true
mv memory_client_test.py legacy/experimental/ 2>/dev/null || true

# Move utilities to tools
mv tests/validate_discord_config.py tools/ 2>/dev/null || true

echo "✅ Archive complete! Production system preserved in root."
echo "📋 Archived systems available in legacy/ directory"
```

## 📋 Production System Summary

**After cleanup, root directory contains only:**

### **Core Production Files**
- `multi_agent_launcher_hybrid.py` - Main launcher
- `agent_config_hybrid.json` - Production config
- `enhanced_discord_agent.py` - Core agent
- `memory_client.py` - PostgreSQL client
- `orchestrator_mvp.py` - Container orchestration
- `llm_providers.py` - LLM integrations

### **Infrastructure**
- `setup_postgres_vector.sh` - Database setup
- `mcp.json` - MCP configuration
- `requirements.txt` - Dependencies
- `.env` - Environment config
- `logs/` - Log directory
- `docs/` - Documentation

### **MCP Discord** (Keep active parts only)
- `mcp-discord/src/` - Core MCP Discord library
- `mcp-discord/pyproject.toml` - Package config

## 🎯 Benefits After Cleanup

1. **Clear Production Path**: Only one way to launch agents
2. **No Confusion**: Legacy experiments archived away
3. **Easy Onboarding**: New developers see only current system
4. **Preserved History**: All legacy code preserved for reference
5. **Clean Codebase**: Root directory contains only production code

## 🚨 WARNING: Run Tests First

Before archiving, ensure the production system works:

```bash
# Test PostgreSQL connection
python memory_client.py

# Test agent launch
python multi_agent_launcher_hybrid.py --list-agents

# Launch single agent test
python multi_agent_launcher_hybrid.py --agents grok4_agent
```

Only proceed with archival after confirming production system stability.