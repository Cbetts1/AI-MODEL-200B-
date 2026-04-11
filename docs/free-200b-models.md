# Free 200B-Class Models for AURA

AURA v0.4.0 introduces the **Model Router** — a system that automatically
connects you to the best available free AI model.  No local GPU required.
The model runs in the cloud; your device stays lightweight.

---

## ✦ How it works

Set any of the environment variables below and AURA will automatically route
to the corresponding free cloud service.  AURA tries backends in priority
order and uses the first one that responds.

```bash
# ── Fastest (set one or all) ──────────────────────────────────────────
export GROQ_API_KEY=gsk_...          # Free tier — llama-3.3-70b @ 750 tok/s
export CEREBRAS_API_KEY=csk_...      # Free tier — llama-3.3-70b, ultra-fast
export OPENROUTER_API_KEY=sk-or-...  # Free tier — many models incl. 70B+
export TOGETHER_API_KEY=...          # Free credits — Llama-3.3-70B-Turbo
export HUGGINGFACE_API_KEY=hf_...    # Free tier — microsoft/Phi-4

# ── Then start AURA ───────────────────────────────────────────────────
aura serve
```

No key? AURA falls back to the built-in echo backend so it always starts.

---

## ✦ Free Provider Quick-Start

### 🟢 Groq — Recommended (Fastest)
> **Model:** `llama-3.3-70b-versatile`  
> **Speed:** ~750 tokens/second  
> **Free tier:** 14,400 requests/day, 500K tokens/day

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card)
3. Create an API key
4. `export GROQ_API_KEY=gsk_your_key_here`

---

### 🟢 Cerebras — Ultra-Fast
> **Model:** `llama-3.3-70b`  
> **Speed:** ~2,000+ tokens/second (fastest available)  
> **Free tier:** Available on sign-up

1. Go to [inference.cerebras.ai](https://inference.cerebras.ai)
2. Sign up (free)
3. Create an API key
4. `export CEREBRAS_API_KEY=csk_your_key_here`

---

### 🟢 OpenRouter — Many Free Models
> **Model:** `meta-llama/llama-3.3-70b-instruct:free` (and many others)  
> **Free tier:** Free models are marked `:free` on the model list

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up (free)
3. Create an API key (no credit card required for free models)
4. `export OPENROUTER_API_KEY=sk-or-your_key_here`

Browse free models at: <https://openrouter.ai/models?q=free>

---

### 🟡 Together AI — Large Model Variety
> **Model:** `meta-llama/Llama-3.3-70B-Instruct-Turbo`  
> **Free credits:** $25 free on sign-up (no credit card)

1. Go to [api.together.xyz](https://api.together.xyz)
2. Sign up
3. Copy your API key
4. `export TOGETHER_API_KEY=your_key_here`

---

### 🟡 HuggingFace Inference API
> **Model:** `microsoft/Phi-4` (and many others)  
> **Free tier:** Rate-limited free tier available

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a token (read access is sufficient)
3. `export HUGGINGFACE_API_KEY=hf_your_token_here`

---

## ✦ Accessing True 200B+ Models

For access to the very largest models (400B+), use OpenRouter:

```bash
export OPENROUTER_API_KEY=sk-or-...
# Then update config/aura.yaml router entry for openrouter:
# model_name: meta-llama/llama-3.1-405b-instruct:free
```

Free 200B+ class models available on OpenRouter include:
- `meta-llama/llama-3.1-405b-instruct` (405B, may require small credits)
- `deepseek/deepseek-r1` (671B MoE — state of the art)
- `google/gemini-2.0-flash-exp:free` (extremely capable, free)
- `qwen/qwen3-235b-a22b:free` (235B MoE, free)

---

## ✦ Router Configuration

Edit `config/aura.yaml` to customise the router priority:

```yaml
model:
  backend: router
  router:
    - name: groq
      base_url: https://api.groq.com/openai/v1
      api_key_env: GROQ_API_KEY
      model_name: llama-3.3-70b-versatile
      temperature: 0.7
      max_tokens: 4096
    # ... add more backends
    - name: echo
      base_url: ""   # always-available offline fallback
```

Or use `backend: free` to auto-load all supported free services from their
environment variables — no manual router config required.

---

## ✦ Check Which Backend is Active

```bash
curl http://localhost:8000/v1/models
```

```json
{
  "backends": [
    {"name": "groq",      "available": true,  "type": "RemoteModelBackend"},
    {"name": "cerebras",  "available": false, "type": "RemoteModelBackend"},
    {"name": "echo",      "available": true,  "type": "EchoModelBackend"}
  ]
}
```

The model badge in the web UI (top bar) also shows the active backend name.

---

## ✦ Privacy Note

When using cloud backends, your messages are sent to the provider's servers.
For sensitive use cases, run a local backend (llama.cpp / Ollama) instead.
AURA never stores your API keys beyond the current shell session when using
environment variables.

---

*AURA is free and open-source, founded by Christopher Betts.*  
*The goal: make powerful AI accessible to everyone, everywhere, for free.*
