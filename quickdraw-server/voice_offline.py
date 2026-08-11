import random
import time
import win32com.client

# Create a single persistent SAPI.SpVoice instance at module import time
speaker = win32com.client.Dispatch("SAPI.SpVoice")

# SAPI 5 SpeechVoiceSpeakFlags
SVSFlagsAsync = 1
SVSFIsXML = 8

# List available voices and select "David" if present
voices = speaker.GetVoices()
for i in range(voices.Count):
    voice = voices.Item(i)
    description = voice.GetDescription()
    if "David" in description:
        speaker.Voice = voice
        break
else:
    # Fallback to the first voice if David is not found, typically Zira or another default.
    if voices.Count > 0:
        speaker.Voice = voices.Item(0)

def speak_word_offline(word):
    """
    Speaks the given word asynchronously with a random pitch variation.
    """
    pitch = random.randint(-2, 6)
    
    # Wrap the word in SAPI XML for pitch variation
    xml_text = f'<pitch absmiddle="{pitch}">{word}</pitch>'
    
    # Speak asynchronously with XML parsing enabled
    speaker.Speak(xml_text, SVSFlagsAsync | SVSFIsXML)

if __name__ == "__main__":
    print("Testing offline voice synthesis...")
    speak_word_offline("testing")
    
    # Wait a moment between words
    time.sleep(1)
    
    speak_word_offline("consecutive")
    
    # Wait to ensure asynchronous speech completes before the script exits
    time.sleep(2)
