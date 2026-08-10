import random

WORD_GROUPS = [
    {
        "shoot_word": "door",
        "rhymes": ["floor", "more", "sore", "lore", "core", "pour"]
    },
    {
        "shoot_word": "cat",
        "rhymes": ["bat", "mat", "hat", "flat", "rat", "pat"]
    },
    {
        "shoot_word": "bell",
        "rhymes": ["shell", "sell", "fell", "well", "tell", "yell"]
    },
    {
        "shoot_word": "light",
        "rhymes": ["night", "sight", "fight", "bright", "might", "kite"]
    },
    {
        "shoot_word": "run",
        "rhymes": ["sun", "fun", "bun", "done", "none", "spun"]
    },
    {
        "shoot_word": "blue",
        "rhymes": ["shoe", "clue", "glue", "true", "flew", "drew"]
    },
    {
        "shoot_word": "game",
        "rhymes": ["fame", "tame", "blame", "flame", "same", "name"]
    },
    {
        "shoot_word": "town",
        "rhymes": ["down", "frown", "crown", "brown", "clown", "noun"]
    },
    {
        "shoot_word": "make",
        "rhymes": ["bake", "lake", "cake", "fake", "snake", "wake"]
    },
    {
        "shoot_word": "tree",
        "rhymes": ["free", "see", "bee", "flee", "knee", "three"]
    }
]

def get_random_round():
    """
    Returns one random group with its rhymes shuffled into a random order.
    """
    # Pick a random word group
    group = random.choice(WORD_GROUPS)
    
    # Create a copy so we don't modify the original list in-place
    rhymes_shuffled = list(group["rhymes"])
    random.shuffle(rhymes_shuffled)
    
    return {
        "shoot_word": group["shoot_word"],
        "rhymes": rhymes_shuffled
    }

if __name__ == "__main__":
    print("Testing get_random_round():\n")
    for i in range(3):
        round_data = get_random_round()
        print(f"Round {i+1}:")
        print(f"  Shoot word: {round_data['shoot_word']}")
        print(f"  Rhymes:     {round_data['rhymes']}\n")
