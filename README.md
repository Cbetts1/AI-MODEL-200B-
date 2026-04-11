# AURA — AI Unified Reasoning Architecture

### Free AI for Everyone — v0.3.0

> Designed and founded by **Christopher Betts**.
> The core mission: **make AI and its services free to the public**.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## ✦ Mission

AURA exists to **change lives, save lives, and help millions**.

AI should not be locked behind paywalls or branded to a single public figure.
AURA is free, open-source, and community-driven — built so that anyone,
anywhere, can benefit from intelligent assistance regardless of means,
location, or background.

---

## ✦ What is AURA?

AURA (**AI Unified Reasoning Architecture**) is a modular, cloud-native AI
assistant built for tool use, workflow orchestration, and deep
personalisation.  It is **not constrained to a single device** — AURA runs
on your laptop, a phone, a cloud server, or embedded in a web page.  It
travels where it is needed and calls home wherever it sets up.

**The model runs remotely — your device stays lightweight.**  Access AURA
from any browser, APK, or API call.  Zero burden on your phone or laptop.

| Capability | Description |
|---|---|
| **Web Chat UI** | Beautiful responsive chat interface with dark/light themes, typing indicators, and message bubbles |
| **Pre-fab Templates** | 10+ ready-to-use modes: Code Helper, Writing Assistant, Math Tutor, Health Advisor, Business Planner, and more |
| **Video / Voice / Screen** | Communication buttons (WebRTC-ready) for future real-time calls |
| **Core Engine** | Session management, memory, intent dispatching |
| **Model Interface** | Swap between local (llama.cpp, Ollama) and remote (OpenAI-compatible) backends |
| **HTTP API** | Cloud-native JSON API — `aura serve` to run anywhere on the network |
| **Tools** | Shell, file I/O, web search, calculator, code runner, summarizer, timer, APK builder |
| **Workflows** | Multi-step automation (e.g., scaffold & build an Android app) |
| **Integrations** | Voice, video, screen-sharing via pluggable connectors |
| **Identity** | Warm, friendly, alive personality — configurable via YAML |
| **PWA / APK** | Installable as a Progressive Web App on any device |
| **Docker** | One-command deployment via Docker / docker-compose |

---

## ✦ What's New in v0.3.0

🚀 **Web Chat Interface** — Full responsive chat UI served from the API server
- Chat bubbles with typing animation and timestamps
- Dark / light theme toggle
- Video call, voice call, screen share buttons
- Welcome screen with quick-action cards
- PWA-installable on any device (add to home screen)
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)

📋 **Pre-fab Templates** — 10 ready-to-use specializations
- 💻 Code Helper — Write, debug, and improve code
- ✍️ Writing Assistant — Essays, emails, reports, stories
- 🔢 Math Tutor — Patient step-by-step explanations
- 🏥 Health & Wellness Advisor — General wellness guidance
- 📊 Business Planner — Strategy and planning
- 📚 Study Buddy — Quizzes, flashcards, explanations
- 🎭 Creative Writer — Stories, poetry, scripts
- 📅 Daily Planner — Tasks, goals, productivity
- 🌍 Language Tutor — Conversation practice
- 🔧 Tech Support — Troubleshooting and fixes

🛠️ **New Tools** — Real-world problem solvers
- 🔢 Calculator — Safe math expression evaluator
- 💻 Code Runner — Execute Python snippets
- 📝 Summarizer — Extract key sentences from text
- ⏱️ Timer — Set and check countdown timers

✨ **Alive Personality** — Warm, friendly, responsive AURA persona

---

## ✦ Repository Layout

```
aura/                   # Core Python package
  core/                 # Engine, session, memory, dispatcher
  model/                # Model backend abstraction (local / remote)
  tools/                # Tools: shell, files, calculator, code runner, etc.
  templates/            # Pre-fab template system (10+ built-in)
  workflows/            # Multi-step workflow runners
  ui/
    api.py              # HTTP API server + web UI serving
    cli.py              # Rich terminal CLI
    gui/
      webui.py          # Self-contained HTML/CSS/JS chat interface
  integrations/         # Voice, video, screen-share connectors
  identity/             # Persona and backstory

config/
  aura.yaml             # Runtime configuration (model, server, features)
  identity.yaml         # AURA's persona definition

scripts/
  install_linux.sh      # One-shot Linux setup
  install_termux.sh     # One-shot Termux/Android setup

tests/                  # 118 pytest unit tests
docs/                   # Architecture, deployment, and usage docs

Dockerfile              # Container image for cloud deployment
docker-compose.yaml     # One-command cloud deployment

setup.py                # pip-installable package
requirements.txt        # Python dependencies
LICENSE                 # Apache 2.0 — free for everyone
CONTRIBUTING.md         # How to contribute
CODE_OF_CONDUCT.md      # Community standards
```

