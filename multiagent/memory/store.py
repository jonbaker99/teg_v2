import json, os

MEM_PATH = "memory.json"

def load_memory():
    if os.path.exists(MEM_PATH):
        return json.load(open(MEM_PATH))
    return {}

def save_memory(mem):
    with open(MEM_PATH, "w") as f:
        json.dump(mem, f, indent=2)
