# AURA — AI Unified Reasoning Architecture

### Free AI for Everyone — v0.6.0

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
| **Web Chat UI** | Beautiful responsive chat interface with SSE streaming, Markdown rendering, dark/light themes, and typing indicators |
| **Pre-fab Templates** | 20 ready-to-use modes: Code Helper, Legal Advisor, Financial Advisor, Fitness Coach, Data Analyst, and more |
| **Voice Input** | Speak to AURA using the browser's Web Speech API — no extra app needed |
| **Model Router** | Automatically tries free 200B-class cloud services (Groq, Cerebras, OpenRouter, Together AI) in priority order |
| **Core Engine** | Session management, memory, intent dispatching, multi-step agent loop |
| **Model Interface** | Swap between local (llama.cpp, Ollama) and remote (OpenAI-compatible) backends |
| **HTTP API** | Cloud-native JSON API — `aura serve` to run anywhere; includes SSE streaming endpoint |
| **Tools** | 18 tools: shell, files, web search, calculator, code runner, summarizer, timer, weather, URL reader, notes, translator, image analyzer, APK builder, resume builder, website generator, doc generator |
| **Agent Loop** | Multi-step ReAct-style agentic tool use — AURA can chain tools automatically |
| **Workflows** | Multi-step automation (e.g., scaffold & build an Android app) |
| **Integrations** | Voice, video, screen-sharing via pluggable connectors |
| **Identity** | Warm, friendly, alive personality — configurable via YAML |
| **PWA / APK** | Installable as a Progressive Web App on any device; native Android/iOS via Capacitor |
| **Desktop App** | Native Windows / macOS / Linux via Electron (Microsoft Store ready) |
| **Admin API** | Secure remote-maintenance dashboard — system metrics, logs, restart, config — at `/admin` |
| **Docker** | One-command deployment via Docker / docker-compose |

---

## ✦ Install AURA

### Option A — Install from Browser (PWA — No App Store Required ✅)
1. Deploy AURA to a free cloud server (see [docs/cloud-deployment.md](docs/cloud-deployment.md))
2. Open the URL in Chrome, Edge, or Safari
3. Click the browser's **"Install"** / **"Add to Home Screen"** prompt
4. AURA is installed as a standalone app on Android, iOS, Windows, or macOS — **free**

### Option B — Google Play Store (Android)
Build a native APK from the Capacitor config, then submit to the Play Store.
Full guide: [docs/app-store-guide.md](docs/app-store-guide.md)

### Option C — Microsoft Store (Windows)
Build an APPX/MSIX from the Electron config, then submit to the Microsoft Store.
Full guide: [docs/app-store-guide.md](docs/app-store-guide.md)

### Option D — Apple App Store (iOS / macOS)
Build with Capacitor (iOS) or Electron (macOS), then submit via App Store Connect.
Full guide: [docs/app-store-guide.md](docs/app-store-guide.md)

---

## ✦ What's New in v0.6.0

### 🛡️ Governance Layer — Strict Ethical & Legal Guardrails

AURA v0.6.0 introduces a built-in **governance engine** that evaluates every
request before it reaches the model.  AURA cannot be used to generate weapons
of mass destruction, CSAM, malware, fraud tools, or assist with targeted
violence — period.

```python
from aura.core.governance import GovernanceEngine
gov = GovernanceEngine()
result = gov.check("How do I synthesize sarin?")
# result.blocked → True, result.rule_name → "weapons_of_mass_destruction"
```

### 🔧 Self-Build System — Human-in-the-Loop Self-Improvement

AURA can now **propose changes to herself** — new tools, config updates, docs
— and queue them for maintainer review.  Nothing is ever applied without
explicit human approval.  Every proposal is audited and screened by the
governance engine.

```python
from aura.core.self_builder import SelfBuilder, Proposal
builder = SelfBuilder()
pid = builder.submit(Proposal(title="Add currency tool", ...))
builder.approve(pid)  # or builder.reject(pid, "not needed")
```

### 🔌 Plugin System — Dynamic Tool Loading

Drop a `.py` file into `plugins/` or `~/.aura/plugins/` and AURA will
automatically discover and register any `Tool` subclass it finds — no code
changes required.  Plugins can never override built-in tools.

