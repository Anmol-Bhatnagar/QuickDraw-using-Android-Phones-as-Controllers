"""
Network Hub: Dual HTTP/HTTPS server + WebSocket Hub.
Connects the PC 3D Game Screen, the Native Android Controller APK,
and the Mobile Web Controller.
"""

import os
import sys
import json
import time
import socket
import ssl
import struct
import base64
import hashlib
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional, Dict, Any, List

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ico": "image/x-icon",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".webm": "video/webm",
    ".apk": "application/vnd.android.package-archive"
}

def get_primary_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_all_ips() -> List[str]:
    ips = {get_primary_ip()}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    ips.discard("0.0.0.0")
    return sorted(ips)

def find_openssl() -> Optional[str]:
    found = shutil.which("openssl")
    if found:
        return found
    candidates = [
        "C:\\Program Files\\Git\\usr\\bin\\openssl.exe",
        "C:\\Program Files\\Git\\mingw64\\bin\\openssl.exe",
        "C:\\Program Files (x86)\\Git\\usr\\bin\\openssl.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def ensure_ssl_certs(project_dir: str, ips: List[str]) -> bool:
    certs_dir = os.path.join(project_dir, "certs")
    cert_path = os.path.join(certs_dir, "cert.pem")
    key_path = os.path.join(certs_dir, "key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True

    openssl = find_openssl()
    if not openssl:
        print("[NetworkHub] OpenSSL not found; running HTTP only.")
        return False

    os.makedirs(certs_dir, exist_ok=True)
    san = ",".join(["DNS:localhost"] + [f"IP:{ip}" for ip in ips] + ["IP:127.0.0.1"])
    print(f"[NetworkHub] Generating self-signed SSL cert for {', '.join(ips)}...")
    cmd = [
        openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", key_path, "-out", cert_path,
        "-days", "820", "-subj", "/CN=PhonePartyGames",
        "-addext", f"subjectAltName={san}",
        "-addext", "basicConstraints=CA:FALSE"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0

class WSClosed(Exception):
    pass

def ws_frame(payload, opcode=0x1) -> bytes:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    head = bytearray([0x80 | opcode])
    n = len(payload)
    if n < 126:
        head.append(n)
    elif n < 65536:
        head.append(126)
        head += struct.pack(">H", n)
    else:
        head.append(127)
        head += struct.pack(">Q", n)
    return bytes(head) + payload

def _read_exact(rfile, n) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = rfile.read(n - len(buf))
        if not chunk:
            raise WSClosed()
        buf += chunk
    return buf

def ws_read(rfile):
    b1, b2 = _read_exact(rfile, 2)
    opcode = b1 & 0x0F
    masked = b2 & 0x80
    length = b2 & 0x7F
    if length == 126:
        length = struct.unpack(">H", _read_exact(rfile, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _read_exact(rfile, 8))[0]
    if length > (1 << 20):
        raise WSClosed()
    mask = _read_exact(rfile, 4) if masked else None
    data = _read_exact(rfile, length) if length else b""
    if mask:
        data = bytes(byte ^ mask[i & 3] for i, byte in enumerate(data))
    return opcode, data

class ConnectedClient:
    def __init__(self, wfile, role="phone"):
        self.wfile = wfile
        self.role = role  # "screen" or "phone"
        self.pid = None
        self.name = ""
        self.lock = threading.Lock()
        self.alive = True

    def send(self, obj: Dict[str, Any]):
        if not self.alive:
            return
        data = ws_frame(json.dumps(obj, separators=(",", ":")))
        try:
            with self.lock:
                self.wfile.write(data)
                self.wfile.flush()
        except OSError:
            self.alive = False

class WsServerAdapter:
    """Adapter for legacy standalone websocket-server connections on port 8000."""
    def __init__(self, server, client_dict, role="phone"):
        self.server = server
        self.client_dict = client_dict
        self.role = role
        self.pid = None
        self.name = ""
        self.lock = threading.Lock()
        self.alive = True

    def send(self, obj: Dict[str, Any]):
        if not self.alive:
            return
        try:
            with self.lock:
                self.server.send_message(self.client_dict, json.dumps(obj, separators=(",", ":")))
        except Exception:
            self.alive = False

class NetworkHub:
    def __init__(self, project_dir: str, ws_port: int = 8000, http_port: int = 8080, https_port: int = 8443):
        self.project_dir = project_dir
        self.ws_port = ws_port
        self.http_port = http_port
        self.https_port = https_port
        self.local_ip = get_primary_ip()
        self.all_ips = get_all_ips()
        
        self.clients: List[Any] = []
        self.legacy_clients: Dict[int, WsServerAdapter] = {}
        self.clients_lock = threading.RLock()
        self.on_message_callback: Optional[Callable] = None
        self.has_ssl = False

    def start(self, on_message: Callable, on_connect: Optional[Callable] = None, on_disconnect: Optional[Callable] = None):
        self.on_message_callback = on_message
        self.has_ssl = ensure_ssl_certs(self.project_dir, self.all_ips)

        # Plain HTTP server on http_port
        http_thread = threading.Thread(target=self._run_http_server, daemon=True)
        http_thread.start()

        # HTTPS server on https_port (if SSL available)
        if self.has_ssl:
            https_thread = threading.Thread(target=self._run_https_server, daemon=True)
            https_thread.start()

        # Standalone WebSocket server on ws_port (e.g. 8000) for native APK
        if self.ws_port and self.ws_port != self.http_port:
            try:
                import websocket_server
                def _ws_new(client, server):
                    adapter = WsServerAdapter(server, client, role="phone")
                    with self.clients_lock:
                        self.legacy_clients[client['id']] = adapter
                    self.add_client(adapter)

                def _ws_left(client, server):
                    with self.clients_lock:
                        adapter = self.legacy_clients.pop(client['id'], None)
                    if adapter:
                        self.remove_client(adapter)

                def _ws_msg(client, server, message):
                    with self.clients_lock:
                        adapter = self.legacy_clients.get(client['id'])
                    if adapter:
                        try:
                            msg = json.loads(message)
                            self.route_message(adapter, msg)
                        except Exception:
                            pass

                def _run_legacy_ws():
                    try:
                        srv = websocket_server.WebsocketServer(host="0.0.0.0", port=self.ws_port)
                        srv.set_fn_new_client(_ws_new)
                        srv.set_fn_client_left(_ws_left)
                        srv.set_fn_message_received(_ws_msg)
                        srv.run_forever()
                    except Exception as e:
                        print(f"[NetworkHub] Legacy WS on port {self.ws_port} notice: {e}")

                ws_thread = threading.Thread(target=_run_legacy_ws, daemon=True)
                ws_thread.start()
                print(f"[NetworkHub] Android WebSocket server on: ws://{self.local_ip}:{self.ws_port}")
            except ImportError:
                pass

        print(f"[NetworkHub] Game Console Screen on: http://localhost:{self.http_port}/")
        if self.has_ssl:
            print(f"[NetworkHub] Mobile Phone Controller (HTTPS): https://{self.local_ip}:{self.https_port}/phone")
        print(f"[NetworkHub] Mobile Phone Controller (HTTP):  http://{self.local_ip}:{self.http_port}/phone")
        print(f"[NetworkHub] Download Android APK at: http://{self.local_ip}:{self.http_port}/download-apk")

    def _make_handler(self, is_tls: bool):
        hub = self
        class DynamicHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "ConsoleHub/2.0"

            def setup(self):
                super().setup()
                try:
                    self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except OSError:
                    pass

            def log_message(self, fmt, *args):
                pass

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path == "/ws":
                    self.handle_ws()
                    return
                elif path == "/info":
                    self.handle_info()
                    return
                elif path == "/download-apk" or path == "/QuickDraw.apk":
                    self.serve_static_file(os.path.join(hub.project_dir, "QuickDraw.apk"))
                    return
                elif path == "/" or path == "/index.html":
                    self.serve_static_file(os.path.join(hub.project_dir, "party_games", "index.html"))
                    return
                elif path == "/phone" or path == "/phone.html":
                    self.serve_static_file(os.path.join(hub.project_dir, "party_games", "phone.html"))
                    return
                elif path.startswith("/games/"):
                    rel = path[len("/games/"):].replace("/", os.sep)
                    self.serve_static_file(os.path.join(hub.project_dir, "games", rel))
                    return
                elif path.startswith("/js/") or path.startswith("/lib/"):
                    rel = path.lstrip("/").replace("/", os.sep)
                    self.serve_static_file(os.path.join(hub.project_dir, "party_games", rel))
                    return
                elif path.startswith("/ui/"):
                    rel = path[len("/ui/"):].replace("/", os.sep)
                    self.serve_static_file(os.path.join(hub.project_dir, "ui", rel))
                    return
                
                # Default fallback
                rel = path.lstrip("/").replace("/", os.sep)
                self.serve_static_file(os.path.join(hub.project_dir, "party_games", rel))

            def handle_info(self):
                phone_url = f"http://{hub.local_ip}:{hub.http_port}/phone"
                body = json.dumps({
                    "ip": hub.local_ip,
                    "ips": hub.all_ips,
                    "httpPort": hub.http_port,
                    "httpsPort": hub.https_port if hub.has_ssl else hub.http_port,
                    "phoneUrl": phone_url
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def serve_static_file(self, full_path: str):
                if not os.path.isfile(full_path):
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"404 Not Found")
                    return

                ext = os.path.splitext(full_path)[1].lower()
                mime = MIME_TYPES.get(ext, "application/octet-stream")
                try:
                    with open(full_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e:
                    self.send_error(500, str(e))

            def handle_ws(self):
                key = self.headers.get("Sec-WebSocket-Key")
                if not key:
                    self.send_error(400, "Missing Sec-WebSocket-Key")
                    return
                accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
                self.wfile.write(
                    b"HTTP/1.1 101 Switching Protocols\r\n"
                    b"Upgrade: websocket\r\n"
                    b"Connection: Upgrade\r\n"
                    b"Sec-WebSocket-Accept: " + accept.encode() + b"\r\n\r\n"
                )
                self.wfile.flush()
                self.close_connection = True

                role = "screen" if "role=screen" in self.path else "phone"
                client = ConnectedClient(self.wfile, role)
                hub.add_client(client)
                try:
                    while client.alive:
                        opcode, data = ws_read(self.rfile)
                        if opcode == 0x8:  # close
                            break
                        elif opcode == 0x9:  # ping -> pong
                            with client.lock:
                                self.wfile.write(ws_frame(data, 0xA))
                                self.wfile.flush()
                            continue
                        elif opcode != 0x1:
                            continue

                        try:
                            msg = json.loads(data.decode("utf-8"))
                        except Exception:
                            continue

                        hub.route_message(client, msg)
                except Exception:
                    pass
                finally:
                    hub.remove_client(client)

        return DynamicHandler

    def _run_http_server(self):
        handler_cls = self._make_handler(is_tls=False)
        server = ThreadingHTTPServer(("0.0.0.0", self.http_port), handler_cls)
        server.serve_forever()

    def _run_https_server(self):
        handler_cls = self._make_handler(is_tls=True)
        server = ThreadingHTTPServer(("0.0.0.0", self.https_port), handler_cls)
        certs_dir = os.path.join(self.project_dir, "certs")
        cert_path = os.path.join(certs_dir, "cert.pem")
        key_path = os.path.join(certs_dir, "key.pem")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
        server.serve_forever()

    def add_client(self, client: ConnectedClient):
        with self.clients_lock:
            if client.role == "phone":
                taken = set(c.pid for c in self.clients if c.role == "phone" and c.pid is not None)
                client.pid = next(i for i in range(1, 9) if i not in taken)
            self.clients.append(client)

        if client.role == "phone":
            client.send({"t": "assigned", "pid": client.pid})
            print(f"[NetworkHub] Phone controller connected -> Player {client.pid}")
        else:
            print("[NetworkHub] PC Game Screen connected")

        self.announce_roster()

    def remove_client(self, client: ConnectedClient):
        with self.clients_lock:
            if client in self.clients:
                self.clients.remove(client)
        client.alive = False
        if client.role == "phone":
            print(f"[NetworkHub] Phone controller disconnected (Player {client.pid})")
            self.broadcast_to_screens({"t": "leave", "pid": client.pid})
        else:
            print("[NetworkHub] PC Game Screen disconnected")
        self.announce_roster()

    def announce_roster(self):
        with self.clients_lock:
            phones = [{"pid": c.pid, "name": c.name} for c in self.clients if c.role == "phone"]
            screens = sum(1 for c in self.clients if c.role == "screen")
            msg = {"t": "roster", "players": phones, "screens": screens}
            for c in list(self.clients):
                c.send(msg)

    def broadcast_to_screens(self, msg: Dict[str, Any]):
        with self.clients_lock:
            for c in list(self.clients):
                if c.role == "screen":
                    c.send(msg)

    def broadcast_to_phones(self, msg: Dict[str, Any]):
        with self.clients_lock:
            for c in list(self.clients):
                if c.role == "phone":
                    c.send(msg)

    def broadcast(self, payload: Dict[str, Any]):
        with self.clients_lock:
            for c in list(self.clients):
                c.send(payload)

    def route_message(self, client: ConnectedClient, msg: Dict[str, Any]):
        kind = msg.get("t") or msg.get("type")

        if kind == "p":  # ping keepalive
            client.send({"t": "p"})
            return

        # Forward to ConsoleManager callback if registered
        if self.on_message_callback:
            try:
                self.on_message_callback(client.pid or 1, msg)
            except Exception as e:
                print(f"[NetworkHub] Message routing error: {e}")

        if client.role == "phone":
            msg["pid"] = client.pid
            # Forward motion and buttons to screens
            self.broadcast_to_screens(msg)
            return

        # From screen: forward mode, hud, buzz to phones
        if kind in ("buzz", "mode", "hud", "quickdraw_state"):
            pid = msg.get("pid")
            if pid:
                with self.clients_lock:
                    for c in self.clients:
                        if c.role == "phone" and c.pid == pid:
                            c.send(msg)
            else:
                self.broadcast_to_phones(msg)
