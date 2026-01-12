import time
import json
import os
import datetime
from collections import deque
from Infrastructure.variables import STATS_HISTORY_PATH

class HistoryRecorder:
    """
    Core service for recording and retrieving time-series productivity data.
    """
    def __init__(self, active_tracker, word_tracker, max_history=86400):
        self.active_tracker = active_tracker
        self.word_tracker = word_tracker
        self.max_history = max_history
        self.filepath = STATS_HISTORY_PATH
        
        # Data structure: list of tuples (timestamp, active_seconds, word_count, char_count, node_label, intention_label)
        self.data_points = deque(maxlen=max_history)
        self.run_start_time = None
        self.load()

    def reset(self):
        self.data_points.clear()
        self.run_start_time = time.time()
        
    def record(self, node_label=None, intention_label=None):
        now = time.time()
        if self.run_start_time is None:
            self.run_start_time = now

        _, active_sec = self.active_tracker.get_stats()
        words, chars = self.word_tracker.get_stats()
        
        # Data point: (timestamp, active_seconds, word_count, char_count, node_label, intention_label)
        self.data_points.append((now, active_sec, words, chars, node_label, intention_label))
        
    def get_data(self):
        if not self.data_points:
            return [], [], [], [], [], []
        
        # Handing old 4/5-tuple and new 6-tuple data
        t, active, words, chars, nodes, intentions = [], [], [], [], [], []
        for pt in self.data_points:
            t.append(pt[0])
            active.append(pt[1])
            words.append(pt[2])
            chars.append(pt[3])
            nodes.append(pt[4] if len(pt) > 4 else None)
            intentions.append(pt[5] if len(pt) > 5 else None)
            
        return t, active, words, chars, nodes, intentions

    def save(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(list(self.data_points), f)
        except Exception as e:
            print(f"HistoryRecorder: Failed to save history: {e}")

    def load(self):
        if not os.path.exists(self.filepath):
            return
            
        try:
            with open(self.filepath, 'r') as f:
                loaded = json.load(f)
                
            today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp()
            
            self.data_points.clear()
            for pt in loaded:
                if pt[0] >= today_start:
                    self.data_points.append(tuple(pt))
        except Exception as e:
            print(f"HistoryRecorder: Failed to load history: {e}")