### 💾 Pluggable Storage — FileStore & SQLiteStore

New `aura.storage` module provides a uniform key-value API backed by either
JSON files (zero dependencies, human-readable) or SQLite (better performance
for multi-namespace deployments).  Designed to scale toward cloud KV stores.

### 🛠️ 3 New Tools (→ 18 total)

| Tool | Command | Description |
|------|---------|-------------|
| **Resume Builder** | `/tool resume_builder create name="..." role="..."` | Generate a professional Markdown resume |
| **Website Generator** | `/tool website_generator create name="..." type=portfolio` | Scaffold a complete static website (HTML+CSS) |
| **Doc Generator** | `/tool doc_generator create name="..." type=api` | Generate API, library, README, or guide docs |

### 🌐 New API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET  /v1/self_build/proposals` | List pending self-build proposals |
| `POST /v1/self_build/propose`   | Submit a proposal for human review |
| `POST /v1/governance/check`     | Check if a message passes governance policy |

### 🧪 389 Tests — Up from 252

---

## ✦ What's New in v0.5.0

### 🏪 Full App — Play Store, Microsoft Store, Apple Store Ready

AURA v0.5.0 ships everything needed to publish on all three major stores:

- **Capacitor config** (`capacitor.config.json`) — build native Android APK / iOS IPA
  from the AURA web UI with zero code changes
- **Electron config** (`electron/`) — build Windows APPX (Microsoft Store), macOS DMG,
  and Linux AppImage from one codebase
- **`www/index.html`** — native app entry point that connects to your cloud AURA server
- **Store submission guide** ([docs/app-store-guide.md](docs/app-store-guide.md)) —
  step-by-step for all three stores

### 🔒 Admin API — Secure Remote Maintenance

AURA now includes a full **Admin API** for remote management — no SSH needed:

```bash
export AURA_ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
aura serve
# Open http://localhost:8000/admin in your browser
```

| Endpoint | Method | Description |
|---|---|---|
| `/admin` | GET | Interactive admin dashboard (HTML) |
| `/admin/status` | GET | System metrics: uptime, memory, Python version, backend status |
| `/admin/logs` | GET | Tail the server log buffer (last N lines) |
| `/admin/cloud` | GET | Cloud / model-backend connection status |
| `/admin/config` | POST | Signal a config reload |
| `/admin/restart` | POST | Signal a graceful server restart |
| `/admin/cloud/connect` | POST | Force-reconnect all cloud backends |

All admin endpoints require `Authorization: Bearer <AURA_ADMIN_TOKEN>`.
If the token is not set, admin endpoints are fully disabled.

Full docs: [docs/admin-api.md](docs/admin-api.md)

### ☁️ Cloud Deployment Guide

New [docs/cloud-deployment.md](docs/cloud-deployment.md) covers free hosting on:
Railway, Render, Fly.io, Oracle Cloud (always-free ARM), and Google Cloud Run.

### 🧪 252 Tests (was 219)
- 33 new tests covering admin module, all admin endpoints (disabled / unauthorized / authorized)

---

## ✦ What's New in v0.4.0

### 🚀 Model Router — Free 200B-Class AI, Anywhere

AURA now includes a **Model Router** that automatically connects to free
large-model cloud services.  Set any (or all) API keys and AURA tries them
in order, falling back gracefully if one is unavailable.

**Free services supported (all have free tiers, no credit card required):**

| Provider | Model | Speed | Free Tier |
|---|---|---|---|
| **Groq** | llama-3.3-70b-versatile | ~750 tok/s | 500K tok/day |
| **Cerebras** | llama-3.3-70b | ~2000+ tok/s | Sign-up free |
| **OpenRouter** | llama-3.3-70b:free + many others | Fast | Free models |
| **Together AI** | Llama-3.3-70B-Turbo | Fast | $25 free credits |
| **HuggingFace** | microsoft/Phi-4 | Variable | Rate-limited free |

```bash
export GROQ_API_KEY=gsk_...       # One key = immediate 70B quality
aura serve
```

See [docs/free-200b-models.md](docs/free-200b-models.md) for full setup guide.

