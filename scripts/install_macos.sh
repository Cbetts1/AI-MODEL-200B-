#!/usr/bin/env bash
# scripts/install_macos.sh — One-shot AURA setup for macOS.
#
# What this script does:
#   1. Installs Homebrew if not already present
#   2. Installs Python 3.11 via Homebrew
#   3. Creates a virtual environment in .venv/
#   4. Installs Python dependencies
#   5. Installs the `aura` package in editable mode
#   6. Prints next steps
#
# Usage:
#   bash scripts/install_macos.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

echo "======================================================"
echo "  AURA — macOS Setup"
echo "======================================================"

# ── Homebrew ───────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "Homebrew not found — installing…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon and Intel Macs
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "Homebrew already installed: $(brew --version | head -1)"
fi

# ── Python ─────────────────────────────────────────────────────────────────────
PYTHON_BIN=""
for candidate in python3.11 python3.12 python3.10 python3; do
    if command -v "${candidate}" &>/dev/null; then
        PYTHON_BIN="${candidate}"
        break
    fi
done

if [[ -z "${PYTHON_BIN}" ]]; then
    echo "Python 3.10+ not found — installing via Homebrew…"
    brew install python@3.11
    PYTHON_BIN="python3.11"
fi

echo "Using Python: $(${PYTHON_BIN} --version)"

# ── Virtual environment ────────────────────────────────────────────────────────
if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtual environment at ${VENV_DIR} …"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
    echo "Virtual environment already exists at ${VENV_DIR}."
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip…"
pip install --quiet --upgrade pip

echo "Installing Python dependencies…"
pip install --quiet -r "${REPO_DIR}/requirements.txt"

echo "Installing AURA package (editable mode)…"
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
echo "  2. Edit the config (optional — defaults are fine):"
echo "     open config/aura.yaml"
echo ""
echo "  3. Set a free API key to unlock 200B-class AI:"
echo "     export GROQ_API_KEY=gsk_...   # https://console.groq.com (free)"
echo ""
echo "  4. Start chatting:"
echo "     aura chat"
echo ""
echo "  5. Or launch the full web UI:"
echo "     aura serve    # open http://localhost:8000"
echo ""
echo "  For the native macOS desktop app:"
echo "     cd electron && npm install && npm start"
echo ""
echo "  For iOS / iPadOS (PWA — no App Store required):"
echo "     Deploy to a free cloud server, then open in Safari and"
echo "     tap Share → 'Add to Home Screen'."
echo "     Full guide: docs/app-store-guide.md"
echo ""
