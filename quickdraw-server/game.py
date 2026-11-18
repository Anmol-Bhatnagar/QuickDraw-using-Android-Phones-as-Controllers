import cv2
import time
import queue
import random
import os
import numpy as np
import threading
import requests
import qrcode
from PIL import Image

import net
import voice

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

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Start network server and get the message queue
    msg_queue = net.start_server(host='0.0.0.0', port=8000)
    
    # Initialize Pygame Mixer
    try:
        import pygame
        pygame.mixer.init()
        bgm_channel_1 = pygame.mixer.Channel(0)
        bgm_channel_2 = pygame.mixer.Channel(1)
        voice_channel = pygame.mixer.Channel(2)
        overlay_channel = pygame.mixer.Channel(3)
        
        bgmusic1 = pygame.mixer.Sound(r"c:\Users\anmol\Desktop\Projects\Quickdraw\bgmusic1.wav")
        bgmusic2 = pygame.mixer.Sound(r"c:\Users\anmol\Desktop\Projects\Quickdraw\bgmusic2.wav")
        try:
            overlay_audio = pygame.mixer.Sound(r"c:\Users\anmol\Desktop\Projects\Quickdraw\reveal_overlay.mp3")
        except:
            overlay_audio = None
            print("Warning: reveal_overlay.mp3 not found.")
            
    except ImportError:
        print("Error: Pygame is not installed. Please run 'pip install pygame'")
        return
    
    # State variables
    state = "WAITING"
    get_ready_start_time = 0
    
    # Pose capture state
    captured_frame = None
    upload_result = {}
    
    # Ensure captures directory exists
    if not os.path.exists("captures"):
        os.makedirs("captures")
    
    # Distracting phase tracking
    reveal_queue = None
    audio_reveal_time = 0
    audio_end_time = 0
    target_word = ""
    
    # Shoot phase / Round over tracking
    shoot_start_time = 0
    round_over_start_time = 0
    winner_message = ""
    shot_results = {}
    round_loser = None
    
    # Track players we've seen to show DNF correctly
    known_players = set()

    def drain_queue():
        while not msg_queue.empty():
            try:
                p, _, _ = msg_queue.get_nowait()
                known_players.add(p)
            except queue.Empty:
                break

    print("Game server running. Press ESC to exit.")
    
    # Setup fullscreen window
    cv2.namedWindow('Quickdraw', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Quickdraw', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Pre-load overlay frames
    ret, test_frame = cap.read()
    if not ret:
        print("Error: Could not open webcam.")
        return
        
    frame_h, frame_w = test_frame.shape[:2]
    overlay_path = r"c:\Users\anmol\Desktop\Projects\Quickdraw\reveal_overlay.webm"
    overlay_frames = []
    overlay_fps = 30.0
    
    if os.path.exists(overlay_path):
        print(f"Loading overlay from {overlay_path}...")
        ov_cap = cv2.VideoCapture(overlay_path)
        fps = ov_cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            overlay_fps = fps
            
        while True:
            ret, ov = ov_cap.read()
            if not ret:
                break
            ov = cv2.resize(ov, (frame_w, frame_h))
            
            # Since the background is black, we create a mask of non-black pixels
            gray = cv2.cvtColor(ov, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 5, 255, cv2.THRESH_BINARY)
            
            overlay_frames.append({
                "frame": ov,
                "mask": mask
            })
        ov_cap.release()
        print(f"Loaded {len(overlay_frames)} overlay frames at {overlay_fps} FPS.")
    else:
        print(f"Overlay clip not found at {overlay_path}. Playing without overlay.")
        
    print(f"[{time.time():.3f}] Transitioning to WAITING")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
            
        # Flip the frame horizontally to act like a mirror
        frame = cv2.flip(frame, 1)
            
        current_time = time.time()
        clean_frame = frame.copy()
        
        if state == "WAITING":
            # Draw "Press SPACE to start round"
            cv2.putText(frame, "Press SPACE to start round", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "(both players ready)", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Ignore stray messages
            drain_queue()
            
        elif state == "GET_READY":
            cv2.putText(frame, "GET READY...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
            
            # After 20 seconds, crossfade and move to DISTRACTING
            if current_time - get_ready_start_time >= 20.0:
                state = "DISTRACTING"
                audio_reveal_time = 0
                audio_end_time = 0
                target_word = ""
                
                print(f"[{current_time:.3f}] Transitioning to DISTRACTING (Crossfading)")
                
                # Crossfade background music
                bgm_channel_1.fadeout(2000)
                bgm_channel_2.play(bgmusic2, loops=-1, fade_ms=2000)
                
                # Kick off the voice audio
                reveal_queue = voice.play_random_audio(channel=voice_channel)
                shot_results = {}
                winner_message = ""
                
                drain_queue()
            
        elif state == "DISTRACTING":
            cv2.putText(frame, "Get ready...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
            
            # Show the target word they are waiting for!
            if target_word:
                cv2.putText(frame, f"Target: {target_word.upper()}", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            
            # Check for false starts
            if not msg_queue.empty():
                player, dev_time, srv_time = msg_queue.get_nowait()
                known_players.add(player)
                
                winner_message = f"Opponent wins ({player} false start!)"
                shot_results = {} # No valid reaction times
                round_loser = player
                state = "WAITING_FOR_AUDIO_END"
                print(f"[{current_time:.3f}] {player} false started! Transitioning to WAITING_FOR_AUDIO_END")
                drain_queue()
            else:
                # Watch the reveal queue for the target word timestamp
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
                    print(f"[{current_time:.3f}] Transitioning to SHOOT_WINDOW (Scheduled time: {shoot_start_time:.3f})")
                    frame = cv2.bitwise_not(frame)
                        
        elif state == "SHOOT_WINDOW":
            cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
            
            # Draw the actual reveal word in large text in the center
            if target_word:
                cv2.putText(frame, target_word.upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)
            
            # Watch the queue for shots
            while not msg_queue.empty():
                try:
                    player, dev_time, srv_time = msg_queue.get_nowait()
                    known_players.add(player)
                    if player not in shot_results:
                        shot_results[player] = (srv_time - shoot_start_time) * 1000
                except queue.Empty:
                    break
                    
            if shot_results:
                # Someone shot! Transition to WAITING_FOR_AUDIO_END
                state = "WAITING_FOR_AUDIO_END"
                winner_message = ""
                
                # Determine the fastest player to identify the loser
                fastest_player = min(shot_results, key=shot_results.get)
                losers = [p for p in known_players if p != fastest_player]
                round_loser = losers[0] if losers else ("player2" if fastest_player == "player1" else "player1")
                
                print(f"[{current_time:.3f}] Shots fired! Transitioning to WAITING_FOR_AUDIO_END")
                
            elif audio_end_time > 0 and current_time >= audio_end_time:
                # Nobody shot before audio ended
                winner_message = "DRAW (Too slow!)"
                state = "ROUND_OVER"
                round_over_start_time = current_time
                drain_queue()
                
                # Stop music and play overlay audio
                bgm_channel_1.stop()
                bgm_channel_2.stop()
                voice_channel.stop()
                if overlay_audio:
                    overlay_channel.play(overlay_audio)
                
        elif state == "WAITING_FOR_AUDIO_END":
            # Display appropriate screen while audio finishes playing
            if "false start" in winner_message:
                cv2.putText(frame, "False start!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 3)
            else:
                cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
                if target_word:
                    cv2.putText(frame, target_word.upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)
            
            # Drain queue for any late shots
            while not msg_queue.empty():
                try:
                    player, dev_time, srv_time = msg_queue.get_nowait()
                    known_players.add(player)
                    if player not in shot_results and "false start" not in winner_message:
                        shot_results[player] = (srv_time - shoot_start_time) * 1000
                except queue.Empty:
                    break
                    
            if audio_end_time > 0 and current_time >= audio_end_time:
                state = "ROUND_OVER"
                round_over_start_time = current_time
                print(f"[{current_time:.3f}] Audio ended. Transitioning to ROUND_OVER")
                
                # Stop music and play overlay audio
                bgm_channel_1.stop()
                bgm_channel_2.stop()
                voice_channel.stop()
                if overlay_audio:
                    overlay_channel.play(overlay_audio)
                
        elif state == "ROUND_OVER":
            drain_queue()
                
            # Play overlay
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
                # False start case
                cv2.putText(frame, winner_message, (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            else:
                # Normal shootout result
                if shot_results:
                    fastest_player = min(shot_results, key=shot_results.get)
                    cv2.putText(frame, f"{fastest_player} WINS!", (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    
                    y_offset += 60
                    
                    # Display both players side-by-side
                    results_text = []
                    # Always try to display 2 players if known
                    display_players = list(known_players) if len(known_players) >= 2 else list(shot_results.keys())
                    for p in display_players:
                        if p in shot_results:
                            results_text.append(f"{p}: {shot_results[p]:.0f}ms")
                        else:
                            results_text.append(f"{p}: DNF")
                            
                    cv2.putText(frame, " vs ".join(results_text), (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                
            # After 3 seconds, allow SPACE to start next round, or T to capture pose
            if current_time - round_over_start_time > 3.0:
                cv2.putText(frame, "Press 'T' for Victory Pose! Or SPACE for next round", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
        elif state == "UPLOADING":
            frame = captured_frame.copy()
            cv2.putText(frame, "Uploading to cloud... please wait!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
            
            if 'url' in upload_result:
                url = upload_result['url']
                qr = qrcode.QRCode(version=1, box_size=5, border=2)
                qr.add_data(url)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
                qr_np = np.array(img_qr)
                # Convert RGB to BGR
                qr_np = qr_np[:, :, ::-1].copy()
                
                # Overlay in bottom right corner
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
                
        # Show the camera frame
        cv2.imshow('Quickdraw', frame)
        
        # Key handling
        key = cv2.waitKey(1)
        if key == 27: # ESC key
            break
        elif key == ord('t') or key == ord('T'):
            if state == "ROUND_OVER" and current_time - round_over_start_time > 3.0:
                # Capture the pose
                captured_frame = apply_sepia(clean_frame)
                h, w, _ = captured_frame.shape
                
                if "DRAW" in winner_message:
                    cv2.putText(captured_frame, "DRAW", (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 255), 6)
                    cv2.putText(captured_frame, "DRAW", (w//2 + 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 255, 255), 6)
                else:
                    # Determine left/right texts
                    if round_loser == "player1":
                        left_text = "I LOST"
                        right_text = "I WON"
                    else:
                        left_text = "I WON"
                        right_text = "I LOST"
                        
                    cv2.putText(captured_frame, left_text, (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255) if "LOST" in left_text else (0, 255, 0), 6)
                    cv2.putText(captured_frame, right_text, (w//2 + 50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255) if "LOST" in right_text else (0, 255, 0), 6)
                
                # Save locally
                filepath = os.path.join("captures", f"pose_{int(time.time())}.jpg")
                cv2.imwrite(filepath, captured_frame)
                
                # Start upload
                upload_result = {}
                threading.Thread(target=upload_to_catbox, args=(filepath, upload_result), daemon=True).start()
                
                state = "UPLOADING"
                
        elif key == 32: # SPACE bar
            if state in ["WAITING", "SHOW_CAPTURE"] or (state == "ROUND_OVER" and current_time - round_over_start_time > 3.0):
                state = "GET_READY"
                get_ready_start_time = current_time
                
                print(f"\n[{current_time:.3f}] Round started. GET_READY phase.")
                
                # Play initial background music
                bgm_channel_1.play(bgmusic1)
                
                drain_queue()

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
