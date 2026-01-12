import datetime
import os
from Infrastructure.variables import FOCUS_DATA_PATH, TREE_DATA_PATH

class AppInitializer:
    """
    Application-level service for handling initialization, cleanup, and midnight resets.
    """
    def __init__(self, main_window, repository, history_recorder):
        self.main_window = main_window
        self.repository = repository
        self.history_recorder = history_recorder
        self.last_reset_date = datetime.date.today().isoformat()
        
    def initialize(self):
        """Restore stats and prepare sensors."""
        data = self.repository.load_focus_stats()
        
        # Load history for cross-validation/repair
        h_t, h_active, h_words, h_chars, _, _ = self.history_recorder.get_data()
        
        if data:
            saved_date = data.get("date")
            today_date = datetime.date.today().isoformat()
            
            if saved_date == today_date:
                active_sec = data.get("active_seconds", 0)
                words = data.get("words", 0)
                chars = data.get("chars", 0)
                total_sec = data.get("total_seconds", 0)

                # REPAIR LOGIC: If history is significantly ahead of summary (indicating a crash/missing save)
                if len(h_active) > 0 and h_active[-1] > active_sec + 5:
                    print(f"AppInitializer: Repairing out-of-sync stats from History (+{h_active[-1] - active_sec:.1f}s recovered)")
                    active_sec = h_active[-1]
                    words = max(words, h_words[-1])
                    chars = max(chars, h_chars[-1])
                    total_sec = max(total_sec, active_sec) # Lower bound sanity

                self.main_window.idle_detector.accumulated_total_seconds = total_sec
                self.main_window.idle_detector.active_seconds = active_sec
                self.main_window.keyboard_listener.total_words = words
                self.main_window.keyboard_listener.total_chars = chars
            else:
                print(f"AppInitializer: Midnight Detected during load. Resetting stats. (Last: {saved_date})")
        elif len(h_active) > 0:
            print("AppInitializer: Focus data missing. Reconstructing from history points.")
            self.main_window.idle_detector.active_seconds = h_active[-1]
            self.main_window.keyboard_listener.total_words = h_words[-1]
            self.main_window.keyboard_listener.total_chars = h_chars[-1]

    def save_on_exit(self):
        """Persist all volatile data to disk."""
        total_sec, active_sec = self.main_window.idle_detector.get_stats()
        words, chars = self.main_window.keyboard_listener.get_stats()
        self.repository.save_focus_stats(total_sec, active_sec, words, chars)
        self.history_recorder.save()
        
        # Save Tree States and Perspective data
        if hasattr(self.main_window, 'tree'):
            self.main_window.tree.save_state()
            self.main_window.problems_manager.save()
            self.main_window.values_manager.save()

    def autosave(self):
        """Periodic background save (Heartbeat)."""
        self.save_on_exit()

    def perform_runtime_reset(self):
        """Hot reset at midnight."""
        today = datetime.date.today().isoformat()
        print(f"AppInitializer: Runtime Midnight Reset Triggered: {today}")
        
        # 1. Final save for yesterday
        self.save_on_exit()
        
        # 2. Reset trackers
        self.main_window.idle_detector.reset()
        self.main_window.keyboard_listener.reset()
        self.history_recorder.reset()
        
        self.last_reset_date = today
        
        # 3. Refresh UI if view is active
        if self.main_window.current_pomodoro_view:
            self.main_window.current_pomodoro_view.update_ui()
