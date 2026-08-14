import queue
import time
import threading
import win32com.client
import pythoncom

# SAPI 5 SpeechVoiceSpeakFlags
SVSFlagsAsync = 1
SVSFIsXML = 8

class SapiEvents:
    def __init__(self):
        self.q = None
        self.reveal_char_pos = -1

    def OnWord(self, StreamNumber, StreamPosition, CharacterPosition, Length):
        """
        Fired by SAPI as speech progresses. CharacterPosition is the index 
        into the original XML string where the current word begins.
        """
        # If we reached or passed the reveal word's known character position, fire the event!
        if self.reveal_char_pos != -1 and CharacterPosition >= self.reveal_char_pos:
            if self.q is not None:
                self.q.put(("reveal_started", time.time()))
                # Clear the queue reference so we only push the event once
                self.q = None

def _speak_thread(xml_text, reveal_pos, result_queue):
    """
    Background worker thread to run the SAPI synthesis and pump COM messages for events.
    """
    # Initialize COM for this background thread
    pythoncom.CoInitialize()
    
    # Create the event-bound SAPI speaker
    speaker = win32com.client.DispatchWithEvents("SAPI.SpVoice", SapiEvents)
    
    # Configure the voice (David if present)
    voices = speaker.GetVoices()
    for i in range(voices.Count):
        if "David" in voices.Item(i).GetDescription():
            speaker.Voice = voices.Item(i)
            break
            
    # Inject our state into the event handler wrapper
    speaker.q = result_queue
    speaker.reveal_char_pos = reveal_pos
    
    # Start speaking asynchronously
    speaker.Speak(xml_text, SVSFlagsAsync | SVSFIsXML)
    
    # Wait until speech is finished, pumping messages periodically
    while not speaker.WaitUntilDone(10):
        pythoncom.PumpWaitingMessages()
        
    pythoncom.CoUninitialize()

def speak_round(round_script: list):
    """
    Builds a single SAPI XML string for the entire round script, hooking word 
    boundary events to detect exactly when the 'reveal' word plays.
    
    Returns a thread-safe queue yielding ("reveal_started", timestamp).
    """
    q = queue.Queue()
    
    xml_parts = []
    
    # No outer <speak> tag is strictly necessary for SAPI to parse inline tags, 
    # but it's safe to just concatenate the tags.
    reveal_char_pos = -1
    
    for segment in round_script:
        text = segment["text"]
        style = segment["style"]
        gap_ms = int(segment["gap_after"] * 1000)
        
        if style == "reveal":
            # The word is spoken at normal rate.
            tag = '<rate absspeed="0">'
            xml_parts.append(tag)
            
            # Now calculate the exact character index where the word itself starts
            xml_prefix = "".join(xml_parts)
            reveal_char_pos = len(xml_prefix)
            
            xml_parts.append(text)
            xml_parts.append("</rate>")
        elif style == "slow":
            # Elongate the last letter for "slow" calls (e.g. readyyyy)
            elongated = text + (text[-1] * 3)
            xml_parts.append(f'<rate absspeed="-5">{elongated}</rate>')
        elif style == "burst":
            # Fast burst rhymes
            xml_parts.append(f'<rate absspeed="5">{text}</rate>')
            
        if gap_ms > 0:
            xml_parts.append(f'<silence msec="{gap_ms}"/>')
            
    final_xml = "".join(xml_parts)
    
    # Spawn background thread to play it and monitor events
    thread = threading.Thread(target=_speak_thread, args=(final_xml, reveal_char_pos, q), daemon=True)
    thread.start()
    
    return q

if __name__ == "__main__":
    import words
    print("Testing offline TTS (SAPI XML + Events)...")
    
    round_data = words.get_random_round()
    script = round_data["script"]
    
    for segment in script:
        print(f"  {segment['text']} ({segment['style']}) -> gap: {segment['gap_after']:.2f}s")
        
    q = speak_round(script)
    
    print("\nWaiting for precise reveal event...")
    while True:
        try:
            event, timestamp = q.get(timeout=0.1)
            if event == "reveal_started":
                print(f"[{timestamp:.3f}] REVEAL STARTED EVENT RECEIVED!")
                print("If you heard the word just now, it works perfectly!")
                break
        except queue.Empty:
            pass
            
    time.sleep(2)
