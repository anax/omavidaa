#!/usr/bin/env python3
"""
OMARCHY TV OS v8.0 // EXTENDED SCREEN & REMOTE SERVER
"""

import http.server
import json
import os
import subprocess
import urllib.request
import urllib.parse
import datetime
from pathlib import Path

PORT = 8765
BASE_DIR = Path(__file__).parent
KEYLOG_FILE = BASE_DIR / "tv_keycodes.log"
REMOTE_FILE = BASE_DIR / "remote.html"

PENDING_COMMANDS = []

SAFE_MAC_COMMANDS = {
    "uname": ["uname", "-a"],
    "uptime": ["uptime"],
    "df": ["df", "-h"],
    "ls_workspace": ["ls", "-la", str(BASE_DIR)],
    "whoami": ["whoami"],
    "date": ["date"],
}

SW_JS = r"""
const CACHE_NAME = 'omarchy-tv-os-v8';
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/') || url.pathname === '/poll_cmd') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
"""

MANIFEST_JSON = json.dumps({
    "name": "Omarchy TV OS",
    "short_name": "Omarchy",
    "start_url": "/",
    "display": "fullscreen",
    "background_color": "#1a1b26",
    "theme_color": "#7aa2f7"
}, indent=2)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OMARCHY TV OS // EXTENDED SCREEN &amp; REMOTE</title>
<link rel="manifest" href="/manifest.json">
<style>
  :root, [data-theme="tokyonight"] {
    --bg: #1a1b26; --bg-alt: #16161e; --bg-panel: rgba(22, 22, 30, 0.94);
    --fg: #c0caf5; --muted: #565f89; --accent: #7aa2f7; --accent2: #bb9af7;
    --green: #9ece6a; --amber: #e0af68; --red: #f7768e; --cyan: #7dcfff; --border: #292e42;
  }
  [data-theme="gruvbox"] {
    --bg: #1d2021; --bg-alt: #282828; --bg-panel: rgba(40, 40, 40, 0.94);
    --fg: #ebdbb2; --muted: #928374; --accent: #fabd2f; --accent2: #d3869b;
    --green: #b8bb26; --amber: #fe8019; --red: #fb4934; --cyan: #8ec07c; --border: #3c3836;
  }
  [data-theme="catppuccin"] {
    --bg: #11111b; --bg-alt: #1e1e2e; --bg-panel: rgba(30, 30, 46, 0.94);
    --fg: #cdd6f4; --muted: #6c7086; --accent: #cba6f7; --accent2: #f5c2e7;
    --green: #a6e3a1; --amber: #fab387; --red: #f38ba8; --cyan: #89dceb; --border: #313244;
  }
  [data-theme="nord"] {
    --bg: #242933; --bg-alt: #2e3440; --bg-panel: rgba(46, 52, 64, 0.94);
    --fg: #eceff4; --muted: #616e88; --accent: #88c0d0; --accent2: #b48ead;
    --green: #a3be8c; --amber: #ebcb8b; --red: #bf616a; --cyan: #8fbcbb; --border: #3b4252;
  }
  [data-theme="everforest"] {
    --bg: #1e2326; --bg-alt: #272e33; --bg-panel: rgba(39, 46, 51, 0.94);
    --fg: #d3c6aa; --muted: #7a8478; --accent: #a7c080; --accent2: #d699b6;
    --green: #a7c080; --amber: #dbbc7f; --red: #e67e80; --cyan: #83c092; --border: #374145;
  }
  [data-theme="kanagawa"] {
    --bg: #16161d; --bg-alt: #1f1f28; --bg-panel: rgba(31, 31, 40, 0.94);
    --fg: #dcd7ba; --muted: #727169; --accent: #7e9cd8; --accent2: #957fb8;
    --green: #98bb6c; --amber: #ffa066; --red: #e46876; --cyan: #7fb4ca; --border: #2a2a37;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  html, body {
    width: 100vw; height: 100vh; overflow: hidden;
    background: var(--bg); color: var(--fg);
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 13px; line-height: 1.4;
  }

  #ambient-canvas {
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    z-index: 0; pointer-events: none; opacity: 0.35;
  }
  .waybar, .workspace, .footer-bar, #app-window-overlay, #remote-qr-modal, #floating-pip-container {
    position: relative; z-index: 1;
  }

  /* WAYBAR TOP STATUS BAR */
  .waybar {
    height: 42px; background: var(--bg-alt); border-bottom: 2px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; padding: 0 14px;
  }
  .wb-left, .wb-center, .wb-right { display: flex; align-items: center; gap: 8px; }
  .distro-pill {
    background: var(--accent); color: #111; font-weight: 800;
    padding: 4px 10px; border-radius: 4px; font-size: 13px; letter-spacing: 0.5px;
  }
  .ws-btn {
    padding: 4px 10px; border-radius: 4px; background: var(--bg);
    border: 1px solid var(--border); color: var(--muted);
    font-size: 12px; font-weight: bold; cursor: pointer;
    display: flex; align-items: center; gap: 6px;
  }
  .ws-btn.active {
    border-color: var(--accent); color: var(--fg);
    background: rgba(122, 162, 247, 0.18);
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dot-red { background: #f7768e; }
  .dot-green { background: #9ece6a; }
  .dot-yellow { background: #e0af68; }
  .dot-blue { background: #7aa2f7; }

  .stat-pill {
    background: var(--bg); border: 1px solid var(--border);
    padding: 3px 9px; border-radius: 4px; font-size: 12px; color: var(--fg);
  }
  .stat-pill b { color: var(--cyan); }

  /* HYPRLAND WORKSPACE CONTAINER */
  .workspace {
    display: none; width: 100vw; height: calc(100vh - 74px);
    padding: 12px; gap: 12px;
  }
  .workspace.active { display: grid; }
  #ws-1 { grid-template-columns: 1.35fr 0.65fr; grid-template-rows: 1fr; }
  #ws-2 { grid-template-columns: 1.3fr 0.7fr; grid-template-rows: 1fr; }
  #ws-3 { grid-template-columns: 1.15fr 0.85fr; grid-template-rows: 1fr; }
  #ws-4 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr; }

  .tile {
    background: var(--bg-panel); border: 2px solid var(--border);
    border-radius: 8px; display: flex; flex-direction: column; overflow: hidden;
  }
  .tile.focused {
    border-color: var(--accent);
    box-shadow: 0 0 20px rgba(122, 162, 247, 0.2);
  }
  .tile-bar {
    height: 32px; background: rgba(0, 0, 0, 0.35);
    border-bottom: 1px solid var(--border); padding: 0 12px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 12px; color: var(--muted);
  }
  .tile.focused .tile-bar { color: var(--accent); font-weight: bold; }
  .tile-body { flex: 1; padding: 12px; overflow-y: auto; }

  /* HERO SHOWCASE CARD */
  .hero-card {
    background: linear-gradient(135deg, rgba(122, 162, 247, 0.15) 0%, rgba(187, 154, 247, 0.08) 50%, rgba(18, 19, 28, 0.95) 100%);
    border: 2px solid var(--accent); border-radius: 8px; padding: 16px 18px;
    margin-bottom: 12px; position: relative; overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  .hero-tag {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(122, 162, 247, 0.2); color: var(--cyan);
    border: 1px solid var(--accent); padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 6px;
  }
  .hero-title { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 4px; }
  .hero-desc { font-size: 11px; color: var(--muted); line-height: 1.4; margin-bottom: 10px; max-width: 90%; }
  .hero-actions { display: flex; gap: 6px; flex-wrap: wrap; }

  /* ENHANCED APP GRID & CARDS */
  .app-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 8px; margin-bottom: 12px;
  }
  .app-card {
    background: rgba(17, 18, 26, 0.85); backdrop-filter: blur(8px);
    border: 1.5px solid var(--border); border-radius: 8px;
    padding: 10px 10px; text-align: left; cursor: pointer;
    display: flex; flex-direction: column; justify-content: space-between;
    min-height: 74px; color: var(--fg); font-family: inherit;
    transition: all 0.15s ease-out; position: relative; overflow: hidden;
  }
  .app-card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .app-card-icon { font-size: 16px; }
  .app-badge {
    font-size: 9px; font-weight: 800; padding: 2px 5px; border-radius: 3px;
    background: rgba(255, 255, 255, 0.08); color: var(--cyan);
    border: 1px solid rgba(125, 207, 255, 0.25);
  }
  .app-card .app-name { font-size: 12px; font-weight: 700; color: var(--fg); }
  .app-card .app-desc { font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .nav-btn {
    display: inline-block; background: var(--bg);
    border: 1px solid var(--border); color: var(--fg);
    padding: 6px 10px; margin: 2px; border-radius: 4px;
    font-family: inherit; font-size: 12px; cursor: pointer;
  }
  .nav-btn.selected, .nav-btn:focus, .app-card.selected, .app-card:focus {
    border-color: var(--accent);
    background: rgba(122, 162, 247, 0.22);
    color: #fff; outline: none;
    box-shadow: 0 0 14px rgba(122, 162, 247, 0.35);
  }

  /* LIVE PULSE TICKER */
  .pulse-ticker {
    background: rgba(13, 14, 20, 0.9); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 12px; display: flex; align-items: center;
    gap: 10px; margin-top: 8px; font-size: 11px;
  }
  .pulse-dot {
    width: 8px; height: 8px; border-radius: 50%; background: var(--red);
    box-shadow: 0 0 8px var(--red); animation: pulse-glow 1.5s infinite;
  }
  @keyframes pulse-glow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }
  .pulse-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--fg); }
  .pulse-text b { color: var(--amber); }

  #gpu-canvas-graph {
    width: 100%; height: 44px; background: #0d0e14;
    border: 1px solid var(--border); border-radius: 4px;
    margin-top: 6px; margin-bottom: 8px; display: block;
  }

  .fastfetch {
    display: flex; gap: 12px; margin-bottom: 10px;
    border-bottom: 1px solid var(--border); padding-bottom: 10px;
  }
  .ascii-logo {
    color: var(--accent); font-size: 10px; line-height: 1.15;
    white-space: pre; font-weight: bold;
  }
  .specs-list { font-size: 11px; flex: 1; }
  .specs-list div { margin-bottom: 3px; }
  .specs-list b { color: var(--amber); display: inline-block; width: 105px; }

  .term-out {
    background: #0d0e14; border: 1px solid var(--border);
    border-radius: 4px; padding: 10px; font-size: 12px;
    height: 220px; overflow-y: auto; white-space: pre-wrap;
    word-break: break-word; color: var(--fg); margin-top: 8px;
  }

  .meter-row { margin-bottom: 7px; }
  .meter-label { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; }
  .meter-track { width: 100%; height: 8px; background: #0d0e14; border-radius: 3px; overflow: hidden; }
  .meter-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--cyan)); transition: width 0.25s ease; }

  .hw-card {
    border: 1px solid var(--border); background: #101118;
    border-radius: 6px; padding: 9px; margin-bottom: 8px;
  }
  .hw-card-title { color: var(--amber); font-weight: bold; margin-bottom: 5px; font-size: 11px; }

  .input-box {
    background: #0d0e14; border: 1px solid var(--border); color: var(--fg);
    padding: 7px 10px; border-radius: 4px; font-family: inherit; font-size: 12px;
  }

  .footer-bar {
    height: 32px; background: var(--bg-alt); border-top: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 14px; font-size: 12px; color: var(--muted);
  }
  .key-hint { margin-right: 12px; }
  .key-hint kbd {
    background: var(--bg); border: 1px solid var(--border);
    padding: 1px 6px; border-radius: 3px; color: var(--cyan); font-size: 11px;
  }

  /* FULLSCREEN IN-APP WEB BROWSER OVERLAY */
  #app-window-overlay {
    display: none; position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: var(--bg); z-index: 9999;
    flex-direction: column;
  }
  #app-window-overlay.open { display: flex; }
  #app-window-overlay.fullscreen-active .app-win-bar,
  #app-window-overlay.fullscreen-active #browser-toolbar {
    display: none !important;
  }

  .app-win-bar {
    height: 40px; background: var(--bg-alt);
    border-bottom: 2px solid var(--accent);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 14px; font-size: 13px; color: var(--fg);
  }

  #browser-toolbar {
    background: #111218; border-bottom: 1px solid var(--border);
    padding: 6px 14px; display: flex; flex-direction: column; gap: 6px;
  }
  .browser-nav-row { display: flex; align-items: center; gap: 6px; }
  .browser-bookmarks-row { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }

  /* EXTENDED SCREEN / DUAL-PANE VIEWPORTS */
  .app-win-body {
    flex: 1; width: 100%; height: 100%;
    overflow: hidden; position: relative; background: #000;
    display: flex;
  }
  .dual-pane {
    flex: 1; height: 100%; border: none; background: #000;
  }
  #dual-pane-divider {
    display: none; width: 4px; height: 100%; background: var(--border);
    border-left: 1px solid var(--accent); cursor: col-resize;
  }
  .dual-active #browser-frame-secondary,
  .dual-active #dual-pane-divider {
    display: block !important;
  }

  /* FLOATING PICTURE-IN-PICTURE (PiP) CONTAINER */
  #floating-pip-container {
    display: none; position: fixed;
    bottom: 24px; right: 24px; width: 380px; height: 214px;
    background: #000; border: 2px solid var(--accent); border-radius: 8px;
    z-index: 10000; box-shadow: 0 10px 35px rgba(0,0,0,0.7);
    overflow: hidden; flex-direction: column;
  }
  #floating-pip-container.active { display: flex; }
  .pip-header {
    height: 26px; background: rgba(22, 22, 30, 0.95);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 8px; font-size: 11px; color: var(--cyan); border-bottom: 1px solid var(--border);
  }
  .pip-frame { flex: 1; width: 100%; height: 100%; border: none; }

  /* PHONE REMOTE QR CODE MODAL */
  #remote-qr-modal {
    display: none; position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(10, 11, 16, 0.88); backdrop-filter: blur(8px);
    z-index: 10001; align-items: center; justify-content: center;
  }
  #remote-qr-modal.open { display: flex; }
  .qr-modal-box {
    background: var(--bg-panel); border: 2px solid var(--accent);
    border-radius: 12px; padding: 24px; max-width: 440px; text-align: center;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6);
  }
  .qr-img {
    width: 200px; height: 200px; margin: 14px auto; background: #fff;
    padding: 8px; border-radius: 8px; display: block;
  }

  #media-stage {
    width: 100%; height: 64%; background: #000;
    border: 1px solid var(--border); border-radius: 4px;
    position: relative; overflow: hidden;
  }
  video, #oipf-broadcast-container { width: 100%; height: 100%; }
