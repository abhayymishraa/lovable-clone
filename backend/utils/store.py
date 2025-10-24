import os 
import json

PROJECT_DIR = "/data/project"

def get_store_path(id: str, filename: str):
    projectpath = os.path.join(PROJECT_DIR, id)
    os.makedirs(projectpath, exist_ok=True)
    return os.path.join(projectpath, filename)

def save_json_store(id: str, filename: str, data: dict or list):
    with open(get_store_path(id, filename), "w") as file:
        json.dump(data, file, indent=2)

def load_json_store(id: str,filename: str):
    path = get_store_path(id, filename=filename)
    if os.path.exists(path):
        with open(path, "r") as r:
            return json.load(r)
    
    return {} if filename.endswith('.json') else []

