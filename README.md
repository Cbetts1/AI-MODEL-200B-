# AURA — AI Unified Reasoning Architecture
# ==========================================
# A highly personalized, modular AI assistant targeting up to 200B parameters.
# Designed for AURA-VoS-Vcpu (AI-native OS concept).
# Portable: Linux & Termux (Android).

---

## ✦ What is AURA?

AURA (**AI Unified Reasoning Architecture**) is a modular, self-contained AI assistant
built for deep personalization, tool use, and workflow orchestration.

| Capability | Description |
|---|---|
| **Core Engine** | Session management, memory, intent dispatching |
| **Model Interface** | Swap between local (llama.cpp, Ollama) and remote (OpenAI-compatible) backends |
| **Tools** | Shell, file I/O, web search, APK builder, extensible registry |
| **Workflows** | Multi-step automation (e.g., scaffold & build an Android app) |
| **Integrations** | Voice, video, screen-sharing via pluggable connectors |
| **Identity** | Consistent persona and backstory configurable via YAML |
| **UI** | Rich CLI today; GUI-ready architecture for tomorrow |

---

## ✦ Repository Layout

```
aura/                   # Core Python package
  core/                 # Engine, session, memory, dispatcher
  model/                # Model backend abstraction (local / remote)
  tools/                # Individual callable tools + registry
  workflows/            # Multi-step workflow runners
  ui/                   # CLI (+ future GUI placeholder)
  integrations/         # Voice, video, screen-share connectors
  identity/             # Persona and backstory

config/
  aura.yaml             # Runtime configuration (model, paths, features)
  identity.yaml         # AURA's persona definition

scripts/
  install_linux.sh      # One-shot Linux setup
  install_termux.sh     # One-shot Termux/Android setup

tests/                  # pytest unit tests
docs/                   # Architecture and usage documentation

setup.py                # pip-installable package
requirements.txt        # Python dependencies
```

---

## ✦ Quick Start (Linux)

```bash
# 1. Clone
git clone https://github.com/Cbetts1/AI-MODEL-200B-.git && cd AI-MODEL-200B-

# 2. Install
pip install -e .

# 3. Run CLI
aura chat
```

## ✦ Quick Start (Termux / Android)

```bash
bash scripts/install_termux.sh
aura chat
```

---

## ✦ Configuration

Edit `config/aura.yaml` to choose your model backend:

```yaml
model:
  backend: local          # "local" | "remote"
  local:
    engine: llamacpp      # llamacpp | ollama
    model_path: models/weights/model.gguf
  remote:
    base_url: http://localhost:11434/v1
    api_key: ""
    model_name: llama3
```

---

## ✦ Roadmap

- [x] Modular repo scaffold
- [x] Core engine with session & memory
- [x] Pluggable model backend (local + remote)
- [x] Tool registry with built-in tools
- [x] CLI interface
- [ ] GUI (web-based or Qt)
- [ ] Voice I/O integration
- [ ] APK auto-build pipeline
- [ ] Fine-tuned 200B-parameter model

---

> "AURA isn't just a chatbot. It's a reasoning layer built into your OS."
