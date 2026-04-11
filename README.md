# AURA — AI Unified Reasoning Architecture

### Free AI for Everyone

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

| Capability | Description |
|---|---|
| **Core Engine** | Session management, memory, intent dispatching |
| **Model Interface** | Swap between local (llama.cpp, Ollama) and remote (OpenAI-compatible) backends |
| **HTTP API** | Cloud-native JSON API — `aura serve` to run anywhere on the network |
| **Tools** | Shell, file I/O, web search, APK builder, extensible registry |
| **Workflows** | Multi-step automation (e.g., scaffold & build an Android app) |
| **Integrations** | Voice, video, screen-sharing via pluggable connectors |
| **Identity** | Consistent persona and backstory configurable via YAML |
| **UI** | Rich CLI today; API server for web/cloud; GUI-ready architecture |
| **Docker** | One-command deployment via Docker / docker-compose |

---

## ✦ Repository Layout

```
aura/                   # Core Python package
  core/                 # Engine, session, memory, dispatcher
  model/                # Model backend abstraction (local / remote)
  tools/                # Individual callable tools + registry
  workflows/            # Multi-step workflow runners
  ui/                   # CLI + HTTP API server (+ future GUI)
  integrations/         # Voice, video, screen-share connectors
  identity/             # Persona and backstory

config/
  aura.yaml             # Runtime configuration (model, server, features)
  identity.yaml         # AURA's persona definition

scripts/
  install_linux.sh      # One-shot Linux setup
  install_termux.sh     # One-shot Termux/Android setup

tests/                  # pytest unit tests
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

# 3. Run CLI
aura chat
```

## ✦ Quick Start (Termux / Android)

```bash
bash scripts/install_termux.sh
aura chat
```

## ✦ Quick Start (Docker — run anywhere)

```bash
docker compose up --build
# AURA API is now live at http://localhost:8000
```

---

## ✦ Cloud / Web Deployment

AURA is cloud-native.  Run it as an HTTP API server so any web page, app, or
device on the network can talk to it:

```bash
# Start the API server
aura serve                      # default: 0.0.0.0:8000
aura serve --port 9090          # custom port
aura serve --host 127.0.0.1    # localhost only
```

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/chat` | Send a message, receive a reply |
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

## ✦ Contributing

AURA is a community project.  Contributions of all kinds are welcome — code,
docs, bug reports, ideas.  See [CONTRIBUTING.md](CONTRIBUTING.md) for
guidelines.

---

## ✦ Roadmap

- [x] Modular repo scaffold
- [x] Core engine with session & memory
- [x] Pluggable model backend (local + remote)
- [x] Tool registry with built-in tools
- [x] CLI interface
- [x] HTTP/JSON API server (cloud-native)
- [x] Docker deployment
- [x] Open-source license (Apache 2.0)
- [x] Community guidelines (CONTRIBUTING, CODE_OF_CONDUCT)
- [ ] GUI (web-based or Qt)
- [ ] Voice I/O integration
- [ ] APK auto-build pipeline
- [ ] Fine-tuned 200B-parameter model

---

## ✦ License

AURA is licensed under the [Apache License 2.0](LICENSE) — free to use,
modify, and distribute.

---

> "AURA isn't just a chatbot.  It's a reasoning layer that belongs to
> everyone — free, open, and built to help millions."
>
> — Christopher Betts, Designer & Founder
