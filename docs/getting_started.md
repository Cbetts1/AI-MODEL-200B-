# Getting Started with AURA

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.9 | Python 3.11 recommended |
| pip | ≥ 23 | `pip install --upgrade pip` |
| A model server | any | Ollama, LM Studio, OpenAI API, etc. |

---

## 1 — Install (Linux)

```bash
git clone https://github.com/Cbetts1/AI-MODEL-200B-.git
cd AI-MODEL-200B-
bash scripts/install_linux.sh
source .venv/bin/activate
```

## 1 — Install (Termux / Android)

```bash
git clone https://github.com/Cbetts1/AI-MODEL-200B-.git
cd AI-MODEL-200B-
bash scripts/install_termux.sh
```

---

## 2 — Choose a Model Backend

### Option A: Ollama (easiest)

```bash
# Install Ollama from https://ollama.com/download
ollama serve &
ollama pull llama3
```

Edit `config/aura.yaml`:

```yaml
model:
  backend: remote
  remote:
    base_url: http://localhost:11434/v1
    api_key: ""
    model_name: llama3
```

### Option B: llama.cpp (local, no server needed)

```bash
pip install llama-cpp-python
# Download a .gguf model, e.g.:
# https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF
```

Edit `config/aura.yaml`:

```yaml
model:
  backend: local
  local:
    engine: llamacpp
    model_path: models/weights/llama-2-7b-chat.Q4_K_M.gguf
```

### Option C: OpenAI API

```yaml
model:
  backend: remote
  remote:
    base_url: https://api.openai.com/v1
    api_key: sk-...
    model_name: gpt-4o
```

---

## 3 — Start Chatting

```bash
aura chat
```

You'll see a prompt like:
```
╭─ AURA — AI Unified Reasoning Architecture ──────────────────╮
│  Session ID: abc123...                                       │
│  Type 'exit' or Ctrl-C to quit.  /tool list to see tools.   │
╰──────────────────────────────────────────────────────────────╯

You> Hello!
╭─ AURA ──────────────────────────────────────────────────────╮
│ Hello! I'm AURA — your AI Unified Reasoning Architecture.    │
│ How can I help you today?                                    │
╰──────────────────────────────────────────────────────────────╯
```

---

## 4 — Using Tools

List available tools:
```
/tool list
```

Run a shell command:
```
/tool shell ls -la
```

Read a file:
```
/tool file_read /etc/hostname
```

Search the web:
```
/tool web_search latest llama model benchmarks
```

Build an APK (requires Android SDK + Java):
```
/tool apk_builder /path/to/my/android/project
```

---

## 5 — Using Workflows

Scaffold an Android app project:
```
/workflow app_scaffold MyApp com.example.myapp /tmp/MyApp
```

This creates a complete Gradle project structure.  Then:
```bash
cd /tmp/MyApp
gradle wrapper          # generate the real gradlew
./gradlew assembleDebug
```

---

## 6 — Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## 7 — Identity & Persona

Edit `config/identity.yaml` to change AURA's name, tone, and backstory.
The changes take effect immediately on the next `aura chat` session.

---

## 8 — Resuming a Session

```bash
aura chat --session <session-id>
```

Session IDs are printed at the start of each chat session and stored as
`~/.aura/memory/<session-id>.jsonl`.
