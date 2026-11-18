"""
Console Manager: Central coordinator for the game console.
Handles:
  - Library state (selected game, navigation)
  - Game lifecycle (launch, stop, return to home)
  - Real-time synchronization between Laptop Console Display and Mobile Controllers
"""

import time
import queue
import threading
from typing import Dict, Any, Optional, Callable, List
from server.game_registry import GameRegistry
from games.base_game import BaseGame

class ConsoleContext:
    """Context object provided to running games."""
    def __init__(self, console_mgr: 'ConsoleManager'):
        self._mgr = console_mgr
        self.project_dir = console_mgr.project_dir

    def send_to_players(self, message: Dict[str, Any]):
        self._mgr.broadcast(message)

    def request_home(self):
        self._mgr.request_home()

    def get_connected_players(self) -> List[str]:
        return list(self._mgr.get_connected_players())

    def on_game_exited(self, game_id: str):
        self._mgr.on_game_finished(game_id)

class ConsoleManager:
    SCREEN_LIBRARY = "LIBRARY"
    SCREEN_IN_GAME = "IN_GAME"

    def __init__(self, project_dir: str, registry: GameRegistry):
        self.project_dir = project_dir
        self.registry = registry
        self.state = self.SCREEN_LIBRARY
        self.selected_index = 0
        self.active_game: Optional[BaseGame] = None
        
        # Connected clients & player mappings
        self.clients_to_players: Dict[int, str] = {}
        self.broadcast_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.ui_update_callback: Optional[Callable[[], None]] = None
        
        self.context = ConsoleContext(self)
        self._lock = threading.Lock()

    def set_broadcast_callback(self, cb: Callable[[Dict[str, Any]], None]):
        self.broadcast_callback = cb

    def set_ui_update_callback(self, cb: Callable[[], None]):
        self.ui_update_callback = cb

    def broadcast(self, message: Dict[str, Any]):
        if self.broadcast_callback:
            try:
                self.broadcast_callback(message)
            except Exception as e:
                print(f"[ConsoleManager] Broadcast error: {e}")

    def notify_ui(self):
        if self.ui_update_callback:
            try:
                self.ui_update_callback()
            except Exception as e:
                print(f"[ConsoleManager] UI update callback error: {e}")

    def get_current_game(self) -> Optional[BaseGame]:
        games = self.registry.get_all_games()
        if not games:
            return None
        self.selected_index = self.selected_index % len(games)
        return games[self.selected_index]

    def get_connected_players(self) -> set:
        return set(p for p in self.clients_to_players.values() if p)

    def register_client(self, client_id: int, player_name: str = ""):
        with self._lock:
            self.clients_to_players[client_id] = player_name
        self.sync_client_state()

    def unregister_client(self, client_id: int):
        with self._lock:
            self.clients_to_players.pop(client_id, None)
        self.sync_client_state()

    def set_client_player(self, client_id: int, player_name: str):
        with self._lock:
            self.clients_to_players[client_id] = player_name
        print(f"[ConsoleManager] Client {client_id} assigned role: {player_name}")
        self.sync_client_state()

    def sync_client_state(self):
        """Broadcasts full console state to all connected mobile controllers."""
        current_game = self.get_current_game()
        manifest = self.registry.get_games_manifest()
        
        state_payload = {
            "type": "sync_state",
            "screen": self.state,
            "selected_index": self.selected_index,
            "game": current_game.to_dict() if current_game else None,
            "games": manifest,
            "connected_players": list(self.get_connected_players())
        }
        self.broadcast(state_payload)
        self.notify_ui()

    def navigate(self, direction: str):
        """Traverse library sequentially: 'prev' or 'next'."""
        with self._lock:
            if self.state != self.SCREEN_LIBRARY:
                return

            games = self.registry.get_all_games()
            if not games:
                return

            if direction in ["next", "right", 1]:
                self.selected_index = (self.selected_index + 1) % len(games)
            elif direction in ["prev", "left", -1]:
                self.selected_index = (self.selected_index - 1) % len(games)

            print(f"[ConsoleManager] Navigated to game [{self.selected_index}]: {games[self.selected_index].title}")
        self.sync_client_state()

    def select_game(self, game_id: Optional[str] = None):
        """Launch the selected game."""
        with self._lock:
            if self.state == self.SCREEN_IN_GAME:
                print("[ConsoleManager] Game already in progress.")
                return

            target_game = None
            if game_id:
                target_game = self.registry.get_game(game_id)
            else:
                target_game = self.get_current_game()

            if not target_game:
                print(f"[ConsoleManager] Cannot launch: Game not found ({game_id})")
                return

            print(f"[ConsoleManager] >>> Launching game: {target_game.title} <<<")
            self.state = self.SCREEN_IN_GAME
            self.active_game = target_game

        # Broadcast game started event with controller specs
        start_payload = {
            "type": "game_started",
            "game_id": target_game.id,
            "title": target_game.title,
            "controller_type": target_game.controller_type,
            "controller_spec": target_game.controller_spec
        }
        self.broadcast(start_payload)
        self.notify_ui()

        # Start game
        target_game.start(self.context)

    def request_home(self):
        """Home button triggered (from phone or laptop): return to Game Library."""
        print("[ConsoleManager] >>> HOME requested: Returning to Game Library <<<")
        with self._lock:
            if self.active_game:
                game_to_stop = self.active_game
                self.active_game = None
                game_to_stop.stop()
            self.state = self.SCREEN_LIBRARY

        stop_payload = {
            "type": "game_stopped",
            "screen": self.SCREEN_LIBRARY
        }
        self.broadcast(stop_payload)
        self.sync_client_state()

    def on_game_finished(self, game_id: str):
        """Called when a game naturally finishes or closes."""
        with self._lock:
            if self.active_game and self.active_game.id == game_id:
                self.active_game = None
            self.state = self.SCREEN_LIBRARY
        print(f"[ConsoleManager] Game {game_id} exited. Returning to library.")
        self.sync_client_state()

    def process_incoming_message(self, client_id: int, raw_data: Dict[str, Any]):
        """Dispatches messages from mobile controllers and PC screen."""
        kind = raw_data.get("t") or raw_data.get("type") or raw_data.get("action")
        player = raw_data.get("player") or f"player{client_id}"

        # Check if registering player role
        if raw_data.get("role"):
            player = raw_data["role"]
            self.set_client_player(client_id, player)
        elif raw_data.get("player") and raw_data.get("player") != "Unknown":
            self.clients_to_players[client_id] = raw_data["player"]

        # Universal Home / Menu button
        if kind in ("home", "menu"):
            self.request_home()
            return

        # Python game launches from screen or controller
        if kind in ("launch_python_game", "start_game"):
            self.select_game(raw_data.get("id", "quickdraw"))
            return
        elif kind in ("stop_python_game", "leave"):
            self.request_home()
            return

        # Library navigation & selection
        if kind == "navigate" or kind == "nav":
            direction = raw_data.get("direction") or raw_data.get("dir", "next")
            self.navigate("prev" if direction in (-1, "prev", "left") else "next")
            return
        elif kind in ("select_game", "start"):
            gid = raw_data.get("game_id") or raw_data.get("id")
            if gid and self.registry.get_game(gid):
                self.select_game(gid)
            else:
                with self._lock:
                    self.state = self.SCREEN_IN_GAME
                self.broadcast({
                    "t": "start",
                    "type": "game_started",
                    "game_id": gid
                })
            return
        elif kind == "set_role":
            self.set_client_player(client_id, raw_data.get("role", "player1"))
            return

        # Quickdraw & In-game inputs
        if self.state == self.SCREEN_IN_GAME and self.active_game:
            if kind in ("shoot", "shot", "b") or "time" in raw_data:
                self.active_game.handle_input(player, raw_data)
