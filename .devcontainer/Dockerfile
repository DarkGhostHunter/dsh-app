# Electron Desktop packaging environment for dsh-app.
# Debian-based so apt package names match CI's ubuntu runners closely,
# plus Node 22 + pnpm 11 for the upstream deepseek-harness monorepo.

FROM mcr.microsoft.com/devcontainers/base:bookworm

# Shared libraries the packaged Electron binaries need at build/smoke time
# (prepare-runtime and the packaged smoke test execute Electron directly),
# plus tools used by CI and local builds.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      wget \
      file \
      ca-certificates \
      git \
      libnspr4 \
      libnss3 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxfixes3 \
      libxrandr2 \
      libgbm1 \
      libasound2 \
      libpango-1.0-0 \
      libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Node 22 (matches upstream's engines field) + pnpm 11 (matches packageManager)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g pnpm@11 \
    && rm -rf /var/lib/apt/lists/*
