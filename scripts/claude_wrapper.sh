#!/bin/bash
# Claude Code Wrapper - Removes API key interference and runs Claude with subscription auth
# This script ensures Claude Code uses subscription authentication instead of API mode

# Remove the interfering API key that forces Claude into API mode
unset ANTHROPIC_API_KEY

# Execute Claude Code with all passed arguments
exec /usr/local/share/npm-global/bin/claude "$@"