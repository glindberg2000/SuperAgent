FROM deepworks/claude-code:latest

# Copy OAuth token from host (you'll need to provide this during build)
# This assumes you've logged in on the host and have the token
ARG OAUTH_TOKEN_PATH
COPY ${OAUTH_TOKEN_PATH} /home/coder/.claude/oauth_token.json

# Set proper permissions
RUN chown -R coder:coder /home/coder/.claude && \
    chmod 600 /home/coder/.claude/oauth_token.json

# The base image already has Claude Code installed
USER coder
WORKDIR /home/coder/project

# Verify Claude Code is authenticated
RUN claude config get auth.type || echo "Auth not configured"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["claude"]