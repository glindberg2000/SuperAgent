FROM deepworks/claude-code:latest

# Create necessary directories with proper permissions
USER root
RUN mkdir -p /home/coder/.claude/projects && \
    mkdir -p /home/coder/.claude/shell-snapshots && \
    mkdir -p /home/coder/.claude/todos && \
    mkdir -p /home/coder/.claude/statsig && \
    mkdir -p /home/coder/.claude/ide && \
    chown -R coder:coder /home/coder/.claude

# Switch back to coder user
USER coder
WORKDIR /home/coder/project

# Note: OAuth authentication must be done manually after building
# Run: docker run -it <image> claude login
# Then commit the authenticated container as a new image

# Add a marker file to indicate this needs auth
RUN echo "This image needs manual OAuth authentication. Run 'claude login' to authenticate." > /home/coder/NEEDS_AUTH.txt

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["claude"]