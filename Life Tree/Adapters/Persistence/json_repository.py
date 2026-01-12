import json
import os
import datetime
from Infrastructure.variables import FOCUS_DATA_PATH, TREE_DATA_PATH

class JsonRepository:
    """
    Adapter for JSON-based storage of application data.
    """
    def __init__(self, focus_path=FOCUS_DATA_PATH, tree_path=TREE_DATA_PATH):
        self.focus_path = focus_path
        self.tree_path = tree_path
        os.makedirs(os.path.dirname(self.focus_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.tree_path), exist_ok=True)

    def save_focus_stats(self, total_seconds, active_seconds, words, chars):
        data = {
            "date": datetime.date.today().isoformat(),
            "total_seconds": total_seconds,
            "active_seconds": active_seconds,
            "words": words,
            "chars": chars
        }
        try:
            with open(self.focus_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"JsonRepository: Error saving focus stats: {e}")

    def load_focus_stats(self):
        if not os.path.exists(self.focus_path):
            return None
        try:
            with open(self.focus_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"JsonRepository: Error loading focus stats: {e}")
            return None

    def save_tree(self, roots_dict_list):
        try:
             with open(self.tree_path, 'w') as f:
                json.dump(roots_dict_list, f, indent=2)
        except Exception as e:
            print(f"JsonRepository: Failed to save tree data: {e}")

    def load_tree(self):
        if not os.path.exists(self.tree_path):
            return None
        try:
            with open(self.tree_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"JsonRepository: Error loading tree data: {e}")
            return None
