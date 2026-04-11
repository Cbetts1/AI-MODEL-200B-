# AURA — App Store Submission Guide

> **Version:** 0.5.0  
> **Author:** Christopher Betts

AURA is designed to run anywhere — in a browser, as a PWA, or as a native app.
This guide covers how to publish AURA to the three major stores: **Google Play**,
**Microsoft Store**, and **Apple App Store**.

---

## Architecture overview

AURA is a **client–server app**:

| Component | What it does |
|---|---|
| **AURA Python server** | Runs inference, tools, memory, workflows — on a cloud VM or local device |
| **Web UI** (`/`) | Full chat interface served by the server — accessible from any browser |
| **PWA** | Installable directly from the browser — no app store needed |
| **Capacitor app** | Native Android / iOS shell that loads the AURA server URL |
| **Electron app** | Native Windows / macOS / Linux desktop app |

The model runs **remotely** on free cloud services (Groq, Cerebras, OpenRouter, etc.) —
users' devices stay lightweight.

---

## Option 1 — PWA (No Store Required)

The simplest distribution method. Users can install AURA directly from the browser:

1. Deploy AURA to a cloud server (see [cloud-deployment.md](cloud-deployment.md))
2. Users visit the URL in Chrome / Edge / Safari
3. Click the browser's **"Install"** or **"Add to Home Screen"** prompt
4. AURA is installed as a standalone app on their device

✅ **Free. No developer account. Works on Android, iOS, Windows, and macOS.**

---

## Option 2 — Google Play Store (Android)

### Prerequisites
- Google Play Developer account ($25 one-time fee)
- Node.js ≥ 18, Java 17, Android Studio

### Build the APK / AAB

```bash
# 1. Install Capacitor tooling
npm install -g @capacitor/cli

# 2. From the repository root
npm init -y
npm install @capacitor/core @capacitor/android @capacitor/splash-screen @capacitor/status-bar

# 3. Add Android platform
npx cap add android

# 4. Configure www/index.html to point to your cloud AURA server URL
#    Replace "http://localhost:8000" with your production URL, e.g.:
#    const SERVER = "https://aura.yourdomain.com";

# 5. Sync web assets
npx cap sync android

# 6. Build release AAB
cd android
./gradlew bundleRelease
```

The AAB (`app/build/outputs/bundle/release/app-release.aab`) is ready to upload
to the Google Play Console.

### Sign the AAB

```bash
keytool -genkey -v -keystore aura-release.jks -alias aura -keyalg RSA -keysize 2048 -validity 10000
# Follow prompts to set a password and fill in details

# Sign the bundle
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
  -keystore aura-release.jks app-release.aab aura
```

### Google Play Console steps
1. Go to <https://play.google.com/console>
2. Create a new app → **Free** → **App**
3. Upload the signed AAB in **Production** > **Releases**
4. Fill in the store listing (screenshots, description, icon)
5. Set **Content Rating** as appropriate (AURA is general-purpose AI)
6. Submit for review

---

## Option 3 — Microsoft Store (Windows)

### Prerequisites
- Microsoft Partner Center account (free)
- Windows 10/11 machine with Node.js ≥ 18

### Build the APPX / MSIX

```bash
# From the electron/ directory
cd electron
npm install
npm run build:win
# Output: electron/dist/AURA-0.5.0.appx
```

### Microsoft Partner Center steps
1. Go to <https://partner.microsoft.com/dashboard>
2. **Windows & Xbox** > **Create a new app** → Name: **AURA**
3. Upload the APPX in **Submissions** > **Packages**
4. Fill in store listing (screenshots, description, icon — 300×300 PNG minimum)
5. Set **Pricing**: **Free**
6. Submit for certification (~3–5 business days)

---

## Option 4 — Apple App Store (iOS / macOS)

### Prerequisites
- Apple Developer Program membership ($99/year)
- macOS machine with Xcode ≥ 15

### Build for iOS

```bash
# From the repository root
npx cap add ios
npx cap sync ios
npx cap open ios   # opens Xcode
```

In Xcode:
1. Set Bundle ID: `com.aura.ai`
2. Set Team to your Apple Developer account
3. **Product** > **Archive**
4. Open **Organizer** > **Distribute App** > **App Store Connect**

### Build for macOS (Mac App Store)

```bash
cd electron
npm run build:mac
# Output: electron/dist/AURA-0.5.0-mas.pkg
```

### App Store Connect steps
1. Go to <https://appstoreconnect.apple.com>
2. **My Apps** > **+** > **New App**
3. Platform: **iOS** or **macOS**
4. Bundle ID: `com.aura.ai`
5. Upload the archive via Xcode Organizer
6. Fill in metadata (screenshots, description, keywords)
7. Set **Price**: **Free**
8. Submit for review (~1–3 business days)

---

## Store Listing Content

Use the following as a starting point for your store listings:

### App Name
**AURA — Free AI Assistant**

### Short Description (80 chars)
Free AI chatbot with voice, tools, and 200B-class intelligence.

### Full Description
```
AURA (AI Unified Reasoning Architecture) is a free, open-source AI assistant
designed to change lives, save lives, and help millions.

✦ COMPLETELY FREE — no subscription, no paywalls, no credit card
✦ 200B-class AI — powered by free cloud services (Groq, Cerebras, OpenRouter)
✦ 20 pre-built modes: Code Helper, Legal Advisor, Financial Advisor, and more
✦ Voice input — speak your questions naturally
✦ 15 built-in tools: web search, calculator, weather, code runner, and more
✦ Works on any device — phone, tablet, or desktop
✦ Private — your data stays yours

AI should not be locked behind paywalls. AURA is for everyone.
```

### Category
- Google Play: **Productivity**
- Microsoft Store: **Productivity**
- App Store: **Productivity**

---

## Free Cloud Server Hosting

AURA needs a server to handle inference. Free hosting options:

| Provider | Free Tier | Notes |
|---|---|---|
| **Railway** | $5/month credit | Easiest deployment |
| **Render** | 750 hrs/month | Free tier available |
| **Fly.io** | 3 shared-CPU VMs free | Good for global deploys |
| **Google Cloud Run** | 2M requests/month free | Scales to zero |
| **Oracle Cloud** | Always-free ARM VMs | Best free compute |

See [cloud-deployment.md](cloud-deployment.md) for step-by-step guides.

---

## Contact & Support

- GitHub: <https://github.com/Cbetts1/AI-MODEL-200B->
- Founded by **Christopher Betts**
- License: Apache 2.0
