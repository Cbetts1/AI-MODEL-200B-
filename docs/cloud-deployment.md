# AURA — Cloud Deployment Guide (Free Tiers)

> **Version:** 0.5.0  
> **Author:** Christopher Betts

AURA is cloud-native from day one. This guide covers deploying AURA for free
on several platforms so anyone can access it from any device — phone, tablet,
or desktop — without paying for compute.

---

## Quick Start (Docker)

```bash
# Pull and run
docker run -d \
  -p 8000:8000 \
  -e GROQ_API_KEY=your_groq_key \
  -e AURA_ADMIN_TOKEN=your_admin_token \
  --name aura \
  --restart always \
  ghcr.io/cbetts1/aura:latest
```

Or with docker-compose:
```bash
GROQ_API_KEY=your_key AURA_ADMIN_TOKEN=your_admin_token docker compose up -d
```

---

## Option 1 — Railway (Recommended for beginners)

**Free tier:** $5/month in free credits — enough for 24/7 AURA hosting.

1. Go to <https://railway.app> and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo** → select `Cbetts1/AI-MODEL-200B-`
3. Railway auto-detects the Dockerfile
4. Set environment variables in the **Variables** tab:
   ```
   GROQ_API_KEY=gsk_...
   AURA_ADMIN_TOKEN=your-strong-token
   ```
5. Click **Deploy** — Railway gives you a public URL like `https://aura-production.up.railway.app`
6. Visit the URL to open AURA

---

## Option 2 — Render

**Free tier:** 750 free instance hours/month (enough for 24/7 with one instance).

1. Go to <https://render.com> and sign in with GitHub
2. **New** → **Web Service** → connect the repo
3. Runtime: **Docker**
4. Set environment variables:
   ```
   GROQ_API_KEY=gsk_...
   AURA_ADMIN_TOKEN=your-strong-token
   ```
5. **Create Web Service** — Render builds and deploys automatically

> **Note:** Free Render instances spin down after 15 minutes of inactivity.
> Use the [Render Cron Job](https://render.com/docs/cron-jobs) to ping `/v1/health` every 10 min to keep it awake.

---

## Option 3 — Fly.io

**Free tier:** 3 shared-CPU VMs always free.

```bash
# Install fly CLI
curl -L https://fly.io/install.sh | sh

# From the repo root
fly launch --name aura-ai --region ord --dockerfile Dockerfile --no-deploy

# Set secrets
fly secrets set GROQ_API_KEY=gsk_...
fly secrets set AURA_ADMIN_TOKEN=your-strong-token

# Deploy
fly deploy

# Get the public URL
fly status
```

---

## Option 4 — Oracle Cloud (Always Free)

Oracle offers **always-free** ARM VMs with 4 OCPUs + 24 GB RAM — plenty for AURA.

1. Create a free account at <https://cloud.oracle.com>
2. Provision an **Ampere A1** VM (4 OCPUs / 24 GB — always free)
3. SSH into the VM and install Docker:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker $USER
   ```
4. Clone and run AURA:
   ```bash
   git clone https://github.com/Cbetts1/AI-MODEL-200B-.git
   cd AI-MODEL-200B-
   GROQ_API_KEY=gsk_... AURA_ADMIN_TOKEN=your-token docker compose up -d
   ```
5. Open port 8000 in the OCI Security List, then access AURA via the public IP

---

## Option 5 — Google Cloud Run

**Free tier:** 2 million requests/month, 360,000 GB-seconds/month.

```bash
# Build and push to Google Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/aura .

# Deploy
gcloud run deploy aura \
  --image gcr.io/YOUR_PROJECT/aura \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars GROQ_API_KEY=gsk_...,AURA_ADMIN_TOKEN=your-token
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Recommended | Free Groq key — 500K tokens/day |
| `CEREBRAS_API_KEY` | Optional | Free Cerebras key — very fast |
| `OPENROUTER_API_KEY` | Optional | Free OpenRouter key |
| `TOGETHER_API_KEY` | Optional | Together AI — $25 free credits |
| `HUGGINGFACE_API_KEY` | Optional | HuggingFace Inference API |
| `AURA_API_TOKEN` | Optional | Bearer token for public API auth |
| `AURA_ADMIN_TOKEN` | Recommended | Token for admin API and dashboard |

---

## Reverse Proxy with HTTPS (nginx)

For production, put AURA behind nginx with a free Let's Encrypt certificate:

```nginx
server {
    listen 443 ssl;
    server_name aura.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/aura.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/aura.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        # Increase timeout for SSE streaming
        proxy_read_timeout 120s;
    }
}
```

```bash
# Get certificate
certbot --nginx -d aura.yourdomain.com
```

---

## Keeping AURA Updated

### Automatic updates with Watchtower (Docker)

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 86400 \
  aura
```

Watchtower checks for a new image every 24 hours and restarts AURA automatically.

### Manual update via Admin API

1. `git pull && docker compose build` on the server
2. `curl -X POST -H "Authorization: Bearer $AURA_ADMIN_TOKEN" http://localhost:8000/admin/restart`
3. Restart the container/service

---

## Monitoring

AURA exposes health and status endpoints:

```bash
# Public health check
curl http://your-server:8000/v1/health

# Admin system metrics (requires token)
curl -H "Authorization: Bearer $AURA_ADMIN_TOKEN" http://your-server:8000/admin/status
```

Use these with UptimeRobot, Grafana, or any monitoring service for 24/7 uptime alerts.
