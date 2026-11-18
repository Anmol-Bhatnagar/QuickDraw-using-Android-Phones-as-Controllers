"""
CONSOLE SERVER & LAUNCHER
Main entry point for the Phone-Controller Game Library.
Starts:
  - Game Registry & Discovery
  - Console Manager & State Machine
  - Unified WebSocket Server (Port 8000)
  - Mobile Companion & Asset HTTP Server (Port 8080)
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

def main():
    parser = argparse.ArgumentParser(description="Phone-Controller Game Library Console")
    parser = argparse.ArgumentParser(description="Phone-Controller Game Library Console")
    parser.add_argument("--ws-port", type=int, default=8000, help="WebSocket port (default: 8000)")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP Web Controller port (default: 8080)")
    parser.add_argument("--headless", action="store_true", help="Run server only without any GUI or browser window")
    parser.add_argument("--browser", action="store_true", help="Open 3D Game Screen in default web browser (default)")
    parser.add_argument("--opencv", action="store_true", help="Open OpenCV graphical console window instead of browser")
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    games_dir = os.path.join(project_dir, "games")

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

    print(f"\n[Console] Access Mobile Web Controller at: http://{network_hub.local_ip}:{args.http_port}")
    print(f"[Console] Android APK connects to: ws://{network_hub.local_ip}:{args.ws_port}")
    print("[Console] Download updated APK at: http://{}:{}/download-apk\n".format(network_hub.local_ip, args.http_port))

    # 4. Decide which Display UI to run (prevents duplicate windows)
    if args.opencv and not args.headless:
        # Run OpenCV Console Window
        display = ConsoleDisplay(
            console_mgr=console_mgr,
            local_ip=network_hub.local_ip,
            http_port=args.http_port,
            ws_port=args.ws_port
        )
        console_mgr.set_ui_update_callback(lambda: None)

        def sig_handler(sig, frame):
            print("\nShutting down Console...")
            display.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, sig_handler)
        display.run_loop()
    elif not args.headless:
        # Default: Open the 3D Game Screen in Web Browser
        import webbrowser
        webbrowser.open(f"http://localhost:{args.http_port}/")
        print("[Console] 🎮 3D Game Console opened in your browser.")
        print("[Console] Server running. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down Console...")
    else:
        print("[Console] Running in HEADLESS mode. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down Console...")

if __name__ == "__main__":
    main()
