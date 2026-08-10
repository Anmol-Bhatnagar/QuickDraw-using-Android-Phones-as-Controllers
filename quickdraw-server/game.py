import cv2
import time
import random
import queue

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
    rhyme_index = 0
    next_speech_time = 0
    
    shoot_word_started = False
    shoot_word_done = False
    shoot_finish_timestamp = 0
    shoot_start_time = 0
    
    round_over_start_time = 0
    winner_message = ""
    reaction_time = 0

    def drain_queue():
        while not msg_queue.empty():
            try:
                msg_queue.get_nowait()
            except queue.Empty:
                break
                
    def on_shoot_word_finished():
        nonlocal shoot_word_done, shoot_finish_timestamp
        # Record the exact time the shoot word finishes speaking
        shoot_finish_timestamp = time.time()
        shoot_word_done = True

    print("Game server running. Press ESC to exit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
            
        current_time = time.time()
        
        if state == "WAITING":
            # Draw "Press SPACE to start round — both players ready"
            cv2.putText(frame, "Press SPACE to start round", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame, "(both players ready)", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # If a message arrives, ignore it
            drain_queue()
            
        elif state == "DISTRACTING":
            cv2.putText(frame, "Get ready...", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)
            
            # Check for false starts
            if not msg_queue.empty():
                player, dev_time, srv_time = msg_queue.get_nowait()
                winner_message = f"Opponent wins ({player} false start!)"
                reaction_time = 0
                state = "ROUND_OVER"
                round_over_start_time = current_time
                drain_queue()
            else:
                # Non-blocking speech sequence
                if rhyme_index < len(round_data['rhymes']):
                    if current_time >= next_speech_time:
                        voice.speak(round_data['rhymes'][rhyme_index])
                        rhyme_index += 1
                        next_speech_time = current_time + random.uniform(0.8, 1.5)
                else:
                    # Rhymes finished, time for the real shoot word
                    if not shoot_word_started:
                        voice.speak(round_data['shoot_word'], on_complete=on_shoot_word_finished)
                        shoot_word_started = True
                    elif shoot_word_done:
                        # Speech finished, transition to SHOOT_WINDOW
                        state = "SHOOT_WINDOW"
                        shoot_start_time = shoot_finish_timestamp
                        
        elif state == "SHOOT_WINDOW":
            cv2.putText(frame, "SHOOT!", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
            
            # Watch the queue for the first message
            if not msg_queue.empty():
                messages = []
                while not msg_queue.empty():
                    try:
                        messages.append(msg_queue.get_nowait())
                    except queue.Empty:
                        break
                        
                # Use server_receive_time to determine ordering if both queued in this frame
                messages.sort(key=lambda x: x[2])
                winner_msg = messages[0]
                player, dev_time, srv_time = winner_msg
                
                # Calculate reaction time in milliseconds
                reaction_time_ms = (srv_time - shoot_start_time) * 1000
                winner_message = f"{player} WINS!"
                reaction_time = reaction_time_ms
                
                state = "ROUND_OVER"
                round_over_start_time = current_time
                drain_queue()
                
        elif state == "ROUND_OVER":
            # Draw winner and reaction time (or false start)
            cv2.putText(frame, winner_message, (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
            
            if reaction_time > 0:
                cv2.putText(frame, f"{reaction_time:.0f} ms", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                
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
            if state == "WAITING":
                state = "DISTRACTING"
                round_data = words.get_random_round()
                rhyme_index = 0
                next_speech_time = current_time + 0.5 # 0.5s pause before first rhyme
                shoot_word_started = False
                shoot_word_done = False
                drain_queue()
                
            elif state == "ROUND_OVER" and (current_time - round_over_start_time > 3.0):
                state = "WAITING"
                drain_queue()

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
