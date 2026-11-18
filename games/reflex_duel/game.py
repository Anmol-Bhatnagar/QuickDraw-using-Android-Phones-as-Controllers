"""
Cyber Reflex: A neon-style reflex battle game.
Demonstrates multi-game modularity in the Console Game Library.
"""

import os
import cv2
import time
import queue
import random
import threading
import numpy as np
from games.base_game import BaseGame

class CyberReflexGame(BaseGame):
    def __init__(self):
        super().__init__(
            game_id="reflex_duel",
            title="Cyber Reflex",
            description="Hyper-speed reflex clash! Watch the screen for the GREEN signal. First player to slam the trigger scores! Best of 5 rounds.",
            thumbnail="thumbnail.png",
            banner="banner.png",
            min_players=1,
            max_players=2,
            controller_type="reflex",
            controller_spec={
                "type": "reflex",
                "title": "Cyber Reflex",
                "instructions": "Keep finger ready! When the screen turns NEON GREEN, hit SLAM TRIGGER instantly!",
                "buttons": ["SLAM TRIGGER"],
                "roles": ["player1", "player2"],
                "haptics": True
            }
        )
        self.msg_queue = queue.Queue()
        self.window_name = "Cyber Reflex - Console"

    def handle_input(self, player: str, data: dict):
        srv_time = time.time()
        self.msg_queue.put((player, srv_time))

    def run(self, stop_event: threading.Event):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        scores = {"player1": 0, "player2": 0}
        state = "ROUND_PREP"
        round_num = 1
        max_rounds = 5
        prep_start_time = time.time()
        green_trigger_time = 0
        round_winner = ""
        round_times = {}
        round_end_time = 0

        w, h = 1280, 720
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        def clear_queue():
            while not self.msg_queue.empty():
                try:
                    self.msg_queue.get_nowait()
                except queue.Empty:
                    break

        print("[CyberReflex] Started. Best of 5 rounds.")

        while not stop_event.is_set():
            now = time.time()
            frame[:] = (20, 20, 25)  # Dark cyber background

            # Persistent Console Home Hint
            cv2.putText(frame, "[HOME] Press Phone HOME or ESC on Laptop to return to Library", (30, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

            # Scoreboard
            cv2.putText(frame, f"CYBER REFLEX - ROUND {round_num}/{max_rounds}", (50, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
            cv2.putText(frame, f"P1 Score: {scores['player1']}   |   P2 Score: {scores['player2']}", (50, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 200, 0), 2)

            if state == "ROUND_PREP":
                frame[150:h-100, 50:w-50] = (20, 20, 80) # Red glow
                cv2.putText(frame, "HOLD YOUR TRIGGER...", (w//2 - 250, h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
                cv2.putText(frame, "DO NOT TAP EARLY!", (w//2 - 180, h//2 + 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 150, 255), 2)

                # Early tap penalty
                if not self.msg_queue.empty():
                    player, t = self.msg_queue.get_nowait()
                    other = "player2" if player == "player1" else "player1"
                    scores[other] += 1
                    round_winner = f"{player} FALSE START! Point to {other}"
                    state = "ROUND_OVER"
                    round_end_time = now
                    clear_queue()
                elif now - prep_start_time > random.uniform(2.5, 5.0):
                    state = "SIGNAL_ACTIVE"
                    green_trigger_time = now
                    clear_queue()
                    if self.context:
                        self.context.send_to_players({"type": "signal", "color": "green"})

            elif state == "SIGNAL_ACTIVE":
                frame[150:h-100, 50:w-50] = (0, 180, 0) # Bright green flash!
                cv2.putText(frame, "SLAM NOW!!!", (w//2 - 180, h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)

                while not self.msg_queue.empty():
                    player, t = self.msg_queue.get_nowait()
                    reaction = (t - green_trigger_time) * 1000
                    if player not in round_times:
                        round_times[player] = reaction

                if round_times:
                    winner = min(round_times, key=round_times.get)
                    scores[winner] += 1
                    round_winner = f"{winner.upper()} WON ({round_times[winner]:.0f}ms)!"
                    state = "ROUND_OVER"
                    round_end_time = now

                elif now - green_trigger_time > 4.0:
                    round_winner = "Too slow! No points awarded."
                    state = "ROUND_OVER"
                    round_end_time = now

            elif state == "ROUND_OVER":
                cv2.putText(frame, round_winner, (w//2 - 300, h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3)

                if now - round_end_time > 2.5:
                    if round_num >= max_rounds:
                        state = "MATCH_OVER"
                    else:
                        round_num += 1
                        round_times = {}
                        prep_start_time = now
                        state = "ROUND_PREP"
                        clear_queue()

            elif state == "MATCH_OVER":
                p1_s, p2_s = scores["player1"], scores["player2"]
                if p1_s > p2_s:
                    champ = "PLAYER 1 IS THE CHAMPION!"
                elif p2_s > p1_s:
                    champ = "PLAYER 2 IS THE CHAMPION!"
                else:
                    champ = "IT'S A TIE!"

                cv2.putText(frame, champ, (w//2 - 350, h//2 - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                cv2.putText(frame, "Press SPACE to rematch, or Phone HOME to exit", (w//2 - 380, h//2 + 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

            cv2.imshow(self.window_name, frame)
            key = cv2.waitKey(16) & 0xFF
            if key == 27:  # ESC
                if self.context:
                    self.context.request_home()
                break
            elif key == 32 and state == "MATCH_OVER":  # SPACE to rematch
                scores = {"player1": 0, "player2": 0}
                round_num = 1
                round_times = {}
                prep_start_time = now
                state = "ROUND_PREP"
                clear_queue()

        cv2.destroyWindow(self.window_name)

    def cleanup(self):
        try:
            cv2.destroyWindow(self.window_name)
        except Exception:
            pass

def create_game():
    return CyberReflexGame()

Game = CyberReflexGame
