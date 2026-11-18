import os
import tempfile
import asyncio
import threading
import time
import queue
import edge_tts
from playsound import playsound

def _async_speak_round(round_script, result_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 1. Group the script into a small number of phrase chunks by style
    chunks = []
    current_chunk_words = []
    current_style = None
    last_gap = 0
    
    for segment in round_script:
        if segment["style"] != current_style:
            if current_chunk_words:
                chunks.append({
                    "text": ", ".join(current_chunk_words),
                    "style": current_style,
                    "gap_after": last_gap
                })
            current_style = segment["style"]
            current_chunk_words = []
            
        current_chunk_words.append(segment["text"])
        last_gap = segment["gap_after"]
        
    if current_chunk_words:
        chunks.append({
            "text": ", ".join(current_chunk_words),
            "style": current_style,
            "gap_after": last_gap
        })

    # 2. Synthesize each chunk
    voice = "en-US-GuyNeural"
    temp_files = []
    reveal_audio_offset = 0.0
    
    async def synthesize():
        nonlocal reveal_audio_offset
        for chunk in chunks:
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            
            # Map styles to edge-tts rate parameters
            rate = "+0%"
            if chunk["style"] == "slow":
                rate = "-25%"
            elif chunk["style"] == "burst":
                rate = "+25%"
                
            boundary = "SentenceBoundary"
            if chunk["style"] == "reveal":
                boundary = "WordBoundary"
                
            comm = edge_tts.Communicate(chunk["text"], voice, rate=rate, boundary=boundary)
            
            # For the reveal chunk, we stream to capture the WordBoundary event
            if chunk["style"] == "reveal":
                with open(temp_path, "wb") as f:
                    async for event in comm.stream():
                        if event["type"] == "audio":
                            f.write(event["data"])
                        elif event["type"] == "WordBoundary":
                            # Store the audio-time offset (given in 100ns units) in seconds
                            # If there are multiple words, we take the first one (the reveal word)
                            if reveal_audio_offset == 0.0:
                                reveal_audio_offset = event["offset"] / 10_000_000.0
            else:
                await comm.save(temp_path)
                
            chunk["file"] = temp_path
            temp_files.append(temp_path)

    try:
        # Run synthesis synchronously from the perspective of this background thread
        loop.run_until_complete(synthesize())
        
        # 3. Play back chunks sequentially
        for chunk in chunks:
            if chunk["style"] == "reveal":
                # Schedule the reveal event based on the exact audio offset
                def fire_reveal(offset):
                    time.sleep(offset)
                    result_queue.put(("reveal_started", time.time()))
                    
                threading.Thread(target=fire_reveal, args=(reveal_audio_offset,), daemon=True).start()
                
            # Play the synthesized mp3
            playsound(chunk["file"])
            
            # Wait the scripted gap between chunk playback start times
            if chunk["gap_after"] > 0:
                time.sleep(chunk["gap_after"])
                
    finally:
        loop.close()
        for f in temp_files:
            try:
                os.remove(f)
            except OSError:
                pass

def speak_round(round_script: list):
    """
    Groups the round script into chunks by style, synthesizes them via edge-tts,
    and plays them sequentially. Uses WordBoundary streaming on the reveal chunk
    to fire the queue event at the precise audio time.
    """
    q = queue.Queue()
    thread = threading.Thread(target=_async_speak_round, args=(round_script, q), daemon=True)
    thread.start()
    return q

if __name__ == "__main__":
    import words
    print("Testing cloud TTS (edge-tts + Chunking + WordBoundary)...")
    
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
