#!/usr/bin/env python3
"""
Updates inspector_server.py with Omarchy v5.0:
- Interactive In-App YouTube Hub (4K HDR playback, channel presets, live video search)
- In-App Hacker News Live Terminal Reader (Realtime Firebase REST API directly from TV)
- In-App Wikipedia Knowledge Explorer (Live REST API with summaries and images)
- In-App 4K Cinema Theater (Tears of Steel, Big Buck Bunny, direct video playback)
- In-App 2048 Retro TV Arcade (Playable via TV Remote D-Pad)
- In-App Custom Web Navigator
- Full TV Remote D-Pad navigation support INSIDE the in-app overlay
- Instant Remote BACK key listener to exit cleanly
"""

import sys
from pathlib import Path

CODE = r'''#!/usr/bin/env python3
"""
OMARCHY TV OS v5.0 // COMPLETE IN-APP APPLICATION RUNTIME
Apps (YouTube Cinema Hub, Hacker News Live Reader, Wikipedia Explorer, 4K Cinema Theater,
2048 TV Arcade, Web Navigator) load and run 100% inside Omarchy with full TV Remote D-Pad controls.
Zero leaving the Omarchy interface.
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
const CACHE_NAME = 'omarchy-tv-os-inapp-v5';
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname === '/poll_cmd') return;
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
<title>OMARCHY TV OS // 100% IN-APP RUNTIME</title>
<link rel="manifest" href="/manifest.json">
<style>
  :root, [data-theme="tokyonight"] {
    --bg: #1a1b26; --bg-alt: #16161e; --bg-panel: rgba(22, 22, 30, 0.96);
    --fg: #c0caf5; --muted: #565f89; --accent: #7aa2f7; --accent2: #bb9af7;
    --green: #9ece6a; --amber: #e0af68; --red: #f7768e; --cyan: #7dcfff; --border: #292e42;
  }
  [data-theme="gruvbox"] {
    --bg: #1d2021; --bg-alt: #282828; --bg-panel: rgba(40, 40, 40, 0.96);
    --fg: #ebdbb2; --muted: #928374; --accent: #fabd2f; --accent2: #d3869b;
    --green: #b8bb26; --amber: #fe8019; --red: #fb4934; --cyan: #8ec07c; --border: #3c3836;
  }
  [data-theme="catppuccin"] {
    --bg: #11111b; --bg-alt: #1e1e2e; --bg-panel: rgba(30, 30, 46, 0.96);
    --fg: #cdd6f4; --muted: #6c7086; --accent: #cba6f7; --accent2: #f5c2e7;
    --green: #a6e3a1; --amber: #fab387; --red: #f38ba8; --cyan: #89dceb; --border: #313244;
  }
  [data-theme="nord"] {
    --bg: #242933; --bg-alt: #2e3440; --bg-panel: rgba(46, 52, 64, 0.96);
    --fg: #eceff4; --muted: #616e88; --accent: #88c0d0; --accent2: #b48ead;
    --green: #a3be8c; --amber: #ebcb8b; --red: #bf616a; --cyan: #8fbcbb; --border: #3b4252;
  }
  [data-theme="everforest"] {
    --bg: #1e2326; --bg-alt: #272e33; --bg-panel: rgba(39, 46, 51, 0.96);
    --fg: #d3c6aa; --muted: #7a8478; --accent: #a7c080; --accent2: #d699b6;
    --green: #a7c080; --amber: #dbbc7f; --red: #e67e80; --cyan: #83c092; --border: #374145;
  }
  [data-theme="kanagawa"] {
    --bg: #16161d; --bg-alt: #1f1f28; --bg-panel: rgba(31, 31, 40, 0.96);
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

  #ws-1 { grid-template-columns: 1.25fr 0.75fr; grid-template-rows: 1fr; }
  #ws-2 { grid-template-columns: 1.3fr 0.7fr; grid-template-rows: 1fr; }
  #ws-3 { grid-template-columns: 1.15fr 0.85fr; grid-template-rows: 1fr; }
  #ws-4 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr; }

  .tile {
    background: var(--bg-panel); border: 2px solid var(--border);
    border-radius: 6px; display: flex; flex-direction: column; overflow: hidden;
  }
  .tile.focused {
    border-color: var(--accent);
    box-shadow: 0 0 18px rgba(122, 162, 247, 0.2);
  }
  .tile-bar {
    height: 30px; background: rgba(0, 0, 0, 0.28);
    border-bottom: 1px solid var(--border); padding: 0 12px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 12px; color: var(--muted);
  }
  .tile.focused .tile-bar { color: var(--accent); font-weight: bold; }
  .tile-body { flex: 1; padding: 12px; overflow-y: auto; }

  .app-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 10px; margin-bottom: 12px;
  }
  .app-card {
    background: var(--bg); border: 2px solid var(--border);
    border-radius: 6px; padding: 14px 12px; text-align: left;
    cursor: pointer; display: flex; flex-direction: column;
    justify-content: space-between; min-height: 74px; color: var(--fg);
    font-family: inherit;
  }
  .app-card .app-name { font-size: 14px; font-weight: bold; color: var(--cyan); margin-bottom: 4px; }
  .app-card .app-desc { font-size: 11px; color: var(--muted); }

  .nav-btn {
    display: inline-block; background: var(--bg);
    border: 1px solid var(--border); color: var(--fg);
    padding: 7px 11px; margin: 3px; border-radius: 4px;
    font-family: inherit; font-size: 12px; cursor: pointer;
  }
  .nav-btn.selected, .nav-btn:focus, .app-card.selected, .app-card:focus {
    border-color: var(--green);
    background: rgba(158, 206, 106, 0.2);
    color: #fff; outline: none;
    box-shadow: 0 0 12px rgba(158, 206, 106, 0.28);
  }

  .fastfetch {
    display: flex; gap: 14px; margin-bottom: 10px;
    border-bottom: 1px solid var(--border); padding-bottom: 10px;
  }
  .ascii-logo {
    color: var(--accent); font-size: 11px; line-height: 1.15;
    white-space: pre; font-weight: bold;
  }
  .specs-list { font-size: 12px; flex: 1; }
  .specs-list div { margin-bottom: 3px; }
  .specs-list b { color: var(--amber); display: inline-block; width: 112px; }

  .term-out {
    background: #0d0e14; border: 1px solid var(--border);
    border-radius: 4px; padding: 10px; font-size: 12px;
    height: 220px; overflow-y: auto; white-space: pre-wrap;
    word-break: break-word; color: var(--fg); margin-top: 8px;
  }

  .meter-row { margin-bottom: 8px; }
  .meter-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
  .meter-track { width: 100%; height: 10px; background: #0d0e14; border-radius: 3px; overflow: hidden; }
  .meter-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--cyan)); transition: width 0.25s ease; }

  .hw-card {
    border: 1px solid var(--border); background: #101118;
    border-radius: 4px; padding: 10px; margin-bottom: 10px;
  }
  .hw-card-title { color: var(--amber); font-weight: bold; margin-bottom: 6px; font-size: 12px; }

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

  /* FULLSCREEN IN-APP APPLICATION OVERLAY */
  #app-window-overlay {
    display: none; position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: var(--bg); z-index: 9999;
    flex-direction: column;
  }
  #app-window-overlay.open { display: flex; }
  .app-win-bar {
    height: 42px; background: var(--bg-alt);
    border-bottom: 2px solid var(--accent);
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 14px; font-size: 13px; color: var(--fg);
  }
  .app-win-body {
    flex: 1; width: 100%; height: calc(100vh - 42px);
    overflow: hidden; position: relative; background: var(--bg);
  }
  .app-win-frame {
    width: 100%; height: 100%; border: none; background: #000;
  }

  /* IN-APP VIEW CONTAINERS */
  .inapp-view {
    display: none; width: 100%; height: 100%; padding: 14px;
    flex-direction: column; gap: 10px; box-sizing: border-box;
    overflow-y: auto;
  }
  .inapp-view.active { display: flex; }

  /* 2048 Game Styles */
  .grid-2048 {
    display: grid; grid-template-columns: repeat(4, 80px);
    grid-template-rows: repeat(4, 80px); gap: 10px;
    background: #101118; padding: 10px; border-radius: 6px;
    border: 2px solid var(--border); width: fit-content;
  }
  .cell-2048 {
    width: 80px; height: 80px; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; font-weight: bold; background: rgba(255,255,255,0.05); color: var(--fg);
  }
  .cell-2048[data-val="2"] { background: #283457; color: #7aa2f7; }
  .cell-2048[data-val="4"] { background: #3d59a1; color: #c0caf5; }
  .cell-2048[data-val="8"] { background: #ff9e64; color: #111; }
  .cell-2048[data-val="16"] { background: #e0af68; color: #111; }
  .cell-2048[data-val="32"] { background: #f7768e; color: #111; }
  .cell-2048[data-val="64"] { background: #db4b4b; color: #fff; }
  .cell-2048[data-val="128"] { background: #bb9af7; color: #111; }
  .cell-2048[data-val="256"] { background: #9ece6a; color: #111; font-size: 22px; }
  .cell-2048[data-val="512"] { background: #73daca; color: #111; font-size: 22px; }
  .cell-2048[data-val="1024"] { background: #7dcfff; color: #111; font-size: 20px; }
  .cell-2048[data-val="2048"] { background: #fabd2f; color: #111; font-size: 20px; box-shadow: 0 0 16px #fabd2f; }

  #media-stage {
    width: 100%; height: 64%; background: #000;
    border: 1px solid var(--border); border-radius: 4px;
    position: relative; overflow: hidden;
  }
  video, #oipf-broadcast-container { width: 100%; height: 100%; }
</style>
</head>
<body data-theme="tokyonight">

<!-- FULLSCREEN IN-APP APP WINDOW -->
<div id="app-window-overlay">
  <div class="app-win-bar">
    <div style="display:flex;align-items:center;gap:8px;">
      <span class="distro-pill" id="app-win-pill">APP</span>
      <b id="app-win-title" style="color:var(--cyan)">In-App Player</b>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <button class="nav-btn selected inapp-ctrl-btn" id="app-win-close-btn" onclick="closeInAppWindow()">Close Window (Remote BACK)</button>
      <button class="nav-btn inapp-ctrl-btn" onclick="reloadInAppWindow()">Reload</button>
    </div>
  </div>

  <div class="app-win-body">
    <!-- DIRECT IFRAME EMBED (FOR WEB BROWSING & DIRECT LINKS) -->
    <iframe id="app-win-iframe" class="app-win-frame" style="display:none;" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>

    <!-- 1. YOUTUBE CINEMA HUB (VERIFIED 4K HDR PLAYBACK & LIVE SEARCH) -->
    <div class="inapp-view" id="view-youtube">
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        <button class="nav-btn inapp-btn selected" onclick="playYtVideo('1la40WSp10U', '4K Nature & Wildlife')">🌲 4K Nature</button>
        <button class="nav-btn inapp-btn" onclick="playYtVideo('jfKfPfyJRdk', 'Lofi Hip Hop Radio 24/7')">☕ Lofi Live</button>
        <button class="nav-btn inapp-btn" onclick="playYtVideo('4xDzrJKXOOY', 'Cyberpunk Synthwave 4K')">🏙️ Synthwave</button>
        <button class="nav-btn inapp-btn" onclick="playYtVideo('LXb3EKWsInQ', 'Costa Rica in 4K 60FPS')">🦜 4K Costa Rica</button>
        <button class="nav-btn inapp-btn" onclick="playYtVideo('R6MlUcmOul8', 'Tears of Steel 4K Sci-Fi')">🎬 Tears of Steel</button>
        <button class="nav-btn inapp-btn" onclick="playYtVideo('aqz-KE-bpKQ', 'Big Buck Bunny 4K')">🐰 Big Buck Bunny</button>
        <input id="yt-inapp-input" class="input-box" style="flex:1;min-width:220px;" placeholder="Search or paste Video ID" onclick="Hisense_enableVKB && Hisense_enableVKB()">
        <button class="nav-btn inapp-btn" onclick="searchOrPlayInAppYouTube()">Play</button>
      </div>
      <div style="flex:1;min-height:500px;background:#000;border:2px solid var(--border);border-radius:6px;overflow:hidden;position:relative;">
        <iframe id="yt-player-frame" style="width:100%;height:100%;border:none;" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>
      </div>
    </div>

    <!-- 2. HACKER NEWS LIVE TERMINAL (REALTIME FIREBASE REST API) -->
    <div class="inapp-view" id="view-hackernews">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <b style="color:var(--amber);font-size:13px;">⚡ HACKER NEWS // LIVE TOP STORIES (REALTIME REST API)</b>
        <button class="nav-btn inapp-btn selected" onclick="fetchHackerNewsStories()">↻ Refresh Live Stories</button>
      </div>
      <div id="hn-stories-list" style="flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:8px;">
        <div style="padding:20px;color:var(--muted);">Connecting to live Hacker News API...</div>
      </div>
    </div>

    <!-- 3. WIKIPEDIA KNOWLEDGE EXPLORER (LIVE REST API) -->
    <div class="inapp-view" id="view-wikipedia">
      <div style="display:flex;align-items:center;gap:8px;">
        <input id="wiki-search-input" class="input-box" style="flex:1;" placeholder="Search Wikipedia (e.g. Linux, Supercomputer, Space, MediaTek)" onclick="Hisense_enableVKB && Hisense_enableVKB()">
        <button class="nav-btn inapp-btn selected" onclick="searchWiki()">Search</button>
        <button class="nav-btn inapp-btn" onclick="randomWiki()">Random Article</button>
      </div>
      <div id="wiki-content" style="flex:1;overflow-y:auto;background:var(--bg-panel);border:1px solid var(--border);border-radius:6px;padding:20px;">
        <div style="color:var(--muted);">Select Search or Random Article above to query Wikipedia live.</div>
      </div>
    </div>

    <!-- 4. 4K CINEMA THEATER (OPEN SOURCE 4K MOVIES & STREAMER) -->
    <div class="inapp-view" id="view-cinema">
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        <button class="nav-btn inapp-btn selected" onclick="playCinemaFilm('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4', 'Tears of Steel (Sci-Fi, 4K)')">🎬 Tears of Steel</button>
        <button class="nav-btn inapp-btn" onclick="playCinemaFilm('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 'Big Buck Bunny (Animation)')">🐰 Big Buck Bunny</button>
        <button class="nav-btn inapp-btn" onclick="playCinemaFilm('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4', 'Elephants Dream (Sci-Fi)')">🐘 Elephants Dream</button>
        <button class="nav-btn inapp-btn" onclick="playCinemaFilm('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4', 'Sintel (Fantasy)')">🐉 Sintel</button>
        <input id="cinema-custom-url" class="input-box" style="flex:1;min-width:180px;" placeholder="Paste MP4 or HLS (.m3u8) Stream" onclick="Hisense_enableVKB && Hisense_enableVKB()">
        <button class="nav-btn inapp-btn" onclick="playCinemaCustom()">Stream</button>
      </div>
      <div style="flex:1;min-height:480px;background:#000;border:2px solid var(--border);border-radius:6px;overflow:hidden;position:relative;">
        <video id="cinema-video-player" controls autoplay style="width:100%;height:100%;"></video>
      </div>
    </div>

    <!-- 5. 2048 TV ARCADE (D-PAD PLAYABLE RETRO GAME) -->
    <div class="inapp-view" id="view-2048">
      <div style="display:flex;align-items:center;gap:14px;">
        <b style="color:var(--accent);font-size:14px;">🎮 2048 TV ARCADE</b>
        <div class="stat-pill">Score: <b id="g2048-score">0</b></div>
        <div class="stat-pill">Best: <b id="g2048-best">0</b></div>
        <button class="nav-btn inapp-btn selected" onclick="init2048()">New Game</button>
        <span style="color:var(--muted);font-size:11px;">Use TV Remote D-Pad (Up, Down, Left, Right) to slide tiles!</span>
      </div>
      <div style="display:flex;align-items:center;justify-content:center;flex:1;">
        <div class="grid-2048" id="grid-2048"></div>
      </div>
    </div>

    <!-- 6. WEB NAVIGATOR -->
    <div class="inapp-view" id="view-browser">
      <div style="display:flex;align-items:center;gap:8px;">
        <input id="browser-url-input" class="input-box" style="flex:1;" placeholder="https://..." value="https://en.m.wikipedia.org" onclick="Hisense_enableVKB && Hisense_enableVKB()">
        <button class="nav-btn inapp-btn selected" onclick="navigateBrowserUrl()">Go</button>
      </div>
      <div style="flex:1;background:#000;border:1px solid var(--border);border-radius:6px;overflow:hidden;">
        <iframe id="browser-frame" style="width:100%;height:100%;border:none;" allow="autoplay; encrypted-media; fullscreen; picture-in-picture"></iframe>
      </div>
    </div>
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

<!-- WORKSPACE 1: WALKER APP DOCK (100% IN-APP EXECUTION) -->
<div class="workspace active" id="ws-1">
  <div class="tile focused">
    <div class="tile-bar">
      <span>walker // In-App Application Launcher</span>
      <span>[D-PAD + ENTER]</span>
    </div>
    <div class="tile-body">
      <div class="app-grid" id="app-dock-grid"></div>

      <div class="hw-card">
        <div class="hw-card-title">PIN CUSTOM WEB APP TO DOCK</div>
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">
          <input id="custom-app-name" class="input-box" style="width:28%" placeholder="App Name" onclick="Hisense_enableVKB && Hisense_enableVKB()">
          <input id="custom-app-url" class="input-box" style="width:42%" placeholder="https://..." onclick="Hisense_enableVKB && Hisense_enableVKB()">
          <button class="nav-btn" onclick="addCustomApp()">+ Pin App</button>
          <button class="nav-btn" onclick="resetCustomApps()">Reset Defaults</button>
        </div>
      </div>
    </div>
  </div>

  <div class="tile">
    <div class="tile-bar">
      <span>telemetry // Live Fastfetch Hardware Query</span>
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

      <div class="hw-card">
        <div class="hw-card-title">LIVE QUICK CONTROLS</div>
        <button class="nav-btn" onclick="cycleTheme()">Cycle Palette (Key 0)</button>
        <button class="nav-btn" onclick="adjustVolume(-2)">Vol -2</button>
        <button class="nav-btn" onclick="adjustVolume(2)">Vol +2</button>
        <button class="nav-btn" onclick="toggleMute()">Toggle Mute</button>
        <button class="nav-btn" onclick="refreshLiveHardware()">Sync Sensors</button>
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
      <span>btop // Live WebGL Timing &amp; Real Telemetry</span>
      <span>[REAL TIMING]</span>
    </div>
    <div class="tile-body">
      <div class="meter-row">
        <div class="meter-label"><span>WebGL Frame Render Time (GPU)</span><span id="gpu-frame-txt">-- ms</span></div>
        <div class="meter-track"><div class="meter-fill" id="gpu-frame-bar" style="width:0%"></div></div>
      </div>
      <div class="meter-row">
        <div class="meter-label"><span>JS Heap Used Memory (Real)</span><span id="mem-heap-txt">-- MB</span></div>
        <div class="meter-track"><div class="meter-fill" id="mem-heap-bar" style="width:0%"></div></div>
      </div>
      <div class="meter-row">
        <div class="meter-label"><span>Panel Backlight Brightness (vowOS)</span><span id="bri-bar-txt">--%</span></div>
        <div class="meter-track"><div class="meter-fill" id="bri-bar" style="width:0%"></div></div>
      </div>
      <div class="meter-row">
        <div class="meter-label"><span>Panel Contrast (vowOS)</span><span id="con-bar-txt">--%</span></div>
        <div class="meter-track"><div class="meter-fill" id="con-bar" style="width:0%"></div></div>
      </div>
      <div class="term-out" id="key-sniffer-box" style="height:150px;">Remote Key Sniffer: Press any remote button...</div>
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
    <span class="key-hint"><kbd>GREEN</kbd>/<kbd>2</kbd> Media/TV</span>
    <span class="key-hint"><kbd>YELLOW</kbd>/<kbd>3</kbd> System</span>
    <span class="key-hint"><kbd>BLUE</kbd>/<kbd>4</kbd> HAL Write</span>
    <span class="key-hint"><kbd>D-PAD</kbd> Navigate</span>
    <span class="key-hint"><kbd>ENTER</kbd> Launch</span>
    <span class="key-hint"><kbd>BACK</kbd> Close In-App</span>
  </div>
  <div id="footer-live-badge">OMARCHY IN-APP RUNTIME v5.0</div>
</div>

<script>
var THEMES = ["tokyonight", "gruvbox", "catppuccin", "nord", "everforest", "kanagawa"];
var currentThemeIdx = 0;
var currentWorkspace = 1;
var navIndex = 0;
var inAppNavIndex = 0;
var broadcastObj = null;
var isAppWindowOpen = false;
var currentInAppView = null;

var liveState = { volume: 0, brightness: 0, contrast: 0, mute: 0 };

var DEFAULT_APPS = [
  { name: "YouTube Cinema", desc: "4K HDR In-App Cinema Hub", appType: "youtube" },
  { name: "Hacker News", desc: "Live Tech Reader (Realtime API)", appType: "hackernews" },
  { name: "Wikipedia TV", desc: "Live Knowledge Encyclopedia", appType: "wikipedia" },
  { name: "4K Cinema", desc: "Open Movies Theater (4K HDR)", appType: "cinema" },
  { name: "2048 Arcade", desc: "TV Remote D-Pad Playable Game", appType: "game_2048" },
  { name: "Web Browser", desc: "In-App Web Navigator", appType: "browser", url: "https://en.m.wikipedia.org" },
  { name: "Live Broadcast", desc: "Hisense TV Tuner (OIPF)", action: "live_tv" },
  { name: "HAL Controls", desc: "Hardware Write", action: "ws_4" }
];

// IN-APP APPLICATION RUNTIME (100% EMBEDDED INSIDE OMARCHY)
function openInAppView(appType, title, param) {
  var overlay = document.getElementById("app-window-overlay");
  var titleEl = document.getElementById("app-win-title");
  var pillEl = document.getElementById("app-win-pill");

  titleEl.textContent = title;
  pillEl.textContent = title.split(" ")[0].toUpperCase();

  // Hide all in-app sub-views and iframe first
  document.getElementById("app-win-iframe").style.display = "none";
  document.getElementById("app-win-iframe").removeAttribute("src");
  var views = document.querySelectorAll(".inapp-view");
  for (var i = 0; i < views.length; i++) views[i].classList.remove("active");

  currentInAppView = appType;
  overlay.classList.add("open");
  isAppWindowOpen = true;

  if (appType === "youtube") {
    var v = document.getElementById("view-youtube");
    v.classList.add("active");
    playYtVideo("1la40WSp10U", "4K Nature & Wildlife");
  } else if (appType === "hackernews") {
    var v = document.getElementById("view-hackernews");
    v.classList.add("active");
    fetchHackerNewsStories();
  } else if (appType === "wikipedia") {
    var v = document.getElementById("view-wikipedia");
    v.classList.add("active");
    randomWiki();
  } else if (appType === "cinema") {
    var v = document.getElementById("view-cinema");
    v.classList.add("active");
    playCinemaFilm("https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4", "Tears of Steel (4K Sci-Fi)");
  } else if (appType === "game_2048") {
    var v = document.getElementById("view-2048");
    v.classList.add("active");
    init2048();
  } else if (appType === "browser") {
    var v = document.getElementById("view-browser");
    v.classList.add("active");
    var input = document.getElementById("browser-url-input");
    if (param) input.value = param;
    navigateBrowserUrl();
  } else if (appType === "direct_frame") {
    var iframe = document.getElementById("app-win-iframe");
    iframe.style.display = "block";
    iframe.src = param;
  }

  inAppNavIndex = 0;
  updateInAppButtonSelection();
}

function closeInAppWindow() {
  var overlay = document.getElementById("app-window-overlay");
  overlay.classList.remove("open");
  isAppWindowOpen = false;
  currentInAppView = null;

  // Stop video/audio immediately to free RAM and stop sound
  var yt = document.getElementById("yt-player-frame");
  if (yt) yt.removeAttribute("src");
  var cin = document.getElementById("cinema-video-player");
  if (cin) { cin.pause(); cin.removeAttribute("src"); cin.load(); }
  var f = document.getElementById("app-win-iframe");
  if (f) f.removeAttribute("src");
  var bf = document.getElementById("browser-frame");
  if (bf) bf.removeAttribute("src");

  updateButtonSelection();
}

function reloadInAppWindow() {
  if (currentInAppView) openInAppView(currentInAppView, document.getElementById("app-win-title").textContent);
}

// 1. YOUTUBE CINEMA FUNCTIONS
function playYtVideo(videoId, title) {
  var frame = document.getElementById("yt-player-frame");
  frame.src = "https://www.youtube-nocookie.com/embed/" + videoId + "?autoplay=1&enablejsapi=1";
  document.getElementById("app-win-title").textContent = "YouTube: " + title;
}

function searchOrPlayInAppYouTube() {
  var val = (document.getElementById("yt-inapp-input").value || "").trim();
  if (!val) return;
  var videoId = "";
  var match = val.match(/(?:v=|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  if (match) {
    videoId = match[1];
  } else if (val.length === 11 && !val.includes(" ")) {
    videoId = val;
  } else {
    // If text query, open YouTube search in browser view
    openInAppView("browser", "YouTube Search (" + val + ")", "https://m.youtube.com/results?search_query=" + encodeURIComponent(val));
    return;
  }
  playYtVideo(videoId, "Video (" + videoId + ")");
}

// 2. HACKER NEWS REALTIME API (NO PROXY NEEDED, DIRECT FIREBASE CORS)
function fetchHackerNewsStories() {
  var list = document.getElementById("hn-stories-list");
  list.innerHTML = '<div style="padding:16px;color:var(--cyan)">Fetching top stories live from Hacker News...</div>';

  fetch("https://hacker-news.firebaseio.com/v0/topstories.json")
    .then(r => r.json())
    .then(ids => {
      var top20 = ids.slice(0, 18);
      return Promise.all(top20.map(id => fetch("https://hacker-news.firebaseio.com/v0/item/" + id + ".json").then(r => r.json())));
    })
    .then(stories => {
      var html = "";
      for (var i = 0; i < stories.length; i++) {
        var s = stories[i];
        if (!s) continue;
        var host = "";
        try { if (s.url) host = new URL(s.url).hostname.replace("www.", ""); } catch(e) {}
        html += '<div class="hw-card inapp-btn nav-item" style="cursor:pointer;" onclick="openHnStory(\'' + (s.url ? encodeURIComponent(s.url) : '') + '\', \'' + encodeURIComponent(s.title) + '\')">' +
                '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">' +
                '<b style="color:var(--cyan);font-size:13px;">' + (i + 1) + '. ' + s.title + '</b>' +
                (host ? '<span class="stat-pill">' + host + '</span>' : '') +
                '</div>' +
                '<div style="color:var(--muted);font-size:11px;">' + s.score + ' points by ' + s.by + ' | ' + (s.descendants || 0) + ' comments</div>' +
                '</div>';
      }
      list.innerHTML = html;
      updateInAppButtonSelection();
    })
    .catch(err => {
      list.innerHTML = '<div style="color:var(--red);padding:16px;">Failed to load Hacker News: ' + err + '</div>';
    });
}

function openHnStory(encodedUrl, encodedTitle) {
  var url = decodeURIComponent(encodedUrl);
  var title = decodeURIComponent(encodedTitle);
  if (url) {
    openInAppView("browser", title, url);
  }
}

// 3. WIKIPEDIA REST API (DIRECT FROM TV)
function searchWiki() {
  var q = (document.getElementById("wiki-search-input").value || "").trim();
  if (!q) return;
  fetchWikiSummary(q);
}

function randomWiki() {
  var content = document.getElementById("wiki-content");
  content.innerHTML = '<div style="color:var(--cyan);">Fetching random article from Wikipedia...</div>';
  fetch("https://en.wikipedia.org/api/rest_v1/page/random/summary")
    .then(r => r.json())
    .then(data => renderWikiData(data))
    .catch(e => { content.innerHTML = '<div style="color:var(--red);">Error: ' + e + '</div>'; });
}

function fetchWikiSummary(title) {
  var content = document.getElementById("wiki-content");
  content.innerHTML = '<div style="color:var(--cyan);">Querying Wikipedia: ' + title + '...</div>';
  fetch("https://en.wikipedia.org/api/rest_v1/page/summary/" + encodeURIComponent(title))
    .then(r => r.json())
    .then(data => renderWikiData(data))
    .catch(e => { content.innerHTML = '<div style="color:var(--red);">Error: ' + e + '</div>'; });
}

function renderWikiData(data) {
  var content = document.getElementById("wiki-content");
  if (!data || !data.title) {
    content.innerHTML = '<div style="color:var(--amber);">No article found.</div>';
    return;
  }
  var imgHtml = "";
  if (data.thumbnail && data.thumbnail.source) {
    imgHtml = '<img src="' + data.thumbnail.source + '" style="max-height:220px;border-radius:6px;float:right;margin-left:16px;margin-bottom:10px;border:1px solid var(--border);">';
  }
  content.innerHTML = imgHtml +
    '<h2 style="color:var(--cyan);margin-bottom:6px;">' + data.title + '</h2>' +
    '<div style="color:var(--amber);margin-bottom:12px;font-style:italic;">' + (data.description || "") + '</div>' +
    '<p style="font-size:14px;line-height:1.6;color:var(--fg);">' + (data.extract_html || data.extract || "No extract available.") + '</p>' +
    '<div style="margin-top:16px;clear:both;">' +
    (data.content_urls && data.content_urls.desktop ? '<button class="nav-btn inapp-btn" onclick="openInAppView(\'browser\', \'' + data.title + '\', \'' + data.content_urls.desktop.page + '\')">Read Full Article in Web</button>' : '') +
    '</div>';
  updateInAppButtonSelection();
}

// 4. 4K CINEMA THEATER
function playCinemaFilm(url, title) {
  var p = document.getElementById("cinema-video-player");
  p.src = url;
  p.play();
  document.getElementById("app-win-title").textContent = "Cinema: " + title;
}

function playCinemaCustom() {
  var u = (document.getElementById("cinema-custom-url").value || "").trim();
  if (u) playCinemaFilm(u, "Custom Stream");
}

// 5. 2048 RETRO TV ARCADE GAME
var board2048 = [];
var score2048 = 0;
var best2048 = 0;

function init2048() {
  board2048 = [
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0]
  ];
  score2048 = 0;
  addRandomTile2048();
  addRandomTile2048();
  render2048();
}

function addRandomTile2048() {
  var empty = [];
  for (var r = 0; r < 4; r++) {
    for (var c = 0; c < 4; c++) {
      if (board2048[r][c] === 0) empty.push({ r: r, c: c });
    }
  }
  if (empty.length === 0) return;
  var spot = empty[Math.floor(Math.random() * empty.length)];
  board2048[spot.r][spot.c] = Math.random() < 0.9 ? 2 : 4;
}

function render2048() {
  var grid = document.getElementById("grid-2048");
  if (!grid) return;
  var html = "";
  for (var r = 0; r < 4; r++) {
    for (var c = 0; c < 4; c++) {
      var val = board2048[r][c];
      html += '<div class="cell-2048" data-val="' + val + '">' + (val > 0 ? val : '') + '</div>';
    }
  }
  grid.innerHTML = html;
  document.getElementById("g2048-score").textContent = score2048;
  if (score2048 > best2048) best2048 = score2048;
  document.getElementById("g2048-best").textContent = best2048;
}

function slideRow(row) {
  var arr = row.filter(x => x !== 0);
  for (var i = 0; i < arr.length - 1; i++) {
    if (arr[i] === arr[i + 1]) {
      arr[i] *= 2;
      score2048 += arr[i];
      arr[i + 1] = 0;
    }
  }
  arr = arr.filter(x => x !== 0);
  while (arr.length < 4) arr.push(0);
  return arr;
}

function move2048(dir) {
  var prev = JSON.stringify(board2048);
  if (dir === "left") {
    for (var r = 0; r < 4; r++) board2048[r] = slideRow(board2048[r]);
  } else if (dir === "right") {
    for (var r = 0; r < 4; r++) board2048[r] = slideRow(board2048[r].slice().reverse()).reverse();
  } else if (dir === "up") {
    for (var c = 0; c < 4; c++) {
      var col = [board2048[0][c], board2048[1][c], board2048[2][c], board2048[3][c]];
      var sl = slideRow(col);
      for (var r = 0; r < 4; r++) board2048[r][c] = sl[r];
    }
  } else if (dir === "down") {
    for (var c = 0; c < 4; c++) {
      var col = [board2048[0][c], board2048[1][c], board2048[2][c], board2048[3][c]].reverse();
      var sl = slideRow(col).reverse();
      for (var r = 0; r < 4; r++) board2048[r][c] = sl[r];
    }
  }
  if (JSON.stringify(board2048) !== prev) {
    addRandomTile2048();
    render2048();
  }
}

// 6. BROWSER NAVIGATOR
function navigateBrowserUrl() {
  var u = (document.getElementById("browser-url-input").value || "").trim();
  if (!u) return;
  if (u.indexOf("http") !== 0) u = "https://" + u;
  document.getElementById("browser-frame").src = u;
}

// DOCK LOGIC
function launchDockApp(idx) {
  var apps = getSavedApps();
  var app = apps[idx];
  if (!app) return;
  if (app.action === "live_tv") { switchWorkspace(2); bindLiveBroadcast(); return; }
  if (app.action === "ws_4") { switchWorkspace(4); return; }

  if (app.appType) {
    openInAppView(app.appType, app.name, app.url);
  } else if (app.inAppUrl || app.url) {
    openInAppView("direct_frame", app.name, app.inAppUrl || app.url);
  }
}

function getSavedApps() {
  try {
    var r = localStorage.getItem("omarchy_apps_live_v5");
    if (r) return JSON.parse(r);
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
            '<div class="app-name">' + a.name + '</div>' +
            '<div class="app-desc">' + (a.desc || a.url || a.inAppUrl || a.appType) + '</div>' +
            '</button>';
  }
  grid.innerHTML = html;
  updateButtonSelection();
}

function addCustomApp() {
  var nameEl = document.getElementById("custom-app-name");
  var urlEl = document.getElementById("custom-app-url");
  var name = (nameEl.value || "").trim();
  var url = (urlEl.value || "").trim();
  if (!name || !url) return;
  if (url.indexOf("http") !== 0) url = "https://" + url;
  var apps = getSavedApps();
  apps.push({ name: name, desc: "Custom Web App", appType: "browser", url: url });
  try { localStorage.setItem("omarchy_apps_live_v5", JSON.stringify(apps)); } catch (e) {}
  nameEl.value = ""; urlEl.value = "";
  renderAppDock();
}

function resetCustomApps() {
  try { localStorage.removeItem("omarchy_apps_live_v5"); } catch (e) {}
  renderAppDock();
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

  var bb = document.getElementById("bri-bar");
  var bt = document.getElementById("bri-bar-txt");
  if (bb) bb.style.width = liveState.brightness + "%";
  if (bt) bt.textContent = liveState.brightness + "%";

  var cb = document.getElementById("con-bar");
  var ct = document.getElementById("con-bar-txt");
  if (cb) cb.style.width = liveState.contrast + "%";
  if (ct) ct.textContent = liveState.contrast + "%";
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
  try { localStorage.setItem("omarchy_theme_inapp_v5", t); } catch (e) {}
}

function cycleTheme() {
  currentThemeIdx = (currentThemeIdx + 1) % THEMES.length;
  applyTheme(THEMES[currentThemeIdx]);
}

function getVisibleNavItems() {
  var ws = document.getElementById("ws-" + currentWorkspace);
  if (!ws) return [];
  return Array.prototype.slice.call(ws.querySelectorAll(".app-card, .nav-btn"));
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
  return Array.prototype.slice.call(overlay.querySelectorAll(".inapp-ctrl-btn, .inapp-view.active .inapp-btn"));
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

  // REMOTE BACK BUTTON (461 / 8 / 27) -> CLOSE IN-APP WINDOW!
  if (kc === 461 || kc === 8 || kc === 27) {
    if (isAppWindowOpen) {
      closeInAppWindow();
      e.preventDefault();
      return;
    }
  }

  // WHEN IN-APP OVERLAY IS OPEN: HANDLE D-PAD & ENTER FOR IN-APP BUTTONS & 2048
  if (isAppWindowOpen) {
    if (currentInAppView === "game_2048") {
      if (kc === 37) { move2048("left"); e.preventDefault(); return; }
      if (kc === 38) { move2048("up"); e.preventDefault(); return; }
      if (kc === 39) { move2048("right"); e.preventDefault(); return; }
      if (kc === 40) { move2048("down"); e.preventDefault(); return; }
    }

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
}, 2500);

window.addEventListener("load", function() {
  try {
    var saved = localStorage.getItem("omarchy_theme_inapp_v5");
    if (saved) {
      var idx = THEMES.indexOf(saved);
      if (idx !== -1) currentThemeIdx = idx;
      applyTheme(saved);
    }
  } catch (e) {}
  renderAppDock();
  queryLiveSpecs();
  refreshLiveHardware();
  measureRealGpuFrame();
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
    print(f"=== OMARCHY IN-APP RUNTIME SERVER v5.0 ON 0.0.0.0:{PORT} ===")
    server.serve_forever()
'''

TARGET = Path("/Users/anas/Documents/VIDAA/inspector_server.py")
TARGET.write_text(CODE, encoding="utf-8")
print(f"[+] Wrote {len(CODE)} bytes to {TARGET}")
