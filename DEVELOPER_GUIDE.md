# SuperAgent Developer Guide: Customizing Bot Personalities & Prompts

## Overview

SuperAgent uses a sophisticated configuration system that allows developers to customize bot personalities, system prompts, and behavior without touching the core agent code. This guide shows you how to modify and extend your Discord bots.

## Configuration Architecture

### 1. Agent Configuration (`agent_config.json`)

The main configuration file controls all aspects of bot behavior:

```json
{
  "agents": {
    "grok4_agent": {
      "name": "Grok4Agent",
      "llm_type": "grok4",
      "max_context_messages": 15,
      "max_turns_per_thread": 30,
      "response_delay": 2.0,
      "personality": "helpful, analytical, and engaging",
      "system_prompt_additions": "You excel at research, analysis, and providing detailed explanations."
    }
  }
}
```

### 2. System Prompt Generation

System prompts are dynamically generated in `enhanced_discord_agent.py:292-298`:

```python
system_prompt = f"""You are {self.config.name}, a helpful Discord bot powered by {self.config.llm_type}.
You're participating in a Discord conversation. Be conversational, helpful, and engaging.
Keep responses concise but informative. Avoid being repetitive or robotic."""
```

## Customization Options

### Personality Configuration

Each agent has configurable personality traits:

| Agent | Current Personality | Specialization |
|-------|-------------------|----------------|
| **Grok4Agent** | "helpful, analytical, and engaging" | Research, analysis, real-time search |
| **ClaudeAgent** | "thoughtful, precise, and helpful" | Code analysis, complex reasoning |
| **GeminiAgent** | "creative, versatile, and collaborative" | Creative tasks, multimodal analysis |

### Response Behavior Settings

```json
{
  "max_context_messages": 15,     // How many previous messages to consider
  "max_turns_per_thread": 30,     // Max responses per conversation thread
  "response_delay": 2.0,          // Seconds to wait before responding
  "ignore_bots": true,            // Whether to ignore other bot messages
  "bot_allowlist": [],            // Specific bots this agent CAN respond to
  "allowed_channels": []          // Restrict to specific Discord channels
}
```

## How to Modify Bot Behavior

### 1. Change Personality & Tone

Edit `agent_config.json`:

```json
{
  "personality": "professional, technical, and direct",
  "system_prompt_additions": "You are a senior software engineer. Provide code examples and technical solutions. Keep responses concise and actionable."
}
```

### 2. Create Role-Specific Bots

Add a new agent configuration:

```json
{
  "agents": {
    "code_reviewer": {
      "name": "CodeReviewerBot",
      "llm_type": "claude",
      "personality": "meticulous, constructive, and educational",
      "system_prompt_additions": "You are a code review specialist. Focus on code quality, security, performance, and best practices. Provide specific, actionable feedback.",
      "allowed_channels": ["code-review", "development"]
    }
  }
}
```

### 3. Channel-Specific Behaviors

Configure bots for different Discord channels:

```json
{
  "support_bot": {
    "personality": "patient, helpful, and beginner-friendly",
    "allowed_channels": ["help", "support", "questions"],
    "max_turns_per_thread": 50
  },
  "casual_bot": {
    "personality": "friendly, casual, and humorous", 
    "allowed_channels": ["general", "off-topic"],
    "response_delay": 0.5
  }
}
```

## Advanced Customization

### 1. Dynamic System Prompts

Modify `enhanced_discord_agent.py:292-298` to include config-based additions:

```python
system_prompt = f"""You are {self.config.name}, a helpful Discord bot powered by {self.config.llm_type}.
You're participating in a Discord conversation. Be conversational, helpful, and engaging.
Keep responses concise but informative. Avoid being repetitive or robotic.

Personality: {getattr(self.config, 'personality', 'helpful and professional')}
{getattr(self.config, 'system_prompt_additions', '')}"""
```

### 2. Context-Aware Prompts

