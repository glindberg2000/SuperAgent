# SuperAgent Containerization & Orchestration PRD
## Product Requirements Document

**Version:** 2.0  
**Date:** 2025-07-22  
**Estimated Timeline:** 1-2 weeks  

## Executive Summary

This PRD outlines the minimal viable implementation for containerizing SuperAgent's Discord bot architecture using Anthropic's recommended MCP transport methods and official containers. The system transforms from a single-process bot to a distributed container-based architecture supporting multiple specialized AI agents without requiring custom API layers.

## Problem Statement

The current SuperAgent system has several limitations:
1. **Transport Issues:** Discord MCP server uses STDIO transport, incompatible with container-to-container communication
2. **Scalability Constraints:** Single-process architecture limits multi-agent capabilities
3. **Memory Limitations:** SQLite-based memory doesn't support advanced vector operations
4. **Development Friction:** Manual setup for each agent instance without standardized workspace preparation

## Solution Overview

Implement a three-phase containerized architecture leveraging Anthropic's ecosystem:
1. **MCP HTTP Transport Configuration** for Discord server containerization
2. **Orchestrator Agent System** using Anthropic's official containers
3. **Enhanced Memory System** with Postgres/pgvector backend

## Technical Requirements

### Phase 1: MCP HTTP Transport Configuration

#### 1.1 Discord MCP Server Transport Update
**Objective:** Configure existing Discord MCP server to use HTTP transport instead of STDIO

**Technical Specifications:**
- **Transport Method:** HTTP (native MCP support)
- **Port:** 9090 (configurable via environment)
- **Protocol:** Standard MCP over HTTP
- **Authentication:** MCP-native authentication

**MCP Configuration:**
```bash
# Configure Discord MCP server for HTTP transport
claude mcp add --transport http discord-server http://discord-mcp:9090

# With authentication if needed
claude mcp add --transport http discord-server http://discord-mcp:9090 \
  --header "Authorization: Bearer ${DISCORD_MCP_TOKEN}"
```

**No Custom API Layer Required:**
- MCP protocol handles all communication
- Standard MCP tools and resources available
- Built-in error handling and retry logic
- Native support for multiple transport methods

#### 1.2 Docker Configuration
**Base Image:** Use existing Discord MCP server base
**Dependencies:** 
- Existing Discord MCP server dependencies
- HTTP transport libraries (if not already included)

**Dockerfile:**
```dockerfile
# Use existing Discord MCP server as base
FROM superagent/discord-mcp:latest

# Configure for HTTP transport
ENV MCP_TRANSPORT=http
ENV MCP_PORT=9090

EXPOSE 9090
CMD ["python", "-m", "discord_mcp_server", "--transport", "http", "--port", "9090"]
```

**Environment Variables:**
- `DISCORD_BOT_TOKEN`: Discord bot authentication
- `MCP_TRANSPORT`: Transport method (http)
- `MCP_PORT`: HTTP port (9090)
- `LOG_LEVEL`: Logging level

#### 1.3 Networking Configuration
**Docker Network:** `superagent-network` (bridge mode)
**Port Mapping:** 9090:9090
**Health Check:** MCP-native health endpoint

### Phase 2: Orchestrator Agent System

#### 2.1 Core Architecture
**Objective:** Single Python application managing multiple containerized AI agents using Anthropic's official containers

**Technical Specifications:**
- **Framework:** asyncio-based with docker-py for container management
- **Base Container:** `anthropic/computer-use-demo` (official Anthropic container)
- **Agent Types:** 
  - Chatbots (lightweight, memory-enhanced)
  - Code Agents (full Claude Code with workspace mounts)
  - Specialized Agents (frontend, backend, devops)

**Class Structure:**
```python
class OrchestratorApp:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.agents: Dict[str, Agent] = {}
        # Connect to Discord MCP server via HTTP
        self.discord_mcp = MCPClient("http://discord-mcp:9090")
    
    async def create_agent(self, agent_config: AgentConfig) -> Agent
    async def destroy_agent(self, agent_id: str) -> bool
    async def route_message(self, message: DiscordMessage) -> None

class Agent:
    def __init__(self, agent_id: str, agent_type: str, container: Container):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.container = container
        self.workspace_path = f"/workspace"  # Standard path in Anthropic containers
    
    async def initialize_workspace(self) -> None
    async def configure_mcp_servers(self) -> None
    async def health_check(self) -> bool
```

