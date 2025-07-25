# Discord Bot Registry

This document maintains the official mapping between Discord bot identities, their tokens, and their intended usage within the SuperAgent system.

## Bot Registry Table

| Bot Name | Discord App Name | Token Env Var | Purpose | Container/Agent |
|----------|------------------|---------------|---------|----------------|
| `CryptoTax_CoderDev1` | CryptoTax CoderDev1 | `DISCORD_TOKEN_CODERDEV1` | Claude Code development container 1 | `claude-isolated-discord` |
| `CryptoTax_CoderDev2` | CryptoTax CoderDev2 | `DISCORD_TOKEN_CODERDEV2` | Claude Code development container 2 | `claude-fullstackdev-persistent` |
| `SuperAgent_DevOps` | SuperAgent DevOps | `DISCORD_TOKEN_DEVOPS` | Orchestration agent launcher | `multi_agent_launcher.py` |
| `SuperAgent_Grok4` | SuperAgent Grok4 | `DISCORD_TOKEN_GROK4` | Research and analysis with live search | `enhanced_discord_agent.py` |
| `SuperAgent_Gemini` | SuperAgent Gemini | `DISCORD_TOKEN_GEMINI` | Creative tasks and multimodal analysis | `enhanced_discord_agent.py` |

## Token Naming Convention

- Format: `DISCORD_TOKEN_{IDENTITY}`
- Identity should be short, clear, and descriptive
- Use UPPERCASE with underscores for consistency
- Examples: `DISCORD_TOKEN_CODERDEV1`, `DISCORD_TOKEN_DEVOPS`

## Usage Guidelines

1. **One Token Per Bot Identity**: Each Discord application should have its own unique token
2. **Environment Segregation**: Use different tokens for different environments/purposes
3. **Never Commit Real Tokens**: Always use `.env.example` with dummy values
4. **Self-Documenting**: Token names should clearly indicate their purpose

## Container Mappings

### Claude Code Containers
- `claude-fullstackdev-persistent`: Uses `DISCORD_TOKEN_CODERDEV1`
- `claude-isolated-discord`: Uses `DISCORD_TOKEN_DEVOPS`

### Python Agents
- Grok4 Agent: Uses `DISCORD_TOKEN_GROK4`
- Gemini Agent: Uses `DISCORD_TOKEN_GEMINI`

## Notes

- **Removed**: `DISCORD_TOKEN_CLAUDE` - Redundant with Claude Code containers
- **Authentication**: Claude Code containers use subscription auth, not API keys
- **Isolation**: Each bot identity operates independently with separate Discord permissions