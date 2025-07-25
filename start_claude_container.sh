#!/bin/bash
# Universal Claude Code Container Startup Script
# Handles all container creation, configuration, and startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/claude_container_config.json"
ENV_FILE="$SCRIPT_DIR/.env"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        print_status "Loading environment from $ENV_FILE"
        # Only export valid environment variable lines (no comments, no spaces in names)
        while IFS= read -r line; do
            if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*=.*$ ]]; then
                export "$line"
            fi
        done < <(grep -E '^[A-Z_][A-Z0-9_]*=' "$ENV_FILE")
    else
        print_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
}

# Check required environment variables
check_env_vars() {
    local required_vars=("DISCORD_TOKEN_CLAUDE" "DEFAULT_SERVER_ID" "ANTHROPIC_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            print_error "Missing required environment variable: $var"
            exit 1
        fi
    done
    
    print_success "All required environment variables found"
}

# Set up Docker connection
setup_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_warning "Standard Docker connection failed, trying Colima..."
        export DOCKER_HOST=unix:///Users/greg/.colima/default/docker.sock
        
        if ! docker info >/dev/null 2>&1; then
            print_error "Docker connection failed. Is Docker or Colima running?"
            exit 1
        fi
    fi
    
    print_success "Docker connection established"
}

# Create isolated workspace
create_workspace() {
    local container_name=$1
    local workspace_path="$HOME/claude_workspaces/$container_name"
    
    mkdir -p "$workspace_path"/{projects,logs,temp}
    
    # Create README
    cat > "$workspace_path/README.txt" << EOF
Claude Code Isolated Container Workspace
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Purpose: Discord-managed autonomous operations
Container: $container_name
Workspace: Isolated from SuperAgent project

This workspace is clean and separate from the main SuperAgent development environment.
EOF
    
    echo "$workspace_path"
}

# Check if container exists and is running
check_container() {
    local container_name=$1
    
    if docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -q "^$container_name"; then
        local status=$(docker ps -a --format "{{.Status}}" --filter "name=$container_name")
        
        if [[ $status == *"Up"* ]]; then
            print_success "Container $container_name is already running"
            return 0
        elif [[ $status == *"Exited"* ]]; then
            print_status "Restarting existing container $container_name"
            docker start "$container_name"
            return 0
        fi
    fi
    
    return 1
}

# Create and start container
create_container() {
    local container_name=${1:-"claude-isolated-discord"}
    local image="superagent/official-claude-code:latest"
    
    print_status "Creating new container: $container_name"
    
    # Create isolated workspace
    local workspace_path=$(create_workspace "$container_name")
    print_status "Using isolated workspace: $workspace_path"
    
    # Set up volumes
    local mcp_discord_path="$SCRIPT_DIR/mcp-discord"
    if [[ ! -d "$mcp_discord_path" ]]; then
        print_error "MCP Discord directory not found: $mcp_discord_path"
        exit 1
    fi
    
    # Set up SSH key mounting for Git access
    local ssh_dir="$HOME/.ssh"
    local git_config="$HOME/.gitconfig"
    
    # Build volume mounts
    local volume_mounts=(
        "-v" "${workspace_path}:/workspace"
        "-v" "${mcp_discord_path}:/home/node/mcp-discord"
    )
    
    # Note: SSH keys will be copied after container creation for proper permissions
    
    # Add Git config if it exists
    if [[ -f "$git_config" ]]; then
        volume_mounts+=("-v" "${git_config}:/home/node/.gitconfig:ro")
        print_status "Mounting Git configuration"
    fi
    
    # Create container
    docker run -d \
        --name "$container_name" \
        --restart unless-stopped \
        -e "DISCORD_TOKEN=$DISCORD_TOKEN_CLAUDE" \
        -e "DEFAULT_SERVER_ID=$DEFAULT_SERVER_ID" \
        -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
        -e "AGENT_TYPE=isolated_claude" \
        -e "AGENT_PERSONALITY=Claude Code container with isolated workspace. I am a separate bot from the SuperAgent system, operating independently for Discord-managed tasks." \
        -e "WORKSPACE_PATH=/workspace" \
        "${volume_mounts[@]}" \
        -w "/workspace" \
        --label "superagent.type=claude-code-isolated" \
        --label "superagent.agent=discord-managed" \
        --label "superagent.team=autonomous" \
        --label "superagent.managed=discord" \
        --label "superagent.workspace=isolated" \
        "$image" \
        sleep infinity
    
    print_success "Container $container_name created successfully"
    
    # Configure the container
    configure_container "$container_name"
}

