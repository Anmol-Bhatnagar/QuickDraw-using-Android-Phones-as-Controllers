"""
Game Registry: Discovers and manages game plugins in the games/ directory.
Adding a new game is as simple as creating a folder inside games/ with a game.py
containing a Game class that inherits from BaseGame.
"""

import os
import sys
import importlib.util
from typing import Dict, List, Optional
from games.base_game import BaseGame

class GameRegistry:
    def __init__(self, games_dir: str):
        self.games_dir = games_dir
        self.games: Dict[str, BaseGame] = {}
        self.game_order: List[str] = []
        self.discover_games()

    def discover_games(self):
        """Scans games_dir for valid game packages."""
        self.games.clear()
        self.game_order.clear()
        
        if not os.path.exists(self.games_dir):
            os.makedirs(self.games_dir, exist_ok=True)
            return

        for entry in os.listdir(self.games_dir):
            game_path = os.path.join(self.games_dir, entry)
            if not os.path.isdir(game_path) or entry.startswith("__"):
                continue

            game_py = os.path.join(game_path, "game.py")
            if not os.path.exists(game_py):
                continue

            try:
                module_name = f"games.{entry}.game"
                spec = importlib.util.spec_from_file_location(module_name, game_py)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Look for Game class or create_game function
                    game_instance = None
                    if hasattr(module, "Game") and issubclass(module.Game, BaseGame):
                        game_instance = module.Game()
                    elif hasattr(module, "create_game"):
                        game_instance = module.create_game()

                    if game_instance:
                        self.games[game_instance.id] = game_instance
                        self.game_order.append(game_instance.id)
                        print(f"[GameRegistry] Loaded game: '{game_instance.title}' (id: {game_instance.id})")
                    else:
                        print(f"[GameRegistry] Skipped {entry}: No BaseGame class found in game.py")
            except Exception as e:
                print(f"[GameRegistry] Failed to load game from {entry}: {e}")
                import traceback
                traceback.print_exc()

    def get_game(self, game_id: str) -> Optional[BaseGame]:
        return self.games.get(game_id)

    def get_all_games(self) -> List[BaseGame]:
        return [self.games[gid] for gid in self.game_order]

    def get_games_manifest(self) -> List[Dict]:
        return [self.games[gid].to_dict() for gid in self.game_order]
