#!/usr/bin/env python3
"""
Packages Omarchy TV OS into an official VIDAA Smart TV Application Bundle (.zip & folder)
Contains appinfo.json, manifest.json, index.html, and valid binary PNG icons.
"""

import json
import os
import struct
import zlib
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
APP_DIR = BASE_DIR / "omarchy-vidaa-app"
ZIP_PATH = BASE_DIR / "omarchy-vidaa-app.zip"


def create_png(width, height, r, g, b):
    """Generate a valid RGBA PNG file without external dependencies."""
    # RGBA scanline: 1 byte filter type (0) + 4 bytes per pixel
    raw_row = bytearray([0])
    for _ in range(width):
        raw_row.extend([r, g, b, 255])
    raw_data = bytes(raw_row * height)
    compressed = zlib.compress(raw_data, 9)

    def chunk(tag, data):
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    return png_bytes


def main():
    APP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Official VIDAA App Manifest: appinfo.json
    appinfo = {
        "id": "org.omarchy.tvos",
        "version": "7.0.0",
        "vendor": "Omarchy",
        "type": "web",
        "main": "index.html",
        "title": "Omarchy TV OS",
        "icon": "icon.png",
        "largeIcon": "icon_large.png",
        "bgImage": "thumbnail.png",
        "splashBackground": "#1a1b26",
        "resolution": "1920x1080",
        "requiredVersion": "3.0.0",
        "transparent": False,
        "supportPreload": True,
        "supportMemory": "1G",
        "trustLevel": "trusted",
        "permissions": [
            "network",
            "media",
            "tv.service"
        ]
    }
    (APP_DIR / "appinfo.json").write_text(json.dumps(appinfo, indent=2), encoding="utf-8")

    # 2. Web App Manifest
    manifest = {
        "name": "Omarchy TV OS",
        "short_name": "Omarchy",
        "start_url": "index.html",
        "display": "fullscreen",
        "background_color": "#1a1b26",
        "theme_color": "#7aa2f7",
        "icons": [
            {"src": "icon_small.png", "sizes": "80x80", "type": "image/png"},
            {"src": "icon.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon_large.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    (APP_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 3. Generate PNG Icons (Tokyo Night Accent Blue #7aa2f7 -> R:122, G:162, B:247)
    (APP_DIR / "icon_small.png").write_bytes(create_png(80, 80, 122, 162, 247))
    (APP_DIR / "icon.png").write_bytes(create_png(192, 192, 122, 162, 247))
    (APP_DIR / "icon_large.png").write_bytes(create_png(512, 512, 122, 162, 247))
    (APP_DIR / "thumbnail.png").write_bytes(create_png(300, 300, 22, 22, 30))

    # 4. Copy standalone index.html from inspector_server.py
    import inspector_server
    standalone_html = inspector_server.HTML_PAGE
    (APP_DIR / "index.html").write_text(standalone_html, encoding="utf-8")

    # 5. Pack into omarchy-vidaa-app.zip
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in APP_DIR.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(APP_DIR)
                zf.write(file, arcname)

    print(f"[+] Successfully built VIDAA App in: {APP_DIR}")
    print(f"[+] Packaged official VIDAA ZIP archive: {ZIP_PATH} ({os.path.getsize(ZIP_PATH)} bytes)")


if __name__ == "__main__":
    main()
