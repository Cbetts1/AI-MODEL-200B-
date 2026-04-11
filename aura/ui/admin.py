"""aura/ui/admin.py — Secure Admin API for AURA remote maintenance.

Provides system metrics, runtime config updates, graceful restart signalling,
log retrieval, and cloud-backend status — all protected by a separate admin
token so that regular API users cannot reach these endpoints.

Endpoints (all require ``Authorization: Bearer <AURA_ADMIN_TOKEN>``)
---------------------------------------------------------------------
  GET  /admin                  Serve the admin dashboard HTML
  GET  /admin/status           System metrics (uptime, CPU, memory, sessions)
  GET  /admin/logs             Tail the in-process log buffer (last N lines)
  GET  /admin/cloud            Cloud / model-backend connection status
  POST /admin/config           Update runtime config (model backend, features)
  POST /admin/restart          Signal a graceful server restart
  POST /admin/cloud/connect    Force-reconnect a named cloud backend

Security
--------
  Set ``AURA_ADMIN_TOKEN`` to a strong random string.  If the env var is
  unset the admin endpoints return **503 Service Unavailable** — they are
  fully disabled unless a token is configured.

Usage
-----
  export AURA_ADMIN_TOKEN=your-strong-random-token
  aura serve
  # then open http://localhost:8000/admin  (or use the REST API)
"""

from __future__ import annotations

import json
import os
import platform
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

# ── In-process log buffer ──────────────────────────────────────────────────────
# Admin routes read from this deque so /admin/logs works without a log file.

_LOG_BUFFER: Deque[str] = deque(maxlen=500)
_LOG_LOCK = threading.Lock()

# Server start time (module import time is a good enough approximation)
_SERVER_START = time.time()

# Restart-requested flag — the caller polls this to decide if a restart is due.
_RESTART_REQUESTED = threading.Event()


