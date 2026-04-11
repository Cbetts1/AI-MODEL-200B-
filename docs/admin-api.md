# AURA Admin API — Remote Maintenance Guide

> **Version:** 0.5.0  
> **Author:** Christopher Betts

AURA v0.5.0 includes a built-in **Admin API** for remote maintenance, monitoring,
and updates — no SSH required.  All admin endpoints are protected by a separate
admin token and return JSON.

---

## Enabling the Admin API

Set the `AURA_ADMIN_TOKEN` environment variable before starting the server:

```bash
# Generate a strong token (do this once, store it safely)
export AURA_ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Start AURA — admin endpoints are now enabled
aura serve
```

If `AURA_ADMIN_TOKEN` is not set, all `/admin/*` endpoints return **503 Service Unavailable**.

> **Security:** Never commit your admin token to version control.
> Use a secrets manager (e.g. GitHub Secrets, Railway Secrets, Docker secrets).

---

## Admin Dashboard (Browser UI)

Open your browser and navigate to:

```
http://your-server:8000/admin
```

Paste your `AURA_ADMIN_TOKEN` into the token box and click **Connect**.

The dashboard shows:
- Live system metrics (uptime, memory, Python version)
- Model / cloud backend status (green = available, red = unavailable)
- Server log tail (last 100 lines, auto-refreshes every 15 s)
- Action buttons: Refresh, Reconnect Cloud, Hot-reload Config, Signal Restart

---

## REST API Reference

All requests must include:
```
Authorization: Bearer <AURA_ADMIN_TOKEN>
```

### GET /admin/status

Returns system metrics.

```bash
curl -H "Authorization: Bearer $AURA_ADMIN_TOKEN" http://localhost:8000/admin/status
```

**Response:**
```json
{
  "version": "0.5.0",
  "uptime_seconds": 3600,
  "uptime": "1h 0m 0s",
  "python_version": "3.11.0",
  "platform": "Linux",
  "architecture": "x86_64",
  "memory": {
    "total_mb": 8192.0,
    "used_mb": 2048.0,
    "available_mb": 6144.0,
    "used_pct": 25.0
  },
  "model_backends": [
    { "name": "groq", "available": true, "type": "RemoteModel" },
    { "name": "cerebras", "available": true, "type": "RemoteModel" }
  ],
  "active_session": "session-abc123",
  "log_buffer_size": 47,
  "restart_pending": false
}
```

---

### GET /admin/logs

Returns the last N lines from the in-process log buffer.

```bash
# Default: last 100 lines
curl -H "Authorization: Bearer $AURA_ADMIN_TOKEN" http://localhost:8000/admin/logs

# Custom count
curl -H "Authorization: Bearer $AURA_ADMIN_TOKEN" "http://localhost:8000/admin/logs?n=50"
```

**Response:**
```json
{
  "lines": [
    "[2024-01-01T12:00:00Z] ADMIN: restart requested via API",
    "[2024-01-01T12:01:00Z] ADMIN: cloud reconnect — 2/5 backends available"
  ],
  "count": 100
}
```

---

### GET /admin/cloud

Returns cloud / model-backend connection status.

```bash
curl -H "Authorization: Bearer $AURA_ADMIN_TOKEN" http://localhost:8000/admin/cloud
```

**Response:**
```json
{
  "cloud_backends": [
    { "name": "groq", "available": true },
    { "name": "cerebras", "available": true },
    { "name": "openrouter", "available": false },
    { "name": "together", "available": true },
    { "name": "huggingface", "available": false }
  ]
}
```

---

### POST /admin/config

Signals a config reload. Feature-flag changes take effect immediately;
model/backend changes require a server restart.

```bash
curl -X POST \
  -H "Authorization: Bearer $AURA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reload": true}' \
  http://localhost:8000/admin/config
```

**Response:**
```json
{
  "message": "Config reload acknowledged. Restart the server to apply model/backend changes.",
  "note": "Feature flags and template changes take effect immediately on next request."
}
```

---

### POST /admin/restart

Signals the server to perform a graceful restart at the next safe point.

```bash
curl -X POST \
  -H "Authorization: Bearer $AURA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/admin/restart
```

**Response:**
```json
{
  "message": "Restart signal received. Server will restart at the next safe point.",
  "restart_pending": true
}
```

> **Note:** The restart signal sets an internal flag.  In production, pair this with a
> process supervisor (systemd, Docker `--restart=always`, or a health-check loop) that
> monitors `/v1/health` and restarts the process when needed.

---

### POST /admin/cloud/connect

Forces a cloud-backend reconnect check and returns updated status.

```bash
curl -X POST \
  -H "Authorization: Bearer $AURA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/admin/cloud/connect
```

**Response:**
```json
{
  "message": "Cloud status checked: 3/5 backends available.",
  "backends": [
    { "name": "groq", "available": true },
    { "name": "cerebras", "available": true },
    { "name": "openrouter", "available": true },
    { "name": "together", "available": false },
    { "name": "huggingface", "available": false }
  ]
}
```

---

## Error Responses

| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing or incorrect `Authorization` header |
| `503 Service Unavailable` | Admin API disabled (AURA_ADMIN_TOKEN not set) |
| `404 Not Found` | Unknown endpoint |

---

## Remote Update Workflow

To update AURA on a remote server without SSH:

1. **Push new code** to your server (git pull, Docker pull, etc.) via your CI/CD pipeline
2. **Signal restart** via the admin API: `POST /admin/restart`
3. Your process supervisor (systemd, Docker) detects the restart and launches the new version
4. **Verify** by checking `/v1/version` or `/admin/status`

### Example with systemd

```ini
# /etc/systemd/system/aura.service
[Unit]
Description=AURA AI Server
After=network.target

[Service]
Environment=AURA_ADMIN_TOKEN=your-token-here
Environment=GROQ_API_KEY=your-groq-key
ExecStart=/usr/local/bin/aura serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# After updating code and signalling restart:
sudo systemctl restart aura
```

### Example with Docker

```bash
# Pull the latest image and restart
docker pull ghcr.io/cbetts1/aura:latest
docker compose up -d --no-deps aura
```

---

## Security Best Practices

- Use a **strong random token** (at minimum 32 hex characters)
- Deploy behind a **reverse proxy** (nginx/Caddy) with HTTPS — never expose admin over plain HTTP on the internet
- Set `AURA_ADMIN_TOKEN` as an **environment variable or secret**, never in config files
- Restrict `/admin` access with a reverse-proxy IP whitelist if possible
- Rotate the admin token periodically
