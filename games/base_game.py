"""
Base class for games in the Console Library.
Every game module in games/ inherits from BaseGame.
"""

import threading
from typing import Dict, Any, Optional

class BaseGame:
    def __init__(self, game_id: str, title: str, description: str, 
                 thumbnail: str = "thumbnail.png",
                 banner: str = "banner.png",
                 min_players: int = 1, 
                 max_players: int = 2,
                 controller_type: str = "generic",
                 controller_spec: Optional[Dict[str, Any]] = None):
        self.id = game_id
        self.title = title
        self.description = description
        self.thumbnail = thumbnail
        self.banner = banner
        self.min_players = min_players
        self.max_players = max_players
        self.controller_type = controller_type
        self.controller_spec = controller_spec or {
            "type": controller_type,
            "title": title,
            "instructions": "Use phone controller to play.",
            "buttons": ["ACTION"]
        }
        
        self.is_active = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.context: Optional[Any] = None

    def start(self, context: Any):
        """
        Launches the game in a managed thread or loop.
        context provides access to:
          - context.send_to_players(message_dict)
          - context.request_home()
          - context.get_connected_players()
          - context.project_dir
        """
        self._stop_event.clear()
        self.is_active = True
        self.context = context
        self._thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self._thread.start()

    def _run_wrapper(self):
        try:
            self.run(self._stop_event)
        except Exception as e:
            print(f"[{self.title}] Error during game execution: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_active = False
            self.cleanup()
            if self.context:
                self.context.on_game_exited(self.id)

    def run(self, stop_event: threading.Event):
        """Override this method to implement the main game loop."""
        raise NotImplementedError("Games must implement run(stop_event)")

    def handle_input(self, player: str, data: Dict[str, Any]):
        """Override this to receive inputs sent from mobile controllers."""
        pass

    def stop(self):
        """Signals the game to stop immediately."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.is_active = False
        self.cleanup()

    def cleanup(self):
        """Clean up game resources (cameras, cv2 windows, sounds, etc.)."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Metadata serialized for console UI and mobile controller library view."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "thumbnail": f"/games/{self.id}/{self.thumbnail}",
            "banner": f"/games/{self.id}/{self.banner}",
            "min_players": self.min_players,
            "max_players": self.max_players,
            "controller_type": self.controller_type,
            "controller_spec": self.controller_spec
        }
