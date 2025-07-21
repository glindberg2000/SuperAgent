# Multi-Agent Discord Listener PRD

## Objective
Enable multiple LLM-backed agents (Grok4, OpenAI, Gemini, O3, etc.) to participate as independent Discord bots in a shared channel, each running as a lightweight Python script, to facilitate cross-LLM research, group conversations, and transparent audit trails—while preventing runaway bot-to-bot loops.

---

## Features

- **Standalone Agents:**  
  Each agent runs as a standalone Python Discord bot, with its own config and token.

- **MCP/Discord Tooling Integration:**  
  Agents may use MCP to access existing Discord toolset (e.g., message history, channel/thread info, user metadata) for advanced context management, or fall back to discord.py for direct event handling.

- **Context Management:**  
  - By default, agents use Discord as the canonical context source.
  - On every round/turn, agents can fetch and send the latest N messages from the channel or thread as part of their prompt context.
  - Optionally, agents can use MCP to access richer context (e.g., cross-channel history, user profiles, message metadata).
  - Agents should be able to distinguish between new threads, user-initiated messages, and bot conversations.

- **Thread Awareness:**  
  - Agents should track Discord thread IDs and associate context with each thread.
  - For group conversations, agents can send the full thread history (or a windowed summary) with each LLM prompt.
  - Option to limit context to only the last N messages, or to the current thread if the message is in a thread.

- **Response Rules:**  
  - Only respond to humans or a designated “lead” bot (configurable).
  - Ignore messages from other bots unless specifically allowed (allowlist).
  - Enforce a max-turns per conversation/thread to prevent endless loops.
  - Optionally, designate an intermediary/arbiter bot to coordinate group discussions and enforce rules.

- **Audit Logging:**  
  - Each agent logs all messages, responses, and context to a defined output directory (e.g., `logs/grok4/`, `logs/openai/`).
  - Logs include: timestamp, channel/thread ID, message content, sender, context window, and response.

- **DB Recommendation:**  
  - For lightweight setups: Use SQLite or JSONL for per-agent logs and state tracking.
  - For scalable, cross-agent coordination: Use a shared PostgreSQL DB (with SQLAlchemy ORM) or leverage the MCP knowledge graph for persistent, queryable memory and agent coordination.
  - MCP can be used for project-wide memory, tagging, and cross-agent entity/relation management.

- **Security:**  
  - All tokens and secrets are stored in `.env` or secure config files, never committed to git.
  - `.gitignore` includes all sensitive files and logs.

---

## Technical Requirements

- Python 3.8+ with discord.py (or nextcord/py-cord) for each agent.
- Each agent must have its own Discord bot token (never shared or committed).
- Configurable via YAML/JSON/TOML file (token, channel, context rules, ignore rules, etc.).
- Output/log directory for each agent.
- Optional: MCP integration for advanced context, memory, and coordination.
- Bot logic includes:
  - Ignore/respond rules (by author, bot, or message content).
  - Max-turns per thread/conversation.
  - Thread/context tracking for group chats.
  - Context window management (N messages, per-thread, or full channel).
- Security: .env or config file for tokens, robust .gitignore.

---

## Context and Thread Handling

- **Default:**  
  - On each message, agent fetches the last N messages from the channel or thread and includes them in the LLM prompt.
  - If the message starts a new thread or is from a new user/channel, agent can include the full thread history or a summary.

- **With MCP:**  
  - Agents can use MCP to fetch richer context (e.g., related messages from other channels, project memory, or user profiles).
  - Agents can log observations, entities, and relations to the project knowledge graph (prefix: `CryptoTax` or project name).
  - Context for each round can be dynamically constructed from both Discord and MCP memory.

---

## Risks & Mitigations

- **Endless Loops:**  
  - Mitigated by ignore rules, max-turns, and/or arbiter logic.

- **Channel Noise:**  
  - Too many bots may clutter the channel. Mitigate with a dedicated #llm-lab or #agent-arena channel.

- **Resource Use:**  
  - Each bot is lightweight, but running many may require process management (e.g., systemd, Docker Compose).

- **Security:**  
  - Tokens must be secret; never commit to git.

---

## Stretch Goals

- Arbiter bot for advanced conversation management.
- Web dashboard for monitoring and controlling agent conversations.
- Dynamic enable/disable of agents via Discord commands.
- Cross-agent context sharing via MCP knowledge graph.

---

## Out of Scope

- Non-Discord chat platforms (for now).
- Direct LLM-to-LLM API orchestration (this PRD is Discord-centric).

---

## Architectural Comparison: Multiple Listeners vs. Single Listener with Router/Arbiter

### Multiple Listeners (One Bot per LLM Agent)
- **Pros:**  
  - Simple, modular, easy to scale horizontally.
  - Each agent is independent; easy to add/remove.
  - No single point of failure.
- **Cons:**  
  - Risk of message ping-pong/loops.
  - Harder to coordinate advanced group logic (e.g., arbitration, turn-taking).
  - More resource/process overhead.

### Single Listener with Router/Arbiter
- **Pros:**  
  - Centralized control—easy to enforce rules, mediate, and manage group logic.
  - Can implement advanced arbitration, turn-taking, and cross-agent context sharing.
  - Lower resource/process overhead (one main process).
- **Cons:**  
  - More complex initial architecture.
  - Single point of failure unless made highly available.
  - Slightly less modular (all agents run in one process, but can be dynamically loaded).

**Recommendation:**  
- For simple use cases and rapid prototyping, multiple listeners is easiest.
- For production, group arbitration, and advanced workflows, a single listener/router/arbiter is preferable.

---
