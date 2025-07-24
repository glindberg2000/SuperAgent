FROM node:20

ARG TZ
ENV TZ="$TZ"

# Install basic development tools and iptables/ipset
RUN apt update && apt install -y less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  curl \
  wget

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
  chown -R node:node /usr/local/share

ARG USERNAME=node

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# Create workspace and config directories and set permissions
RUN mkdir -p /home/node/workspace /home/node/.claude && \
  chown -R node:node /home/node/workspace /home/node/.claude

WORKDIR /home/node/workspace

RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/0.18.2/git-delta_0.18.2_${ARCH}.deb" && \
  sudo dpkg -i "git-delta_0.18.2_${ARCH}.deb" && \
  rm "git-delta_0.18.2_${ARCH}.deb"

# Set up non-root user
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Set the default shell to zsh rather than sh
ENV SHELL=/usr/bin/zsh

# Install UV and MCP Discord dependencies for the node user
USER root
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    python3 -m pip install --break-system-packages discord.py mcp python-dotenv
ENV PATH="/root/.local/bin:$PATH"
USER node
ENV PATH="/root/.local/bin:$PATH"

CMD ["/bin/bash"]