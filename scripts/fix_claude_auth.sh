#!/bin/bash
# Fix Claude Code authentication by removing API key from running containers
# This preserves existing authentication while removing the interfering API key

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to remove API key from running container
fix_container_auth() {
    local container_name=$1
    
    print_status "Fixing Claude Code authentication in container: $container_name"
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        print_error "Container $container_name is not running"
        return 1
    fi
    
    # Check if API key is set
    if docker exec "$container_name" printenv ANTHROPIC_API_KEY >/dev/null 2>&1; then
        print_warning "ANTHROPIC_API_KEY found in container - this interferes with Claude Code subscription auth"
        
        # Test current Claude Code status
        print_status "Testing current Claude Code status..."
        if docker exec "$container_name" claude --version >/dev/null 2>&1; then
            print_success "Claude Code is available"
            
            # Test execution
            if docker exec "$container_name" bash -c "unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions --print 'Auth test'" >/dev/null 2>&1; then
                print_success "Claude Code authentication is working without API key"
            else
                print_warning "Claude Code needs re-authentication"
                print_status "The userID is preserved, so re-authentication should be possible"
            fi
        else
            print_error "Claude Code is not responding"
        fi
        
        # Create a startup script that unsets the API key
        print_status "Creating startup script to remove API key interference..."
        docker exec "$container_name" bash -c 'cat > /home/node/fix_claude_auth.sh << "EOF"
#!/bin/bash
# Remove ANTHROPIC_API_KEY to allow Claude Code subscription authentication
unset ANTHROPIC_API_KEY
exec "$@"
EOF'
        
        docker exec "$container_name" chmod +x /home/node/fix_claude_auth.sh
        
        print_success "Container $container_name authentication fix prepared"
        print_status "To use Claude Code in this container, run commands like:"
        print_status "  docker exec $container_name bash -c 'unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions --print \"Your message\"'"
        
    else
        print_success "No ANTHROPIC_API_KEY found in container $container_name - authentication should work properly"
    fi
    
    # Test MCP connection
    print_status "Testing MCP Discord connection..."
    if docker exec "$container_name" claude mcp list 2>&1 | grep -q "Connected"; then
        print_success "MCP Discord connection is working"
    else
        print_warning "MCP connection may need attention"
    fi
}

# Main function
main() {
    print_status "🔧 FIXING CLAUDE CODE AUTHENTICATION IN RUNNING CONTAINERS"
    echo "============================================================"
    print_status "This script removes API key interference without destroying containers"
    echo ""
    
    # Get list of Claude containers
    containers=$(docker ps --filter "name=claude" --format "{{.Names}}" | grep -E "(claude-|fullstack|isolated)" || true)
    
    if [ -z "$containers" ]; then
        print_error "No running Claude containers found"
        exit 1
    fi
    
    print_status "Found Claude containers: $containers"
    echo ""
    
    # Fix each container
    for container in $containers; do
        fix_container_auth "$container"
        echo ""
    done
    
    print_success "🎉 Authentication fix completed for all containers"
    echo ""
    echo "Next steps:"
    echo "1. Test Claude Code: docker exec CONTAINER_NAME bash -c 'unset ANTHROPIC_API_KEY && claude --version'"
    echo "2. If authentication is lost, you'll need to re-authenticate once more"
    echo "3. Future containers created with the fixed start_claude_container.sh won't have this issue"
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [container_name]"
        echo ""
        echo "Fix Claude Code authentication by removing API key interference"
        echo ""
        echo "Options:"
        echo "  container_name    Fix specific container (optional - fixes all if not specified)"
        echo ""
        echo "Examples:"
        echo "  $0                                    # Fix all Claude containers"
        echo "  $0 claude-fullstackdev-persistent    # Fix specific container"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        fix_container_auth "$1"
        ;;
esac