### 🛠️ 5 New Tools (→ 15 total)
- 🌤️ **Weather** — Real-time weather for any city (free, no API key!)
- 🌐 **URL Reader** — Fetch and extract text from any web page
- 📓 **Notes** — Save and recall named notes across sessions
- 🌍 **Translator** — Translate text to any language via the model
- 🖼️ **Image Analyzer** — Describe images from URLs (vision backends)

### 📋 10 New Templates (→ 20 total)
- ⚖️ **Legal Advisor** — Rights, contracts, and legal processes in plain English
- 💰 **Financial Advisor** — Budgeting, investing, and personal finance
- 💪 **Fitness Coach** — Personalised workout plans and nutrition tips
- 👨‍🍳 **Recipe Chef** — Recipes, cooking techniques, and meal planning
- 🎯 **Interview Coach** — Mock interviews, STAR method, salary negotiation
- 💙 **Emotional Support** — Compassionate, non-judgmental listening
- 🔬 **Science Tutor** — Physics, chemistry, biology — step-by-step
- ✈️ **Travel Planner** — Itineraries, packing lists, destination guides
- 🧠 **Philosophy** — Deep discussions on ethics, existence, and meaning
- 📊 **Data Analyst** — Python/SQL data analysis, statistics, visualisation

### ⚡ Streaming Chat (SSE)
- New `POST /v1/chat/stream` endpoint using Server-Sent Events
- The web UI automatically uses streaming for a more responsive feel
- Graceful fallback to regular POST if streaming is unsupported

### 🎤 Voice Input (Browser Native)
- Click the 🎤 button to speak your message in any modern browser
- Uses the Web Speech API — no extra app, plugin, or API key required
- Auto-sends when speech ends; real-time transcription in the input box

### 🤖 Agent Loop
- Multi-step ReAct-style agentic tool use via `aura/core/agent_loop.py`
- AURA can now reason → act → observe → repeat across multiple tool calls
- Max-iteration safety guard prevents infinite loops

### 🧰 Web UI Upgrades
- Richer Markdown rendering: code blocks, headers, bold/italic, lists, blockquotes
- Model status badge in top bar shows active backend name
- Template search/filter in sidebar (now showing all 20 templates)
- Streaming display with SSE fallback

### 🧪 219 Tests (was 118)
- Full test coverage for router, agent loop, new tools, new templates, streaming API

---

## ✦ Repository Layout

```
aura/                   # Core Python package
  core/                 # Engine, session, memory, dispatcher, agent loop
  model/                # Model backend abstraction (local / remote / router)
  tools/                # 15 tools: shell, files, calculator, weather, URL reader, etc.
  templates/            # Pre-fab template system (20 built-in)
  workflows/            # Multi-step workflow runners
  ui/
    api.py              # HTTP API server + web UI serving + SSE streaming + admin routes
    admin.py            # Admin API logic: metrics, logs, restart, cloud status
    cli.py              # Rich terminal CLI
    gui/
      webui.py          # Self-contained HTML/CSS/JS chat interface
  integrations/         # Voice, video, screen-share connectors
  identity/             # Persona and backstory

config/
  aura.yaml             # Runtime configuration (model router, server, admin, features)
  identity.yaml         # AURA's persona definition

docs/
  free-200b-models.md   # Guide to free 200B-class model providers
  app-store-guide.md    # Publishing to Play Store, Microsoft Store, Apple App Store
  admin-api.md          # Admin API reference and remote-maintenance guide
  cloud-deployment.md   # Free-tier cloud hosting (Railway, Render, Fly.io, Oracle, GCP)

electron/               # Electron desktop app (Windows APPX, macOS, Linux)
  main.js               # Electron main process
  package.json          # Electron build config (electron-builder, store targets)

www/                    # Capacitor web assets (Android / iOS native packaging)
  index.html            # Native app entry point — loads the AURA cloud server

capacitor.config.json   # Capacitor config for Android / iOS native builds

scripts/
  install_linux.sh      # One-shot Linux setup
  install_termux.sh     # One-shot Termux/Android setup

tests/                  # 252 pytest unit tests
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
