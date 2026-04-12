#!/usr/bin/env bash
# scripts/install_linux.sh — One-shot AURA setup for Linux.
#
# What this script does:
#   1. Checks for Python 3.9+
#   2. Creates a virtual environment in .venv/
#   3. Installs Python dependencies
#   4. Installs the `aura` package in editable mode
#   5. Prints next steps
#
# Usage:
#   bash scripts/install_linux.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

echo "======================================================"
echo "  AURA — Linux Setup"
echo "======================================================"

# ── Check Python version ───────────────────────────────────────────────────────
PYTHON_BIN="python3"
if ! command -v "${PYTHON_BIN}" &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.9+ and rerun."
    exit 1
fi

PYTHON_VER="$("${PYTHON_BIN}" -c 'import sys; print(sys.version_info[:2])')"
echo "Found Python: $("${PYTHON_BIN}" --version)"

# ── Create virtual environment ─────────────────────────────────────────────────
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtual environment at ${VENV_DIR} ..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
    echo "Virtual environment already exists at ${VENV_DIR}."
fi

# ── Activate and install ───────────────────────────────────────────────────────
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
pip install --quiet --upgrade pip

echo "Installing Python dependencies..."
pip install --quiet -r "${REPO_DIR}/requirements.txt"

echo "Installing AURA package (editable mode)..."
pip install --quiet -e "${REPO_DIR}"

echo ""
echo "======================================================"
echo "  Installation complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Edit the config file:"
echo "     \$EDITOR config/aura.yaml"
echo ""
echo "  3. Start chatting:"
echo "     aura chat"
echo ""
