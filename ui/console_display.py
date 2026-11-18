"""
Console Display: Visual dashboard for the laptop console (Home / Game Library).
Styled like a modern gaming console (Nintendo Switch / PlayStation Big Picture).
Provides real-time interactive game carousel and phone connection QR code.
"""

import os
import cv2
import time
import qrcode
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
from server.console_manager import ConsoleManager
from games.base_game import BaseGame

class ConsoleDisplay:
    WINDOW_NAME = "CONSOLE GAME HUB - Library"

    def __init__(self, console_mgr: ConsoleManager, local_ip: str, http_port: int, ws_port: int):
        self.mgr = console_mgr
        self.local_ip = local_ip
        self.http_port = http_port
        self.ws_port = ws_port
        self.project_dir = console_mgr.project_dir
        self.is_running = False
        
        # Pre-generate QR Code for mobile controller connection
        self.qr_img = self._generate_qr_code(f"http://{self.local_ip}:{self.http_port}/phone")
        self.cached_thumbnails = {}

    def _generate_qr_code(self, url: str) -> np.ndarray:
        qr = qrcode.QRCode(version=1, box_size=4, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        np_img = np.array(img)[:, :, ::-1]  # RGB to BGR
        return np_img

    def _load_game_thumbnail(self, game: BaseGame, target_w: int, target_h: int) -> np.ndarray:
        cache_key = (game.id, target_w, target_h)
        if cache_key in self.cached_thumbnails:
            return self.cached_thumbnails[cache_key]

        game_dir = os.path.join(self.project_dir, "games", game.id)
        thumb_path = os.path.join(game_dir, game.thumbnail)
        
        if os.path.exists(thumb_path):
            img = cv2.imread(thumb_path)
            if img is not None:
                img = cv2.resize(img, (target_w, target_h))
                self.cached_thumbnails[cache_key] = img
                return img

        # Fallback card if thumbnail missing
        fallback = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        fallback[:] = (40, 30, 30)
        cv2.rectangle(fallback, (2, 2), (target_w - 3, target_h - 3), (0, 200, 255), 2)
        cv2.putText(fallback, game.title[:12], (15, target_h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        self.cached_thumbnails[cache_key] = fallback
        return fallback

    def render_frame(self, w: int = 1280, h: int = 720) -> np.ndarray:
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # Gradient background
        for y in range(h):
            ratio = y / h
            b = int(25 + ratio * 15)
            g = int(20 + ratio * 10)
            r = int(18 + ratio * 8)
            frame[y, :] = (b, g, r)

        games = self.mgr.registry.get_all_games()
        curr_idx = self.mgr.selected_index
        selected_game = games[curr_idx] if games else None

        # 1. Top Bar
        cv2.rectangle(frame, (0, 0), (w, 70), (15, 12, 10), -1)
        cv2.line(frame, (0, 70), (w, 70), (0, 200, 255), 2)

        # Title
        cv2.putText(frame, "CONSOLE GAME HUB", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 3)

        # Connected Controllers & Players
        connected_players = list(self.mgr.get_connected_players())
        p_text = f"Controllers Connected: {len(connected_players)}"
        if "player1" in connected_players:
            p_text += "  [P1 Ready]"
        if "player2" in connected_players:
            p_text += "  [P2 Ready]"
        cv2.putText(frame, p_text, (400, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 255, 120), 2)

        # Server IP Indicator
        ip_text = f"Server: {self.local_ip}:{self.ws_port}"
        cv2.putText(frame, ip_text, (w - 300, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        # 2. Main Game Library Carousel
        if not games:
            cv2.putText(frame, "No games installed in games/ folder.", (w // 2 - 250, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return frame

        # Carousel positioning
        center_x = w // 2
        card_w, card_h = 320, 240
        active_w, active_h = 380, 280
        center_y = 260

        total_games = len(games)
        for offset in range(-2, 3):
            idx = (curr_idx + offset) % total_games
            game = games[idx]

            is_active = (offset == 0)
            cw = active_w if is_active else card_w
            ch = active_h if is_active else card_h
            cx = center_x + offset * (card_w + 40)
            cy = center_y

            x1 = cx - cw // 2
            y1 = cy - ch // 2
            x2 = x1 + cw
            y2 = y1 + ch

            if x2 <= 0 or x1 >= w or y2 <= 0 or y1 >= h:
                continue

            thumb = self._load_game_thumbnail(game, cw, ch)
            
            # Clamp coordinates to frame boundaries
            fx1 = max(0, x1)
            fy1 = max(0, y1)
            fx2 = min(w, x2)
            fy2 = min(h, y2)

            tx1 = fx1 - x1
            ty1 = fy1 - y1
            tx2 = tx1 + (fx2 - fx1)
            ty2 = ty1 + (fy2 - fy1)

            cropped_thumb = thumb[ty1:ty2, tx1:tx2]

            if is_active:
                frame[fy1:fy2, fx1:fx2] = cropped_thumb
                # Glowing border around active game card
                cv2.rectangle(frame, (fx1 - 4, fy1 - 4), (fx2 + 4, fy2 + 4), (0, 240, 255), 4)
                # "PLAY NOW" banner over card
                banner_y1 = max(fy1, fy2 - 40)
                cv2.rectangle(frame, (fx1, banner_y1), (fx2, fy2), (0, 200, 255), -1)
                cv2.putText(frame, "▶ PRESS PLAY / ENTER", (fx1 + 45, fy2 - 13),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2)
            else:
                # Dim unselected cards slightly
                dimmer = np.zeros_like(cropped_thumb)
                cv2.addWeighted(cropped_thumb, 0.55, dimmer, 0.45, 0, frame[fy1:fy2, fx1:fx2])
                cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (80, 80, 80), 2)

        # 3. Selected Game Details Card
        if selected_game:
            detail_y = 440
            cv2.rectangle(frame, (50, detail_y), (w - 50, detail_y + 160), (25, 22, 20), -1)
            cv2.rectangle(frame, (50, detail_y), (w - 50, detail_y + 160), (60, 60, 60), 2)

            # Title & Metadata
            title_str = f"{selected_game.title.upper()} ({curr_idx + 1}/{total_games})"
            cv2.putText(frame, title_str, (80, detail_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 230, 255), 3)

            meta_str = f"Players: {selected_game.min_players}-{selected_game.max_players}  |  Controller: {selected_game.controller_type.upper()}"
            cv2.putText(frame, meta_str, (80, detail_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 180), 2)

            # Description (word wrap)
            desc = selected_game.description
            cv2.putText(frame, desc[:90], (80, detail_y + 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 1)
            if len(desc) > 90:
                cv2.putText(frame, desc[90:180], (80, detail_y + 135), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 1)

            # QR Code on the right side of detail card
            qr_h, qr_w = self.qr_img.shape[:2]
            qr_x = w - 80 - qr_w
            qr_y = detail_y + 15
            if qr_x > 0 and qr_y + qr_h < h:
                frame[qr_y:qr_y + qr_h, qr_x:qr_x + qr_w] = self.qr_img
                cv2.putText(frame, "Scan for Phone Controller", (qr_x - 30, qr_y + qr_h + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 4. Bottom Controls Bar
        cv2.rectangle(frame, (0, h - 50), (w, h), (15, 12, 10), -1)
        cv2.line(frame, (0, h - 50), (w, h - 50), (60, 60, 60), 1)

        ctrl_help = "PHONE: Swipe/Buttons to Browse & Select  |  LAPTOP: Left/Right Arrows, ENTER to Play, ESC to Exit"
        cv2.putText(frame, ctrl_help, (50, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

        return frame

    def run_loop(self):
        """Main display loop when in LIBRARY screen."""
        self.is_running = True
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        print("[ConsoleDisplay] Console Library Display opened.")

        while self.is_running:
            # If a game is currently active, hide library window and yield loop
            if self.mgr.state == ConsoleManager.SCREEN_IN_GAME:
                time.sleep(0.1)
                continue

            frame = self.render_frame()
            cv2.imshow(self.WINDOW_NAME, frame)

            key = cv2.waitKey(30) & 0xFF
            if key == 27:  # ESC
                print("[ConsoleDisplay] Exiting console server.")
                self.is_running = False
                break
            elif key in [81, 2, 2424832]:  # Left Arrow
                self.mgr.navigate("prev")
            elif key in [83, 3, 2555904]:  # Right Arrow
                self.mgr.navigate("next")
            elif key in [13, 32]:  # ENTER or SPACE
                self.mgr.select_game()

        cv2.destroyWindow(self.WINDOW_NAME)
        self.is_running = False

    def close(self):
        self.is_running = False
        try:
            cv2.destroyWindow(self.WINDOW_NAME)
        except Exception:
            pass