#### 2.2 Agent Configuration System
**Configuration Format:** YAML-based agent definitions

**Example Agent Config:**
```yaml
# Project configuration (set per project)
project:
  name: "CryptoTaxCalc"
  repo_url: "git@github.com:glindberg2000/CryptoTaxCalc.git"
  # Alternative: "https://github.com/glindberg2000/CryptoTaxCalc.git"
  branch: "main"
  docs_path: "/workspace/docs"

agents:
  CryptoTax_FullStack:
    type: "claude-code"
    image: "anthropic/computer-use-demo:latest"
    workspace:
      repo_url: "${PROJECT_REPO_URL}"  # Uses project config
      mount_path: "/workspace"
      docs_path: "${PROJECT_DOCS_PATH}"
    environment:
      - "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
      - "DISCORD_BOT_TOKEN=${CRYPTOTAX_FULLSTACK_TOKEN}"
      - "DISCORD_SERVER_ID=${DISCORD_SERVER_ID}"
      - "PROJECT_NAME=${PROJECT_NAME}"
    rules_file: "claude_rules/fullstack_dev.md"
    
  CryptoTax_CoderDev1:
    type: "claude-code"
    image: "anthropic/computer-use-demo:latest"
    workspace:
      repo_url: "${PROJECT_REPO_URL}"  # Uses project config
      mount_path: "/workspace"
      docs_path: "${PROJECT_DOCS_PATH}"
    environment:
      - "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
      - "DISCORD_BOT_TOKEN=${CRYPTOTAX_CODERDEV1_TOKEN}"
      - "DISCORD_SERVER_ID=${DISCORD_SERVER_ID}"
      - "PROJECT_NAME=${PROJECT_NAME}"
    rules_file: "claude_rules/coder_dev.md"
    
  CryptoTax_CoderDev2:
    type: "claude-code"
    image: "anthropic/computer-use-demo:latest"
    workspace:
      repo_url: "${PROJECT_REPO_URL}"  # Uses project config
      mount_path: "/workspace"
      docs_path: "${PROJECT_DOCS_PATH}"
    environment:
      - "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}"
      - "DISCORD_BOT_TOKEN=${CRYPTOTAX_CODERDEV2_TOKEN}"
      - "DISCORD_SERVER_ID=${DISCORD_SERVER_ID}"
      - "PROJECT_NAME=${PROJECT_NAME}"
    rules_file: "claude_rules/coder_dev.md"

# Memory chatbots run in main Python app (not containerized)
memory_chatbots:
  - name: "memory_assistant"
    type: "lightweight_chatbot"
    direct_db_access: true
    capabilities: ["memory_search", "quick_queries", "context_prep"]
```

#### 2.3 Workspace Preparation
**Objective:** Automated workspace setup with repo mounts, documentation, and agent-specific configurations

**Implementation:**
```python
class WorkspaceManager:
    async def prepare_workspace(self, agent_config: AgentConfig) -> str:
        workspace_path = f"/tmp/workspaces/{agent_config.agent_id}"
        
        # Create workspace directory
        os.makedirs(workspace_path, exist_ok=True)
        
        # Clone repository if specified
        if agent_config.repo_url:
            await self.clone_repository(agent_config.repo_url, workspace_path)
        
        # Copy agent-specific rules and documentation
        await self.setup_claude_md(agent_config, workspace_path)
        await self.copy_shared_docs(workspace_path)
        
        # Set up environment files
        await self.create_env_files(agent_config, workspace_path)
        
        return workspace_path
    
    async def setup_claude_md(self, config: AgentConfig, workspace: str):
        claude_md_content = f"""
# Agent: {config.agent_id}
## Role: {config.type}

## Project Context
Repository: {config.workspace.repo_url}
Documentation: Available in /workspace/docs/

## Rules and Guidelines
{self.load_rules_template(config.rules_file)}

## Available Tools
- File operations (read, write, edit)
- Terminal access for development tasks
- Discord communication via MCP API
- Memory operations for context retention

## Escalation Protocol
- For complex decisions: Mention @orchestrator
- For cross-agent coordination: Use #agent-coordination channel
- For user questions: Route to appropriate specialist
"""
        with open(f"{workspace}/CLAUDE.md", "w") as f:
            f.write(claude_md_content)
```

