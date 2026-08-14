import os
import re
import queue
import time
import random
import wave
import pygame

VOICE_DIR = os.path.join(os.path.dirname(__file__), "assets", "Target Words (Cowboy)")
_voice_registry = {}

# Pattern: word_(TIMESTAMPs).wav or word_(TIMESTAMPsec).wav
# e.g., shoot_(12.55s).wav or shoot_(12.55sec).wav
pattern = re.compile(r'^([a-zA-Z0-9_-]+)_\(([\d\.]+)(?:s|sec)\)\.wav$')

def get_wav_duration(filepath):
    try:
        with wave.open(filepath, 'r') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return frames / float(rate)
    except Exception as e:
        print(f"Error reading duration for {filepath}: {e}")
        return 0

if os.path.exists(VOICE_DIR):
    for filename in os.listdir(VOICE_DIR):
        if not filename.lower().endswith(".wav"):
            continue
            
        match = pattern.match(filename)
        if match:
            word = match.group(1)
            timestamp = float(match.group(2))
            filepath = os.path.join(VOICE_DIR, filename)
            duration = get_wav_duration(filepath)
            _voice_registry[filename] = (filepath, timestamp, duration, word)
        else:
            print(f"WARNING: File '{filename}' in {VOICE_DIR} does not match expected pattern (e.g. word_(1.23s).wav). Skipping.")
else:
    print(f"WARNING: Voice directory {VOICE_DIR} does not exist.")

def play_random_audio(channel=None) -> queue.Queue:
    """
    Picks a random audio file, plays it on the specified pygame channel, and returns a thread-safe queue.
    Pushes a 'reveal_at' event containing the scheduled reveal time, audio end time, and target word.
    """
    if not _voice_registry:
        raise ValueError(f"No valid audio files found in {VOICE_DIR}.")
        
    filename = random.choice(list(_voice_registry.keys()))
    file_path, timestamp, duration, word = _voice_registry[filename]
    
    q = queue.Queue()
    
    reveal_time = time.time() + timestamp
    end_time = time.time() + duration
    q.put(("reveal_at", reveal_time, end_time, word))
    
    sound = pygame.mixer.Sound(file_path)
    if channel:
        channel.play(sound)
    else:
        sound.play()
    
    return q