</style>
</head>
<body data-theme="tokyonight">

<!-- AMBIENT GPU PARTICLE CANVAS -->
<canvas id="ambient-canvas"></canvas>

<!-- FLOATING PICTURE-IN-PICTURE CONTAINER -->
<div id="floating-pip-container">
  <div class="pip-header">
    <b>🖼️ PiP: <span id="pip-title">YouTube 4K</span></b>
    <div style="display:flex;gap:4px;">
      <button class="nav-btn" style="padding:1px 6px;font-size:10px;" onclick="expandPipToMain()">⛶ Expand</button>
      <button class="nav-btn" style="padding:1px 6px;font-size:10px;color:var(--red);" onclick="togglePipMode(false)">✕ Close</button>
    </div>
  </div>
  <iframe id="pip-iframe" class="pip-frame" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>
</div>

<!-- PHONE REMOTE QR CODE MODAL -->
<div id="remote-qr-modal">
  <div class="qr-modal-box">
    <div class="distro-pill" style="display:inline-block;margin-bottom:8px;">MOBILE PHONE REMOTE</div>
    <h2 style="color:#fff;font-size:18px;margin-bottom:6px;">Scan to Control Your TV</h2>
    <p style="color:var(--muted);font-size:12px;">Open your iPhone or Android camera to point-and-control your TV with touch D-Pad, phone keyboard, split-screen toggles, and volume.</p>
    <img id="qr-code-img" class="qr-img" src="" alt="Remote QR Code">
    <div style="margin-bottom:12px;font-size:12px;color:var(--cyan);word-break:break-all;" id="qr-url-text">Loading URL...</div>
    <div style="display:flex;gap:8px;justify-content:center;">
      <button class="nav-btn selected" onclick="closeRemoteQrModal()">Close (Remote BACK)</button>
      <button class="nav-btn" onclick="openRemoteInNewTab()">Open on this Device</button>
    </div>
  </div>
</div>