Add channel or user-specific prompt modifications:

```python
def _build_system_prompt(self, channel_id: str, context_messages: List[Dict]) -> str:
    base_prompt = f"You are {self.config.name}..."
    
    # Channel-specific additions
    if channel_id in self.config.get('technical_channels', []):
        base_prompt += "\nFocus on technical accuracy and provide code examples."
    elif channel_id in self.config.get('casual_channels', []):
        base_prompt += "\nBe more conversational and use emojis occasionally."
    
    return base_prompt
```

### 3. Agent Capability Configuration

Configure different capabilities per agent:

```json
{
  "agents": {
    "research_bot": {
      "name": "ResearchBot",
      "llm_type": "grok4",
      "capabilities": {
        "web_search": true,
        "file_upload": true,
        "code_execution": false
      }
    }
  }
}
```

## Built-in LLM Capabilities

### Grok4 (Live Search Available)
- **Real-time search**: Automatically searches web, X platform, news
- **Enable in requests**: Set `search_parameters: {"mode": "on"}`
- **Cost**: Free during beta, then $0.025 per source
- **Use cases**: Current events, trending topics, real-time data

### Claude (Function Calling Available)
- **Structured responses**: JSON, code generation
- **Tool integration**: Can be extended with function calling
- **Use cases**: Code analysis, complex reasoning, structured data

### Gemini (Multimodal Capabilities)
- **Image understanding**: Can process images (if extended)
- **Creative generation**: Writing, brainstorming, content creation
- **Use cases**: Creative tasks, multimodal analysis

## Testing Your Changes

### 1. Test Individual Agents

```bash
# Test specific agent configuration
python enhanced_discord_agent.py --config-override '{"personality": "test personality"}'

# Or modify agent_config.json and run:
python multi_agent_launcher.py --agents grok4_agent
```

### 2. Validate Configuration

```bash
# Test configuration loading
python -c "
import json
with open('agent_config.json') as f:
    config = json.load(f)
    print('Config loaded successfully:', list(config['agents'].keys()))
"
```

### 3. Monitor Responses

Check logs for prompt effectiveness:

```bash
tail -f logs/discord_agent.log | grep "system_prompt"
```

## Best Practices

### 1. Gradual Changes
- Test personality changes with one agent first
- Monitor response quality and user engagement
- Adjust based on Discord community feedback

### 2. Consistent Branding
- Keep agent names and personalities aligned with their purpose
- Use consistent terminology across related bots
- Document personality choices for team alignment

### 3. Performance Considerations
- Longer system prompts use more tokens (cost)
- Balance detail with efficiency
- Monitor response times and adjust context limits

### 4. Safety Guidelines
- Avoid personalities that could be offensive or inappropriate
- Include safety guidelines in system prompts for public bots
- Test edge cases and unusual inputs

## Complete File Structure & Cleanup Guide

### **Core Production Files** ✅ (Keep & Commit)

```
SuperAgent/
├── CLAUDE.md                      # Project documentation & instructions
├── DEVELOPER_GUIDE.md             # This guide for developers  
├── MCP_DISCORD_ENHANCEMENTS.md    # File operations enhancement spec
├── README.md                      # Project overview
├── agent_config.json              # Main agent configuration
├── enhanced_discord_agent.py      # Primary Discord agent with memory
├── llm_providers.py               # LLM integrations (Grok4, Claude, Gemini)
├── multi_agent_launcher.py        # Multi-agent orchestration system
├── mcp.json                       # MCP Discord server configuration
├── requirements.txt               # Python dependencies
├── test_agent.py                  # Agent testing suite
├── memory.example.json            # Example memory configuration
└── .env.example                   # Environment variables template
```

### **Data & Logs** 📁 (Keep, Don't Commit)