#### 2.4 Container Lifecycle Management
**Container Orchestration using Anthropic's Official Container:**
```python
class ContainerManager:
    async def create_agent_container(self, agent_config: AgentConfig) -> Container:
        # Prepare workspace
        workspace_path = await self.workspace_manager.prepare_workspace(agent_config)
        
        # Configure container using Anthropic's official image
        container_config = {
            "image": "anthropic/computer-use-demo:latest",
            "name": f"agent-{agent_config.agent_id}",
            "network": "superagent-network",
            "volumes": {
                workspace_path: {"bind": "/workspace", "mode": "rw"},
                "/shared/docs": {"bind": "/shared/docs", "mode": "ro"},
                "/shared/memory": {"bind": "/shared/memory", "mode": "rw"},
                # Mount host SSH keys for git operations
                f"{os.path.expanduser('~')}/.ssh": {"bind": "/home/anthropic/.ssh", "mode": "ro"}
            },
            "environment": [
                f"ANTHROPIC_API_KEY={agent_config.api_key}",
                f"DISCORD_BOT_TOKEN={agent_config.discord_token}",
                f"DISCORD_SERVER_ID={agent_config.discord_server_id}",
                f"AGENT_ID={agent_config.agent_id}",
                f"AGENT_TYPE={agent_config.agent_type}",
                "DISPLAY=:1",  # Required for computer use
                *agent_config.environment
            ],
            "restart_policy": {"Name": "unless-stopped"},
            "security_opt": ["seccomp:unconfined"],  # Required for computer use
            "shm_size": "2g"  # Shared memory for GUI applications
            # No resource limits - running on single laptop
        }
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config, detach=True)
        
        # Configure MCP servers within the container
        await self.configure_container_mcp(container, agent_config)
        
        # Configure git with SSH keys and agent identity
        await self.configure_git_in_container(container, agent_config)
        
        # Wait for container to be ready
        await self.wait_for_container_ready(container)
        
        return container
    
    async def configure_container_mcp(self, container: Container, config: AgentConfig):
        """Configure MCP servers within the agent container"""
        # Add Discord MCP server connection
        mcp_commands = [
            f"claude mcp add --transport http discord-server http://discord-mcp:9090",
            # Add other MCP servers as needed
            f"claude mcp add --transport http memory-server http://memory-server:8081"
        ]
        
        for cmd in mcp_commands:
            container.exec_run(cmd, user="anthropic")
    
    async def configure_git_in_container(self, container: Container, agent_config: AgentConfig):
        """Configure git with proper SSH and user settings"""
        git_commands = [
            # Set git user (agent-specific for commit attribution)
            f"git config --global user.name '{agent_config.agent_id}'",
            f"git config --global user.email '{agent_config.agent_id}@cryptotax.local'",
            # Configure SSH to use mounted keys
            "git config --global core.sshCommand 'ssh -i /home/anthropic/.ssh/id_rsa -o StrictHostKeyChecking=no'",
            # Set proper permissions on SSH keys
            "chmod 700 /home/anthropic/.ssh",
            "chmod 600 /home/anthropic/.ssh/id_rsa",
            "chmod 644 /home/anthropic/.ssh/id_rsa.pub",
            # Add GitHub to known hosts
            "ssh-keyscan github.com >> /home/anthropic/.ssh/known_hosts"
        ]
        
        for cmd in git_commands:
            container.exec_run(f"su - anthropic -c '{cmd}'")
```

#### 2.5 MCP Tools for Shared Resource Access
**Objective:** Provide containerized agents with tools to access shared Postgres vector store and documentation