<!-- FULLSCREEN IN-APP WEB BROWSER / EXTENDED SCREEN -->
<div id="app-window-overlay">
  <div class="app-win-bar" id="app-win-bar">
    <div style="display:flex;align-items:center;gap:8px;">
      <span class="distro-pill" id="app-win-pill">WEB</span>
      <b id="app-win-title" style="color:var(--cyan)">In-App Web Browser</b>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <button class="nav-btn inapp-ctrl-btn" id="btn-toggle-dual" onclick="toggleDualScreen()">🪟 Dual Split 50/50 (Key 5)</button>
      <button class="nav-btn inapp-ctrl-btn" id="btn-toggle-pip" onclick="togglePipMode()">🖼️ Float PiP (Key 6)</button>
      <button class="nav-btn inapp-ctrl-btn selected" id="btn-toggle-fullscreen" onclick="toggleBrowserFullscreen()">⛶ Fullscreen (GREEN / 2)</button>
      <button class="nav-btn inapp-ctrl-btn" id="app-win-close-btn" onclick="closeInAppWindow()">✖ Close (Remote BACK)</button>
    </div>
  </div>

  <div id="browser-toolbar">
    <div class="browser-nav-row">
      <button class="nav-btn inapp-ctrl-btn" onclick="browserGoBack()">◀ Back</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browserGoForward()">▶ Fwd</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browserReload()">↻ Reload</button>
      <input id="browser-url-input" class="input-box" style="flex:1;font-size:13px;padding:6px 12px;" placeholder="Website address or search query" value="https://fis.com.mv" onclick="Hisense_enableVKB && Hisense_enableVKB()">
      <button class="nav-btn inapp-ctrl-btn" onclick="navigateToInputUrl()">Go</button>
    </div>
    <div class="browser-bookmarks-row">
      <span style="color:var(--muted);font-size:11px;margin-right:4px;">QUICK:</span>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://fis.com.mv', 'Flight Info (FIS)')">✈️ Flight Info (FIS)</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://www.youtube.com/tv', 'YouTube TV (4K Leanback)')">📺 YouTube TV</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://m.youtube.com', 'YouTube Web')">▶ YouTube Web</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://www.google.com', 'Google Search')">🔍 Google</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://en.m.wikipedia.org', 'Wikipedia')">📖 Wikipedia</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://www.twitch.tv', 'Twitch')">🟣 Twitch</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://news.ycombinator.com', 'Hacker News')">⚡ Hacker News</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://old.reddit.com', 'Reddit')">👽 Reddit</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="browseTo('https://app.plex.tv/desktop', 'Plex TV')">🎥 Plex TV</button>
    </div>
  </div>

  <!-- MULTI-VIEWPORT WORKSPACE (DUAL EXTENDED SCREEN 50/50) -->
  <div class="app-win-body" id="app-win-body">
    <!-- Primary Viewport -->
    <iframe id="browser-frame" class="dual-pane"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
      allowfullscreen="true" webkitallowfullscreen="true" mozallowfullscreen="true">
    </iframe>

    <div id="dual-pane-divider"></div>

    <!-- Secondary Viewport (Extended Screen) -->
    <iframe id="browser-frame-secondary" class="dual-pane" style="display:none;"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
      allowfullscreen="true" webkitallowfullscreen="true" mozallowfullscreen="true">
    </iframe>
  </div>
</div>

<!-- TOP WAYBAR -->
<div class="waybar">
  <div class="wb-left">
    <div class="distro-pill">OMARCHY LIVE</div>
    <div class="ws-btn active" id="wb-ws-1" onclick="switchWorkspace(1)">
      <span class="dot dot-red"></span> 1:DOCK
    </div>
    <div class="ws-btn" id="wb-ws-2" onclick="switchWorkspace(2)">
      <span class="dot dot-green"></span> 2:MEDIA &amp; TV
    </div>
    <div class="ws-btn" id="wb-ws-3" onclick="switchWorkspace(3)">
      <span class="dot dot-yellow"></span> 3:SYSTEM
    </div>
    <div class="ws-btn" id="wb-ws-4" onclick="switchWorkspace(4)">
      <span class="dot dot-blue"></span> 4:HAL WRITE
    </div>
  </div>

  <div class="wb-center">
    <button class="ws-btn" onclick="openRemoteQrModal()" style="border-color:var(--cyan);color:var(--cyan);">
      <span>📱</span> Mobile Remote (QR)
    </button>
    <button class="ws-btn" onclick="toggleDualScreen()" style="border-color:var(--amber);color:var(--amber);">
      <span>🪟</span> Dual Split 50/50
    </button>
    <div class="stat-pill"><span id="wb-live-model">CONNECTING...</span> // <b id="wb-theme-name">TOKYO NIGHT</b></div>
  </div>

  <div class="wb-right">
    <div class="stat-pill">VOL <b id="wb-vol">--</b></div>
    <div class="stat-pill">BRI <b id="wb-bri">--</b></div>
    <div class="stat-pill">CON <b id="wb-con">--</b></div>
    <div class="stat-pill">RTT <b id="wb-rtt">-- ms</b></div>
    <div class="stat-pill"><b id="wb-clock">--:--:--</b></div>
  </div>
</div>

<!-- WORKSPACE 1: WALKER APP DOCK (CINEMATIC LIVING HOME) -->
<div class="workspace active" id="ws-1">
  <div class="tile focused">
    <div class="tile-bar">
      <span>walker // Application Launcher &amp; Living Dashboard</span>
      <span>[D-PAD + ENTER]</span>
    </div>
    <div class="tile-body">
      <!-- HERO SHOWCASE CARD -->
      <div class="hero-card">
        <div class="hero-tag">FEATURED // 4K HDR 60FPS</div>
        <div class="hero-title">YouTube TV &bull; Leanback 4K Cinema</div>
        <div class="hero-desc">Official Smart TV interface engineered for remote D-Pad navigation, spatial audio, and borderless fullscreen viewing on your 65" panel.</div>
        <div class="hero-actions">
          <button class="nav-btn selected" onclick="browseTo('https://www.youtube.com/tv', 'YouTube TV', true)">▶ Launch 4K Fullscreen</button>
          <button class="nav-btn" onclick="browseTo('https://fis.com.mv', 'Flight Info (FIS)')">✈️ Flight Info (FIS)</button>
          <button class="nav-btn" onclick="toggleDualScreen(true)">🪟 Dual Split (FIS + YouTube)</button>
          <button class="nav-btn" onclick="openRemoteQrModal()">📱 Phone Remote QR</button>
        </div>
      </div>

      <!-- 12 APP LAUNCHER CARDS -->
      <div class="app-grid" id="app-dock-grid"></div>

      <!-- LIVE PULSE BREAKING TICKER -->
      <div class="pulse-ticker">
        <div class="pulse-dot"></div>
        <div class="pulse-text" id="pulse-text">Loading live tech pulse from Hacker News...</div>
      </div>

      <!-- QUICK URL LAUNCH BAR -->
      <div class="hw-card" style="margin-top:10px;">
        <div class="hw-card-title">QUICK WEB NAVIGATOR</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">
          <input id="custom-app-url" class="input-box" style="flex:1;min-width:260px;" placeholder="Enter any URL or search keywords" value="https://fis.com.mv" onclick="Hisense_enableVKB && Hisense_enableVKB()">
          <button class="nav-btn" onclick="launchCustomUrl()">Browse</button>
          <button class="nav-btn" onclick="addCustomPin()">+ Pin Card</button>
          <button class="nav-btn" onclick="resetCustomApps()">Reset</button>
        </div>
      </div>
    </div>
  </div>

  <div class="tile">
    <div class="tile-bar">
      <span>telemetry // Extended Screen &amp; Remote Control</span>
      <span>[LIVE SENSORS]</span>
    </div>
    <div class="tile-body">
      <div class="fastfetch">
        <div class="ascii-logo">      /\
     /  \
    /\   \
   /  ,,  \
  /  |  | -\
 /_-''  ''-_\</div>
        <div class="specs-list" id="live-specs-list">
          <div><b>Host:</b> <span id="spec-host">Querying...</span></div>
          <div><b>SoC / Chip:</b> <span id="spec-chip">Querying...</span></div>
          <div><b>GPU:</b> <span id="spec-gpu">Querying...</span></div>
          <div><b>OS / Build:</b> <span id="spec-os">Querying...</span></div>
          <div><b>Firmware:</b> <span id="spec-fw">Querying...</span></div>
          <div><b>Resolution:</b> <span id="spec-res">Querying...</span></div>
          <div><b>IP Address:</b> <span id="spec-ip">Querying...</span></div>
          <div><b>Ad Target:</b> <span id="spec-ad">Querying...</span></div>
        </div>
      </div>

      <!-- EXTENDED SCREEN CONTROLS -->
      <div class="hw-card">
        <div class="hw-card-title">EXTENDED SCREEN &amp; TILING</div>
        <button class="nav-btn" onclick="toggleDualScreen()">🪟 Toggle 50/50 Dual Screen</button>
        <button class="nav-btn" onclick="togglePipMode()">🖼️ Toggle Floating PiP</button>
        <button class="nav-btn" onclick="openRemoteQrModal()">📱 Connect Phone Remote</button>
      </div>

      <!-- LIVE GPU LATENCY OSCILLOSCOPE GRAPH -->
      <div class="hw-card">
        <div class="hw-card-title">MALI-G52 GPU RENDER OSCILLOSCOPE (60 FPS)</div>
        <canvas id="gpu-canvas-graph" width="280" height="44"></canvas>
        <div class="meter-row">
          <div class="meter-label"><span>Render Latency (WebGL)</span><span id="gpu-frame-txt">-- ms</span></div>
          <div class="meter-track"><div class="meter-fill" id="gpu-frame-bar" style="width:0%"></div></div>
        </div>
        <div class="meter-row">
          <div class="meter-label"><span>JS Heap Memory (V8)</span><span id="mem-heap-txt">-- MB</span></div>
          <div class="meter-track"><div class="meter-fill" id="mem-heap-bar" style="width:0%"></div></div>
        </div>
      </div>

      <!-- QUICK HARDWARE PRESETS -->
      <div class="hw-card">
        <div class="hw-card-title">PANEL PRESETS (vowOS HAL)</div>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(80)">Day 80%</button>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(50)">Cinema 50%</button>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(25)">Night 25%</button>
        <button class="nav-btn" onclick="toggleMute()">Mute</button>
        <button class="nav-btn" onclick="cycleTheme()">Theme (0)</button>
      </div>
    </div>
  </div>
