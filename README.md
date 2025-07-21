# SuperAgent

SuperAgent is a next-generation, multi-project AI agent framework designed for deep technical collaboration, autonomous support, and seamless integration with Discord, Grok-4, and the Model Context Protocol (MCP) ecosystem. It is built for engineering teams that need an always-on, context-aware assistant capable of handling routine tasks, escalating complex issues, and supporting architectural decisions with advanced LLMs and persistent memory.

## Features
- **Discord Integration:** Monitors channels, answers questions, and escalates to Grok-4 for deep thinking.
- **Grok-4 & LLM Handoff:** Packages all relevant context, files, and conversations for advanced reasoning and round-trip collaboration with Grok-4.
- **Knowledge Graph Memory:** Uses a project-tagged, persistent knowledge graph memory MCP for storing entities, relations, and observations.
- **Autonomous Task Handling:** Handles lower-level engineering tasks, unblocks issues, and provides high-level architecture support.
- **Windsurf Workflow Prompt:** Orchestrates agent behavior, memory, and escalation logic via Windsurf config.
- **Security First:** Never commits secrets; robust .gitignore and memory handling.

## Installation
1. Clone the repo:
   ```bash
   git clone git@github.com:glindberg2000/SuperAgent.git
   cd SuperAgent
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # Or manually:
   pip install xai-sdk python-dotenv
   ```
4. Copy the example memory file:
   ```bash
   cp memory.example.json memory.json
   ```
5. Add your secrets to `.env` (never commit this file):
   ```env
   DISCORD_BOT_TOKEN=your_token_here
   XAI_API_KEY=your_grok4_key_here
   ```

## Usage
- Start the agent and it will monitor Discord, handle routine tasks, and escalate deep technical issues to Grok-4 as needed.
- Use the `workflow_prompt.md` for Windsurf or config integration to orchestrate agent behavior.
- All persistent memory is managed via the knowledge graph memory MCP and is project-tagged for context.

## Security & Best Practices
- **Do not commit**: `.env`, `memory.json`, or any secrets. Only commit `memory.example.json` as a template.
- All sensitive files and common Python/IDE artifacts are excluded via `.gitignore`.
- Treat `memory.json` as a database, not a config file.

## Contributing
1. Fork the repo and create your feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```
2. Commit your changes (no secrets!) and push:
   ```bash
   git commit -am 'Add new feature'
   git push origin feature/your-feature
   ```
3. Open a pull request.

## License
MIT

---

For more details, see the PRD (`NextGenDiscordChatbot_PRD.md`) and workflow prompt (`workflow_prompt.md`).