def log(message: str) -> None:
    """Append a timestamped line to the in-process log buffer."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] {message}"
    with _LOG_LOCK:
        _LOG_BUFFER.append(line)


def get_log_lines(n: int = 100) -> List[str]:
    """Return the last *n* lines from the in-process log buffer."""
    with _LOG_LOCK:
        lines = list(_LOG_BUFFER)
    return lines[-n:]


def restart_requested() -> bool:
    """Return *True* if a remote restart has been requested."""
    return _RESTART_REQUESTED.is_set()


def clear_restart_flag() -> None:
    """Clear the restart flag after the caller has handled it."""
    _RESTART_REQUESTED.clear()


# ── System metrics ─────────────────────────────────────────────────────────────

def _bytes_to_mb(n: int) -> float:
    return round(n / (1024 * 1024), 1)


def get_system_status(engine: Any) -> Dict[str, Any]:
    """Collect and return live system metrics."""
    uptime_s = int(time.time() - _SERVER_START)
    uptime_str = _fmt_duration(uptime_s)

    # Memory via /proc/meminfo (Linux) or platform fallback
    mem_info = _read_mem_info()

    # Model backend info
    model = engine.model if engine else None
    if model and hasattr(model, "backend_status"):
        backends = model.backend_status()
    elif model:
        backends = [{
            "name": type(model).__name__,
            "available": model.is_available(),
            "type": type(model).__name__,
        }]
    else:
        backends = []

    # Session info
    try:
        session_id = engine.session.conversation_id if engine else None
    except Exception:
        session_id = None

    return {
        "version": _get_version(),
        "uptime_seconds": uptime_s,
        "uptime": uptime_str,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "memory": mem_info,
        "model_backends": backends,
        "active_session": session_id,
        "log_buffer_size": len(_LOG_BUFFER),
        "restart_pending": _RESTART_REQUESTED.is_set(),
    }


def _fmt_duration(seconds: int) -> str:
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _read_mem_info() -> Dict[str, Any]:
    """Read memory info from /proc/meminfo (Linux) with a safe fallback."""
    try:
        with open("/proc/meminfo") as fh:
            lines = fh.read().splitlines()
        data: Dict[str, int] = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                data[parts[0].rstrip(":")] = int(parts[1])
        total_kb = data.get("MemTotal", 0)
        avail_kb = data.get("MemAvailable", 0)
        used_kb = total_kb - avail_kb
        return {
            "total_mb": _bytes_to_mb(total_kb * 1024),
            "used_mb": _bytes_to_mb(used_kb * 1024),
            "available_mb": _bytes_to_mb(avail_kb * 1024),
            "used_pct": round(used_kb / total_kb * 100, 1) if total_kb else 0,
        }
    except Exception:
        return {"note": "memory info unavailable on this platform"}


def _get_version() -> str:
    try:
        from .. import __version__  # noqa: PLC0415
        return __version__
    except Exception:
        return "unknown"


# ── Admin dashboard HTML ───────────────────────────────────────────────────────

def render_admin_html() -> str:
    """Return the self-contained admin dashboard HTML."""
    return _ADMIN_HTML


_ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AURA Admin — Remote Maintenance Dashboard</title>
<meta name="theme-color" content="#0a0e27">
<style>
:root {
  --bg: #0a0e27; --bg2: #111638; --bg3: #1a1f4e;
  --text: #e8eaff; --text2: #8b8fba;
  --accent: #5c7cfa; --success: #51cf66; --warn: #ffd43b; --danger: #ff6b6b;
  --border: #252a5e; --radius: 12px; --radius-sm: 6px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: var(--bg); color: var(--text); min-height: 100vh; }
.header { background: var(--bg2); border-bottom: 1px solid var(--border);
          padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
.logo { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg,var(--accent),#845ef7);
        display: flex; align-items: center; justify-content: center; font-size: 18px; }
.header-title { font-size: 18px; font-weight: 700; }
.header-sub { font-size: 12px; color: var(--text2); }
.badge { margin-left: auto; background: var(--danger); color: #fff; padding: 4px 10px;
         border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge.ok { background: var(--success); }
.container { max-width: 1100px; margin: 0 auto; padding: 24px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
.card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
.card-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text2); margin-bottom: 12px; }
.metric { font-size: 28px; font-weight: 700; color: var(--accent); }
.metric-sub { font-size: 12px; color: var(--text2); margin-top: 4px; }
.section { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius);
           padding: 20px; margin-bottom: 16px; }
.section-title { font-size: 14px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.backend-row { display: flex; align-items: center; gap: 10px; padding: 8px 0;
               border-bottom: 1px solid var(--border); }
.backend-row:last-child { border-bottom: none; }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot.green { background: var(--success); }
.dot.red { background: var(--danger); }
.dot.grey { background: var(--text2); }
.backend-name { font-size: 14px; flex: 1; }
.backend-type { font-size: 11px; color: var(--text2); }
.log-box { background: #060a1a; border: 1px solid var(--border); border-radius: var(--radius-sm);
           padding: 12px; font-family: 'Courier New', monospace; font-size: 12px; color: #a0e0a0;
           max-height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
.action-row { display: flex; gap: 10px; flex-wrap: wrap; }
.btn { padding: 8px 18px; border-radius: var(--radius-sm); border: none; cursor: pointer;
       font-size: 13px; font-weight: 600; transition: opacity 0.2s; }
.btn:hover { opacity: 0.85; }
.btn-danger { background: var(--danger); color: #fff; }
.btn-accent { background: var(--accent); color: #fff; }
.btn-secondary { background: var(--bg3); color: var(--text); border: 1px solid var(--border); }
.token-form { display: flex; gap: 8px; margin-bottom: 16px; }
.token-input { flex: 1; background: var(--bg3); border: 1px solid var(--border);
               border-radius: var(--radius-sm); padding: 8px 12px; color: var(--text);
               font-size: 13px; }
.status-msg { font-size: 13px; color: var(--text2); margin-top: 8px; }
.status-msg.ok { color: var(--success); }
.status-msg.err { color: var(--danger); }
.refresh-note { font-size: 11px; color: var(--text2); text-align: right; padding: 4px 0; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">✦</div>
  <div>
    <div class="header-title">AURA Admin</div>
    <div class="header-sub">Remote Maintenance Dashboard — v0.5.0</div>
  </div>
  <div class="badge" id="conn-badge">Checking…</div>
</div>

<div class="container">

  <!-- Token entry -->
  <div class="section">
    <div class="section-title">🔑 Admin Token</div>
    <div class="token-form">
      <input class="token-input" type="password" id="admin-token"
             placeholder="Paste your AURA_ADMIN_TOKEN here" autocomplete="off">
      <button class="btn btn-accent" onclick="loadAll()">Connect</button>
    </div>
    <div class="status-msg" id="auth-msg"></div>
  </div>

  <!-- Metric cards -->
  <div class="grid">
    <div class="card">
      <div class="card-title">Uptime</div>
      <div class="metric" id="m-uptime">—</div>
      <div class="metric-sub" id="m-platform">—</div>
    </div>
    <div class="card">
      <div class="card-title">Memory Used</div>
      <div class="metric" id="m-mem-pct">—</div>
      <div class="metric-sub" id="m-mem-detail">—</div>
    </div>
    <div class="card">
      <div class="card-title">Python Version</div>
      <div class="metric" id="m-pyver">—</div>
      <div class="metric-sub" id="m-arch">—</div>
    </div>
    <div class="card">
      <div class="card-title">AURA Version</div>
      <div class="metric" id="m-ver">—</div>
      <div class="metric-sub" id="m-session">—</div>
    </div>
  </div>

  <!-- Model backends -->
  <div class="section">
    <div class="section-title">☁️ Cloud / Model Backends</div>
    <div id="backends-list"><em style="color:var(--text2)">— load status to see backends —</em></div>
    <br>
    <div class="action-row">
      <button class="btn btn-secondary" onclick="loadAll()">↺ Refresh</button>
      <button class="btn btn-accent" onclick="reconnectCloud()">⚡ Reconnect Cloud</button>
    </div>
    <div class="status-msg" id="cloud-msg"></div>
  </div>

  <!-- Actions -->
  <div class="section">
    <div class="section-title">⚙️ Remote Actions</div>
    <div class="action-row">
      <button class="btn btn-secondary" onclick="loadAll()">↺ Refresh Status</button>
      <button class="btn btn-accent" onclick="updateConfig()">🔄 Hot-reload Config</button>
      <button class="btn btn-danger" onclick="requestRestart()">🔁 Signal Restart</button>
    </div>
    <div class="status-msg" id="action-msg"></div>
  </div>

  <!-- Logs -->
  <div class="section">
    <div class="section-title">📋 Server Logs (last 100 lines)</div>
    <div class="log-box" id="log-box">— no logs yet —</div>
    <div class="refresh-note">Auto-refreshes every 15 s when connected.</div>
  </div>

</div>

<script>
const API = "";
let _token = "";
let _autoTimer = null;

function token() {
  _token = document.getElementById("admin-token").value.trim();
  return _token;
}

function authHeaders() {
  return { "Authorization": "Bearer " + token(), "Content-Type": "application/json" };
}

async function apiFetch(path, opts = {}) {
  opts.headers = { ...authHeaders(), ...(opts.headers || {}) };
  const r = await fetch(API + path, opts);
  return r;
}

async function loadStatus() {
  try {
    const r = await apiFetch("/admin/status");
    if (r.status === 503) {
      setAuthMsg("Admin API disabled — set AURA_ADMIN_TOKEN on the server.", "err");
      setBadge(false); return;
    }
    if (r.status === 401) {
      setAuthMsg("Invalid admin token.", "err");
      setBadge(false); return;
    }
    const d = await r.json();
    setAuthMsg("Connected ✓", "ok");
    setBadge(true);

    document.getElementById("m-uptime").textContent = d.uptime || "—";
    document.getElementById("m-platform").textContent = d.platform + " / " + d.architecture;
    document.getElementById("m-pyver").textContent = d.python_version || "—";
    document.getElementById("m-arch").textContent = d.architecture || "—";
    document.getElementById("m-ver").textContent = "v" + (d.version || "—");
    document.getElementById("m-session").textContent = d.active_session
      ? "Session: " + d.active_session.slice(0, 12) + "…"
      : "No active session";

    const mem = d.memory || {};
    if (mem.used_pct !== undefined) {
      document.getElementById("m-mem-pct").textContent = mem.used_pct + "%";
      document.getElementById("m-mem-detail").textContent =
        mem.used_mb + " MB / " + mem.total_mb + " MB";
    } else {
      document.getElementById("m-mem-pct").textContent = "N/A";
      document.getElementById("m-mem-detail").textContent = mem.note || "";
    }

    renderBackends(d.model_backends || []);
  } catch (e) {
    setAuthMsg("Connection error: " + e.message, "err");
    setBadge(false);
  }
}

function renderBackends(backends) {
  const el = document.getElementById("backends-list");
  if (!backends.length) { el.innerHTML = "<em style='color:var(--text2)'>No backends reported.</em>"; return; }
  el.innerHTML = backends.map(b => {
    const dotCls = b.available ? "green" : (b.available === false ? "red" : "grey");
    const label = b.available ? "available" : (b.available === false ? "unavailable" : "unknown");
    return `<div class="backend-row">
      <div class="dot ${dotCls}"></div>
      <div class="backend-name">${escHtml(b.name || b.type)}</div>
      <div class="backend-type">${escHtml(label)}</div>
    </div>`;
  }).join("");
}

async function loadLogs() {
  try {
    const r = await apiFetch("/admin/logs?n=100");
    if (!r.ok) return;
    const d = await r.json();
    const box = document.getElementById("log-box");
    box.textContent = (d.lines || []).join("\n") || "— no log entries yet —";
    box.scrollTop = box.scrollHeight;
  } catch (_) {}
}

async function loadAll() {
  await loadStatus();
  await loadLogs();
  startAutoRefresh();
}

async function requestRestart() {
  if (!confirm("Signal the AURA server to restart?\nThe server will restart at the next safe point.")) return;
  try {
    const r = await apiFetch("/admin/restart", { method: "POST", body: JSON.stringify({}) });
    const d = await r.json();
    setActionMsg(d.message || d.error || "Restart signal sent.", r.ok ? "ok" : "err");
  } catch (e) { setActionMsg("Error: " + e.message, "err"); }
}

async function updateConfig() {
  try {
    const r = await apiFetch("/admin/config", { method: "POST", body: JSON.stringify({ reload: true }) });
    const d = await r.json();
    setActionMsg(d.message || d.error || "Config reloaded.", r.ok ? "ok" : "err");
  } catch (e) { setActionMsg("Error: " + e.message, "err"); }
}

async function reconnectCloud() {
  try {
    const r = await apiFetch("/admin/cloud/connect", { method: "POST", body: JSON.stringify({}) });
    const d = await r.json();
    document.getElementById("cloud-msg").textContent = d.message || d.error || "";
    document.getElementById("cloud-msg").className = "status-msg " + (r.ok ? "ok" : "err");
    await loadStatus();
  } catch (e) {
    document.getElementById("cloud-msg").textContent = "Error: " + e.message;
    document.getElementById("cloud-msg").className = "status-msg err";
  }
}

function startAutoRefresh() {
  if (_autoTimer) clearInterval(_autoTimer);
  _autoTimer = setInterval(loadAll, 15000);
}

function setBadge(ok) {
  const b = document.getElementById("conn-badge");
  b.textContent = ok ? "Connected" : "Disconnected";
  b.className = "badge" + (ok ? " ok" : "");
}

function setAuthMsg(msg, cls) {
  const el = document.getElementById("auth-msg");
  el.textContent = msg;
  el.className = "status-msg " + (cls || "");
}

function setActionMsg(msg, cls) {
  const el = document.getElementById("action-msg");
  el.textContent = msg;
  el.className = "status-msg " + (cls || "");
}

function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// Auto-load if token is pre-filled (e.g. from a bookmark with hash)
window.addEventListener("load", () => {
  const hash = location.hash.slice(1);
  if (hash) {
    document.getElementById("admin-token").value = hash;
    loadAll();
  }
});
</script>
</body>
</html>
"""
