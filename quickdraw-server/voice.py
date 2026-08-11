import time

# Set this to False before running with no internet available.
USE_CLOUD_VOICE = True

import voice_offline
import voice_cloud

def speak_word(word: str):
    """
    Speaks the given word using either the cloud or offline voice synthesizer,
    depending on the USE_CLOUD_VOICE flag.
    """
    if USE_CLOUD_VOICE:
        voice_cloud.speak_word_cloud(word)
    else:
        voice_offline.speak_word_offline(word)

if __name__ == "__main__":
    print(f"Testing unified voice interface (Cloud Voice: {USE_CLOUD_VOICE})...")
    
    speak_word("testing")
    
    # Wait a bit between words
    time.sleep(2.5)
    
    speak_word("consecutive")
    
    # Wait a bit longer to ensure async operations complete before exiting
    time.sleep(3)
