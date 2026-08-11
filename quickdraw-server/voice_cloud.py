import os
import tempfile
import asyncio
import threading
import edge_tts
from playsound import playsound

def _async_speak(word: str):
    """
    Background worker that creates a new event loop,
    fetches the TTS audio, saves it to a temp file, and plays it.
    """
    # edge-tts is async, but this runs in a thread, so we need a dedicated event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # We use a natural-sounding English voice
    voice = "en-US-GuyNeural"
    communicate = edge_tts.Communicate(word, voice)
    
    # Create a temporary mp3 file
    fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    
    try:
        # Fetch audio from Edge TTS and save to temp file
        loop.run_until_complete(communicate.save(temp_path))
        
        # Play the saved audio file
        playsound(temp_path)
    finally:
        # Cleanup: close the event loop and remove the temporary file
        loop.close()
        try:
            os.remove(temp_path)
        except OSError:
            pass

def speak_word_cloud(word: str):
    """
    Synthesizes the word using edge-tts (cloud-based) and plays it back.
    This function spawns a background thread and returns immediately, 
    so it never blocks the caller.
    """
    thread = threading.Thread(target=_async_speak, args=(word,), daemon=True)
    thread.start()

if __name__ == "__main__":
    import time
    
    print("Testing cloud voice synthesis (edge-tts)...")
    speak_word_cloud("testing")
    
    # Wait a bit between words to prevent overlap
    time.sleep(2.5)
    
    speak_word_cloud("consecutive")
    
    # Wait a bit longer to ensure the second word finishes before the script exits
    time.sleep(3)