# Configure container with MCP and required files
configure_container() {
    local container_name=$1
    
    print_status "Configuring container $container_name"
    
    # CRITICAL: Wait for Claude Code to initialize properly
    print_status "Waiting for Claude Code initialization..."
    sleep 5
    
    # CRITICAL: Preserve Claude Code authentication by getting existing config
    print_status "Preserving Claude Code authentication..."
    docker exec "$container_name" claude --version > /dev/null 2>&1 || {
        print_error "Claude Code not properly initialized in container"
        return 1
    }
    
    # Create critical __main__.py file FIRST
    docker exec "$container_name" sh -c 'echo "from discord_mcp import main; main()" > /home/node/mcp-discord/src/discord_mcp/__main__.py'
    
    # Copy SSH keys for Git access with proper permissions
    print_status "Setting up Git SSH access..."
    local ssh_dir="$HOME/.ssh"
    if [[ -d "$ssh_dir" ]]; then
        docker exec "$container_name" bash -c "
            # Copy SSH keys to container
            mkdir -p /home/node/.ssh_temp
            cp -r $ssh_dir/* /home/node/.ssh_temp/ 2>/dev/null || true
            
            # Set proper permissions
            chmod 700 /home/node/.ssh_temp
            chmod 600 /home/node/.ssh_temp/id_* 2>/dev/null || true
            chmod 600 /home/node/.ssh_temp/config 2>/dev/null || true
            chmod 644 /home/node/.ssh_temp/*.pub 2>/dev/null || true
            chown -R node:node /home/node/.ssh_temp
            
            # Replace mounted read-only directory
            rm -rf /home/node/.ssh
            mv /home/node/.ssh_temp /home/node/.ssh
        "
        docker cp "$ssh_dir" "$container_name:/home/node/.ssh_host"
        docker exec "$container_name" bash -c "
            rm -rf /home/node/.ssh
            mv /home/node/.ssh_host /home/node/.ssh
            chmod 700 /home/node/.ssh
            chmod 600 /home/node/.ssh/id_* 2>/dev/null || true
            chmod 600 /home/node/.ssh/config 2>/dev/null || true  
            chmod 644 /home/node/.ssh/*.pub 2>/dev/null || true
            chown -R node:node /home/node/.ssh
        "
        print_success "SSH keys configured for Git access"
    else
        print_warning "SSH directory not found - Git operations may not work"
    fi
    
    # CRITICAL FIX: Use claude mcp add to preserve authentication instead of overwriting config
    print_status "Adding MCP Discord server (preserving authentication)..."
    docker exec "$container_name" bash -c "
        export PYTHONPATH=/home/node/mcp-discord/src
        # Remove any existing discord server config
        claude mcp remove discord-isolated 2>/dev/null || true
        # Add MCP server while preserving Claude Code authentication
        claude mcp add discord-isolated stdio -- python3 -m discord_mcp --token '$DISCORD_TOKEN_CLAUDE' --server-id '$DEFAULT_SERVER_ID'
    " || {
        print_error "Failed to configure MCP server"
        return 1
    }
    
    # Test Claude authentication
    print_status "Testing Claude Code authentication..."
    if docker exec "$container_name" claude --version >/dev/null 2>&1; then
        local version=$(docker exec "$container_name" claude --version 2>/dev/null)
        print_success "Claude Code working: $version"
    else
        print_warning "Claude Code authentication test failed"
    fi
    
    # Test MCP connection
    print_status "Testing MCP Discord connection..."
    if docker exec "$container_name" claude mcp list 2>&1 | grep -q "Connected"; then
        print_success "MCP Discord connection working"
    else
        print_warning "MCP connection may have issues"
    fi
    
    # Copy startup scripts
    if [[ -f "$SCRIPT_DIR/discord_claude_manager.py" ]]; then
        docker cp "$SCRIPT_DIR/discord_claude_manager.py" "$container_name:/workspace/"
        docker exec "$container_name" chmod +x /workspace/discord_claude_manager.py
        print_success "Discord manager script installed"
    fi
}

# Send initial check-in message
send_checkin() {
    local container_name=$1
    
    print_status "Sending initial Discord check-in..."
    
    local checkin_result=$(docker exec "$container_name" claude \
        --dangerously-skip-permissions \
        --print "Send a brief message to Discord: '🤖 $container_name is now online and ready for Discord-managed tasks! Isolated workspace active.'" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        print_success "Initial check-in sent to Discord"
    else
        print_warning "Check-in message may have failed: $checkin_result"
    fi
}

# Start persistent monitoring (optional)
start_monitoring() {
    local container_name=$1
    
    if [[ -f "$SCRIPT_DIR/discord_claude_manager.py" ]]; then
        print_status "Starting persistent Discord monitoring..."
        
        # Start the monitoring script in background
        docker exec -d "$container_name" python3 /workspace/discord_claude_manager.py
        print_success "Discord monitoring started in background"
    else
        print_warning "Discord manager script not found, skipping monitoring"
    fi
}

# Save container info to registry
save_container_info() {
    local container_name=$1
    local registry_file="$SCRIPT_DIR/container_registry.json"
    
    local container_info=$(cat << EOF
{
  "$container_name": {
    "container_id": "$(docker inspect --format='{{.Id}}' "$container_name")",
    "container_name": "$container_name",
    "image": "$(docker inspect --format='{{.Config.Image}}' "$container_name")",
    "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "discord_token_env": "DISCORD_TOKEN_CLAUDE",
    "authentication": "api_key",
    "workspace": "$(docker inspect --format='{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}' "$container_name")",
    "type": "isolated",
    "status": "created_successfully",
    "startup_script": "$0",
    "config_file": "$CONFIG_FILE"
  }
}
EOF
)
    
    # Merge with existing registry or create new
    if [[ -f "$registry_file" ]] && [[ -s "$registry_file" ]]; then
        # Update existing registry (simplified approach)
        local temp_file=$(mktemp)
        jq --argjson new "$container_info" '. + $new' "$registry_file" > "$temp_file" && mv "$temp_file" "$registry_file"
    else
        echo "$container_info" > "$registry_file"
    fi
    
    print_success "Container info saved to $registry_file"
}

# Main function
main() {
    local container_name=${1:-"claude-isolated-discord"}
    local skip_monitoring=${2:-false}
    
    print_status "🚀 Starting Claude Code Container: $container_name"
    echo "=========================================="
    
    # Setup
    load_env
    check_env_vars
    setup_docker
    
    # Check if container already exists
    if check_container "$container_name"; then
        print_success "Container $container_name is running"
    else
        create_container "$container_name"
    fi
    
    # Send check-in
    send_checkin "$container_name"
    
    # Start monitoring if requested
    if [[ "$skip_monitoring" != "true" ]]; then
        start_monitoring "$container_name"
    fi
    
    # Save container info
    save_container_info "$container_name"
    
    print_success "🎉 Container $container_name is ready!"
    echo ""
    echo "Next steps:"
    echo "  • Monitor: docker logs -f $container_name"
    echo "  • Execute: docker exec $container_name claude --dangerously-skip-permissions --print 'Your command here'"
    echo "  • Stop: docker stop $container_name"
    echo "  • Restart: $0 $container_name"
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [container_name] [skip_monitoring]"
        echo ""
        echo "Options:"
        echo "  container_name    Name for the container (default: claude-isolated-discord)"
        echo "  skip_monitoring   Set to 'true' to skip starting monitoring (default: false)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Create default container with monitoring"
        echo "  $0 my-claude-bot                     # Create custom named container"
        echo "  $0 claude-isolated-discord true      # Create without monitoring"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac