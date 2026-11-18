"""
Tilt Maze: Phone-controlled 3D marble physics game.
Tilt phone to roll ball, shake or tap JUMP to hop over pits, collect stars!
"""

import os
import cv2
import time
import math
import queue
import random
import threading
import numpy as np
from games.base_game import BaseGame

class TiltMazeGame(BaseGame):
    def __init__(self):
        super().__init__(
            game_id="tilt_maze",
            title="Tilt Maze",
            description="Roll the ball by tilting phone, shake or tap JUMP over hazard pits, and collect glowing stars!",
            thumbnail="thumbnail.png",
            banner="banner.png",
            min_players=1,
            max_players=2,
            controller_type="tilt_maze",
            controller_spec={
                "type": "tilt_maze",
                "title": "Tilt Maze",
                "instructions": "Tilt phone to roll ball across the table. Tap JUMP or shake phone to hop over red pits!",
                "buttons": ["JUMP"],
                "roles": ["player1", "player2"],
                "haptics": True
            }
        )
        self.input_queue = queue.Queue()
        self.window_name = "Tilt Maze - Console"

    def handle_input(self, player: str, data: dict):
        self.input_queue.put((player, data, time.time()))

    def run(self, stop_event: threading.Event):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WINDOW_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        w, h = 1280, 720
        arena_w, arena_h = 900, 560
        arena_x = (w - arena_w) // 2
        arena_y = (h - arena_h) // 2

        # Pits configuration (relative to arena center)
        pits = [
            (-280, -160, 48),
            (280, -160, 48),
            (-280, 160, 48),
            (280, 160, 48),
            (0, -110, 52),
            (0, 110, 52),
            (-150, 0, 45),
            (150, 0, 45)
        ]

        # Player states
        players_state = {
            "player1": {
                "x": arena_x + arena_w // 2 - 120.0,
                "y": arena_y + arena_h // 2,
                "vx": 0.0, "vy": 0.0,
                "jump_t": 0.0, "score": 0,
                "falling": 0.0, "color": (255, 180, 50), # Cyan/Blue BGR
                "label": "P1"
            },
            "player2": {
                "x": arena_x + arena_w // 2 + 120.0,
                "y": arena_y + arena_h // 2,
                "vx": 0.0, "vy": 0.0,
                "jump_t": 0.0, "score": 0,
                "falling": 0.0, "color": (50, 140, 255), # Orange BGR
                "label": "P2"
            }
        }

        # Collectible star
        star = {"x": arena_x + arena_w // 2, "y": arena_y + arena_h // 2, "r": 24}

        def respawn_star():
            for _ in range(30):
                rx = arena_x + 60 + random.random() * (arena_w - 120)
                ry = arena_y + 60 + random.random() * (arena_h - 120)
                safe = True
                for px, py, pr in pits:
                    center_px = arena_x + arena_w // 2 + px
                    center_py = arena_y + arena_h // 2 + py
                    if math.hypot(rx - center_px, ry - center_py) < pr + 50:
                        safe = False
                        break
                if safe:
                    star["x"] = rx
                    star["y"] = ry
                    return
            star["x"] = arena_x + arena_w // 2
            star["y"] = arena_y + arena_h // 2

        respawn_star()

        last_time = time.time()
        start_time = time.time()
        round_duration = 60.0

        ball_radius = 20.0
        accel_factor = 1400.0
        drag = 0.05
        jump_duration = 0.62

        tilt_inputs = {"player1": (0.0, 0.0), "player2": (0.0, 0.0)}

        while not stop_event.is_set():
            now = time.time()
            dt = min(now - last_time, 0.05)
            last_time = now

            # Process input queue
            while not self.input_queue.empty():
                try:
                    role, data, t = self.input_queue.get_nowait()
                    if role not in players_state:
                        role = "player1"

                    # Button Jump
                    if data.get("type") in ("button", "action") or data.get("key") == "a" or data.get("action") == "JUMP":
                        if players_state[role]["jump_t"] <= 0 and players_state[role]["falling"] <= 0:
                            players_state[role]["jump_t"] = jump_duration
                            if self.context:
                                self.context.send_to_players({"t": "buzz", "ms": 30, "target": role})

                    # Motion
                    if "tilt_x" in data and "tilt_y" in data:
                        tilt_inputs[role] = (float(data["tilt_x"]), float(data["tilt_y"]))
                    elif "roll" in data and "pitch" in data:
                        tilt_inputs[role] = (float(data["roll"]) / 45.0, float(data["pitch"]) / 45.0)
                    elif "aim" in data and "lean" in data:
                        tilt_inputs[role] = (float(data["aim"]), float(data["lean"]))

                    # Shake jump
                    if data.get("speed", 0) > 14.0 or data.get("accel_mag", 0) > 15.0:
                        if players_state[role]["jump_t"] <= 0 and players_state[role]["falling"] <= 0:
                            players_state[role]["jump_t"] = jump_duration
                            if self.context:
                                self.context.send_to_players({"t": "buzz", "ms": 30, "target": role})

                except queue.Empty:
                    break

            # Update Physics
            for role, p in players_state.items():
                if p["falling"] > 0:
                    p["falling"] += dt
                    if p["falling"] > 0.65:
                        p["falling"] = 0.0
                        p["x"] = arena_x + arena_w // 2 + (-120 if role == "player1" else 120)
                        p["y"] = arena_y + arena_h // 2
                        p["vx"] = 0.0
                        p["vy"] = 0.0
                    continue

                tx, ty = tilt_inputs.get(role, (0.0, 0.0))
                tx = max(-1.0, min(1.0, tx))
                ty = max(-1.0, min(1.0, ty))

                p["vx"] += tx * accel_factor * dt
                p["vy"] += ty * accel_factor * dt

                friction = math.pow(drag, dt)
                p["vx"] *= friction
                p["vy"] *= friction

                if p["jump_t"] > 0:
                    p["jump_t"] -= dt
                    if p["jump_t"] < 0:
                        p["jump_t"] = 0.0

                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

                # Wall bounds
                if p["x"] - ball_radius < arena_x:
                    p["x"] = arena_x + ball_radius
                    p["vx"] = -p["vx"] * 0.6
                elif p["x"] + ball_radius > arena_x + arena_w:
                    p["x"] = arena_x + arena_w - ball_radius
                    p["vx"] = -p["vx"] * 0.6

                if p["y"] - ball_radius < arena_y:
                    p["y"] = arena_y + ball_radius
                    p["vy"] = -p["vy"] * 0.6
                elif p["y"] + ball_radius > arena_y + arena_h:
                    p["y"] = arena_y + arena_h - ball_radius
                    p["vy"] = -p["vy"] * 0.6

                # Pit check (if not jumping)
                if p["jump_t"] <= 0:
                    for px, py, pr in pits:
                        cpx = arena_x + arena_w // 2 + px
                        cpy = arena_y + arena_h // 2 + py
                        if math.hypot(p["x"] - cpx, p["y"] - cpy) < pr * 0.8:
                            p["falling"] = 0.01
                            p["score"] = max(0, p["score"] - 1)
                            if self.context:
                                self.context.send_to_players({"t": "buzz", "ms": 200, "target": role})
                            break

                # Star collection
                if math.hypot(p["x"] - star["x"], p["y"] - star["y"]) < ball_radius + star["r"]:
                    p["score"] += 1
                    respawn_star()
                    if self.context:
                        self.context.send_to_players({"t": "buzz", "ms": 45, "target": role})

            # Draw Render Frame
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:] = (20, 16, 12) # Dark background

            # Arena bed
            cv2.rectangle(frame, (arena_x, arena_y), (arena_x + arena_w, arena_y + arena_h), (40, 32, 26), -1)
            cv2.rectangle(frame, (arena_x, arena_y), (arena_x + arena_w, arena_y + arena_h), (200, 180, 100), 4)

            # Draw Hazard Pits
            for px, py, pr in pits:
                cpx = int(arena_x + arena_w // 2 + px)
                cpy = int(arena_y + arena_h // 2 + py)
                cv2.circle(frame, (cpx, cpy), int(pr), (30, 20, 120), -1)
                cv2.circle(frame, (cpx, cpy), int(pr), (50, 50, 240), 3)

            # Draw Star
            sx, sy = int(star["x"]), int(star["y"])
            cv2.circle(frame, (sx, sy), int(star["r"]), (30, 220, 255), -1)
            cv2.circle(frame, (sx, sy), int(star["r"] + 4), (0, 255, 255), 2)
            cv2.putText(frame, "STAR", (sx - 20, sy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)

            # Draw Players
            for role, p in players_state.items():
                if p["falling"] > 0:
                    scale = max(0.1, 1.0 - p["falling"] * 1.5)
                    cv2.circle(frame, (int(p["x"]), int(p["y"])), int(ball_radius * scale), p["color"], -1)
                    continue

                lift = 0
                if p["jump_t"] > 0:
                    prog = 1.0 - (p["jump_t"] / jump_duration)
                    lift = int(math.sin(prog * math.pi) * 22)

                # Shadow
                cv2.ellipse(frame, (int(p["x"]), int(p["y"])), (int(ball_radius * 1.2), int(ball_radius * 0.7)),
                            0, 0, 360, (15, 12, 10), -1)

                # Marble
                bx, by = int(p["x"]), int(p["y"] - lift)
                cv2.circle(frame, (bx, by), int(ball_radius), p["color"], -1)
                cv2.circle(frame, (bx, by), int(ball_radius), (255, 255, 255), 2)
                cv2.putText(frame, p["label"], (bx - 10, by + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            # Header Scoreboard
            rem = max(0, int(round_duration - (now - start_time)))
            cv2.putText(frame, f"TILT MAZE  |  TIME: {rem}s", (w // 2 - 160, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame, f"P1: {players_state['player1']['score']}", (arena_x + 20, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 180, 50), 3)
            cv2.putText(frame, f"P2: {players_state['player2']['score']}", (arena_x + arena_w - 120, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (50, 140, 255), 3)

            cv2.imshow(self.window_name, frame)
            key = cv2.waitKey(16) & 0xFF
            if key == 27: # ESC
                if self.context:
                    self.context.request_home()
                break
            elif key == ord(' '): # Keyboard Jump test
                players_state["player1"]["jump_t"] = jump_duration

        cv2.destroyWindow(self.window_name)

    def cleanup(self):
        try:
            cv2.destroyWindow(self.window_name)
        except Exception:
            pass

def create_game():
    return TiltMazeGame()

Game = TiltMazeGame
