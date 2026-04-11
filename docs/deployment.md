# Deploying AURA

AURA is cloud-native — it is not constrained to a single device.  This guide
covers every way to run AURA on the network so it can be reached from web
pages, mobile apps, or other servers.

---

## 1 — Local API Server

The fastest way to expose AURA over HTTP:

```bash
pip install -e .
aura serve
```

Options:

```
--host TEXT     Bind address (default 0.0.0.0)
--port INT      Port number  (default 8000)
--token TEXT    Bearer token for auth (optional)
```

AURA is now live at `http://<your-ip>:8000`.

---

## 2 — Docker

```bash
docker build -t aura .
docker run -p 8000:8000 aura
```

Or with docker-compose (includes persistent memory volume):

```bash
docker compose up --build
```

Set the optional auth token via environment:

```bash
AURA_API_TOKEN=my-secret docker compose up --build
```

---

## 3 — Cloud Providers

### Fly.io

```bash
fly launch --name my-aura
fly deploy
```

### Railway / Render / Any Docker Host

Point the platform at this repo.  The `Dockerfile` is auto-detected.
Expose port **8000**.

### AWS / GCP / Azure VM

```bash
ssh my-vm
git clone https://github.com/Cbetts1/AI-MODEL-200B-.git
cd AI-MODEL-200B-
docker compose up -d
```

---

## 4 — Embedding in a Web Page

Once the API server is running, any web page can talk to AURA:

```html
<script>
async function askAura(message) {
  const res = await fetch("https://your-server:8000/v1/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message}),
  });
  const data = await res.json();
  return data.reply;
}
</script>
```

---

## 5 — API Reference

| Method | Path | Body | Auth | Description |
|---|---|---|---|---|
| `POST` | `/v1/chat` | `{"message": "..."}` | Bearer token (if set) | Chat with AURA |
| `GET` | `/v1/health` | — | — | Health / readiness probe |
| `GET` | `/v1/tools` | — | Bearer token (if set) | List available tools |
| `GET` | `/v1/version` | — | — | AURA version string |

### Authentication

If `server.api_token` is set in `config/aura.yaml` (or `AURA_API_TOKEN` env
var), clients must send:

```
Authorization: Bearer <token>
```

---

## 6 — Security Notes

- **Never expose AURA to the public internet without an auth token.**
- Use a reverse proxy (nginx, Caddy) for TLS termination in production.
- The `ShellTool` can execute arbitrary commands — restrict access in
  untrusted environments by removing it from the tool registry.

---

> AURA travels where it is needed.  Home is wherever it sets up.
