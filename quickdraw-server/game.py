import cv2
import time
import queue
import random

import net
import voice
import words

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Start network server and get the message queue
    msg_queue = net.start_server(host='0.0.0.0', port=8000)
    
    # State variables
    state = "WAITING"
    round_data = None
    
    # Distracting phase tracking
    reveal_queue = None
    
    # Shoot phase / Round over tracking
    shoot_start_time = 0
    round_over_start_time = 0
    winner_message = ""
    shot_results = {}
    
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
    print(f"[{time.time():.3f}] Transitioning to WAITING")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
            
        current_time = time.time()
        
        if state == "WAITING":
            # Draw "Press SPACE to start round"
            cv2.putText(frame, "Press SPACE to start round", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "(both players ready)", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Ignore stray messages
            drain_queue()
            
        elif state == "DISTRACTING":
            cv2.putText(frame, "Get ready...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
            
            # Check for false starts
            if not msg_queue.empty():
                player, dev_time, srv_time = msg_queue.get_nowait()
                known_players.add(player)
                
                winner_message = f"Opponent wins ({player} false start!)"
                shot_results = {} # No valid reaction times
                state = "ROUND_OVER"
                round_over_start_time = current_time
                print(f"[{current_time:.3f}] {player} false started! Transitioning to ROUND_OVER")
                drain_queue()
            else:
                # Watch the reveal queue for the exact moment the target word is spoken
                if reveal_queue is not None:
                    try:
                        event, timestamp = reveal_queue.get_nowait()
                        if event == "reveal_started":
                            state = "SHOOT_WINDOW"
                            shoot_start_time = timestamp
                            print(f"[{current_time:.3f}] Transitioning to SHOOT_WINDOW (Audio time: {timestamp:.3f})")
                            
                            # Flash effect: invert the frame briefly to simulate a bold flash-card reveal
                            frame = cv2.bitwise_not(frame)
                    except queue.Empty:
                        pass
                        
        elif state == "SHOOT_WINDOW":
            cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
            
            # Draw the actual reveal word in large text in the center
            if round_data:
                cv2.putText(frame, round_data['reveal_word'].upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)
            
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
                # Someone shot! Transition to ROUND_OVER, but we will allow a brief 0.5s window
                # in ROUND_OVER to collect the other player's shot if they fired slightly later.
                state = "ROUND_OVER"
                round_over_start_time = current_time
                winner_message = ""
                print(f"[{current_time:.3f}] Shots fired! Transitioning to ROUND_OVER")
                
        elif state == "ROUND_OVER":
            # Collect late shots for the first 0.5 seconds
            if current_time - round_over_start_time < 0.5:
                while not msg_queue.empty():
                    try:
                        player, dev_time, srv_time = msg_queue.get_nowait()
                        known_players.add(player)
                        if player not in shot_results:
                            shot_results[player] = (srv_time - shoot_start_time) * 1000
                    except queue.Empty:
                        break
            else:
                drain_queue()
                
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
                
            # After 3 seconds, allow SPACE to start next round
            if current_time - round_over_start_time > 3.0:
                cv2.putText(frame, "Press SPACE for next round", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                
        # Show the camera frame
        cv2.imshow('Quickdraw', frame)
        
        # Key handling
        key = cv2.waitKey(1)
        if key == 27: # ESC key
            break
        elif key == 32: # SPACE bar
            if state == "WAITING" or (state == "ROUND_OVER" and current_time - round_over_start_time > 3.0):
                state = "DISTRACTING"
                round_data = words.get_random_round()
                
                print(f"\n[{current_time:.3f}] Round started. Target word is: {round_data['reveal_word']}")
                print(f"[{current_time:.3f}] Transitioning to DISTRACTING")
                
                # Kick off the audio script and get the event queue
                reveal_queue = voice.speak_round(round_data["script"])
                shot_results = {}
                winner_message = ""
                
                drain_queue()

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
