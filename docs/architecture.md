# AURA Architecture

## Overview

AURA follows a layered, single-responsibility architecture.  Each layer
communicates only with the layer directly below it through well-defined
interfaces.

```
┌─────────────────────────────────────────────────────┐
│                     USER / UI                       │
│           CLI (click + rich)   │   future GUI       │
└────────────────────┬────────────────────────────────┘
                     │ user message
┌────────────────────▼────────────────────────────────┐
│                  AuraEngine (core)                  │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌──────┐  │
│  │ Session │  │ Dispatcher│  │ Memory │  │Persona│  │
│  └─────────┘  └──────────┘  └────────┘  └──────┘  │
└────────────────────┬────────────────────────────────┘
          ┌──────────┼──────────┐
          ▼          ▼          ▼
   ModelBackend   ToolRegistry  Workflows
   (local/remote) (shell, file, (app_scaffold,
                   web, apk…)    …)
```

---

## Modules

### `aura/core/`

| Module | Responsibility |
|---|---|
| `engine.py` | Top-level orchestrator; ties all subsystems together |
| `session.py` | One conversation's state: history + metadata |
| `memory.py` | Read/write session history from `.jsonl` files on disk |
| `dispatcher.py` | Parses `/tool` and `/workflow` prefixes; routes messages |

### `aura/model/`

| Module | Responsibility |
|---|---|
| `base.py` | `ModelBackend` ABC — every backend must implement `complete()` |
| `local.py` | `LocalModelBackend` — llama.cpp or Ollama |
| `remote.py` | `RemoteModelBackend` — OpenAI-compatible HTTP API |

### `aura/tools/`

| Module | Responsibility |
|---|---|
| `registry.py` | `Tool` ABC + `ToolRegistry` dict + `build_default_registry()` |
| `shell.py` | `ShellTool` — run any shell command |
| `file_ops.py` | `FileReadTool`, `FileWriteTool`, `FileListTool` |
| `web_search.py` | `WebSearchTool` — DuckDuckGo Instant Answers |
| `apk_builder.py` | `ApkBuilderTool` — trigger `./gradlew assembleDebug` |

### `aura/workflows/`

| Module | Responsibility |
|---|---|
| `base.py` | `Workflow` ABC — every workflow must implement `run()` |
| `app_scaffold.py` | `AppScaffoldWorkflow` — scaffold a minimal Android app |

### `aura/ui/`

| Module | Responsibility |
|---|---|
| `cli.py` | Click CLI: `aura chat`, `aura tools`, `aura version` |
| `gui/` | Placeholder package for future web/Qt GUI |

### `aura/integrations/`

| Module | Responsibility |
|---|---|
| `voice.py` | `VoiceInput` / `VoiceOutput` stubs |
| `video.py` | `VideoCapture` stub |
| `screen_share.py` | `ScreenCapture` stub |

### `aura/identity/`

| Module | Responsibility |
|---|---|
| `persona.py` | Loads `config/identity.yaml` → builds the system prompt |

---

## Data Flow: Chat Turn

```
User types: "What time is it?"

  1. cli.py             → engine.chat("What time is it?")
  2. engine.py          → session.add_message("user", ...)
  3. dispatcher.py      → dispatch() → DispatchResult(kind="chat")
  4. engine.py          → model.complete(session.get_history_dicts())
  5. RemoteModelBackend → POST /v1/chat/completions → returns reply
  6. engine.py          → session.add_message("assistant", reply)
  7. engine.py          → memory.save(session)
  8. cli.py             → print Panel(reply)
```

## Data Flow: Tool Call

```
User types: "/tool shell ls -la"

  1. dispatcher.py → DispatchResult(kind="tool", name="shell", args="ls -la")
  2. engine.py     → tool_registry.get("shell").run("ls -la")
  3. ShellTool     → subprocess.run(["ls", "-la"]) → output string
  4. engine.py     → session.add_message("assistant", output)
```

---

## Adding a New Tool

1. Create `aura/tools/my_tool.py`:

```python
from aura.tools.registry import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "Does something useful."

    def run(self, args: str) -> str:
        return f"Did something with: {args}"
```

2. Register it in `aura/tools/registry.py` → `build_default_registry()`.

3. Test it:
```bash
pytest tests/test_tools.py
```

---

## Adding a New Model Backend

1. Subclass `aura.model.base.ModelBackend`.
2. Implement `complete()` and `is_available()`.
3. Wire it up in `aura/core/engine.py` → `_build_model_from_config()`.
