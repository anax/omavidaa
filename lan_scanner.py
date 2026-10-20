#!/usr/bin/env python3
"""
Omarchy TV OS - VIDAA Local Network (SSDP / UPnP / MQTT / Debug Port) Scanner
Discovers Hisense/VIDAA TVs on the LAN and inspects open ports and UPnP descriptors.
"""

import socket
import ssl
import sys
import urllib.request
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

VIDAA_PORTS = {
    36669: "VIDAA RemoteNOW MQTT Broker (TLS)",
    36670: "VIDAA RemoteNOW Companion Service",
    8008: "DIAL / Cast HTTP Service",
    8009: "Cast TLS Service",
    9222: "Chromium Remote Debugging (DevTools)",
    9223: "Cobalt / WebKit Remote Debugging",
    49152: "UPnP / DLNA MediaRenderer",
    49153: "UPnP / DLNA Service",
    38400: "Hisense SmartTV Service",
    55000: "Legacy TV Remote Control"
}


def ssdp_discover(timeout=3.0):
    """Send SSDP M-SEARCH multicast to discover UPnP/DIAL Smart TVs."""
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        "ST: ssdp:all\r\n\r\n"
    ).encode("utf-8")

    discovered = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)
    try:
        sock.sendto(msg, ("239.255.255.250", 1900))
        while True:
            data, addr = sock.recvfrom(4096)
            ip = addr[0]
            text = data.decode("utf-8", errors="ignore")
            loc_match = re.search(r"(?i)^LOCATION:\s*(.+)$", text, re.M)
            srv_match = re.search(r"(?i)^SERVER:\s*(.+)$", text, re.M)
            loc = loc_match.group(1).strip() if loc_match else None
            srv = srv_match.group(1).strip() if srv_match else None
            if ip not in discovered:
                discovered[ip] = {"locations": set(), "servers": set()}
            if loc:
                discovered[ip]["locations"].add(loc)
            if srv:
                discovered[ip]["servers"].add(srv)
    except socket.timeout:
        pass
    except Exception as e:
        print(f"[!] SSDP multicast error: {e}")
    finally:
        sock.close()
    return discovered


def check_port(ip, port, timeout=0.6):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.close()
        return True
    except Exception:
        return False


def probe_mqtt_tls_cert(ip, port=36669):
    """Inspect the TLS certificate presented by the VIDAA MQTT broker on 36669."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((ip, port), timeout=1.5) as sock:
            with ctx.wrap_socket(sock, server_hostname=ip) as ssock:
                return {
                    "cipher": ssock.cipher(),
                    "version": ssock.version(),
                }
    except Exception as e:
        return {"error": str(e)}


def probe_host(ip):
    open_ports = {}
    for port, desc in VIDAA_PORTS.items():
        if check_port(ip, port):
            open_ports[port] = desc
    return ip, open_ports


def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Omarchy-Inspector/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.read(8192).decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error: {e}"


def main():
    target_ip = sys.argv[1] if len(sys.argv) > 1 else None
    if target_ip:
        print(f"[*] Probing target TV IP: {target_ip} ...")
        _, open_ports = probe_host(target_ip)
        print(f"[+] Open VIDAA ports on {target_ip}: {open_ports}")
        if 36669 in open_ports:
            print(f"[+] MQTT Broker TLS info: {probe_mqtt_tls_cert(target_ip, 36669)}")
        return

    print("[*] Running SSDP multicast discovery on LAN...")
    ssdp = ssdp_discover()
    for ip, info in ssdp.items():
        print(f"\n[SSDP Device] {ip}")
        for s in info["servers"]:
            print(f"  Server: {s}")
        for loc in list(info["locations"])[:3]:
            print(f"  Location: {loc}")
            xml = fetch_url(loc)
            friendly = re.findall(r"<friendlyName>(.*?)</friendlyName>", xml)
            model = re.findall(r"<modelName>(.*?)</modelName>", xml)
            mfg = re.findall(r"<manufacturer>(.*?)</manufacturer>", xml)
            if friendly or model or mfg:
                print(f"    -> Manufacturer: {mfg} | Model: {model} | Name: {friendly}")

        _, open_ports = probe_host(ip)
        if open_ports:
            print(f"  Open VIDAA Ports: {open_ports}")
            if 36669 in open_ports:
                print(f"  MQTT TLS Probe: {probe_mqtt_tls_cert(ip)}")


if __name__ == "__main__":
    main()
