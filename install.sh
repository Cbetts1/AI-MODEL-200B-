#!/usr/bin/env bash
# install.sh — AURA universal one-shot installer.
#
# Detects your platform and runs the correct setup script automatically.
#
# Supported platforms
#   Linux (Ubuntu, Debian, Fedora, Arch, etc.)
#   macOS (Homebrew required — installed automatically if missing)
#   Termux / Android (run inside the Termux terminal app)
#
# Usage — paste one line into your terminal:
#
#   bash install.sh
#
# Or using curl:
#
#   curl -fsSL https://raw.githubusercontent.com/Cbetts1/AI-MODEL-200B-/main/install.sh | bash
#
# After installation:
#   source .venv/bin/activate     # Linux / macOS
#   aura serve                    # starts the web UI at http://localhost:8000
#
# For iOS / iPadOS:
#   Deploy AURA to any cloud server (Render, Railway, Fly.io — all free tiers).
#   Then open the URL in Safari and tap Share → "Add to Home Screen".
#   AURA installs as a PWA with a native app icon — no App Store required.
#   Full guide: docs/app-store-guide.md

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="${REPO_DIR}/scripts"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}${BOLD}[AURA]${RESET} $*"; }
success() { echo -e "${GREEN}${BOLD}[AURA]${RESET} $*"; }
error()   { echo -e "${RED}${BOLD}[AURA ERROR]${RESET} $*" >&2; exit 1; }

echo ""
echo -e "${BOLD}  ✦  AURA — AI Unified Reasoning Architecture  ✦${RESET}"
echo -e "     Free AI for Everyone — v0.7.0"
echo -e "     https://github.com/Cbetts1/AI-MODEL-200B-"
echo ""

# ── Detect platform ───────────────────────────────────────────────────────────
detect_platform() {
    # Termux sets PREFIX to /data/data/com.termux/...
    if [[ "${PREFIX:-}" == *termux* ]] || [[ "${TERMUX_VERSION:-}" != "" ]]; then
        echo "termux"
        return
    fi
    case "$(uname -s)" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        *)       echo "unknown" ;;
    esac
}

PLATFORM="$(detect_platform)"
info "Detected platform: ${PLATFORM}"

case "${PLATFORM}" in
    linux)
        info "Running Linux installer…"
        bash "${SCRIPT_DIR}/install_linux.sh"
        ;;
    macos)
        info "Running macOS installer…"
        bash "${SCRIPT_DIR}/install_macos.sh"
        ;;
    termux)
        info "Running Termux (Android) installer…"
        bash "${SCRIPT_DIR}/install_termux.sh"
        ;;
    *)
        error "Unsupported platform: $(uname -s).
  Supported platforms: Linux, macOS, Termux (Android).
  For iOS / iPadOS: deploy to a cloud server and open in Safari.
  See docs/app-store-guide.md for native iOS/Android packaging."
        ;;
esac
