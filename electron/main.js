// electron/main.js — AURA Desktop App (Electron)
//
// Wraps the AURA web UI in a native desktop window for Windows, macOS,
// and Linux.  Can be packaged as:
//   - Windows MSIX / APPX for the Microsoft Store
//   - macOS DMG / App Store
//   - Linux AppImage / Snap / Flatpak
//
// Usage:
//   cd electron
//   npm install
//   npm start             # dev: opens window pointing at localhost:8000
//   npm run build         # package with electron-builder
//
// The app expects the AURA Python server to be running separately
// (or launched as a child process — see launchServer() below).
// For store distribution the Python server binary is bundled.

const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

// ── Configuration ────────────────────────────────────────────────────────────

const AURA_PORT = process.env.AURA_PORT || 8000;
const AURA_HOST = process.env.AURA_HOST || "127.0.0.1";
const AURA_URL  = `http://${AURA_HOST}:${AURA_PORT}`;

let mainWindow = null;
let serverProcess = null;

// ── Server management ────────────────────────────────────────────────────────

function launchServer() {
  // Try to launch the bundled AURA server (production) or fall back to PATH.
  const auraExe = process.env.AURA_EXE || "aura";
  console.log(`[AURA Desktop] Launching server: ${auraExe} serve --port ${AURA_PORT}`);
  serverProcess = spawn(auraExe, ["serve", "--host", "127.0.0.1", "--port", String(AURA_PORT)], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  serverProcess.stdout.on("data", d => console.log("[AURA Server]", d.toString().trim()));
  serverProcess.stderr.on("data", d => console.error("[AURA Server]", d.toString().trim()));
  serverProcess.on("exit", code => {
    console.log(`[AURA Server] exited with code ${code}`);
    serverProcess = null;
  });
}

function waitForServer(retries, callback) {
  http.get(`${AURA_URL}/v1/health`, res => {
    if (res.statusCode === 200) { callback(); return; }
    retry(retries, callback);
  }).on("error", () => retry(retries, callback));
}

function retry(retries, callback) {
  if (retries <= 0) {
    dialog.showErrorBox(
      "AURA — Server Unavailable",
      `Could not connect to AURA server at ${AURA_URL}.\n\nMake sure the server is running:\n  aura serve`
    );
    return;
  }
  setTimeout(() => waitForServer(retries - 1, callback), 800);
}

// ── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 700,
    minHeight: 500,
    title: "AURA — AI Unified Reasoning Architecture",
    backgroundColor: "#0a0e27",
    icon: path.join(__dirname, "icons", "aura-256.png"),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false,
  });

  mainWindow.once("ready-to-show", () => mainWindow.show());

  // Open external links in the default browser, not in the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(AURA_URL)) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  mainWindow.on("closed", () => { mainWindow = null; });

  buildMenu();
  waitForServer(15, () => mainWindow.loadURL(AURA_URL));
}

// ── Menu ─────────────────────────────────────────────────────────────────────

function buildMenu() {
  const template = [
    {
      label: "AURA",
      submenu: [
        { label: "About AURA", click: showAbout },
        { type: "separator" },
        { label: "Open Admin Dashboard", click: () => mainWindow && mainWindow.loadURL(AURA_URL + "/admin") },
        { type: "separator" },
        { label: "Quit", accelerator: "CmdOrCtrl+Q", role: "quit" },
      ],
    },
    {
      label: "Chat",
      submenu: [
        { label: "New Session", click: () => mainWindow && mainWindow.loadURL(AURA_URL) },
        { label: "Reload", accelerator: "CmdOrCtrl+R", click: () => mainWindow && mainWindow.reload() },
        { label: "Force Reload", accelerator: "CmdOrCtrl+Shift+R", click: () => mainWindow && mainWindow.webContents.reloadIgnoringCache() },
      ],
    },
    {
      label: "View",
      submenu: [
        { label: "Zoom In",  accelerator: "CmdOrCtrl+=", role: "zoomIn" },
        { label: "Zoom Out", accelerator: "CmdOrCtrl+-", role: "zoomOut" },
        { label: "Reset Zoom", accelerator: "CmdOrCtrl+0", role: "resetZoom" },
        { type: "separator" },
        { label: "Toggle Full Screen", accelerator: "F11", role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        { label: "AURA on GitHub", click: () => shell.openExternal("https://github.com/Cbetts1/AI-MODEL-200B-") },
        { label: "Open Admin Dashboard", click: () => mainWindow && mainWindow.loadURL(AURA_URL + "/admin") },
        { type: "separator" },
        { label: "Toggle DevTools", accelerator: "CmdOrCtrl+Shift+I", role: "toggleDevTools" },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function showAbout() {
  dialog.showMessageBox(mainWindow, {
    type: "info",
    title: "About AURA",
    message: "AURA — AI Unified Reasoning Architecture",
    detail: "Version: 0.7.0\nFree AI for everyone.\n\nDesigned and founded by Christopher Betts.\nLicensed under Apache 2.0.",
    buttons: ["OK"],
  });
}

// ── App lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  // Try to start the server if not already running.
  http.get(`${AURA_URL}/v1/health`, res => {
    if (res.statusCode !== 200) launchServer();
  }).on("error", () => launchServer());

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
});
