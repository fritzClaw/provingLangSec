# Self-contained environment: pinned Dafny + Z3, Python, a C compiler (for the SQLite oracle),
# and Claude Code. Builds natively on x86_64 and arm64 (Apple Silicon).
# BASE_IMAGE exists only so that networks with a TLS-intercepting proxy can inject their CA.
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git make gcc libc6-dev unzip python3 sudo nodejs npm dotnet-sdk-8.0 \
    && rm -rf /var/lib/apt/lists/*

# Pinned verification toolchain (versions and hashes: tools/versions.env)
COPY tools/versions.env /tmp/provinglangsec/tools/versions.env
COPY tools/install/install-toolchain.sh /tmp/provinglangsec/tools/install/install-toolchain.sh
RUN PREFIX=/opt/provinglangsec sh /tmp/provinglangsec/tools/install/install-toolchain.sh \
    && rm -rf /tmp/provinglangsec

# Claude Code, pinned to the version the agent harness was written against
RUN npm install -g @anthropic-ai/claude-code@2.1.295 && npm cache clean --force

ENV DOTNET_ROOT=/usr/lib/dotnet \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    GATE_DAFNY=/opt/provinglangsec/dotnet-tools/dafny \
    GATE_Z3=/opt/provinglangsec/z3/bin/z3 \
    PATH=/opt/provinglangsec/dotnet-tools:/opt/provinglangsec/z3/bin:$PATH

# Ubuntu 24.04 ships a non-root user "ubuntu" (uid 1000)
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu
USER ubuntu
WORKDIR /workspaces/provingLangSec
