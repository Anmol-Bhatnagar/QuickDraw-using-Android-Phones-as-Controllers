# 🎮 Phone-Controlled Game Console & Library

A complete multiplayer game library console where a laptop acts as the **Console & Display Screen** and smartphones act as **Wireless Controllers & Triggers** via Wi-Fi (using either the native Android APK or the instant Web Companion).

Like a **Nintendo Switch** or modern gaming console, players can browse a sequential game library, select games from either the laptop or the phone, and have the controller interface dynamically adapt to whatever game is selected. A persistent **HOME** button is present on the phone controller at all times, returning the console and phones to the Game Library.

---

## 🌟 20 Games in the Library

All games are fully playable with phone controllers and synced in real time:

1. **🤠 Quickdraw**: Classic Wild West duel with cowboy voice audio, camera reaction capture, false start penalties, sepia victory pose sharing, and volume key trigger shooting!
2. **🎾 Tennis**: Swing phone to hit; tilt as you swing to place the ball.
3. **🎳 Bowling**: Tilt to aim, hold trigger, swing down, release to bowl with real pin physics!
4. **🥊 Boxing**: Punch forward to hit, hold button to guard, tilt hard to dodge.
5. **🏎️ Racing**: Steer phone like a steering wheel, hold gas & brake pedals on screen.
6. **🦆 Duck Shooting**: Aim phone like a light gun; track your on-screen reticle and pull the trigger!
7. **🔴 Connect Four**: Drop chips into columns by tilting and tapping.
8. **🚢 Battleships**: Command your naval fleet against a friend or AI.
9. **♟️ Chess**: 3D chess arena; tilt to piece, pick up, and place.
10. **🏁 Dame (Checkers)**: Classic checkers board with real piece jumping.
11. **🏀 Basketball**: Tilt to aim, swing up to shoot before the shot clock expires.
12. **🎯 Darts**: Tilt to sight your throw, flick phone to launch dart at the board.
13. **🥤 Cup Pong**: Table tennis ball throw physics into red cups.
14. **⛳ Golf**: Address the ball, calibrate your backswing, and drive onto the green.
15. **🎱 Billiards**: 8-ball pool with real-time cue ball spin and pocketing.
16. **🚀 Tanks**: Drive your tank and aim artillery shells around obstacles.
17. **🏒 Air Hockey**: Glide your mallet across the table surface to score puck goals.
18. **⚾ Baseball**: Watch the pitch, time your swing with the phone bat!
19. **⚡ Light Cycles**: High-speed neon light trails; dodge walls and cut off opponents!
20. **❓ Quiz**: Four-button trivia showdown; race to lock in A, B, C, or D!

---

## 📱 Dual Phone Controller Options

### 1. Instant Mobile Web Companion (No Install Required)
- Open `http://<laptop-ip>:8080/phone` on any iPhone or Android phone.
- Or simply scan the on-screen QR code shown in the console window.
- Full access to 3D motion sensors (accelerometer, gyroscope), steering pedals, quiz ABCD keys, tactical quickdraw trigger, and the **⌂ HOME** button.

### 2. Native Android App (`QuickDraw.apk`)
- Located directly in the project root: `QuickDraw.apk`.
- Native hardware **Volume Up / Down button interception** for the Quickdraw duel trigger.
- Persistent top bar with **⌂ HOME** button, role switcher (**P1 / P2**), IP configuration dialog, and **🌐 WEB / 📱 APP** view mode toggle.
- Can be downloaded directly to any phone over Wi-Fi from: `http://<laptop-ip>:8080/download-apk`.

---

## 🕹️ Controls & Navigation

