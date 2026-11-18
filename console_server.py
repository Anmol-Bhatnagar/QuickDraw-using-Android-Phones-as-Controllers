"""
CONSOLE SERVER & LAUNCHER
Main entry point for the Phone-Controller Game Library.
Starts:
  - Game Registry & Discovery
  - Console Manager & State Machine
  - Unified WebSocket Server (Port 8000)
  - Mobile Companion & Asset HTTP Server (Port 8080)
  - Optional ngrok tunnel (bypasses firewalls automatically)
  - Fullscreen Interactive Console Display (Pygame / OpenCV)
"""

import os
import sys
import argparse
import signal
import time

from server.game_registry import GameRegistry
from server.console_manager import ConsoleManager
from server.network_hub import NetworkHub
from ui.console_display import ConsoleDisplay


def print_qr(url: str):
    """Print a QR code in the terminal for the given URL."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        pass  # qrcode library not installed, skip


def main():
    parser = argparse.ArgumentParser(description="Phone-Controller Game Library Console")
    parser.add_argument("--ws-port",   type=int, default=8000,  help="WebSocket port (default: 8000)")
    parser.add_argument("--http-port", type=int, default=8080,  help="HTTP Web Controller port (default: 8080)")
    parser.add_argument("--headless",  action="store_true", help="Run server only without any GUI or browser window")
    parser.add_argument("--browser",   action="store_true", help="Open 3D Game Screen in default web browser")
    parser.add_argument("--opencv",    action="store_true", help="Open OpenCV graphical console window")
    parser.add_argument("--no-tunnel", action="store_true", help="Disable ngrok tunnel (LAN only)")
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir   = os.path.join(project_dir, "games")

    print("==================================================")
    print("🎮  PHONE-CONTROLLER GAME LIBRARY CONSOLE  🎮")
    print("==================================================")

    # 1. Initialize Game Registry
    registry = GameRegistry(games_dir=games_dir)
    print(f"Loaded {len(registry.games)} game(s): {', '.join(registry.games.keys())}")

    # 2. Initialize Console Manager
    console_mgr = ConsoleManager(project_dir=project_dir, registry=registry)

    # 3. Initialize Network Hub
    network_hub = NetworkHub(project_dir=project_dir, ws_port=args.ws_port, http_port=args.http_port)

    # Connect callbacks
    console_mgr.set_broadcast_callback(network_hub.broadcast)
    network_hub.start(
        on_message=console_mgr.process_incoming_message,
        on_connect=console_mgr.register_client,
        on_disconnect=console_mgr.unregister_client
    )

    local_ip    = network_hub.local_ip
    http_port   = args.http_port
    ws_port     = args.ws_port

    # 4. Start ngrok tunnel (bypasses Windows Firewall GPO restrictions)
    public_phone_url = f"http://{local_ip}:{http_port}/phone"
    public_ws_url    = f"ws://{local_ip}:{ws_port}"
    tunnel_mgr       = None

    if not args.no_tunnel:
        try:
            from server.tunnel import TunnelManager
            tunnel_mgr = TunnelManager(local_port=http_port, project_dir=project_dir)
            tunnel_url = tunnel_mgr.start()
            if tunnel_url:
                public_phone_url = tunnel_url + "/phone"
                # For WebSocket, the ngrok HTTP tunnel also proxies WS connections
                public_ws_url = tunnel_url.replace("https://", "wss://").replace("http://", "ws://")
                # Push tunnel URLs into network_hub so /info endpoint returns them
                network_hub.tunnel_phone_url = public_phone_url
                network_hub.tunnel_ws_url    = public_ws_url
        except Exception as e:
            print(f"[Console] Tunnel skipped: {e}")

    # 5. Print connection info
    print("\n" + "="*52)
    print("  📱  PHONE CONNECTION INFO")
    print("="*52)
    print(f"  Local URL:   http://{local_ip}:{http_port}/phone")
    if tunnel_mgr and tunnel_mgr.public_url:
        print(f"  PUBLIC URL:  {public_phone_url}")
        print(f"  (Works on ANY network — Wi-Fi, hotspot, cellular)")
    print(f"  APK WS:      ws://{local_ip}:{ws_port}")
    print("="*52)
    print(f"\n  📲 Scan this QR to open on phone:")
    print_qr(public_phone_url)
    print(f"\n  URL: {public_phone_url}\n")

    # 6. Decide which Display UI to run
    def on_exit(*_):
        print("\nShutting down Console...")
        if tunnel_mgr:
            tunnel_mgr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_exit)

    if args.opencv and not args.headless:
        display = ConsoleDisplay(
            console_mgr=console_mgr,
            local_ip=local_ip,
            http_port=http_port,
            ws_port=ws_port
        )
        console_mgr.set_ui_update_callback(lambda: None)
        display.run_loop()

    elif not args.headless:
        import webbrowser
        webbrowser.open(f"http://localhost:{http_port}/")
        print("[Console] 🎮 3D Game Console opened in your browser.")
        print("[Console] Server running. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            on_exit()
    else:
        print("[Console] Running in HEADLESS mode. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            on_exit()


if __name__ == "__main__":
    main()