**Implementation:**
```python
class SharedResourceMCPServer:
    """MCP server providing tools for database and docs access"""
    
    def __init__(self, memory_manager: MemoryManager, docs_manager: DocsManager):
        self.memory_manager = memory_manager
        self.docs_manager = docs_manager
    
    @mcp_tool
    async def search_vector_memory(self, query: str, agent_id: str = None, 
                                 memory_type: str = None, limit: int = 10) -> List[Dict]:
        """Search the shared Postgres vector store for relevant memories"""
        memories = await self.memory_manager.search_memories(
            query=query, 
            agent_id=agent_id, 
            memory_type=memory_type, 
            limit=limit
        )
        return [{
            "content": mem.content,
            "memory_type": mem.memory_type,
            "importance": mem.importance_score,
            "created_at": mem.created_at.isoformat()
        } for mem in memories]
    
    @mcp_tool
    async def store_memory(self, content: str, memory_type: str, 
                         importance: float = 0.5, agent_id: str = None) -> str:
        """Store information in the shared memory system"""
        memory_id = await self.memory_manager.store_memory(
            agent_id=agent_id or "unknown",
            content=content,
            memory_type=memory_type,
            importance=importance
        )
        return f"Memory stored with ID: {memory_id}"
    
    @mcp_tool
    async def get_shared_docs(self, doc_path: str) -> str:
        """Retrieve shared documentation content"""
        try:
            content = await self.docs_manager.get_document(doc_path)
            return content
        except FileNotFoundError:
            return f"Document not found: {doc_path}"
    
    @mcp_tool
    async def list_shared_docs(self, directory: str = "/shared/docs") -> List[str]:
        """List available shared documentation files"""
        return await self.docs_manager.list_documents(directory)
    
    @mcp_tool
    async def search_docs(self, query: str, doc_type: str = None) -> List[Dict]:
        """Search through shared documentation using vector similarity"""
        results = await self.docs_manager.search_documents(query, doc_type)
        return [{
            "filename": result.filename,
            "content_snippet": result.content[:500] + "..." if len(result.content) > 500 else result.content,
            "similarity_score": result.similarity_score
        } for result in results]

# Configure MCP server for shared resources
shared_mcp_server = SharedResourceMCPServer(memory_manager, docs_manager)
```

**MCP Server Configuration:**
```bash
# Add shared resource MCP server to agent containers
claude mcp add --transport http memory-server http://memory-server:8081
claude mcp add --transport http docs-server http://docs-server:8082
```

### Phase 3: Enhanced Memory System

#### 3.1 Postgres/pgvector Integration
**Objective:** Replace SQLite with scalable vector database

**Database Schema:**
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Core memory tables
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL, -- 'static', 'episodic', 'working'
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    importance_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255),
    channel_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- User profiles and preferences
CREATE TABLE user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    interaction_patterns JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversation tracking
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    participants JSONB NOT NULL,
    summary TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

-- Document storage and embeddings
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    content TEXT,
    embedding VECTOR(1536),
    uploaded_by VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    file_size INTEGER,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_memories_agent_type ON memories (agent_id, memory_type);
