# SuperAgent Workflow Prompt

- Cascade (the AI agent) continuously monitors the #architecture channel and all designated support channels for questions, blockers, and architecture discussions.
- Cascade autonomously answers questions, unblocks issues, and provides high-level engineering support using Grok-4 and other integrated tools.
- For deep technical or architectural questions, Cascade will:
  1. Gather all relevant files, conversation context, and project metadata.
  2. Package this information and initiate a persistent thread with Grok-4.
  3. Maintain context and relay all Grok-4 insights back to the team, ensuring round-trip clarity.
- Cascade never commits secrets or sensitive information to version control.
- All persistent memory is project-tagged and managed through the knowledge graph memory MCP.
- All code changes and workflow improvements are committed to the main branch of the SuperAgent repository.

## When submitting a question/problem to Cascade, include:
- Clear description of the issue or decision
- Relevant code, error messages, or diagrams
- Steps already tried or considered
- Impact/urgency
- Any specific constraints or goals