</div>

<!-- WORKSPACE 2: LIVE BROADCAST TUNER & MPV STREAMER -->
<div class="workspace" id="ws-2">
  <div class="tile focused">
    <div class="tile-bar">
      <span>mpv // Hardware Streamer &amp; Live OIPF Broadcast</span>
      <span id="stream-status">STANDBY</span>
    </div>
    <div class="tile-body">
      <div id="media-stage">
        <video id="tv-player" controls></video>
        <div id="oipf-broadcast-container" style="display:none;"></div>
      </div>
      <div style="margin-top:10px;">
        <button class="nav-btn" onclick="bindLiveBroadcast()">Mount Live Broadcast Tuner</button>
        <button class="nav-btn" onclick="channelStep(1)">Channel +</button>
        <button class="nav-btn" onclick="channelStep(-1)">Channel -</button>
        <button class="nav-btn" onclick="playLiveStream('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4', 'Tears of Steel (1080p MP4)')">Play Tears of Steel</button>
        <button class="nav-btn" onclick="playLiveStream('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 'Big Buck Bunny (1080p MP4)')">Play Big Buck Bunny</button>
        <button class="nav-btn" onclick="toggleFullscreenVideo()">Fullscreen</button>
        <button class="nav-btn" onclick="stopStream()">Stop Playback</button>
      </div>
    </div>
  </div>

  <div class="tile">
    <div class="tile-bar">
      <span>media-stats // Live Player &amp; Tuner Telemetry</span>
      <span>[LIVE METRICS]</span>
    </div>
    <div class="tile-body">
      <div style="margin-bottom:8px;">
        <input id="custom-stream-url" class="input-box" style="width:68%" placeholder="https://.../stream.m3u8" onclick="Hisense_enableVKB && Hisense_enableVKB()">
        <button class="nav-btn" onclick="playCustomStream()">Stream</button>
      </div>
      <div class="term-out" id="media-log" style="height:340px;">Ready. Media state and broadcast events will stream live here.</div>
    </div>
  </div>
</div>

<!-- WORKSPACE 3: REAL GHOSTTY TERMINAL & REAL HARDWARE METRICS -->
<div class="workspace" id="ws-3">
  <div class="tile focused">
    <div class="tile-bar">
      <span>ghostty // Interactive Host &amp; Phoenix Shell</span>
      <span>[LIVE EXEC]</span>
    </div>
    <div class="tile-body">
      <div style="margin-bottom:6px;color:var(--cyan);font-size:12px;">EXECUTE COMMANDS:</div>
      <div>
        <button class="nav-btn" onclick="runLiveHostCmd('uname')">Mac: uname -a</button>
        <button class="nav-btn" onclick="runLiveHostCmd('uptime')">Mac: uptime</button>
        <button class="nav-btn" onclick="runLiveHostCmd('df')">Mac: df -h</button>
        <button class="nav-btn" onclick="runLiveHostCmd('ls_workspace')">Mac: ls VIDAA</button>
        <button class="nav-btn" onclick="fetchLivePackages()">TV: Query Installed Packages</button>
        <button class="nav-btn" onclick="dumpLiveSensors()">TV: Query All Native Bridges</button>
      </div>
      <div class="term-out" id="term-output" style="height:350px;">[omarchy@vidaa ~]$ Ready for live execution. Select a command above.</div>
    </div>
  </div>

  <div class="tile">
    <div class="tile-bar">
      <span>btop // Live Telemetry &amp; Remote Key Sniffer</span>
      <span>[REAL TIMING]</span>
    </div>
    <div class="tile-body">
      <div class="hw-card">
        <div class="hw-card-title">REMOTE KEY SNIFFER (LIVE TV CODES)</div>
        <div class="term-out" id="key-sniffer-box" style="height:280px;">Press any TV remote button to sniff keyCode...</div>
      </div>
    </div>
  </div>
</div>

<!-- WORKSPACE 4: REAL HARDWARE WRITE & PHOENIX IPC CALLER -->
<div class="workspace" id="ws-4">
  <div class="tile focused">
    <div class="tile-bar">
      <span>vidaa-hal // Live Hardware Write Controls</span>
      <span>[REAL READ/WRITE]</span>
    </div>
    <div class="tile-body">
      <div class="hw-card">
        <div class="hw-card-title">PANEL BRIGHTNESS (vowOS.tvinfo.setBrightness)</div>
        <button class="nav-btn" onclick="setLiveBrightness(-10)">Brightness -10</button>
        <button class="nav-btn" onclick="setLiveBrightness(10)">Brightness +10</button>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(35)">Preset 35%</button>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(70)">Preset 70%</button>
        <button class="nav-btn" onclick="setLiveBrightnessPreset(100)">Preset 100%</button>
      </div>

      <div class="hw-card">
        <div class="hw-card-title">PANEL CONTRAST (vowOS.tvinfo.setContrast)</div>
        <button class="nav-btn" onclick="setLiveContrast(-10)">Contrast -10</button>
        <button class="nav-btn" onclick="setLiveContrast(10)">Contrast +10</button>
        <button class="nav-btn" onclick="setLiveContrastPreset(50)">Preset 50%</button>
        <button class="nav-btn" onclick="setLiveContrastPreset(80)">Preset 80%</button>
      </div>

      <div class="hw-card">
        <div class="hw-card-title">AUDIO VOLUME &amp; MUTE (TvInfo_setParam)</div>
        <button class="nav-btn" onclick="adjustVolume(-2)">Volume -2</button>
        <button class="nav-btn" onclick="adjustVolume(2)">Volume +2</button>
        <button class="nav-btn" onclick="toggleMute()">Toggle Mute</button>
      </div>

      <div class="term-out" id="hal-output" style="height:140px;">Live Hardware Controller Ready.</div>
    </div>
  </div>

  <div class="tile">
    <div class="tile-bar">
      <span>phoenix-rpc // Live http://localhost:9009 Caller</span>
      <span>[REAL RPC]</span>
    </div>
    <div class="tile-body">
      <button class="nav-btn" onclick="callLiveRpc('pkgmgr', 'getInstalledPkgs', '')">pkgmgr: getInstalledPkgs</button>
      <button class="nav-btn" onclick="callLiveRpc('hiutils', 'getOSVersion', '')">hiutils: getOSVersion</button>
      <button class="nav-btn" onclick="callLiveRpc('hiutils', 'getVersionStatus', '')">hiutils: getVersionStatus</button>
      <button class="nav-btn" onclick="callLiveRpc('tvinfo', 'supportHdrAndDolbyVision', '')">tvinfo: HDR</button>
      <button class="nav-btn" onclick="callLiveRpc('tvinfo', 'playerFeatureInfo', '')">tvinfo: PlayerFeature</button>
      <div class="term-out" id="rpc-output" style="height:340px;">Select an RPC endpoint above. Response will be queried live from localhost:9009.</div>
    </div>
  </div>
</div>

<!-- BOTTOM BAR -->
<div class="footer-bar">
  <div>
    <span class="key-hint"><kbd>RED</kbd>/<kbd>1</kbd> Dock</span>
    <span class="key-hint"><kbd>GREEN</kbd>/<kbd>2</kbd> Fullscreen</span>
    <span class="key-hint"><kbd>5</kbd> Split 50/50</span>
    <span class="key-hint"><kbd>6</kbd> PiP</span>
    <span class="key-hint"><kbd>9</kbd> Phone Remote</span>
    <span class="key-hint"><kbd>D-PAD</kbd> Navigate</span>
    <span class="key-hint"><kbd>ENTER</kbd> Launch</span>
    <span class="key-hint"><kbd>BACK</kbd> Exit / Close</span>
  </div>
  <div id="footer-live-badge">OMARCHY TV OS v8.0</div>
</div>

<script>
var THEMES = ["tokyonight", "gruvbox", "catppuccin", "nord", "everforest", "kanagawa"];
var currentThemeIdx = 0;
var currentWorkspace = 1;
var navIndex = 0;
var inAppNavIndex = 0;
var broadcastObj = null;
var isAppWindowOpen = false;
var isBrowserFullscreen = false;
var isDualScreenActive = false;
var isPipActive = false;
var gpuHistory = new Array(28).fill(16.6);

var liveState = { volume: 0, brightness: 0, contrast: 0, mute: 0 };

