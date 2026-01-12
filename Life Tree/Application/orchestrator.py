from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont
import json
import os
from datetime import datetime

from Infrastructure.variables import SESSION_LOGS_PATH, NTFY_PRIORITY_URGENT, NTFY_PRIORITY_DEFAULT, FOCUS_TIME, SHORT_BREAK_TIME, LONG_BREAK_TIME
from Adapters.External.ntfy_notifier import NtfyNotifier

# --- Hexagonal UI Adapters (Popups) ---
from Adapters.UI.Popups.focus_end_popup import FocusEndPopup
from Adapters.UI.Popups.review_dialog import SessionReviewDialog
from Adapters.UI.Popups.break_end_dialog import BreakEndPopup

class Orchestrator(QObject):
    """
    Application-level orchestrator (Hexagonal Application Layer).
    Coordinates session transitions and alerts.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.popup = None
        self.review_dialog = None
        self.break_end_dialog = None

    def show_focus_end(self):
        """Brings app to top and shows the binary outcome review dialog."""
        self._finish_focus_end()

    def _finish_focus_end(self):
        """Shows the review dialog and sends notifications."""
        self._force_to_top()

        if self.main_window.current_pomodoro_view:
            self.main_window.timer_engine.start_break()
            self.main_window.show_graphs_window()

        # Remote Notification
        NtfyNotifier.send(
            title="Focus Complete! 🧘",
            message=f"Nice work. Your break has automatically started.",
            tags="heavy_check_mark,coffee",
            priority=NTFY_PRIORITY_DEFAULT
        )

        self._show_session_review()

    def _show_session_review(self):
        # Create non-blocking (modeless) dialog
        self.review_dialog = SessionReviewDialog(self.main_window)
        self.review_dialog.setWindowModality(Qt.WindowModality.NonModal)
        
        # Connect finished signal to handle saving
        self.review_dialog.finished.connect(self._handle_review_finished)
        self.review_dialog.show()
        
    def _handle_review_finished(self, result):
        if hasattr(self, 'review_dialog') and self.review_dialog:
            outcome = self.review_dialog.get_outcome()
            if outcome:
                self.save_session_review(outcome)
            self.review_dialog.deleteLater()
            self.review_dialog = None

    def save_session_review(self, outcome):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "duration_mins": self.main_window.timer_engine.config.get("focus_minutes", 25)
        }
        
        logs = []
        if os.path.exists(SESSION_LOGS_PATH):
            try:
                with open(SESSION_LOGS_PATH, 'r') as f:
                    logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, PermissionError):
                logs = []
        
        logs.append(log_entry)
        with open(SESSION_LOGS_PATH, 'w') as f:
            json.dump(logs, f, indent=4)

    def show_break_end(self):
        """Called when the break timer finishes."""
        self._force_to_top()
        
        # Remote Notification
        NtfyNotifier.send(
            title="Break Finished! ⏱️",
            message="Ready to start focusing again?",
            tags="alarm_clock",
            priority=NTFY_PRIORITY_URGENT
        )
        
        self.break_end_dialog = BreakEndPopup(self.main_window)
        
        # Center logic
        geom = self.main_window.geometry()
        x = geom.x() + (geom.width() - self.break_end_dialog.width()) // 2
        y = geom.y() + (geom.height() - self.break_end_dialog.height()) // 2
        self.break_end_dialog.move(x, y)
        
        if self.break_end_dialog.exec():
            if self.main_window.current_pomodoro_view:
                view = self.main_window.current_pomodoro_view
                if view.has_incomplete_intentions():
                    self.main_window.timer_engine.start_focus()
                else:
                    self.main_window.timer_engine.stop()
        else:
            if self.main_window.current_pomodoro_view:
                view = self.main_window.current_pomodoro_view
                self.main_window.timer_engine.stop()
                view.intentions_list.setCurrentRow(-1)

    def handle_focus_start(self):
        """Called when a focus session starts."""
        self.main_window.show_graphs_window()
        self.main_window.keyboard_listener.start_session()
        
        # Reset milestones for the new session
        self.main_window._milestone_word_last = 0
        self.main_window._milestone_char_last = 0
        
        focus_mins = self.main_window.timer_engine.config.get("focus_minutes", 25)
        msg = f"{focus_mins} minutes—go!"

        # Local Notification
        if hasattr(self.main_window, 'tray_manager'):
            self.main_window.tray_manager.notify("Focus Started ⏱️", msg)

        # Remote Notification
        NtfyNotifier.send(
            title="Focus Started ⏱️",
            message=msg,
            tags="timer_clock",
            priority=NTFY_PRIORITY_DEFAULT
        )

    def _force_to_top(self):
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        
        # Don't change flags at runtime (crash risk), just raise and activate
        self.main_window.raise_()
        self.main_window.activateWindow()
        self.main_window.show()
