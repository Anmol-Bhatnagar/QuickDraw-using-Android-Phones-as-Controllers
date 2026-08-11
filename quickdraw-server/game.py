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
    rhymes_left = []
    rhyme_index = 0
    next_word_time = 0
    current_spoken_word = ""
    
    # Shoot phase tracking
    shoot_start_time = 0
    
    # Round over tracking
    round_over_start_time = 0
    winner_message = ""
    reaction_time = 0

    def drain_queue():
        while not msg_queue.empty():
            try:
                msg_queue.get_nowait()
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
            
            # Visually draw the current spoken word for feedback
            if current_spoken_word:
                cv2.putText(frame, current_spoken_word, (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (200, 200, 200), 2)
            
            # Check for false starts
            if not msg_queue.empty():
                player, dev_time, srv_time = msg_queue.get_nowait()
                winner_message = f"Opponent wins ({player} false start!)"
                reaction_time = 0
                state = "ROUND_OVER"
                round_over_start_time = current_time
                print(f"[{current_time:.3f}] {player} false started! Transitioning to ROUND_OVER")
                drain_queue()
            else:
                # Time to speak the next word?
                if current_time >= next_word_time:
                    if rhymes_left:
                        # Pop the next rhyme word
                        word = rhymes_left.pop(0)
                        voice.speak_word(word)
                        current_spoken_word = word
                        print(f"[{current_time:.3f}] Speaking rhyme: {word}")
                        
                        rhyme_index += 1
                        
                        if rhymes_left:
                            gap = random.uniform(0.3 + rhyme_index*0.15, 0.9 + rhyme_index*0.3)
                            if random.random() < 0.20:
                                gap *= 2.0
                        else:
                            gap = random.uniform(0.05, 0.3)
                            
                        next_word_time = current_time + gap
                    else:
                        # All rhymes exhausted, queue shoot word and transition immediately
                        word = round_data['shoot_word']
                        voice.speak_word(word)
                        print(f"[{current_time:.3f}] Speaking SHOOT word: {word}")
                        
                        state = "SHOOT_WINDOW"
                        shoot_start_time = current_time
                        print(f"[{current_time:.3f}] Transitioning to SHOOT_WINDOW")
                        
        elif state == "SHOOT_WINDOW":
            cv2.putText(frame, "SHOOT!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 5)
            
            # Draw the actual shoot word in large text in the center
            if round_data:
                cv2.putText(frame, round_data['shoot_word'].upper(), (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 255), 5)
            
            # Watch the queue for the first message
            if not msg_queue.empty():
                messages = []
                while not msg_queue.empty():
                    try:
                        messages.append(msg_queue.get_nowait())
                    except queue.Empty:
                        break
                        
                # Use server_receive_time to determine ordering
                messages.sort(key=lambda x: x[2])
                winner_msg = messages[0]
                player, dev_time, srv_time = winner_msg
                
                # Calculate reaction time in milliseconds
                reaction_time_ms = (srv_time - shoot_start_time) * 1000
                winner_message = f"{player} WINS!"
                reaction_time = reaction_time_ms
                
                state = "ROUND_OVER"
                round_over_start_time = current_time
                print(f"[{current_time:.3f}] {player} wins in {reaction_time_ms:.0f}ms! Transitioning to ROUND_OVER")
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
                rhymes_left = list(round_data['rhymes'])  # Make a copy we can pop from
                rhyme_index = 0
                
                gap = random.uniform(0.3, 0.9)
                if random.random() < 0.20:
                    gap *= 2.0
                next_word_time = current_time + gap
                
                current_spoken_word = ""
                
                print(f"\n[{current_time:.3f}] Round started. Target word is: {round_data['shoot_word']}")
                print(f"[{current_time:.3f}] Transitioning to DISTRACTING")
                drain_queue()
                
            elif state == "ROUND_OVER" and (current_time - round_over_start_time > 3.0):
                state = "WAITING"
                print(f"[{current_time:.3f}] Transitioning to WAITING")
                drain_queue()

    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
