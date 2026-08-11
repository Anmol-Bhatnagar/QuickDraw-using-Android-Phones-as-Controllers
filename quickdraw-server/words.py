import random

WORD_GROUPS = [
    {
        "reveal_word": "shoot",
        "rhymes": ["loot", "boot", "root", "suit", "flute", "cute", "mute"],
        "red_herrings": ["shout", "shut", "shoe"]
    },
    {
        "reveal_word": "fire",
        "rhymes": ["wire", "tire", "liar", "hire", "choir", "higher"],
        "red_herrings": ["fair", "fear", "four"]
    },
    {
        "reveal_word": "draw",
        "rhymes": ["flaw", "law", "raw", "claw", "straw", "jaw"],
        "red_herrings": ["drag", "drop", "drum"]
    },
    {
        "reveal_word": "now",
        "rhymes": ["cow", "how", "plow", "wow", "vow", "bow"],
        "red_herrings": ["no", "new", "know"]
    },
    {
        "reveal_word": "go",
        "rhymes": ["slow", "flow", "glow", "blow", "show", "crow"],
        "red_herrings": ["got", "get", "good"]
    },
    {
        "reveal_word": "bang",
        "rhymes": ["fang", "hang", "slang", "gang", "pang", "twang"],
        "red_herrings": ["bag", "bat", "bad"]
    },
    {
        "reveal_word": "hit",
        "rhymes": ["bit", "fit", "kit", "lit", "pit", "sit"],
        "red_herrings": ["hat", "hot", "hut"]
    },
    {
        "reveal_word": "strike",
        "rhymes": ["bike", "hike", "like", "mike", "spike", "tyke"],
        "red_herrings": ["streak", "stuck", "stroke"]
    }
]

SLOW_WORDS = ["ready", "steady", "aim", "wait", "hold", "focus", "breathe", "calm"]

def get_random_round():
    """
    Returns an explicitly ordered script for the round, including dynamic gaps,
    slow anticipatory words, quick burst words, optional red herrings, and the final reveal.
    """
    group = random.choice(WORD_GROUPS)
    script = []
    
    # 1. 2 slow elongated calls (e.g. "ready", "steady")
    slow_picks = random.sample(SLOW_WORDS, 2)
    for word in slow_picks:
        script.append({
            "text": word,
            "style": "slow",
            "gap_after": random.uniform(1.0, 1.8)
        })
        
    # 2. 2-4 burst-style close rhymes
    num_burst = random.randint(2, 4)
    burst_picks = random.sample(group["rhymes"], min(num_burst, len(group["rhymes"])))
    for word in burst_picks:
        script.append({
            "text": word,
            "style": "burst",
            "gap_after": random.uniform(0.15, 0.3)
        })
        
    # 3. Optional red-herring near-rhyme to mess with anticipation
    if random.random() < 0.35 and group.get("red_herrings"):
        red_herring = random.choice(group["red_herrings"])
        
        # Noticeably longer gap BEFORE the red herring to break the burst rhythm
        script[-1]["gap_after"] = random.uniform(1.0, 2.0)
        
        script.append({
            "text": red_herring,
            "style": "burst",
            "gap_after": random.uniform(0.15, 0.3)
        })
        
    # Gap BEFORE the reveal word is short and unpredictable
    script[-1]["gap_after"] = random.uniform(0.05, 0.25)
    
    # 4. The reveal word
    script.append({
        "text": group["reveal_word"],
        "style": "reveal",
        "gap_after": 0.1 # End of round
    })
    
    return {
        "reveal_word": group["reveal_word"],
        "script": script
    }

if __name__ == "__main__":
    import pprint
    print("Testing get_random_round():\n")
    for i in range(2):
        print(f"Round {i+1}:")
        pprint.pprint(get_random_round(), sort_dicts=False)
        print()
