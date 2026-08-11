import time
import queue

# Set this to False before running with no internet available.
USE_CLOUD_VOICE = False

import voice_offline
import voice_cloud

def speak_round(round_script: list):
    """
    Speaks the given round script using either the cloud or offline voice synthesizer,
    depending on the USE_CLOUD_VOICE flag.
    
    Returns a thread-safe queue.Queue that will yield a ("reveal_started", timestamp)
    event exactly when the final reveal word is spoken.
    """
    if USE_CLOUD_VOICE:
        return voice_cloud.speak_round(round_script)
    else:
        return voice_offline.speak_round(round_script)

if __name__ == "__main__":
    import words
    print(f"Testing unified voice interface (Cloud Voice: {USE_CLOUD_VOICE})...")
    
    round_data = words.get_random_round()
    script = round_data["script"]
    
    print("Script:")
    for segment in script:
        print(f"  {segment['text']} ({segment['style']}) -> gap: {segment['gap_after']:.2f}s")
        
    q = speak_round(script)
    
    print("\nWaiting for reveal event...")
    while True:
        try:
            event, timestamp = q.get(timeout=0.1)
            if event == "reveal_started":
                print(f"[{timestamp:.3f}] REVEAL STARTED EVENT RECEIVED!")
                break
        except queue.Empty:
            pass
            
    # Wait a bit longer to ensure async operations complete before exiting
    time.sleep(1)
