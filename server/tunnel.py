"""
tunnel.py - Automatic tunnel manager (no account required).
Tries cloudflared first (Cloudflare Tunnel — completely free, no sign-up),
then falls back to ngrok if an authtoken is configured.

Cloudflared install:  winget install Cloudflare.cloudflared
Ngrok install:        winget install Ngrok.Ngrok  (then: ngrok config add-authtoken <token>)
"""

import json
import os
import re
import subprocess
import sys
import time
from typing import Optional

# ── Cloudflared search paths ──────────────────────────────────────────────────
CLOUDFLARED_PATHS = [
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"),
    os.path.expandvars(r"%USERPROFILE%\scoop\shims\cloudflared.exe"),
]

# ── Ngrok search paths ────────────────────────────────────────────────────────
NGROK_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"),
    r"C:\ProgramData\chocolatey\bin\ngrok.exe",
    os.path.expandvars(r"%USERPROFILE%\scoop\shims\ngrok.exe"),
]


def _which(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)


def find_cloudflared() -> Optional[str]:
    found = _which("cloudflared")
    if found:
        return found
    for p in CLOUDFLARED_PATHS:
        if os.path.isfile(p):
            return p
    return None


def find_ngrok() -> Optional[str]:
    found = _which("ngrok")
    if found:
        return found
    for p in NGROK_PATHS:
        if os.path.isfile(p):
            return p
    return None


def _kill_by_name(exe_name: str):
    """Silently kill all processes by executable name."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", exe_name],
                           capture_output=True)
    except Exception:
        pass


class TunnelManager:
    def __init__(self, local_port: int, project_dir: str):
        self.local_port   = local_port
        self.project_dir  = project_dir
        self.public_url: Optional[str] = None
        self.ws_url:     Optional[str] = None
        self._process:   Optional[subprocess.Popen] = None
        self._kind:      Optional[str] = None          # "cloudflared" | "ngrok"

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> Optional[str]:
        """
        Try cloudflared first (no auth), then ngrok.
        Returns the public HTTPS URL, or None if no tunnel tool found.
        """
        url = self._try_cloudflared()
        if url:
            return url
        url = self._try_ngrok()
        if url:
            return url

        print("[Tunnel] No tunnel tool available — running LAN-only mode.")
        print("[Tunnel] Install cloudflared: winget install Cloudflare.cloudflared")
        return None

    def stop(self):
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None
        if self._kind == "cloudflared":
            _kill_by_name("cloudflared.exe")
        elif self._kind == "ngrok":
            _kill_by_name("ngrok.exe")
        self._remove_tunnel_file()

    # ─────────────────────────────────────────────────────────────────────────
    # Cloudflared (Cloudflare Quick Tunnel — no account needed)
    # ─────────────────────────────────────────────────────────────────────────

    def _try_cloudflared(self) -> Optional[str]:
        exe = find_cloudflared()
        if not exe:
            return None

        _kill_by_name("cloudflared.exe")
        print(f"[Tunnel] Starting Cloudflare tunnel (no auth required)...")

        try:
            # cloudflared tunnel --url http://localhost:<port> --no-autoupdate
            self._process = subprocess.Popen(
                [exe, "tunnel", "--url", f"http://localhost:{self.local_port}",
                 "--no-autoupdate"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if sys.platform == "win32" else 0)
            )
        except Exception as e:
            print(f"[Tunnel] cloudflared failed to start: {e}")
            return None

        # cloudflared prints the URL to stderr
        url = self._read_cloudflared_url(timeout=20.0)
        if not url:
            print("[Tunnel] cloudflared did not emit a URL within 20 s")
            return None

        self._kind = "cloudflared"
        self._set_urls(url)
        return url

    def _read_cloudflared_url(self, timeout: float) -> Optional[str]:
        """Read stderr of the cloudflared process until a trycloudflare URL appears."""
        url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._process.poll() is not None:   # process died
                break
            try:
                line = self._process.stderr.readline()
            except Exception:
                break
            if not line:
                time.sleep(0.1)
                continue
            m = url_re.search(line)
            if m:
                return m.group(0)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Ngrok (requires free account + authtoken)
    # ─────────────────────────────────────────────────────────────────────────

    def _try_ngrok(self) -> Optional[str]:
        exe = find_ngrok()
        if not exe:
            return None

        _kill_by_name("ngrok.exe")
        print(f"[Tunnel] Trying ngrok tunnel...")

        try:
            self._process = subprocess.Popen(
                [exe, "http", str(self.local_port),
                 "--log=stdout", "--log-level=warn"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if sys.platform == "win32" else 0)
            )
        except Exception as e:
            print(f"[Tunnel] ngrok failed to start: {e}")
            return None

        url = self._poll_ngrok_api(timeout=12.0)
        if not url:
            print("[Tunnel] ngrok not configured (needs authtoken). "
                  "Run: ngrok config add-authtoken <your_token>")
            return None

        self._kind = "ngrok"
        self._set_urls(url)
        return url

    def _poll_ngrok_api(self, timeout: float) -> Optional[str]:
        import urllib.request, urllib.error
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:4040/api/tunnels", timeout=2) as r:
                    data = json.loads(r.read())
                    for t in data.get("tunnels", []):
                        u = t.get("public_url", "")
                        if u.startswith("https"):
                            return u
                        if u.startswith("http"):
                            return u
            except Exception:
                pass
            time.sleep(0.5)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_urls(self, http_url: str):
        self.public_url = http_url
        self.ws_url = (http_url
                       .replace("https://", "wss://")
                       .replace("http://",  "ws://"))
        self._write_tunnel_file()
        print(f"[Tunnel] ✅ Public URL : {self.public_url}")
        print(f"[Tunnel] ✅ Phone URL  : {self.public_url}/phone")
        print(f"[Tunnel] ✅ APK WS URL : {self.ws_url}")

    def _write_tunnel_file(self):
        tunnel_file = os.path.join(self.project_dir, ".tunnel_url")
        with open(tunnel_file, "w") as f:
            json.dump({
                "http": self.public_url,
                "ws":   self.ws_url,
                "local_port": self.local_port
            }, f)

    def _remove_tunnel_file(self):
        try:
            os.remove(os.path.join(self.project_dir, ".tunnel_url"))
        except Exception:
            pass
