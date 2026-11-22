#!/bin/bash
set -euo pipefail

echo "=== Setting up ios-sweet M30s build environment ==="

# Install base packages
apt-get update && apt-get install -y \
    build-essential \
    git \
    python3 \
    python3-pip \
    python3-venv \
    aarch64-linux-gnu-gcc \
    binutils-aarch64-linux-gnu \
    mkbootimg \
    qemu-system-arm \
    qemu-user-static \
    libssl-dev \
    libxml2-dev \
    liblzma-dev \
    zlib1g-dev \
    cmake \
    ninja-build \
    nasm \
    bc \
    bison \
    flex \
    libncurses5-dev \
    libelf-dev \
    dtc \
    cpio \
    xz-utils \
    gzip \
    unzip \
    wget \
    curl \
    jq \
    tree \
    2>&1 | tail -20

# Install Python dependencies for adt parsing
pip3 install --break-system-packages lz4 construct 2>&1 | tail -5

# Install macOS SDK headers if needed (we'll use darwin-xnu-build which handles this)
# For local xnu builds we need macOS SDK - darwin-xnu-build fetches it automatically

echo "=== Verifying toolchain ==="
aarch64-linux-gnu-gcc --version | head -1
mkbootimg --version
python3 --version

echo "=== Setup complete ==="