| Action | Phone Controller | Laptop Keyboard |
| :--- | :--- | :--- |
| **Browse Previous Game** | Tap `◀ PREV` or tilt left | Left Arrow (`←`) |
| **Browse Next Game** | Tap `NEXT ▶` or tilt right | Right Arrow (`→`) |
| **Launch Game** | Tap `▶ PLAY` or button `A` | `ENTER` or `SPACE` |
| **Return to Game Library** | Tap **⌂ HOME** (Always on top bar) | `ESC` key |
| **Quickdraw Shoot** | Tap `⚡ FIRE TRIGGER` or press **Volume Up / Down** | Space |
| **Swing Sports (Tennis/Golf/Baseball)** | Swing phone naturally with acceleration | Space (virtual swing) |
| **Racing Steering** | Rotate phone like a steering wheel | `←` / `→` or `A` / `D` |
| **Racing Pedals** | Hold `GAS` and `BRAKE` pedals | `W` (Gas), `S` (Brake) |
| **Quiz Answers** | Tap `A`, `B`, `C`, `D` buttons | `1`, `2`, `3`, `4` |

---

## 🚀 Quick Start

### 1. Requirements
Ensure Python 3.10+ is installed.
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Launch the Console Server
```bash
# Launch with 3D Game Screen in default web browser
python console_server.py --browser

# Or launch server-only in headless mode
python console_server.py --headless
```

The server automatically starts:
- **3D Game Screen**: `http://localhost:8080/`
- **Mobile Phone Controller (HTTP)**: `http://<laptop-ip>:8080/phone`
- **Mobile Phone Controller (HTTPS with SSL for motion sensors)**: `https://<laptop-ip>:8443/phone`
- **Android APK direct download**: `http://<laptop-ip>:8080/download-apk`
- **Native Android WebSocket Server**: `ws://<laptop-ip>:8000`

---

## 🧩 Adding New Games Easily

The console is architected to make adding future games effortless:

### Adding a Python Camera/Voice Game (like Quickdraw):
1. Create a folder in `games/<game_id>/game.py` inheriting from `BaseGame`:
```python
from games.base_game import BaseGame
import threading, time

class MyNewGame(BaseGame):
    def __init__(self):
        super().__init__(
            game_id="my_game",
            title="My Game",
            description="My cool new phone-controlled game!",
            thumbnail="thumbnail.png",
            min_players=1,
            max_players=4
        )

    def run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            time.sleep(0.016)

    def handle_input(self, player: str, data: dict):
        print(f"[{player}] Received input: {data}")

Game = MyNewGame
```
2. The game is automatically discovered by `GameRegistry` on startup!

### Adding a Three.js / Web Sport Game:
1. Create `party_games/js/games/<game_id>.js` with `enter()`, `exit()`, `update()`, and input handlers.
2. Register in `GAMES` inside `party_games/js/main.js`.
3. Add a `<div class="card" data-game="<game_id>">` in `party_games/index.html`.

---

## 📁 Repository Structure

```
Quickdraw/
├── console_server.py         # Main console server & game launcher
├── QuickDraw.apk            # Pre-compiled Android Controller APK (7.35 MB)
├── server/
│   ├── console_manager.py   # State machine, navigation, lifecycle & sync
│   ├── game_registry.py     # Automatic game discovery plugin manager
│   └── network_hub.py       # Dual HTTP/HTTPS + WebSocket hub
├── games/
│   ├── base_game.py         # Base class for all console games
│   ├── quickdraw/           # Wild West Quickdraw (camera & voice engine)
│   │   ├── game.py          # Quickdraw game logic & OpenCV duel
│   │   ├── voice.py         # Synchronized voice reveal logic
│   │   └── assets/          # Cowboy voice audio
│   └── reflex_duel/         # Cyber Reflex Duel
├── party_games/             # Full library of 20 3D sports & party games
│   ├── index.html           # 3D Console Arena & Carousel
│   ├── phone.html           # Universal Mobile Controller with persistent HOME
│   └── js/
│       ├── main.js          # Central console game coordinator
│       └── games/           # 20 game implementations (tennis, racing, quickdraw, etc.)
├── ui/
│   └── console_display.py   # Fullscreen visual console UI & QR code generator
└── requirements.txt         # Python dependencies
```
