# Tauri 2 Linux build environment for dsh-app.
# Debian-based so the Tauri docs' apt package names apply verbatim,
# plus Node 22 + pnpm 11 for the upstream deepseek-harness monorepo.

FROM mcr.microsoft.com/devcontainers/base:bookworm

# Tauri 2 system dependencies (Linux) + tools used by CI and local builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      wget \
      file \
      libxdo-dev \
      libssl-dev \
      libgtk-3-dev \
      libwebkit2gtk-4.1-dev \
      libayatana-appindicator3-dev \
      librsvg2-dev \
      libdbus-1-dev \
      patchelf \
    && rm -rf /var/lib/apt/lists/*

# Node 22 (matches upstream's engines field) + pnpm 11 (matches packageManager)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g pnpm@11 \
    && rm -rf /var/lib/apt/lists/*

# Rust (stable) with the common Tauri components, as the default user
RUN su vscode -c "rustup toolchain install stable --profile minimal --component clippy rustfmt && rustup default stable"

# Tauri CLI in the user's cargo home
RUN su vscode -c "cargo install tauri-cli --locked --version ^2.0"
