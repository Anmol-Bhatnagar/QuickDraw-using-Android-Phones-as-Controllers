import os
import sys
from scipy.io.wavfile import write as write_wav

# Set environment variables for Bark (MUST be done before importing bark)
os.environ["SUNO_USE_SMALL_MODELS"] = "True"
os.environ["SUNO_OFFLOAD_CPU"] = "True"

import torch
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

from bark import SAMPLE_RATE, generate_audio, preload_models
import words

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "voice")

def ensure_dir():
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)

def generate_and_save(text, filename):
    filepath = os.path.join(ASSETS_DIR, filename)
    if os.path.exists(filepath):
        print(f"[SKIP] {filepath} already exists.")
        return
        
    print(f"[GENERATE] Synthesizing '{filename}'...")
    print(f"  Text: {text}")
    try:
        # Generate audio array using a standard male voice preset
        audio_array = generate_audio(text, history_prompt="v2/en_speaker_6")
        
        # Save to wav
        write_wav(filepath, SAMPLE_RATE, audio_array)
        print(f"[OK] Saved {filepath}")
    except Exception as e:
        print(f"[ERROR] Failed to generate {filename}: {e}")

def main():
    ensure_dir()
    
    print("Preloading Bark models (this may download weights on first run)...")
    preload_models()
    print("Models loaded successfully!\n")
    
    groups = words.WORD_GROUPS
    total_groups = len(groups)
    
    print(f"Found {total_groups} word groups. Beginning generation...")
    
    for i, group in enumerate(groups, 1):
        reveal_word = group["reveal_word"]
        print(f"\n--- Processing Group {i}/{total_groups}: {reveal_word.upper()} ---")
        
        # Buildup string: elongated calls, then a fast rhyme burst, then a red-herring pause
        # e.g., "READYYYYY... STEADYYYYY... loot. boot. root... shout."
        # We can take words from words.py
        
        slow1 = words.SLOW_WORDS[0]
        slow2 = words.SLOW_WORDS[1]
        
        # Elongate and capitalize
        slow1_stylized = (slow1 + slow1[-1]*4).upper()
        slow2_stylized = (slow2 + slow2[-1]*4).upper()
        
        # Take up to 3 rhymes for the burst
        rhymes = group["rhymes"][:3]
        rhyme_str = ". ".join(rhymes) + "."
        
        # Take 1 red herring if available
        red_herring_str = ""
        if group.get("red_herrings"):
            red_herring = group["red_herrings"][0]
            red_herring_str = f"... {red_herring}."
            
        buildup_text = f"{slow1_stylized}... {slow2_stylized}... {rhyme_str}{red_herring_str}"
        buildup_filename = f"{reveal_word}_buildup.wav"
        
        # Reveal string
        reveal_text = f"{reveal_word.upper()}!"
        reveal_filename = f"{reveal_word}_reveal.wav"
        
        generate_and_save(buildup_text, buildup_filename)
        generate_and_save(reveal_text, reveal_filename)
        
    print("\nAll assets processed successfully.")

if __name__ == "__main__":
    main()