---

## ✦ Quick Start (Linux)

```bash
# 1. Clone
git clone https://github.com/Cbetts1/AI-MODEL-200B-.git && cd AI-MODEL-200B-

# 2. Install
pip install -e .

# 3. Run the Web UI (open http://localhost:8000 in your browser)
aura serve

# Or use the CLI
aura chat
```

## ✦ Quick Start (Termux / Android)

```bash
bash scripts/install_termux.sh
aura serve    # then open http://localhost:8000 in your browser
```

## ✦ Quick Start (Docker — run anywhere)

```bash
docker compose up --build
# AURA Web UI is now live at http://localhost:8000
```

---

## ✦ Cloud / Web Deployment

AURA is cloud-native.  Run it as an HTTP API server so any web page, app, or
device on the network can talk to it.  **The web chat UI is served at the
root URL** — just open your browser!

```bash
# Start the server with web UI
aura serve                      # default: 0.0.0.0:8000
aura serve --port 9090          # custom port
aura serve --host 127.0.0.1    # localhost only
```

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | **Web Chat Interface** — open in any browser |
| `POST` | `/v1/chat` | Send a message, receive a reply |
| `GET` | `/v1/templates` | List available pre-fab templates |
| `POST` | `/v1/template` | Activate a template |
| `GET` | `/v1/health` | Health check / readiness probe |
| `GET` | `/v1/tools` | List available tools |
| `GET` | `/v1/version` | AURA version |

**Example — talk to AURA from any web page:**

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, AURA!"}'
```

See [docs/deployment.md](docs/deployment.md) for Docker, cloud, and
production deployment details.

---

## ✦ Pre-fab Templates

Use templates to instantly specialise AURA for your task:

```bash
# In the CLI
aura chat
> /template list
> /template use code_helper

# Via the API
curl -X POST http://localhost:8000/v1/template \
  -H "Content-Type: application/json" \
  -d '{"template": "math_tutor"}'
```

Or click any template card in the web UI sidebar!

---

## ✦ Configuration

Edit `config/aura.yaml` to choose your model backend:

```yaml
model:
  backend: remote         # "echo" | "local" | "remote"
  preset: max             # small | medium | large | max
  local:
    engine: llamacpp      # llamacpp | ollama
    model_path: models/weights/model.gguf
  remote:
    base_url: http://localhost:11434/v1
    api_key: ""
    model_name: llama3
```

---

## ✦ Contributing

AURA is a community project.  Contributions of all kinds are welcome — code,
docs, bug reports, ideas.  See [CONTRIBUTING.md](CONTRIBUTING.md) for
guidelines.

---

## ✦ Roadmap

- [x] Modular repo scaffold
- [x] Core engine with session & memory
- [x] Pluggable model backend (local + remote)
- [x] Tool registry with built-in tools (10 tools)
- [x] CLI interface
- [x] HTTP/JSON API server (cloud-native)
- [x] Docker deployment
- [x] **Web Chat Interface** — responsive, beautiful, PWA-ready
- [x] **Pre-fab templates** — 10 ready-to-use specializations
- [x] **New tools** — calculator, code runner, summarizer, timer
- [x] **Enhanced persona** — warm, friendly, alive personality
- [x] Open-source license (Apache 2.0)
- [x] Community guidelines (CONTRIBUTING, CODE_OF_CONDUCT)
- [ ] WebRTC voice / video calls
- [ ] Screen sharing with OCR
- [ ] APK auto-build pipeline
- [ ] Fine-tuned 200B-parameter model
- [ ] Multi-user session management
- [ ] Plugin marketplace

---

## ✦ License

AURA is licensed under the [Apache License 2.0](LICENSE) — free to use,
modify, and distribute.

---

> "AURA isn't just a chatbot.  It's a reasoning layer that belongs to
> everyone — free, open, and built to help millions."
>
> — Christopher Betts, Designer & Founder
