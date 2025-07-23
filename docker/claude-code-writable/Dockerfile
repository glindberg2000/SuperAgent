FROM deepworks/claude-code:latest

# Switch to root to fix permissions and install properly
USER root

# Give coder user full access to modify global npm installations
RUN chown -R coder:coder /usr/local/lib/node_modules && \
    chown -R coder:coder /usr/local/bin && \
    chmod -R 755 /usr/local/lib/node_modules && \
    chmod -R 755 /usr/local/bin

# Create and set proper permissions for Claude directories
RUN mkdir -p /home/coder/.claude/projects && \
    mkdir -p /home/coder/.claude/shell-snapshots && \
    mkdir -p /home/coder/.claude/todos && \
    mkdir -p /home/coder/.claude/statsig && \
    mkdir -p /home/coder/.claude/ide && \
    mkdir -p /home/coder/.claude/local && \
    chown -R coder:coder /home/coder/.claude && \
    chmod -R 755 /home/coder/.claude

# Switch back to coder user
USER coder
WORKDIR /home/coder/project

# Set up shell with proper PATH
RUN echo 'export PATH="/home/coder/.claude/local:$PATH"' >> ~/.bashrc && \
    echo 'alias claude-local="/home/coder/.claude/local/claude"' >> ~/.bashrc

# Note: Manual authentication still required after building
RUN echo "Container ready for authentication. Run 'claude login' to authenticate with Max plan." > /home/coder/README_AUTH.txt

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["/bin/bash"]