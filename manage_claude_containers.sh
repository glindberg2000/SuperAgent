#!/bin/bash
# Claude Container Management Script
# Easy operations for Claude Code containers

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Setup Docker
setup_docker() {
    if ! docker info >/dev/null 2>&1; then
        export DOCKER_HOST=unix:///Users/greg/.colima/default/docker.sock
        if ! docker info >/dev/null 2>&1; then
            print_error "Docker connection failed"
            exit 1
        fi
    fi
}

# List all Claude containers
list_containers() {
    print_status "Claude Code Containers:"
    echo "================================================"
    
    # Get all containers with claude labels or names
    local containers=$(docker ps -a --filter "label=superagent.type=claude-code" --filter "label=superagent.type=claude-code-isolated" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.CreatedAt}}")
    
    if [[ -z "$containers" ]] || [[ "$containers" == "NAMES"* ]]; then
        print_warning "No Claude Code containers found"
        return
    fi
    
    echo "$containers"
    echo ""
    
    # Show additional details
    docker ps -a --filter "label=superagent.type=claude-code" --filter "label=superagent.type=claude-code-isolated" --format "{{.Names}}" | while read name; do
        if [[ -n "$name" ]]; then
            echo "📋 $name Details:"
            echo "   ID: $(docker inspect --format='{{.Id}}' "$name" 2>/dev/null | cut -c1-12)"
            echo "   Workspace: $(docker inspect --format='{{range .Mounts}}{{if eq .Destination "/workspace"}}{{.Source}}{{end}}{{end}}' "$name" 2>/dev/null)"
            echo "   Type: $(docker inspect --format='{{index .Config.Labels "superagent.type"}}' "$name" 2>/dev/null)"
            echo ""
        fi
    done
}

# Start a container
start_container() {
    local name=${1:-"claude-isolated-discord"}
    
    if docker ps --format "{{.Names}}" | grep -q "^$name$"; then
        print_success "Container $name is already running"
        return
    fi
    
    if docker ps -a --format "{{.Names}}" | grep -q "^$name$"; then
        print_status "Starting existing container $name"
        docker start "$name"
        print_success "Container $name started"
    else
        print_status "Container $name not found, creating new one..."
        "$SCRIPT_DIR/start_claude_container.sh" "$name"
    fi
}

# Stop a container
stop_container() {
    local name=${1:-"claude-isolated-discord"}
    
    if docker ps --format "{{.Names}}" | grep -q "^$name$"; then
        print_status "Stopping container $name"
        docker stop "$name"
        print_success "Container $name stopped"
    else
        print_warning "Container $name is not running"
    fi
}

# Remove a container
remove_container() {
    local name=${1:-"claude-isolated-discord"}
    
    print_warning "This will permanently delete container $name"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop "$name" 2>/dev/null || true
        docker rm "$name" 2>/dev/null || true
        print_success "Container $name removed"
    else
        print_status "Operation cancelled"
    fi
}

# Execute command in container
exec_command() {
    local name=$1
    shift
    local command="$*"
    
    if [[ -z "$command" ]]; then
        print_error "No command provided"
        exit 1
    fi
    
    if ! docker ps --format "{{.Names}}" | grep -q "^$name$"; then
        print_error "Container $name is not running"
        exit 1
    fi
    
    print_status "Executing in $name: $command"
    docker exec -it "$name" $command
}

# Send Discord message
send_message() {
    local name=${1:-"claude-isolated-discord"}
    local message=${2:-"Test message from Claude Code container"}
    
    if ! docker ps --format "{{.Names}}" | grep -q "^$name$"; then
        print_error "Container $name is not running"
        exit 1
    fi
    
    print_status "Sending Discord message via $name"
    docker exec "$name" claude \
        --dangerously-skip-permissions \
        --print "Send this message to Discord: '$message'"
}

# Check container health
health_check() {
    local name=${1:-"claude-isolated-discord"}
    
    if ! docker ps --format "{{.Names}}" | grep -q "^$name$"; then
        print_error "Container $name is not running"
        return 1
    fi
    
    print_status "Health check for $name:"
    echo "================================"
    
    # Check Claude Code
    echo "🔍 Claude Code Version:"
    if docker exec "$name" claude --version 2>/dev/null; then
        print_success "Claude Code is working"
    else
        print_error "Claude Code is not working"
    fi
    
    echo ""
    echo "🔍 MCP Connection:"
    if docker exec "$name" claude mcp list 2>&1 | grep -q "Connected"; then
        print_success "MCP Discord is connected"
        docker exec "$name" claude mcp list | grep -E "(discord|Connected)"
    else
        print_error "MCP Discord connection failed"
    fi
    
    echo ""
    echo "🔍 Container Resources:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" "$name"
}

# Show logs
show_logs() {
    local name=${1:-"claude-isolated-discord"}
    local lines=${2:-50}
    
    print_status "Showing last $lines lines from $name"
    docker logs --tail "$lines" -f "$name"
}

# Show usage
show_usage() {
    echo "Claude Container Management Script"
    echo "=================================="
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  list                          List all Claude containers"
    echo "  start [name]                  Start container (default: claude-isolated-discord)"
    echo "  stop [name]                   Stop container"
    echo "  remove [name]                 Remove container (with confirmation)"
    echo "  exec <name> <command>         Execute command in container"
    echo "  message [name] [text]         Send Discord message via container"
    echo "  health [name]                 Run health check on container"
    echo "  logs [name] [lines]           Show container logs (default: 50 lines)"
    echo "  create [name]                 Create new container"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 start claude-isolated-discord"
    echo "  $0 message claude-isolated-discord 'Hello from container!'"
    echo "  $0 exec claude-isolated-discord bash"
    echo "  $0 health claude-isolated-discord"
    echo "  $0 logs claude-isolated-discord 100"
}

# Main command dispatcher
main() {
    setup_docker
    
    local command=${1:-"help"}
    shift || true
    
    case "$command" in
        list|ls)
            list_containers
            ;;
        start)
            start_container "$@"
            ;;
        stop)
            stop_container "$@"
            ;;
        remove|rm)
            remove_container "$@"
            ;;
        exec)
            exec_command "$@"
            ;;
        message|msg)
            send_message "$@"
            ;;
        health|check)
            health_check "$@"
            ;;
        logs)
            show_logs "$@"
            ;;
        create)
            "$SCRIPT_DIR/start_claude_container.sh" "$@"
            ;;
        help|-h|--help)
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"