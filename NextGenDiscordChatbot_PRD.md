# Product Requirements Document (PRD): SuperAgent (Generic Multi-Project AI Chatbot)

## Objective
Build a modular, scalable, and maintainable AI agent framework (`SuperAgent`) that can serve as a Discord chatbot and general-purpose MCP tool. The agent will leverage Grok-4 (or similar LLM), persistent memory via a knowledge graph memory MCP server, and extensible tool integrations. Designed for easy development, multi-project support, and deployment with Windsurf and MCP.

---

## Features

### 1. Generic Agent Core
- Connects to Discord via bot token (or other platforms in the future).
- Handles message events, commands, and DMs.
- Supports multiple channels, servers, and projects (project-aware context).

### 2. LLM Integration (Grok-4 or OpenAI)
- Routes user messages to LLM for intelligent responses.
- Supports context windows and conversation threading.
- Allows pluggable LLM backends (start with Grok-4, make extensible).

### 3. Memory & Persistence
- Uses a knowledge graph memory MCP server as the default persistent memory backend.
- Stores conversation history, user context, and project-specific knowledge as entities/relations/observations.
- Supports retrieval-augmented generation (RAG) for improved memory.
- Memory is tagged per project for multi-project support.
- Modular backend: can swap to local file/db or cloud as needed.

### 4. MCP Tooling & Extensibility
- Exposes agent actions as MCP tools for Windsurf (send message, get info, etc).
- Supports additional tools/plugins (e.g., web search, code execution, etc).

### 5. Config & Secrets Management
- All secrets (tokens, API keys) managed via `.env` or Windsurf config panel.
- No hardcoded secrets in repo.

### 6. Developer Experience
- Clean, generic repo structure (`SuperAgent`), ready for multi-project use.
- Clear README and setup scripts.
- Dev/test with Windsurf, but not dependent on any legacy codebase.

### 7. Deployment
- Easy local dev (venv, Docker optional).
- Cloud deployment optional (Heroku, Fly.io, etc).

---

## Current Focus (as of July 2025)
- Project renamed to `SuperAgent` for generic, multi-project use.
- Recreating Python virtual environment and reinstalling dependencies after folder rename.
- Preparing to install and configure the Knowledge Graph Memory MCP server as the persistent memory backend.
- Planning for project-aware tagging of all memory operations.
- Next steps: Environment setup, memory integration, and agent scaffold.

---

## Stretch Goals
- Web dashboard for monitoring and admin.
- Multi-LLM routing (Grok-4, OpenAI, Anthropic, etc).
- Advanced moderation and analytics.

---

## Out of Scope
- Letta-specific integrations.
- Legacy code or configs from previous projects.

---

## Next Steps
1. Create a new, empty project directory.
2. Scaffold the initial repo (choose Python, Node, or your preferred stack).
3. Set up Discord bot skeleton and MCP server.
4. Incrementally add LLM and memory modules.

---

## Context & Rationale
- This project is a clean break from Letta and legacy artifacts, ensuring no memory or config conflicts.
- Designed for rapid prototyping and future extensibility.
- All context, requirements, and rationale are captured here so you (or Cascade) can pick up in a clean session and proceed efficiently.