CREATE INDEX idx_conversations_channel ON conversations (channel_id);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
```

#### 3.2 Memory Management Classes
```python
class MemoryManager:
    def __init__(self, db_url: str):
        self.db = asyncpg.create_pool(db_url)
        self.embedder = OpenAIEmbedder(model="text-embedding-3-large")
    
    async def store_memory(self, agent_id: str, content: str, memory_type: str, 
                          importance: float = 0.0, metadata: dict = None) -> str:
        embedding = await self.embedder.embed(content)
        
        query = """
        INSERT INTO memories (agent_id, content, memory_type, embedding, 
                            importance_score, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """
        
        async with self.db.acquire() as conn:
            memory_id = await conn.fetchval(
                query, agent_id, content, memory_type, 
                embedding, importance, metadata or {}
            )
        
        return str(memory_id)
    
    async def search_memories(self, query: str, agent_id: str = None, 
                            memory_type: str = None, limit: int = 10) -> List[Memory]:
        query_embedding = await self.embedder.embed(query)
        
        sql = """
        SELECT id, content, memory_type, importance_score, created_at, metadata,
               1 - (embedding <=> $1) as similarity
        FROM memories
        WHERE ($2::text IS NULL OR agent_id = $2)
          AND ($3::text IS NULL OR memory_type = $3)
        ORDER BY embedding <=> $1
        LIMIT $4
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(sql, query_embedding, agent_id, memory_type, limit)
        
        return [Memory.from_row(row) for row in rows]

class DocumentProcessor:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.chunker = TextChunker(chunk_size=1000, overlap=200)
    
    async def process_document(self, file_path: str, uploaded_by: str) -> str:
        # Extract text content
        content = await self.extract_text(file_path)
        
        # Create document record
        doc_id = await self.store_document(file_path, content, uploaded_by)
        
        # Chunk and embed content
        chunks = self.chunker.chunk_text(content)
        for i, chunk in enumerate(chunks):
            await self.memory_manager.store_memory(
                agent_id="document_processor",
                content=chunk,
                memory_type="document",
                metadata={
                    "document_id": doc_id,
                    "chunk_index": i,
                    "filename": os.path.basename(file_path)
                }
            )
        
        return doc_id
```

#### 3.3 Context Preparation System
```python
class ContextPreparer:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    async def prepare_context(self, agent_id: str, current_message: str, 
                            max_tokens: int = 4000) -> str:
        # Search for relevant memories
        relevant_memories = await self.memory_manager.search_memories(
            query=current_message,
            agent_id=agent_id,
            limit=20
        )
        
        # Get static memories (always included)
        static_memories = await self.memory_manager.search_memories(
            query="",
            agent_id=agent_id,
            memory_type="static",
            limit=10
        )
        
        # Combine and rank by importance and relevance
        all_memories = self.rank_memories(relevant_memories + static_memories)
        
        # Build context within token limit
        context_parts = []
        token_count = 0
        
        for memory in all_memories:
            memory_tokens = self.estimate_tokens(memory.content)
            if token_count + memory_tokens > max_tokens:
                break
            
            context_parts.append(f"[{memory.memory_type.upper()}] {memory.content}")
            token_count += memory_tokens
        
        return "\n\n".join(context_parts)
    
    def rank_memories(self, memories: List[Memory]) -> List[Memory]:
        """Rank memories by combined importance and recency"""
        def score_memory(memory: Memory) -> float:
            recency_score = self.calculate_recency_score(memory.created_at)
            importance_score = memory.importance_score
            return (importance_score * 0.7) + (recency_score * 0.3)
        
        return sorted(memories, key=score_memory, reverse=True)
```

## Implementation Plan

### Week 1: Core Infrastructure
**Days 1-2:** MCP Transport Configuration
- Configure Discord MCP server for HTTP transport
- Update container networking and configuration
- Test MCP HTTP communication

**Days 3-4:** Orchestrator with Anthropic Containers
- Implement container lifecycle management using official containers
- Create workspace preparation system
- Configure MCP server connections within containers

**Day 5:** Integration Testing
- Test Discord MCP ↔ agent container communication
- Verify workspace mounting and file access
- Test CLAUDE.md and documentation access

### Week 2: Memory & Agent Enhancement
**Days 1-2:** Postgres/pgvector Setup
- Database schema implementation
- Memory management classes
- MCP memory server for shared context

**Days 3-4:** Agent Initialization & Configuration
- CLAUDE.md generation system
- Workspace mounting and repo preparation
- Agent-specific rule templates and configurations

**Day 5:** End-to-End Testing
- Full workflow testing with multiple agents
- Memory persistence and retrieval testing
- Documentation and deployment guides

## Success Criteria

### Functional Requirements
- [ ] Discord MCP server runs in container with HTTP transport
- [ ] Orchestrator can create/destroy agent containers using Anthropic's official images
- [ ] Agents have properly mounted workspaces with repos and docs
- [ ] Agents can access and modify Markdown files and documentation
- [ ] Memory system stores and retrieves context across sessions
- [ ] MCP servers properly configured within each agent container

### Performance Requirements
- [ ] MCP communication response time < 200ms
- [ ] Memory search returns results in < 500ms
- [ ] Container startup time < 45 seconds (including GUI setup)
- [ ] System supports 5+ concurrent agents

### Quality Requirements
- [ ] 95% uptime for core services
- [ ] Comprehensive logging and monitoring
- [ ] Error recovery and graceful degradation
- [ ] Security: proper container isolation and no secrets exposure

## Risk Mitigation

### Technical Risks
- **MCP transport compatibility:** Test HTTP transport thoroughly with existing Discord server
- **Container resource usage:** Anthropic containers require more resources for GUI support
- **Agent initialization failures:** Robust retry logic and MCP connection health checks

### Operational Risks
- **Resource constraints:** Monitor CPU/memory usage of GUI-enabled containers
- **Data persistence:** Regular backups of Postgres data and workspace volumes
- **Security vulnerabilities:** Follow Anthropic's security guidelines for computer use

## Future Enhancements

### Phase 2 Extensions
- Advanced memory consolidation and cleanup
- Multi-modal document processing using Anthropic's vision capabilities
- Agent collaboration and handoff protocols via MCP
- Advanced monitoring and analytics dashboard

### Integration Opportunities
- Kubernetes deployment using Anthropic's container best practices
- Integration with CI/CD pipelines via Claude Code GitHub Actions
- Advanced security following Anthropic's computer use guidelines
- Multi-tenant support with isolated container environments

## Example Usage: CryptoTax Team Deployment

### Setup Instructions

**1. Environment Configuration:**
```bash
# Set project-specific variables
export PROJECT_NAME="CryptoTaxCalc"
export PROJECT_REPO_URL="git@github.com:glindberg2000/CryptoTaxCalc.git"
export PROJECT_DOCS_PATH="/workspace/docs"

# Set Discord tokens for each agent
export CRYPTOTAX_FULLSTACK_TOKEN="your_discord_bot_token_1"
export CRYPTOTAX_CODERDEV1_TOKEN="your_discord_bot_token_2"
export CRYPTOTAX_CODERDEV2_TOKEN="your_discord_bot_token_3"
export DISCORD_SERVER_ID="your_discord_server_id"

# Set Anthropic API key
export ANTHROPIC_API_KEY="your_anthropic_api_key"

# Database connection
export POSTGRES_URL="postgresql://user:pass@localhost:5432/superagent"
```

**2. Start the Orchestrator:**
```bash
# Launch the SuperAgent orchestrator with CryptoTax team config
cd /Users/greg/repos/SuperAgent
python orchestrator.py --config configs/cryptotax_team.yaml
```

**3. Verify Agent Deployment:**
```bash
# Check running containers
docker ps --filter "name=agent-CryptoTax"

# Verify MCP connections
claude mcp list

# Test Discord connectivity
# Each agent should appear online in your Discord server
```

### Expected Behavior

**Agent Initialization:**
- **CryptoTax_FullStack**: Clones CryptoTaxCalc repo, configures full-stack development environment
- **CryptoTax_CoderDev1**: Clones CryptoTaxCalc repo, configures coding environment with specialized tools
- **CryptoTax_CoderDev2**: Clones CryptoTaxCalc repo, configures coding environment with specialized tools

**Workspace Setup:**
```
/workspace/
├── CryptoTaxCalc/          # Cloned project repository
│   ├── src/
│   ├── docs/
│   ├── tests/
│   └── README.md
├── CLAUDE.md               # Agent-specific rules and context
└── shared/
    ├── docs/               # Shared documentation
    └── memory/             # Shared memory files
```

**Available Tools per Agent:**
- **File Operations**: Read, write, edit project files
- **Git Operations**: Clone, commit, push, pull (using host SSH keys)
- **Memory Access**: Search/store in shared Postgres vector store
- **Documentation Access**: Retrieve shared docs and project documentation
- **Discord Communication**: Send messages, reactions, file uploads
- **Computer Use**: Full GUI access for development tasks

### Sample Workflow

**1. User Request in Discord:**
```
@CryptoTax_FullStack Please add a new tax calculation feature for crypto staking rewards
```

**2. Agent Response:**
- Searches memory for relevant context about staking calculations
- Reviews project documentation and existing code
- Creates feature branch and implements changes
- Commits and pushes code with proper attribution
- Reports back to Discord with progress

**3. Collaboration Example:**
```
@CryptoTax_CoderDev1 Please review the staking feature PR and add unit tests
@CryptoTax_CoderDev2 Can you update the documentation for the new staking feature?
```

### Switching Projects

To work on a different project (e.g., a new client project):

```bash
# Update project configuration
export PROJECT_NAME="NewClientProject"
export PROJECT_REPO_URL="git@github.com:glindberg2000/NewClientProject.git"

# Restart orchestrator with new config
python orchestrator.py --config configs/cryptotax_team.yaml --restart
```

Agents will automatically:
- Clone the new repository
- Update their workspace context
- Maintain their memory and Discord identities
- Continue with the same team structure

---

**Approval Required From:**
- Technical Lead: Architecture and implementation approach
- Product Owner: Feature scope and success criteria
- DevOps: Infrastructure and deployment strategy

**Next Steps:**
1. Technical review and approval
2. Environment setup (development containers)
3. Sprint planning and task breakdown
4. Implementation kickoff
