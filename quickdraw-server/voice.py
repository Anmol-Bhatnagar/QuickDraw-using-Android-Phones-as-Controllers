import pyttsx3
import threading

# On import, initialize the engine once
global_engine = pyttsx3.init()
voices = global_engine.getProperty('voices')

# Explicitly search for a local Windows SAPI voice
# On Windows, local offline voices usually have "Desktop" in the name (e.g. Microsoft David Desktop)
# or they reside in the traditional Speech\Voices\Tokens registry path.
active_voice_id = None

for voice in voices:
    if 'Desktop' in voice.name or 'Desktop' in voice.id:
        active_voice_id = voice.id
        break

# Fallback if no "Desktop" voice is found
if not active_voice_id and voices:
    for voice in voices:
        # Avoid OneCore voices if possible as some can be mobile/network dependent
        if 'Tokens' in voice.id and 'Speech_OneCore' not in voice.id:
            active_voice_id = voice.id
            break

if not active_voice_id and voices:
    active_voice_id = voices[0].id

# Set the active voice globally as requested
if active_voice_id:
    global_engine.setProperty('voice', active_voice_id)


def speak(text, on_complete=None):
    """Runs speech in a fresh background thread."""
    def worker(t):
        # On Windows, Pyttsx3 uses COM (SAPI5). COM objects created in one thread 
        # (like global_engine) often cannot be invoked in a new thread without throwing
        # "CoInitialize has not been called" or apartment state errors.
        # So we create a fresh thread-local engine but apply the voice we found globally.
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass
            
        thread_engine = pyttsx3.init()
        if active_voice_id:
            thread_engine.setProperty('voice', active_voice_id)
            
        thread_engine.say(t)
        thread_engine.runAndWait()
        
        if on_complete:
            on_complete()

    thread = threading.Thread(target=worker, args=(text,))
    thread.start()


if __name__ == "__main__":
    import time
    print(f"Initialized active voice: {active_voice_id}")
    print("Testing offline voice. You can turn off Wi-Fi to confirm it works.")
    speak("testing offline voice")
    
    # Keep the main thread alive long enough for the speech thread to finish
    time.sleep(4)