var DEFAULT_APPS = [
  { name: "Flight Info (FIS)", desc: "Velana Airport Flights", icon: "✈️", badge: "AIRPORT", url: "https://fis.com.mv" },
  { name: "YouTube TV", desc: "4K Leanback UI", icon: "📺", badge: "4K HDR", url: "https://www.youtube.com/tv" },
  { name: "YouTube Web", desc: "Browse & Search", icon: "▶", badge: "WEB", url: "https://m.youtube.com" },
  { name: "Google Search", desc: "Web Search", icon: "🔍", badge: "SEARCH", url: "https://www.google.com" },
  { name: "Wikipedia", desc: "Encyclopedia", icon: "📖", badge: "WIKI", url: "https://en.m.wikipedia.org" },
  { name: "Twitch", desc: "Live Streams", icon: "🟣", badge: "LIVE", url: "https://www.twitch.tv" },
  { name: "Hacker News", desc: "Tech Stories", icon: "⚡", badge: "NEWS", url: "https://news.ycombinator.com" },
  { name: "Reddit", desc: "Frontpage", icon: "👽", badge: "FORUM", url: "https://old.reddit.com" },
  { name: "Plex TV", desc: "Media Server", icon: "🎥", badge: "MEDIA", url: "https://app.plex.tv/desktop" },
  { name: "4K Cinema", desc: "Tears of Steel", icon: "🎬", badge: "FILM", url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4" },
  { name: "Live Broadcast", desc: "TV Tuner", icon: "📡", badge: "DVB-T2", action: "live_tv" },
  { name: "HAL Controls", desc: "Hardware Write", icon: "⚙️", badge: "SYSTEM", action: "ws_4" }
];

// 1. EXTENDED SCREEN: DUAL-PANE TILING (50/50 SPLIT SCREEN)
function toggleDualScreen(forceVal) {
  isDualScreenActive = (typeof forceVal === "boolean") ? forceVal : !isDualScreenActive;
  var body = document.getElementById("app-win-body");
  var frame2 = document.getElementById("browser-frame-secondary");
  var btn = document.getElementById("btn-toggle-dual");

  if (!isAppWindowOpen && isDualScreenActive) {
    browseTo("https://fis.com.mv", "Flight Info (FIS)");
  }

  if (isDualScreenActive) {
    body.classList.add("dual-active");
    frame2.style.display = "block";
    if (!frame2.src || frame2.src === "about:blank") {
      frame2.src = "https://www.youtube.com/tv";
    }
    if (btn) btn.textContent = "🖥️ Single Pane (Key 5)";
    document.getElementById("app-win-title").textContent = "Dual Screen: Flight Info + YouTube TV";
  } else {
    body.classList.remove("dual-active");
    frame2.style.display = "none";
    if (btn) btn.textContent = "🪟 Dual Split 50/50 (Key 5)";
  }
}

// 2. EXTENDED SCREEN: FLOATING PICTURE-IN-PICTURE (PiP)
function togglePipMode(forceVal) {
  isPipActive = (typeof forceVal === "boolean") ? forceVal : !isPipActive;
  var pip = document.getElementById("floating-pip-container");
  var pipFrame = document.getElementById("pip-iframe");

  if (isPipActive) {
    pip.classList.add("active");
    if (!pipFrame.src || pipFrame.src === "about:blank") {
      pipFrame.src = "https://www.youtube-nocookie.com/embed/jfKfPfyJRdk?autoplay=1";
    }
  } else {
    pip.classList.remove("active");
    pipFrame.removeAttribute("src");
  }
}

function expandPipToMain() {
  var pipFrame = document.getElementById("pip-iframe");
  var src = pipFrame.src;
  togglePipMode(false);
  browseTo(src || "https://www.youtube.com/tv", "Main Viewport", true);
}

// 3. PHONE REMOTE QR CODE MODAL
function openRemoteQrModal() {
  var modal = document.getElementById("remote-qr-modal");
  var img = document.getElementById("qr-code-img");
  var txt = document.getElementById("qr-url-text");

  var remoteUrl = window.location.origin + "/remote";
  txt.textContent = remoteUrl;
  img.src = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + encodeURIComponent(remoteUrl);

  modal.classList.add("open");
}

function closeRemoteQrModal() {
  document.getElementById("remote-qr-modal").classList.remove("open");
  updateButtonSelection();
}

function openRemoteInNewTab() {
  window.open(window.location.origin + "/remote", "_blank");
}

// 4. AMBIENT GPU CANVAS (60FPS STARFIELD)
function initAmbientCanvas() {
  var cvs = document.getElementById("ambient-canvas");
  if (!cvs) return;
  var ctx = cvs.getContext("2d");
  var w = cvs.width = window.innerWidth;
  var h = cvs.height = window.innerHeight;

  var stars = [];
  var count = 35;
  for (var i = 0; i < count; i++) {
    stars.push({
      x: Math.random() * w, y: Math.random() * h,
      r: Math.random() * 1.6 + 0.6,
      dx: (Math.random() - 0.5) * 0.35, dy: (Math.random() - 0.5) * 0.35,
      a: Math.random() * 0.7 + 0.3
    });
  }

  function loop() {
    ctx.clearRect(0, 0, w, h);
    var style = getComputedStyle(document.body);
    var color = style.getPropertyValue("--accent").trim() || "#7aa2f7";

    for (var i = 0; i < count; i++) {
      var s = stars[i];
      s.x += s.dx; s.y += s.dy;
      if (s.x < 0) s.x = w; if (s.x > w) s.x = 0;
      if (s.y < 0) s.y = h; if (s.y > h) s.y = 0;

      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = s.a;
      ctx.fill();
    }

    ctx.globalAlpha = 0.08;
    ctx.strokeStyle = color;
    for (var i = 0; i < count; i++) {
      for (var j = i + 1; j < count; j++) {
        var dx = stars[i].x - stars[j].x;
        var dy = stars[i].y - stars[j].y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100) {
          ctx.beginPath();
          ctx.moveTo(stars[i].x, stars[i].y);
          ctx.lineTo(stars[j].x, stars[j].y);
          ctx.stroke();
        }
      }
    }
    ctx.globalAlpha = 1.0;
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
}

// 5. LIVE PULSE TICKER
function updateLivePulseTicker() {
  fetch("https://hacker-news.firebaseio.com/v0/topstories.json")
    .then(r => r.json())
    .then(ids => fetch("https://hacker-news.firebaseio.com/v0/item/" + ids[0] + ".json"))
    .then(r => r.json())
    .then(item => {
      var el = document.getElementById("pulse-text");
      if (el && item && item.title) {
        el.innerHTML = "<b>LIVE PULSE:</b> " + item.title + " &bull; <b>" + (item.score || 0) + " pts</b> by @" + (item.by || "anon");
        el.onclick = function() { if (item.url) browseTo(item.url, item.title); };
        el.style.cursor = "pointer";
      }
    })
    .catch(e => {});
}

// 6. GPU LATENCY SPARKLINE OSCILLOSCOPE
function recordGpuTime(ms) {
  gpuHistory.push(ms);
  gpuHistory.shift();
  drawGpuGraph();
}

function drawGpuGraph() {
  var cvs = document.getElementById("gpu-canvas-graph");
  if (!cvs) return;
  var ctx = cvs.getContext("2d");
  var w = cvs.width;
  var h = cvs.height;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(255,255,255,0.08)";
  ctx.lineWidth = 1;
  var y60 = h - (16.6 / 35.0) * h;
  ctx.beginPath();
  ctx.moveTo(0, y60);
  ctx.lineTo(w, y60);
  ctx.stroke();

  ctx.beginPath();
  ctx.strokeStyle = "#7dcfff";
  ctx.lineWidth = 1.8;
  var step = w / (gpuHistory.length - 1);
  for (var i = 0; i < gpuHistory.length; i++) {
    var val = Math.min(35.0, gpuHistory[i]);
    var y = h - (val / 35.0) * (h - 8) - 4;
    var x = i * step;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

// 7. IN-APP FULLSCREEN WEB BROWSER
function browseTo(url, title, autoFullscreen) {
  var overlay = document.getElementById("app-window-overlay");
  var frame = document.getElementById("browser-frame");
  var input = document.getElementById("browser-url-input");
  var titleEl = document.getElementById("app-win-title");
  var pillEl = document.getElementById("app-win-pill");

  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    if (url.includes(".") && !url.includes(" ")) {
      url = "https://" + url;
    } else {
      url = "https://www.google.com/search?q=" + encodeURIComponent(url);
    }
  }

  input.value = url;
  titleEl.textContent = title || url;
  pillEl.textContent = (title || "WEB").split(" ")[0].toUpperCase();

  frame.src = url;
  overlay.classList.add("open");
  isAppWindowOpen = true;

  if (autoFullscreen) {
    setBrowserFullscreen(true);
  } else {
    setBrowserFullscreen(false);
  }

  inAppNavIndex = 0;
  updateInAppButtonSelection();
}

function setBrowserFullscreen(enable) {
  isBrowserFullscreen = enable;
  var overlay = document.getElementById("app-window-overlay");
  var fsBtn = document.getElementById("btn-toggle-fullscreen");

  if (enable) {
    overlay.classList.add("fullscreen-active");
    if (fsBtn) fsBtn.textContent = "Exit Fullscreen (Remote BACK)";
  } else {
    overlay.classList.remove("fullscreen-active");
    if (fsBtn) fsBtn.textContent = "⛶ Fullscreen (GREEN / 2)";
  }
}

function toggleBrowserFullscreen() {
  setBrowserFullscreen(!isBrowserFullscreen);
}

function closeInAppWindow() {
  var overlay = document.getElementById("app-window-overlay");
  overlay.classList.remove("open");
  overlay.classList.remove("fullscreen-active");
  isAppWindowOpen = false;
  isBrowserFullscreen = false;
  isDualScreenActive = false;

  var frame = document.getElementById("browser-frame");
  if (frame) frame.removeAttribute("src");
  var frame2 = document.getElementById("browser-frame-secondary");
  if (frame2) { frame2.removeAttribute("src"); frame2.style.display = "none"; }

  updateButtonSelection();
}

function browserReload() {
  var frame = document.getElementById("browser-frame");
  if (frame && frame.src) frame.src = frame.src;
}

function browserGoBack() {
  var frame = document.getElementById("browser-frame");
  try { frame.contentWindow.history.back(); } catch (e) {}
}

function browserGoForward() {
  var frame = document.getElementById("browser-frame");
  try { frame.contentWindow.history.forward(); } catch (e) {}
}

function navigateToInputUrl() {
  var val = (document.getElementById("browser-url-input").value || "").trim();
  if (val) browseTo(val, val);
}

function launchCustomUrl() {
  var val = (document.getElementById("custom-app-url").value || "").trim();
  if (val) browseTo(val, val);
}

function addCustomPin() {
  var val = (document.getElementById("custom-app-url").value || "").trim();
  if (!val) return;
  var apps = getSavedApps();
  var name = val.replace(/^https?:\/\//, "").split("/")[0];
  apps.push({ name: name, desc: val, icon: "🌐", badge: "PIN", url: val });
  try { localStorage.setItem("omarchy_apps_v8", JSON.stringify(apps)); } catch (e) {}
  renderAppDock();
}

function resetCustomApps() {
  try { localStorage.removeItem("omarchy_apps_v8"); } catch (e) {}
  renderAppDock();
}

function launchDockApp(idx) {
  var apps = getSavedApps();
  var app = apps[idx];
  if (!app) return;
  if (app.action === "live_tv") { switchWorkspace(2); bindLiveBroadcast(); return; }
  if (app.action === "ws_4") { switchWorkspace(4); return; }

  if (app.url) {
    var autoFs = (app.url.includes("youtube.com/tv") || app.url.endsWith(".mp4"));
    browseTo(app.url, app.name, autoFs);
  }
}

function getSavedApps() {
  try {
    var r = localStorage.getItem("omarchy_apps_v8");
    if (r) {
      var parsed = JSON.parse(r);
      if (!parsed.some(a => a.url && a.url.includes("fis.com.mv"))) {
        parsed.unshift({ name: "Flight Info (FIS)", desc: "Velana Airport Flights", icon: "✈️", badge: "AIRPORT", url: "https://fis.com.mv" });
        try { localStorage.setItem("omarchy_apps_v8", JSON.stringify(parsed)); } catch(e) {}
      }
      return parsed;
    }
  } catch (e) {}
  return DEFAULT_APPS.slice();
}

function renderAppDock() {
  var grid = document.getElementById("app-dock-grid");
  if (!grid) return;
  var apps = getSavedApps();
  var html = "";
  for (var i = 0; i < apps.length; i++) {
    var a = apps[i];
    html += '<button class="app-card nav-item" onclick="launchDockApp(' + i + ')">' +
            '<div class="app-card-top">' +
            '<span class="app-card-icon">' + (a.icon || '📱') + '</span>' +
            '<span class="app-badge">' + (a.badge || 'APP') + '</span>' +
            '</div>' +
            '<div class="app-name">' + a.name + '</div>' +
            '<div class="app-desc">' + (a.desc || a.url) + '</div>' +
            '</button>';
  }
  grid.innerHTML = html;
  updateButtonSelection();
}

function getGPUInfo() {
  try {
    var c = document.createElement("canvas");
    var gl = c.getContext("webgl") || c.getContext("experimental-webgl");
    if (!gl) return "WebGL Unavailable";
    var dbg = gl.getExtension("WEBGL_debug_renderer_info");
    return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  } catch (e) { return String(e); }
}

function queryLiveSpecs() {
  try {
    var brand = typeof Hisense_GetBrand === "function" ? Hisense_GetBrand() : "";
    var model = typeof Hisense_GetModelName === "function" ? Hisense_GetModelName() : "Smart TV";
    var host = (brand ? brand + " " : "") + model;
    document.getElementById("spec-host").textContent = host;
    document.getElementById("wb-live-model").textContent = host;

    document.getElementById("spec-chip").textContent = typeof Hisense_GetChipSetName === "function" ? Hisense_GetChipSetName() : "Unknown";
    document.getElementById("spec-gpu").textContent = getGPUInfo();
    document.getElementById("spec-os").textContent = (typeof Hisense_GetOSVersion === "function" ? "VIDAA " + Hisense_GetOSVersion() : "") + " (" + (typeof Hisense_GetCurrentBrowser === "function" ? Hisense_GetCurrentBrowser() : "Browser") + " Chrome/" + (typeof Hisense_GetChromiumVersion === "function" ? Hisense_GetChromiumVersion() : "") + ")";
    document.getElementById("spec-fw").textContent = typeof Hisense_GetFirmWareVersion === "function" ? Hisense_GetFirmWareVersion() : "Unknown";
    document.getElementById("spec-res").textContent = (typeof Hisense_GetPanelResolution === "function" ? Hisense_GetPanelResolution() + " Panel " : "") + "(" + screen.width + "x" + screen.height + " @" + window.devicePixelRatio + "x)";
    document.getElementById("spec-ip").textContent = (typeof Hisense_GetIPAddress === "function" ? Hisense_GetIPAddress() : "127.0.0.1") + " (" + (typeof Hisense_GetNetType === "function" ? Hisense_GetNetType() : "net") + ")";
    document.getElementById("spec-ad").textContent = typeof TvInfo_getParam === "function" ? (TvInfo_getParam("adTargetEnable") == 1 ? "Enabled" : "Disabled (Debloated)") : "N/A";
  } catch (e) {}
}

function refreshLiveHardware() {
  try {
    if (typeof Hisense_GetVolume === "function") liveState.volume = Number(Hisense_GetVolume());
    if (typeof Hisense_GetMute === "function") liveState.mute = Number(Hisense_GetMute());
    if (window.vowOS && window.vowOS.tvinfo) {
      if (typeof window.vowOS.tvinfo.getBrightness === "function") liveState.brightness = Number(window.vowOS.tvinfo.getBrightness());
      if (typeof window.vowOS.tvinfo.getContrast === "function") liveState.contrast = Number(window.vowOS.tvinfo.getContrast());
    }
  } catch (e) {}

  document.getElementById("wb-vol").textContent = (liveState.mute ? "MUTE " : "") + liveState.volume + "%";
  document.getElementById("wb-bri").textContent = liveState.brightness + "%";
  document.getElementById("wb-con").textContent = liveState.contrast + "%";
}

function setLiveBrightness(delta) {
  var next = Math.max(0, Math.min(100, liveState.brightness + delta));
  try {
    window.vowOS.tvinfo.setBrightness(next);
    liveState.brightness = Number(window.vowOS.tvinfo.getBrightness());
    refreshLiveHardware();
    logHal("vowOS.tvinfo.setBrightness(" + next + ") -> " + liveState.brightness + "%");
  } catch (e) { logHal("Err: " + e); }
}

function setLiveBrightnessPreset(val) {
  try {
    window.vowOS.tvinfo.setBrightness(val);
    liveState.brightness = Number(window.vowOS.tvinfo.getBrightness());
    refreshLiveHardware();
    logHal("Brightness -> " + val + "%");
  } catch (e) { logHal("Err: " + e); }
}

function setLiveContrast(delta) {
  var next = Math.max(0, Math.min(100, liveState.contrast + delta));
  try {
    window.vowOS.tvinfo.setContrast(next);
    liveState.contrast = Number(window.vowOS.tvinfo.getContrast());
    refreshLiveHardware();
    logHal("vowOS.tvinfo.setContrast(" + next + ") -> " + liveState.contrast + "%");
  } catch (e) { logHal("Err: " + e); }
}

function setLiveContrastPreset(val) {
  try {
    window.vowOS.tvinfo.setContrast(val);
    liveState.contrast = Number(window.vowOS.tvinfo.getContrast());
    refreshLiveHardware();
    logHal("Contrast -> " + val + "%");
  } catch (e) { logHal("Err: " + e); }
}

function adjustVolume(delta) {
  var next = Math.max(0, Math.min(100, liveState.volume + delta));
  try {
    TvInfo_setParam("soundVolume", next);
    setTimeout(function() {
      if (typeof Hisense_GetVolume === "function") liveState.volume = Number(Hisense_GetVolume());
      refreshLiveHardware();
      logHal("Volume -> " + liveState.volume + "%");
    }, 150);
  } catch (e) { logHal("Err: " + e); }
}

function toggleMute() {
  var next = liveState.mute ? 0 : 1;
  try {
    TvInfo_setParam("soundMute", next);
    setTimeout(function() {
      if (typeof Hisense_GetMute === "function") liveState.mute = Number(Hisense_GetMute());
      refreshLiveHardware();
      logHal("Mute -> " + liveState.mute);
    }, 150);
  } catch (e) { logHal("Err: " + e); }
}

function logHal(msg) {
  var el = document.getElementById("hal-output");
  if (el) el.textContent = "[" + new Date().toLocaleTimeString() + "] " + msg + "\n" + el.textContent;
}

function runLiveHostCmd(cmdName) {
  logTerm("Executing on host: " + cmdName + " ...");
  var t0 = performance.now();
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/run_mac_cmd", true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.onload = function() {
    var dur = Math.round(performance.now() - t0);
    try {
      var res = JSON.parse(xhr.responseText);
      logTerm("Host [" + cmdName + "] in " + dur + "ms:\n" + res.output);
    } catch (e) { logTerm("Error: " + e); }
  };
  xhr.send(JSON.stringify({ cmd: cmdName }));
}

function fetchLivePackages() {
  logTerm("Querying http://localhost:9009/service/pkgmgr -> getInstalledPkgs ...");
  try {
    var res = window.vowOS.store.getInstalledPkgs();
    logTerm("LIVE INSTALLED PACKAGES:\n" + JSON.stringify(res, null, 2));
  } catch (e) { logTerm("Err: " + e); }
}

function dumpLiveSensors() {
  logTerm("Querying all live native getters...");
  try {
    var out = {
      device: typeof Hisense_GetDeviceInfo === "function" ? Hisense_GetDeviceInfo() : null,
      drm: typeof Hisense_GetDrmInfo === "function" ? Hisense_GetDrmInfo() : null,
      network: typeof Hisense_GetNetworkInfo === "function" ? Hisense_GetNetworkInfo() : null,
      picture: typeof Hisense_GetPictureInfo === "function" ? Hisense_GetPictureInfo() : null,
      volume: typeof Hisense_GetVolume === "function" ? Hisense_GetVolume() : null,
      brightness: window.vowOS && window.vowOS.tvinfo ? window.vowOS.tvinfo.getBrightness() : null,
      contrast: window.vowOS && window.vowOS.tvinfo ? window.vowOS.tvinfo.getContrast() : null
    };
    logTerm("LIVE SENSOR DUMP:\n" + JSON.stringify(out, null, 2));
  } catch (e) { logTerm("Err: " + e); }
}

function callLiveRpc(service, api, args) {
  var out = document.getElementById("rpc-output");
  out.textContent = "Querying live http://localhost:9009/service/" + service + " (" + api + ")...";
  try {
    var res = window.vowOS.service.syncExecute(service, { api: api, args: args });
    out.textContent = "POST http://localhost:9009/service/" + service + "\n" + JSON.stringify(res, null, 2);
  } catch (e) { out.textContent = "RPC Error: " + e; }
}

function logTerm(msg) {
  var el = document.getElementById("term-output");
  if (el) el.textContent = "[omarchy@vidaa ~]$ " + msg + "\n\n" + el.textContent;
}

function bindLiveBroadcast() {
  var v = document.getElementById("tv-player");
  var c = document.getElementById("oipf-broadcast-container");
  v.pause(); v.style.display = "none"; c.style.display = "block";

  try {
    if (!broadcastObj && window.oipfObjectFactory) {
      broadcastObj = window.oipfObjectFactory.createVideoBroadcastObject();
      broadcastObj.style.width = "100%"; broadcastObj.style.height = "100%";
      c.innerHTML = ""; c.appendChild(broadcastObj);
    }
    if (broadcastObj && typeof broadcastObj.bindToCurrentChannel === "function") {
      broadcastObj.bindToCurrentChannel();
      logMedia("Bound to live TV channel via oipfObjectFactory");
    }
    document.getElementById("stream-status").textContent = "LIVE TV TUNER";
  } catch (e) { logMedia("Err: " + e); }
}

function channelStep(dir) {
  try {
    if (broadcastObj) {
      if (dir > 0 && typeof broadcastObj.nextChannel === "function") broadcastObj.nextChannel();
      if (dir < 0 && typeof broadcastObj.prevChannel === "function") broadcastObj.prevChannel();
      logMedia("Stepped channel " + (dir > 0 ? "+1" : "-1"));
    }
  } catch (e) { logMedia("Err: " + e); }
}

function playLiveStream(url, title) {
  var v = document.getElementById("tv-player");
  var c = document.getElementById("oipf-broadcast-container");
  c.style.display = "none"; v.style.display = "block";
  v.src = url; v.play();
  document.getElementById("stream-status").textContent = "PLAYING: " + title;
  logMedia("Playing: " + title);
}

function playCustomStream() {
  var u = (document.getElementById("custom-stream-url").value || "").trim();
  if (u) playLiveStream(u, "Custom URL");
}

function stopStream() {
  var v = document.getElementById("tv-player");
  v.pause(); v.removeAttribute("src"); v.load();
  try { if (broadcastObj && typeof broadcastObj.stop === "function") broadcastObj.stop(); } catch (e) {}
  document.getElementById("stream-status").textContent = "STOPPED";
}

function toggleFullscreenVideo() {
  var st = document.getElementById("media-stage");
  if (st.requestFullscreen) st.requestFullscreen();
  else if (st.webkitRequestFullscreen) st.webkitRequestFullscreen();
}

function logMedia(msg) {
  var el = document.getElementById("media-log");
  if (el) el.textContent = "[" + new Date().toLocaleTimeString() + "] " + msg + "\n\n" + el.textContent;
}

function measureRealGpuFrame() {
  var t0 = performance.now();
  var c = document.createElement("canvas");
  c.width = 16; c.height = 16;
  var gl = c.getContext("webgl");
  if (gl) {
    gl.clearColor(0.1, 0.2, 0.3, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.finish();
  }
  var dt = performance.now() - t0;
  var txt = document.getElementById("gpu-frame-txt");
  var bar = document.getElementById("gpu-frame-bar");
  if (txt) txt.textContent = dt.toFixed(2) + " ms (" + (dt < 16.6 ? "60 FPS" : "30 FPS") + ")";
  if (bar) bar.style.width = Math.min(100, Math.round((dt / 33.3) * 100)) + "%";

  recordGpuTime(dt);

  if (performance && performance.memory) {
    var used = Math.round(performance.memory.usedJSHeapSize / 1048576);
    var limit = Math.round(performance.memory.jsHeapSizeLimit / 1048576);
    var htxt = document.getElementById("mem-heap-txt");
    var hbar = document.getElementById("mem-heap-bar");
    if (htxt) htxt.textContent = used + " / " + limit + " MB";
    if (hbar) hbar.style.width = Math.min(100, Math.round((used / limit) * 100)) + "%";
  }
}

function applyTheme(t) {
  document.body.setAttribute("data-theme", t);
  var lbl = document.getElementById("wb-theme-name");
  if (lbl) lbl.textContent = t.toUpperCase();
  try { localStorage.setItem("omarchy_theme_v8", t); } catch (e) {}
}

function cycleTheme() {
  currentThemeIdx = (currentThemeIdx + 1) % THEMES.length;
  applyTheme(THEMES[currentThemeIdx]);
}

function getVisibleNavItems() {
  var ws = document.getElementById("ws-" + currentWorkspace);
  if (!ws) return [];
  return Array.prototype.slice.call(ws.querySelectorAll(".hero-actions .nav-btn, .app-card, .hw-card .nav-btn"));
}

function updateButtonSelection() {
  var items = getVisibleNavItems();
  if (navIndex >= items.length) navIndex = 0;
  for (var i = 0; i < items.length; i++) {
    if (i === navIndex) {
      items[i].classList.add("selected");
      items[i].focus();
    } else {
      items[i].classList.remove("selected");
    }
  }
}

function getVisibleInAppItems() {
  var overlay = document.getElementById("app-window-overlay");
  if (!overlay || !overlay.classList.contains("open")) return [];
  if (isBrowserFullscreen) {
    return [document.getElementById("btn-toggle-fullscreen")];
  }
  return Array.prototype.slice.call(overlay.querySelectorAll(".inapp-ctrl-btn"));
}

function updateInAppButtonSelection() {
  var items = getVisibleInAppItems();
  if (items.length === 0) return;
  if (inAppNavIndex >= items.length) inAppNavIndex = 0;
  for (var i = 0; i < items.length; i++) {
    if (i === inAppNavIndex) {
      items[i].classList.add("selected");
      items[i].focus();
    } else {
      items[i].classList.remove("selected");
    }
  }
}

function switchWorkspace(n) {
  if (isAppWindowOpen) closeInAppWindow();
  currentWorkspace = n;
  for (var i = 1; i <= 4; i++) {
    var ws = document.getElementById("ws-" + i);
    var btn = document.getElementById("wb-ws-" + i);
    if (ws) ws.classList.toggle("active", i === n);
    if (btn) btn.classList.toggle("active", i === n);
  }
  navIndex = 0;
  updateButtonSelection();
}

// REAL REMOTE CONTROL KEYLOGGER & D-PAD CONTROLLER
window.addEventListener("keydown", function(e) {
  var kc = e.keyCode || e.which;

  var kbox = document.getElementById("key-sniffer-box");
  if (kbox) kbox.textContent = "[" + new Date().toLocaleTimeString() + "] Key: " + e.key + " (keyCode=" + kc + ")\n" + kbox.textContent.slice(0, 400);

  // REMOTE BACK BUTTON (461 / 8 / 27)
  if (kc === 461 || kc === 8 || kc === 27) {
    if (document.getElementById("remote-qr-modal").classList.contains("open")) {
      closeRemoteQrModal();
      e.preventDefault();
      return;
    }
    if (isAppWindowOpen) {
      if (isBrowserFullscreen) {
        setBrowserFullscreen(false);
      } else {
        closeInAppWindow();
      }
      e.preventDefault();
      return;
    }
  }

  // KEY 5 -> TOGGLE DUAL SCREEN 50/50
  if (kc === 53) { toggleDualScreen(); e.preventDefault(); return; }

  // KEY 6 -> TOGGLE PiP
  if (kc === 54) { togglePipMode(); e.preventDefault(); return; }

  // KEY 9 -> OPEN REMOTE QR MODAL
  if (kc === 57) { openRemoteQrModal(); e.preventDefault(); return; }

  // GREEN BUTTON (404 / 50) -> TOGGLE FULLSCREEN IN BROWSER
  if (kc === 404 || kc === 50) {
    if (isAppWindowOpen) {
      toggleBrowserFullscreen();
      e.preventDefault();
      return;
    }
  }

  // WHEN BROWSER OVERLAY IS OPEN:
  if (isAppWindowOpen) {
    if (!isBrowserFullscreen) {
      var inItems = getVisibleInAppItems();
      if (kc === 37 || kc === 38) {
        if (inItems.length > 0) {
          inAppNavIndex = (inAppNavIndex - 1 + inItems.length) % inItems.length;
          updateInAppButtonSelection();
          e.preventDefault();
        }
      } else if (kc === 39 || kc === 40) {
        if (inItems.length > 0) {
          inAppNavIndex = (inAppNavIndex + 1) % inItems.length;
          updateInAppButtonSelection();
          e.preventDefault();
        }
      } else if (kc === 13) {
        if (inItems[inAppNavIndex]) {
          inItems[inAppNavIndex].click();
          e.preventDefault();
        }
      }
    }
    return;
  }

  // WORKSPACE HOTKEYS
  if (kc === 403 || kc === 49) { switchWorkspace(1); e.preventDefault(); return; }
  if (kc === 404 || kc === 50) { switchWorkspace(2); e.preventDefault(); return; }
  if (kc === 405 || kc === 51) { switchWorkspace(3); e.preventDefault(); return; }
  if (kc === 406 || kc === 52) { switchWorkspace(4); e.preventDefault(); return; }
  if (kc === 48) { cycleTheme(); e.preventDefault(); return; }

  var items = getVisibleNavItems();
  if (kc === 37 || kc === 38) {
    if (items.length > 0) {
      navIndex = (navIndex - 1 + items.length) % items.length;
      updateButtonSelection();
      e.preventDefault();
    }
  } else if (kc === 39 || kc === 40) {
    if (items.length > 0) {
      navIndex = (navIndex + 1) % items.length;
      updateButtonSelection();
      e.preventDefault();
    }
  } else if (kc === 13) {
    if (items[navIndex]) {
      items[navIndex].click();
      e.preventDefault();
    }
  }
});

setInterval(function() {
  var now = new Date();
  document.getElementById("wb-clock").textContent = now.toTimeString().split(" ")[0];
  measureRealGpuFrame();
}, 2000);

setInterval(function() {
  updateLivePulseTicker();
}, 15000);

setInterval(function() {
  var t0 = performance.now();
  var xhr = new XMLHttpRequest();
  xhr.open("GET", "/poll_cmd", true);
  xhr.onload = function() {
    var rtt = Math.round(performance.now() - t0);
    document.getElementById("wb-rtt").textContent = rtt + " ms";
    if (xhr.status === 200 && xhr.responseText) {
      try {
        var cmdObj = JSON.parse(xhr.responseText);
        if (cmdObj && cmdObj.js) {
          var res;
          try { res = eval(cmdObj.js); } catch (err) { res = { error: String(err) }; }
          var rxhr = new XMLHttpRequest();
          rxhr.open("POST", "/cmd_result", true);
          rxhr.setRequestHeader("Content-Type", "application/json");
          rxhr.send(JSON.stringify({ id: cmdObj.id, result: res }));
        }
      } catch (e) {}
    }
  };
  xhr.onerror = function() {
    document.getElementById("wb-rtt").textContent = "OFFLINE";
  };
  xhr.send();
}, 2000);

window.addEventListener("load", function() {
  try {
    var saved = localStorage.getItem("omarchy_theme_v8");
    if (saved) {
      var idx = THEMES.indexOf(saved);
      if (idx !== -1) currentThemeIdx = idx;
      applyTheme(saved);
    }
  } catch (e) {}
  initAmbientCanvas();
  renderAppDock();
  queryLiveSpecs();
  refreshLiveHardware();
  measureRealGpuFrame();
  updateLivePulseTicker();
  updateButtonSelection();
});
</script>
</body>
</html>
"""

class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True

class OmarchyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ("/remote", "/remote.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if REMOTE_FILE.exists():
                self.wfile.write(REMOTE_FILE.read_bytes())
            else:
                self.wfile.write(b"<h1>Remote not found</h1>")
            return

        if parsed.path == "/sw.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(SW_JS.encode("utf-8"))
            return

        if parsed.path == "/manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(MANIFEST_JSON.encode("utf-8"))
            return

        if parsed.path == "/poll_cmd":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            cmd_file = BASE_DIR / "cmd_queue.json"
            if cmd_file.exists():
                try:
                    raw_cmd = cmd_file.read_text(encoding="utf-8")
                    cmd_file.unlink()
                    print(f"\n[SENT CMD TO TV] {raw_cmd[:100]}")
                    self.wfile.write(raw_cmd.encode("utf-8"))
                    return
                except Exception as e:
                    print(f"[!] Error reading cmd_queue.json: {e}")
            if PENDING_COMMANDS:
                cmd = PENDING_COMMANDS.pop(0)
                self.wfile.write(json.dumps(cmd).encode("utf-8"))
            else:
                self.wfile.write(b"{}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")

        if self.path == "/api/remote_command":
            try:
                data = json.loads(raw)
                js = ""
                if data.get("type") == "key":
                    js = f"window.dispatchEvent(new KeyboardEvent('keydown', { keyCode: {data.get('keyCode')}, bubbles: true }))"
                elif data.get("type") == "action":
                    act = data.get("action")
                    if act == "screen_split": js = "toggleDualScreen(true)"
                    elif act == "screen_single": js = "toggleDualScreen(false)"
                    elif act == "screen_pip": js = "togglePipMode()"
                elif data.get("type") in ("launch", "browse"):
                    u = data.get("url", "")
                    t = data.get("title", u)
                    js = f"browseTo({json.dumps(u)}, {json.dumps(t)})"
                elif data.get("type") == "hal":
                    p = data.get("param")
                    v = data.get("val")
                    if p == "brightness": js = f"setLiveBrightness({v})"
                    elif p == "brightness_preset": js = f"setLiveBrightnessPreset({v})"
                    elif p == "volume": js = f"adjustVolume({v})"
                    elif p == "mute": js = "toggleMute()"

                if js:
                    cmd_obj = {"id": int(datetime.datetime.now().timestamp() * 1000), "js": js}
                    (BASE_DIR / "cmd_queue.json").write_text(json.dumps(cmd_obj), encoding="utf-8")
                    print(f"\n[REMOTE INPUT QUEUED] {data} -> {js}")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
                return

        if self.path == "/run_mac_cmd":
            try:
                data = json.loads(raw)
                cmd_key = data.get("cmd", "")
                if cmd_key in SAFE_MAC_COMMANDS:
                    out = subprocess.check_output(SAFE_MAC_COMMANDS[cmd_key], stderr=subprocess.STDOUT, text=True, timeout=3)
                else:
                    out = f"Command {cmd_key} not recognized."
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "output": out}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "output": str(e)}).encode("utf-8"))
                return

        elif self.path == "/cmd_result":
            try:
                data = json.loads(raw)
                res_file = BASE_DIR / "tv_cmd_results.jsonl"
                with open(res_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(data) + "\n")
                print(f"\n[CMD RESULT #{data.get('id')}] {str(data.get('result'))[:300]}")
            except Exception as e:
                print(f"[!] Error saving cmd result: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    server = ReusableThreadingHTTPServer(("0.0.0.0", PORT), OmarchyHandler)
    print(f"=== OMARCHY TV OS SERVER v8.0 ON 0.0.0.0:{PORT} ===")
    server.serve_forever()
