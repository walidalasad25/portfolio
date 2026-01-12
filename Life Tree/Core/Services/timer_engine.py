import time
from enum import Enum

class PomodoroPhase(Enum):
    IDLE = 0
    FOCUS = 1
    BREAK = 2
    WAIT_FOCUS = 3

class TimerEngine:
    """
    Core Pomodoro engine (formerly PomodoroSession).
    Manages phases, timing, and session tracking.
    """
    def __init__(self, focus_min=25, short_break_min=5, long_break_min=15, long_break_interval=4):
        self.config = {
            "focus_minutes": focus_min,
            "short_break_minutes": short_break_min,
            "long_break_minutes": long_break_min,
            "long_break_interval": long_break_interval
        }
        self.phase = PomodoroPhase.IDLE
        self.elapsed_seconds = 0
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.cycles_completed = 0
        self.is_running = False
        self.afk_mode = False
        self.is_long_break = False
        self.restriction_armed = False
        
        # Tracking last session for graphs
        self.last_focus_start = None
        self.last_focus_end = None
        self.start_time = None

    def start_focus(self):
        self.phase = PomodoroPhase.FOCUS
        self.total_seconds = int(self.config["focus_minutes"] * 60)
        self.elapsed_seconds = 0
        self.remaining_seconds = self.total_seconds
        self.is_running = True
        self.start_time = time.time()

    def start_break(self):
        self.phase = PomodoroPhase.BREAK
        
        # Determine if it's a long break
        # (Total cycles completed: if cycles_completed > 0 and multiples of interval)
        if self.cycles_completed > 0 and self.cycles_completed % self.config["long_break_interval"] == 0:
            break_mins = self.config["long_break_minutes"]
            self.is_long_break = True
        else:
            break_mins = self.config["short_break_minutes"]
            self.is_long_break = False
            
        self.total_seconds = int(break_mins * 60)
        self.elapsed_seconds = 0
        self.remaining_seconds = self.total_seconds
        self.is_running = True

    def pause(self):
        self.is_running = False

    def resume(self):
        if self.phase != PomodoroPhase.IDLE:
            self.is_running = True

    def stop(self):
        self.phase = PomodoroPhase.IDLE
        self.is_running = False
        self.elapsed_seconds = 0
        self.total_seconds = 0
        self.remaining_seconds = 0

    def tick(self):
        """Advances the timer by 1 second."""
        if not self.is_running:
            return

        if self.phase == PomodoroPhase.FOCUS:
            self.elapsed_seconds += 1
            if self.elapsed_seconds >= self.total_seconds:
                self.last_focus_end = time.time()
                self.last_focus_start = self.start_time
                self.cycles_completed += 1 # Important for long break logic
                self.is_running = False
        else:
            self.elapsed_seconds += 1
            self.remaining_seconds = max(0, self.total_seconds - self.elapsed_seconds) 
            if self.elapsed_seconds >= self.total_seconds:
                self.is_running = False

    def get_time_string(self):
        # Always count UP for both Focus and Break
        s = self.elapsed_seconds
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def get_progress(self):
        if self.total_seconds == 0:
            return 0.0
        # Always return relative completion (elapsed / total)
        return min(1.0, self.elapsed_seconds / self.total_seconds)
