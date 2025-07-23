#!/bin/bash
# Setup script to create pre-authenticated Claude Code container

echo "🔧 Creating pre-authenticated Claude Code container..."

# Start a container with interactive terminal
docker run -it \
  --name claude-auth-setup \
  -v /Users/greg/repos/SuperAgent:/workspace \
  -w /workspace \
  deepworks/claude-code:latest \
  /bin/bash -c "
    echo '📝 Setting up Claude Code authentication...'
    echo ''
    echo 'Please run the following commands inside the container:'
    echo '1. claude login'
    echo '2. Choose Pro/Max plan authentication'
    echo '3. Complete the OAuth flow'
    echo '4. Test with: claude --print \"Hello from authenticated Claude\"'
    echo '5. Exit the container when done'
    echo ''
    /bin/bash
  "

echo "✅ Authentication complete! Now creating image..."

# Commit the container as a new image
docker commit \
  --message "Pre-authenticated Claude Code with Max plan" \
  claude-auth-setup \
  superagent/claude-code-authenticated:latest

echo "🎉 Created authenticated image: superagent/claude-code-authenticated:latest"

# Clean up
docker rm claude-auth-setup

echo "✨ Done! You can now use this image in your orchestrator."