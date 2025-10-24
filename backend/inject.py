import os
import json

def list_files_recursive(path):
    file_structure = []
    for root, _, files in os.walk(path):
        for name in files:
            relative_path = os.path.relpath(os.path.join(root, name), path)
            file_structure.append(relative_path)
    return file_structure

if __name__ == "__main__":
    react_app_path = "/home/user/react-app"
    if os.path.exists(react_app_path):
        files = list_files_recursive(react_app_path)
        print(json.dumps(files))
    else:
        print(json.dumps([]))