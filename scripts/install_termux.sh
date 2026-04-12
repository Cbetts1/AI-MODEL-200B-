#!/usr/bin/env bash
# scripts/install_termux.sh — One-shot AURA setup for Termux (Android).
#
# Termux is a terminal emulator + Linux environment for Android.
# Install it from: https://f-droid.org/packages/com.termux/
#
# What this script does:
#   1. Updates Termux packages
#   2. Installs Python + build dependencies
#   3. Installs Python dependencies from requirements.txt
#   4. Installs the `aura` package in editable mode
#   5. Prints next steps
#
# Usage (inside Termux):
#   bash scripts/install_termux.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "======================================================"
echo "  AURA — Termux (Android) Setup"
echo "======================================================"

# ── Update packages ────────────────────────────────────────────────────────────
echo "Updating pkg repository..."
pkg update -y

echo "Installing required packages..."
# python  — Python 3 interpreter
# clang   — C compiler (needed to build llama-cpp-python from source)
pkg install -y python clang libffi openssl

# ── Upgrade pip ────────────────────────────────────────────────────────────────
echo "Upgrading pip..."
pip install --upgrade pip

# ── Install Python dependencies ────────────────────────────────────────────────
echo "Installing Python dependencies..."
pip install -r "${REPO_DIR}/requirements.txt"

# ── Install AURA package ───────────────────────────────────────────────────────
echo "Installing AURA package..."
pip install -e "${REPO_DIR}"

echo ""
echo "======================================================"
echo "  Installation complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "  1. Edit the config:"
echo "     nano config/aura.yaml"
echo ""
echo "  2. Start chatting:"
echo "     aura chat"
echo ""
echo "Optional — install a local model via Ollama:"
echo "  pkg install tur-repo && pkg install ollama"
echo "  ollama serve &"
echo "  ollama pull llama3"
echo "  # Then set model.backend: local, engine: ollama in config/aura.yaml"
echo ""