```
├── data/                          # SQLite databases & analysis data
│   ├── agent_memory.db           # Main conversation database
│   ├── test_memory.db            # Test database
│   ├── 2024_tax_analysis.txt     # Tax analysis data (user data)
│   ├── 2024_transactions.csv     # Transaction data (user data) 
│   ├── fmv_analysis_summary.txt  # FMV analysis results
│   ├── missing_fmv_data.csv      # Missing data tracking
│   ├── 2Blue/                    # User's crypto tax data folder
│   └── samples/                  # Sample data for testing
└── logs/                          # Agent logs (auto-generated)
    ├── discord_agent.log         # Main agent log
    ├── Grok4Agent/               # Per-agent log directories
    └── TestAgent/                # Test agent logs
```

### **Legacy/Test Files** ❌ (Safe to Delete)

```
├── discord_mcp_agent.py          # Basic MCP agent (superseded)
├── discord_mcp_async_agent.py    # Async test version (superseded)
├── discord_mcp_grok_agent.py     # Grok-specific test (superseded) 
├── discord_mcp_improved_agent.py # Improved version (superseded)
├── discord_mcp_simple_agent.py   # Simple test version (superseded)
├── superagent_grok4.py           # Old Grok4 integration (superseded)
├── analyze_memory.py             # One-off memory analysis script
└── workflow_prompt.md            # Old workflow documentation
```

### **Generated Content** 📝 (Keep, Don't Commit)

```
├── grok4_fmv_response.md          # Generated analysis response
├── grok4_responses/               # Grok4 response archive
│   ├── fmv_followup_*.md         # Follow-up analysis files
│   ├── fmv_research_*.md         # Research response files
│   └── fmv_followup_prompt_*.md  # Prompt templates
├── FMV_Research_PRD.md            # Generated PRD document
├── MultiAgent_Discord_Listener_PRD.md  # System requirements
└── NextGenDiscordChatbot_PRD.md   # Chatbot specification
```

### **Cleanup Commands** 🧹

```bash
# Remove legacy Discord agent files
rm discord_mcp_agent.py discord_mcp_async_agent.py discord_mcp_grok_agent.py 
rm discord_mcp_improved_agent.py discord_mcp_simple_agent.py superagent_grok4.py

# Remove one-off scripts
rm analyze_memory.py workflow_prompt.md

# Clean up logs (optional - they regenerate)
rm -rf logs/*

# Keep generated content but don't commit (add to .gitignore)
echo "grok4_responses/" >> .gitignore
echo "*.md" >> .gitignore  # If you don't want to commit generated docs
echo "data/" >> .gitignore  # User data shouldn't be committed
echo "logs/" >> .gitignore  # Logs are auto-generated
```

### **Essential .gitignore Additions**

```gitignore
# User data & databases
data/
logs/
*.db
*.log

# Generated responses & analysis
grok4_responses/
*_response.md
*_analysis.txt

# Environment & secrets
.env
*.env
!.env.example

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
```

## Quick Reference: Configuration Keys

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `name` | string | Bot display name | "CodeReviewerBot" |
| `llm_type` | enum | LLM provider | "grok4", "claude", "gemini" |
| `personality` | string | Personality description | "helpful and analytical" |
| `system_prompt_additions` | string | Extra system prompt text | "You excel at..." |
| `max_context_messages` | int | Message history limit | 15 |
| `max_turns_per_thread` | int | Response limit per thread | 30 |
| `response_delay` | float | Seconds between responses | 2.0 |
| `allowed_channels` | array | Channel restriction list | ["general", "help"] |
| `ignore_bots` | boolean | Ignore other bot messages | true |
| `bot_allowlist` | array | Allowed bot usernames | ["helpful_bot"] |

---

## Need Help?

- **Configuration issues**: Check `logs/discord_agent.log`
- **API errors**: Verify `.env` file has correct API keys
- **Bot not responding**: Check `max_turns_per_thread` limits
- **Personality not working**: Verify `agent_config.json` syntax

For advanced customization, modify the core agent files and test thoroughly before deployment.