"""
Quickdraw Game Module.
Adapted to run within the Console Game Library.
"""

import os
import sys
import cv2
import time
import queue
import random
import threading
import requests
import qrcode
import numpy as np
from PIL import Image

import pygame
from games.base_game import BaseGame

# Import local voice module
from games.quickdraw import voice

def apply_sepia(frame):
    sepia_kernel = np.array([[0.272, 0.534, 0.131],
                             [0.349, 0.686, 0.168],
                             [0.393, 0.769, 0.189]])
    sepia = cv2.transform(frame, sepia_kernel)
    sepia = np.clip(sepia, 0, 255).astype(np.uint8)
    return sepia

def upload_to_catbox(filepath, result_dict):
    try:
        with open(filepath, 'rb') as f:
            files = {'reqtype': (None, 'fileupload'), 'fileToUpload': f}
            response = requests.post('https://catbox.moe/user/api.php', files=files, timeout=15)
            if response.status_code == 200:
                result_dict['url'] = response.text.strip()
            else:
                result_dict['error'] = f"Status: {response.status_code}"
    except Exception as e:
        result_dict['error'] = str(e)

class QuickdrawGame(BaseGame):
    def __init__(self):
        super().__init__(
            game_id="quickdraw",
            title="Quickdraw",
            description="Classic Wild West Duel! Holster your phone, listen to the outlaw, and draw when you hear the target word. Fastest trigger wins!",
            thumbnail="thumbnail.png",
            banner="banner.png",
            min_players=2,
            max_players=2,
            controller_type="quickdraw",
            controller_spec={
                "type": "quickdraw",
                "title": "Quickdraw Duel",
                "instructions": "Holster phone. Listen carefully. Press Volume Up/Down or tap TRIGGER when the word is shouted!",
                "buttons": ["TRIGGER"],
                "roles": ["player1", "player2"],
                "haptics": True
            }
        )
        self.msg_queue = queue.Queue()
        self.current_window_name = "Quickdraw - Console"

    def handle_input(self, player: str, data: dict):
        """Called when a controller sends input."""
        server_receive_time = time.time()
        device_time = data.get("time", "Unknown time")
        # Put into message queue
        self.msg_queue.put((player, device_time, server_receive_time))

    def run(self, stop_event: threading.Event):
        game_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(os.path.dirname(game_dir))
        
        # Audio assets
        bgmusic1_path = os.path.join(project_dir, "bgmusic1.wav")
        bgmusic2_path = os.path.join(project_dir, "bgmusic2.wav")
        overlay_audio_path = os.path.join(project_dir, "reveal_overlay.mp3")
        overlay_video_path = os.path.join(project_dir, "reveal_overlay.webm")

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        bgm_channel_1 = pygame.mixer.Channel(0)
        bgm_channel_2 = pygame.mixer.Channel(1)
        voice_channel = pygame.mixer.Channel(2)
        overlay_channel = pygame.mixer.Channel(3)

        bgmusic1 = pygame.mixer.Sound(bgmusic1_path) if os.path.exists(bgmusic1_path) else None
        bgmusic2 = pygame.mixer.Sound(bgmusic2_path) if os.path.exists(bgmusic2_path) else None
        overlay_audio = pygame.mixer.Sound(overlay_audio_path) if os.path.exists(overlay_audio_path) else None

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Quickdraw] Warning: Webcam not opened, trying index 1...")
            cap = cv2.VideoCapture(1)

        # Clear queue
        while not self.msg_queue.empty():
            try:
                self.msg_queue.get_nowait()
            except queue.Empty:
                break

        state = "WAITING"
        get_ready_start_time = 0
        captured_frame = None
        upload_result = {}

        captures_dir = os.path.join(project_dir, "captures")
        os.makedirs(captures_dir, exist_ok=True)

        reveal_queue = None
        audio_reveal_time = 0
        audio_end_time = 0
        target_word = ""

        shoot_start_time = 0
        round_over_start_time = 0
        winner_message = ""
        shot_results = {}
        round_loser = None
        known_players = set()

        def drain_queue():
            while not self.msg_queue.empty():
                try:
                    p, _, _ = self.msg_queue.get_nowait()
                    known_players.add(p)
                except queue.Empty:
                    break

        cv2.namedWindow(self.current_window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.current_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        # Pre-load overlay frames
        ret, test_frame = cap.read()
        frame_w = 640
        frame_h = 480
        if ret and test_frame is not None:
            frame_h, frame_w = test_frame.shape[:2]

        overlay_frames = []
        overlay_fps = 30.0

        if os.path.exists(overlay_video_path):
            ov_cap = cv2.VideoCapture(overlay_video_path)
            fps = ov_cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                overlay_fps = fps
            while True:
                ret, ov = ov_cap.read()
                if not ret:
                    break
                ov = cv2.resize(ov, (frame_w, frame_h))
                gray = cv2.cvtColor(ov, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, 5, 255, cv2.THRESH_BINARY)
                overlay_frames.append({"frame": ov, "mask": mask})
            ov_cap.release()

        print("[Quickdraw] Started. Press SPACE to begin round, or Phone HOME to exit.")

        # Notify mobile controllers that Quickdraw is ready
        if self.context:
            self.context.send_to_players({
                "t": "mode",
                "layout": "quickdraw",
                "name": "Quick Draw",
                "hint": "Holster your phone. Shoot on DRAW!"
            })
            self.context.send_to_players({
                "type": "game_state",
                "t": "quickdraw_state",
                "game_state": "WAITING",
                "state": "WAITING",
                "info": "Press SPACE on laptop or get ready"
            })

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret or frame is None:
                # Fallback blank frame if no camera available
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(frame, "Quickdraw - Camera Not Available", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
            else:
                frame = cv2.flip(frame, 1)

            current_time = time.time()
            clean_frame = frame.copy()

            # Render persistent home hint
            cv2.putText(frame, "[HOME] Press Phone HOME or ESC on Laptop to return to Library", (20, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

            if state == "WAITING":
                cv2.putText(frame, "Press SPACE to start round", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(frame, "(Both players ready your phones)", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                drain_queue()

            elif state == "GET_READY":
                cv2.putText(frame, "GET READY...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)

                # Wait 5 seconds (or 20 in full tournament) or SPACE to accelerate
                if current_time - get_ready_start_time >= 5.0:
                    state = "DISTRACTING"
                    audio_reveal_time = 0
                    audio_end_time = 0
                    target_word = ""

                    if bgm_channel_1 and bgmusic1:
                        bgm_channel_1.fadeout(1500)
                    if bgm_channel_2 and bgmusic2:
                        bgm_channel_2.play(bgmusic2, loops=-1, fade_ms=1500)

                    try:
                        reveal_queue = voice.play_random_audio(channel=voice_channel)
                    except Exception as e:
                        print(f"[Quickdraw] Audio play error: {e}")
                        # Fallback timer if voice audio fails
                        audio_reveal_time = current_time + random.uniform(3.0, 6.0)
                        audio_end_time = audio_reveal_time + 4.0
                        target_word = "DRAW"

                    shot_results = {}
                    winner_message = ""
                    drain_queue()

                    if self.context:
                        self.context.send_to_players({
                            "type": "game_state",
                            "game_state": "DISTRACTING",
                            "t": "quickdraw_state",
                            "state": "DISTRACTING",
                            "info": "Listen to the outlaw..."
                        })

            elif state == "DISTRACTING":
                cv2.putText(frame, "Get ready...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
                if target_word:
                    cv2.putText(frame, f"Target: {target_word.upper()}", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

                # Check for false starts
                if not self.msg_queue.empty():
                    player, dev_time, srv_time = self.msg_queue.get_nowait()
                    known_players.add(player)
                    winner_message = f"Opponent wins ({player} false start!)"
                    shot_results = {}
                    round_loser = player
                    state = "WAITING_FOR_AUDIO_END"
                    drain_queue()

                    if self.context:
                        self.context.send_to_players({
                            "type": "game_state",
                            "game_state": "FALSE_START",
                            "t": "quickdraw_state",
                            "state": "FALSE_START",
                            "loser": player
                        })
                else:
                    if reveal_queue is not None:
                        try:
                            event, reveal_time, end_time, word = reveal_queue.get_nowait()
                            if event == "reveal_at":
                                audio_reveal_time = reveal_time
                                audio_end_time = end_time
                                target_word = word
                                reveal_queue = None
                        except queue.Empty:
                            pass

                    if audio_reveal_time > 0 and current_time >= audio_reveal_time:
                        state = "SHOOT_WINDOW"
                        shoot_start_time = audio_reveal_time
                        frame = cv2.bitwise_not(frame)
                        if self.context:
                            self.context.send_to_players({
                                "type": "game_state",
                                "game_state": "SHOOT",
                                "t": "quickdraw_state",
                                "state": "SHOOT",
                                "word": target_word
                            })

            elif state == "SHOOT_WINDOW":
                cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
                if target_word:
                    cv2.putText(frame, target_word.upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)

                while not self.msg_queue.empty():
                    try:
                        player, dev_time, srv_time = self.msg_queue.get_nowait()
                        known_players.add(player)
                        if player not in shot_results:
                            shot_results[player] = (srv_time - shoot_start_time) * 1000
                    except queue.Empty:
                        break

                if shot_results:
                    state = "WAITING_FOR_AUDIO_END"
                    winner_message = ""
                    fastest_player = min(shot_results, key=shot_results.get)
                    losers = [p for p in known_players if p != fastest_player]
                    round_loser = losers[0] if losers else ("player2" if fastest_player == "player1" else "player1")

                elif audio_end_time > 0 and current_time >= audio_end_time:
                    winner_message = "DRAW (Too slow!)"
                    state = "ROUND_OVER"
                    round_over_start_time = current_time
                    drain_queue()
                    if bgm_channel_1: bgm_channel_1.stop()
                    if bgm_channel_2: bgm_channel_2.stop()
                    if voice_channel: voice_channel.stop()
                    if overlay_audio and overlay_channel:
                        overlay_channel.play(overlay_audio)
                    if self.context:
                        self.context.send_to_players({
                            "type": "game_state",
                            "game_state": "ROUND_OVER",
                            "t": "quickdraw_state",
                            "state": "ROUND_OVER",
                            "winner": None,
                            "info": "DRAW (Too slow!)"
                        })

            elif state == "WAITING_FOR_AUDIO_END":
                if "false start" in winner_message:
                    cv2.putText(frame, "False start!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 3)
                else:
                    cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
                    if target_word:
                        cv2.putText(frame, target_word.upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)

                while not self.msg_queue.empty():
                    try:
                        player, dev_time, srv_time = self.msg_queue.get_nowait()
                        known_players.add(player)
                        if player not in shot_results and "false start" not in winner_message:
                            shot_results[player] = (srv_time - shoot_start_time) * 1000
                    except queue.Empty:
                        break

                if (audio_end_time > 0 and current_time >= audio_end_time) or (audio_end_time == 0 and current_time - shoot_start_time > 2.0):
                    state = "ROUND_OVER"
                    round_over_start_time = current_time
                    if bgm_channel_1: bgm_channel_1.stop()
                    if bgm_channel_2: bgm_channel_2.stop()
                    if voice_channel: voice_channel.stop()
                    if overlay_audio and overlay_channel:
                        overlay_channel.play(overlay_audio)
                    if self.context:
                        win_txt = winner_message if winner_message else (f"{fastest_player.upper()} WINS!" if shot_results else "DRAW")
                        self.context.send_to_players({
                            "type": "game_state",
                            "game_state": "ROUND_OVER",
                            "t": "quickdraw_state",
                            "state": "ROUND_OVER",
                            "winner": fastest_player if shot_results else None,
                            "info": win_txt
                        })

            elif state == "ROUND_OVER":
                drain_queue()
                if overlay_frames:
                    elapsed = current_time - round_over_start_time
                    frame_idx = int(elapsed * overlay_fps)
                    if frame_idx < len(overlay_frames):
                        ov_data = overlay_frames[frame_idx]
                        ov = ov_data["frame"]
                        mask = ov_data["mask"]
                        if round_loser == "player1":
                            ov = cv2.flip(ov, 1)
                            mask = cv2.flip(mask, 1)
                        cv2.copyTo(ov, mask, frame)

                y_offset = 100
                if winner_message:
                    cv2.putText(frame, winner_message, (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                else:
                    if shot_results:
                        fastest_player = min(shot_results, key=shot_results.get)
                        cv2.putText(frame, f"{fastest_player.upper()} WINS!", (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3)
                        y_offset += 60
                        results_text = []
                        display_players = list(known_players) if len(known_players) >= 2 else list(shot_results.keys())
                        for p in display_players:
                            if p in shot_results:
                                results_text.append(f"{p}: {shot_results[p]:.0f}ms")
                            else:
                                results_text.append(f"{p}: DNF")
                        cv2.putText(frame, " vs ".join(results_text), (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

                if current_time - round_over_start_time > 3.0:
                    cv2.putText(frame, "Press 'T' for Victory Pose! Or SPACE for next round", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            elif state == "UPLOADING":
                frame = captured_frame.copy()
                cv2.putText(frame, "Uploading to cloud...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
                if 'url' in upload_result:
                    url = upload_result['url']
                    qr = qrcode.QRCode(version=1, box_size=5, border=2)
                    qr.add_data(url)
                    qr.make(fit=True)
                    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                    qr_np = np.array(img_qr)[:, :, ::-1].copy()
                    h_qr, w_qr, _ = qr_np.shape
                    h_f, w_f, _ = captured_frame.shape
                    if h_f > h_qr and w_f > w_qr:
                        captured_frame[h_f-h_qr:h_f, w_f-w_qr:w_f] = qr_np
                    cv2.putText(captured_frame, "Scan to Download!", (w_f-w_qr-20, h_f-h_qr-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    state = "SHOW_CAPTURE"
                elif 'error' in upload_result:
                    cv2.putText(captured_frame, f"Upload Failed: {upload_result['error']}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    state = "SHOW_CAPTURE"

            elif state == "SHOW_CAPTURE":
                frame = captured_frame.copy()
                cv2.putText(frame, "Press SPACE for next round", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

            cv2.imshow(self.current_window_name, frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC key
                print("[Quickdraw] ESC pressed on laptop. Exiting to Library.")
                if self.context:
                    self.context.request_home()
                break
            elif key == ord('t') or key == ord('T'):
                if state == "ROUND_OVER" and current_time - round_over_start_time > 3.0:
                    captured_frame = apply_sepia(clean_frame)
                    h, w, _ = captured_frame.shape
                    if "DRAW" in winner_message:
                        cv2.putText(captured_frame, "DRAW", (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 255), 6)
                        cv2.putText(captured_frame, "DRAW", (w//2 + 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 255), 6)
                    else:
                        left_text = "I LOST" if round_loser == "player1" else "I WON"
                        right_text = "I WON" if round_loser == "player1" else "I LOST"
                        cv2.putText(captured_frame, left_text, (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0,
                                    (0, 0, 255) if "LOST" in left_text else (0, 255, 0), 6)
                        cv2.putText(captured_frame, right_text, (w//2 + 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0,
                                    (0, 0, 255) if "LOST" in right_text else (0, 255, 0), 6)
                    filepath = os.path.join(captures_dir, f"pose_{int(time.time())}.jpg")
                    cv2.imwrite(filepath, captured_frame)
                    upload_result = {}
                    threading.Thread(target=upload_to_catbox, args=(filepath, upload_result), daemon=True).start()
                    state = "UPLOADING"
            elif key == 32:  # SPACE
                if state in ["WAITING", "SHOW_CAPTURE"] or (state == "ROUND_OVER" and current_time - round_over_start_time > 3.0):
                    state = "GET_READY"
                    get_ready_start_time = current_time
                    if bgm_channel_1 and bgmusic1:
                        bgm_channel_1.play(bgmusic1)
                    drain_queue()
                    if self.context:
                        self.context.send_to_players({
                            "type": "game_state",
                            "game_state": "GET_READY",
                            "t": "quickdraw_state",
                            "state": "GET_READY",
                            "info": "Round started! Get ready!"
                        })

        # Cleanup on exit
        cap.release()
        cv2.destroyWindow(self.current_window_name)
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        print("[Quickdraw] Exited cleanly.")

    def cleanup(self):
        try:
            cv2.destroyWindow(self.current_window_name)
        except Exception:
            pass
        try:
            if pygame.mixer.get_init():
                pygame.mixer.stop()
        except Exception:
            pass

def create_game():
    return QuickdrawGame()

Game = QuickdrawGame
