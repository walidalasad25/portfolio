import time
import ctypes
from ctypes import Structure, c_uint, sizeof, byref
from Infrastructure.variables import IDLE_THRESHOLD_SECONDS

class IdleDetector:
    """
    Adapter for monitoring Windows user activity.
    """
    def __init__(self, idle_threshold_sec=IDLE_THRESHOLD_SECONDS):
        self.start_time = None
        self.active_seconds = 0.0
        self.accumulated_total_seconds = 0.0 # Time from previous sessions
        self.last_check_time = 0.0
        self.is_running = False
        self.idle_threshold_sec = idle_threshold_sec
        
        # Windows struct for idle checking
        class LASTINPUTINFO(Structure):
            _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]
        self._last_input_info = LASTINPUTINFO()
        self._last_input_info.cbSize = sizeof(LASTINPUTINFO)

    def start(self):
        self.last_check_time = time.time()
        if self.start_time is None:
            self.start_time = self.last_check_time
        self.is_running = True

    def stop(self):
        self.is_running = False

    def reset(self):
        self.active_seconds = 0.0
        self.accumulated_total_seconds = 0.0
        self.start_time = time.time()
        self.last_check_time = self.start_time

    def update(self, force_active=False):
        if not self.is_running:
            return

        now = time.time()
        elapsed = now - self.last_check_time
        self.last_check_time = now
        
        if elapsed <= 0:
            return

        idle_duration_ms = self._get_idle_duration_ms()
        idle_seconds = idle_duration_ms / 1000.0
        if force_active or idle_seconds < self.idle_threshold_sec:
            self.active_seconds += elapsed
            
    def get_stats(self):
        if self.start_time is None:
            return self.accumulated_total_seconds, self.active_seconds
            
        current_session_total = time.time() - self.start_time
        return self.accumulated_total_seconds + current_session_total, self.active_seconds

    def is_user_active(self):
        idle_duration_ms = self._get_idle_duration_ms()
        return (idle_duration_ms / 1000.0) < self.idle_threshold_sec

    def _get_idle_duration_ms(self):
        ctypes.windll.user32.GetLastInputInfo(byref(self._last_input_info))
        millis = ctypes.windll.kernel32.GetTickCount()
        return millis - self._last_input_info.dwTime

    @staticmethod
    def format_time(seconds):
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
