# Omarchy TV OS for VIDAA (`omavidaa`)

> **Omarchy TV OS** is a custom Linux-inspired tiling desktop shell (Hyprland / Waybar / Walker aesthetic) and standalone application runtime engineered for **Hisense & VIDAA Smart TVs** (MediaTek MTK9602 SoC, Chromium 111 Odin runtime).

![Omarchy TV OS](omarchy-vidaa-app/thumbnail.png)

---

## ✨ Features

- **Hyprland Tiling Aesthetic:** Tokyo Night, Gruvbox, Catppuccin, Nord, Everforest, and Kanagawa palettes with dynamic palette cycling.
- **Full In-App Web Browser:** Free web browsing, custom URL input, search engine integration, and instant bookmarks (*YouTube, Google, Wikipedia, Twitch, Hacker News, Reddit, Plex*).
- **True Borderless Fullscreen YouTube:**
  - **YouTube TV (Leanback 4K):** Native Smart TV interface optimized for remote D-Pad navigation.
  - **YouTube Web:** Channel, search, and video browsing with 1-click borderless fullscreen expansion (**GREEN button**).
- **Zero Mock Telemetry (100% Live):**
  - Live GPU render benchmarks via WebGL Mali-G52 hardware timing.
  - Live Chromium V8 JS Heap memory tracking.
  - Live hardware panel query: Brand, Model, SoC, Firmware, Resolution, and IP.
- **Direct Hardware Write & HAL Controls:**
  - Adjust panel backlight brightness via `window.vowOS.tvinfo.setBrightness()`.
  - Adjust panel contrast via `window.vowOS.tvinfo.setContrast()`.
  - Adjust audio volume & mute via `TvInfo_setParam()`.
  - Disable tracking & ad targeting (`adTargetEnable: 0`, `eulaAdEnable: 0`).
- **Live Broadcast Tuner:** Mounts and controls the physical TV tuner via `window.oipfObjectFactory.createVideoBroadcastObject()`.
- **Ghostty Host Bridge:** Run host diagnostics and query internal Phoenix IPC (`localhost:9009`).
- **100% TV Remote Mapped:**
  - **D-Pad (Up, Down, Left, Right):** Focus navigation across cards and buttons.
  - **OK / Enter:** Launch selected app or activate control.
  - **BACK (keyCode 461 / 8):** Smart exit — exits fullscreen first, then closes in-app browser window to return to dock.
  - **RED / 1:** Workspace 1 (Walker Dock & Launcher).
  - **GREEN / 2:** Toggle Fullscreen in browser (or Workspace 2: Media & TV Tuner).
  - **YELLOW / 3:** Workspace 3 (Ghostty Shell & Live Telemetry).
  - **BLUE / 4:** Workspace 4 (HAL Hardware Controls).
  - **0 Button:** Cycle color themes.

---

## 📁 Repository Structure

```
.
├── omarchy-vidaa-app/        # Unpacked standalone VIDAA app bundle
│   ├── appinfo.json          # Official VIDAA manifest (org.omarchy.tvos)
│   ├── manifest.json         # Web App manifest
│   ├── index.html            # Standalone Omarchy TV OS runtime
│   └── *.png                 # App icons (80x80, 192x192, 512x512)
├── omarchy-vidaa-app.zip     # Packaged ZIP ready for VIDAA sideloading
├── inspector_server.py       # Live HTTP/WebSocket server & remote hot-reloader
├── package_vidaa_app.py      # App packager & icon generator
├── lan_scanner.py            # Local network scanner & TV discovery utility
├── tv_dump.json              # Full hardware, SoC, and native bridge dump
├── tv_bridge_source.json     # Decompiled VIDAA internal JS bridge sources
└── tv_cmd_results.jsonl      # Live command execution audit log from TV
```

---

## 🚀 Installation & Usage

### Method 1: Run via Local / Cloudflare Server (Recommended for Development)
1. Start the server on your development machine:
   ```bash
   python3 inspector_server.py
   ```
2. Expose the port (e.g. via Cloudflare Tunnel):
   ```bash
   cloudflared tunnel --url http://localhost:8765
   ```
3. Open the public URL in your TV's browser. It will automatically cache as a PWA and connect to the live hot-reload command channel.

### Method 2: Sideload as Standalone VIDAA Application
1. Copy `omarchy-vidaa-app.zip` or the `omarchy-vidaa-app/` folder to a FAT32-formatted USB flash drive under `hisense_apps/org.omarchy.tvos/`.
2. Insert into the TV's USB port.
3. Open the TV's **App Installer / Media Center** and select **Install App**.

---

## 🔬 Reverse Engineering Notes

- **SoC:** MediaTek MTK9602 (Quad-Core ARM Cortex-A53, `armv7l` 32-bit userland on 64-bit kernel).
- **GPU:** ARM Mali-G52 (OpenGL ES 2.0 / WebGL 1.0).
- **Security:** Hardware-fused RSA Secure Boot + dm-verity on read-only SquashFS partitions.
- **Internal Daemons:**
  - REST: `http://localhost:9009/service/{tvinfo|hiutils|pkgmgr}`
  - WebSocket: `wss://localhost:9888` (`phoenix://service/tvinfo`)

---

## 📄 License
MIT License. Created by [Anas](https://github.com/anax).
