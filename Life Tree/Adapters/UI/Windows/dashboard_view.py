from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame, QLineEdit, QListWidget, QListWidgetItem, QGridLayout, QSizePolicy, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QAction
import os

from Core.Services.timer_engine import TimerEngine, PomodoroPhase
from Adapters.Sensors.idle_detector import IdleDetector
from Adapters.Sensors.keyboard_listener import KeyboardListener
from Core.Services.percentage_engine import calculate_node_percentage
from Adapters.UI.Components.percentage_ui import RotatingProgressCircle
from Infrastructure.variables import BG_COLOR, CARD_BG_COLOR, TEXT_COLOR, ACCENT_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, DANGER_COLOR
import pygetwindow as gw
from Adapters.UI.Popups.distraction_ui import DistractionWarning

class PomodoroWindow(QWidget):
    moved = pyqtSignal()
    toggle_expand_requested = pyqtSignal() # Request parent to expand/collapse me
    toggle_graphs_requested = pyqtSignal()
    close_requested = pyqtSignal()
    mark_solved_requested = pyqtSignal(object)

    focus_started = pyqtSignal()

    def __init__(self, node, roots, active_tracker, word_tracker, state_manager=None, pomodoro_session=None, show_percentages=True, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True) # Required for background-color to work
        if parent:
             self.setWindowFlags(Qt.WindowType.Widget)
        
        self.node = node
        self.roots = roots
        self.state_manager = state_manager
        node_label = node.label if hasattr(node, 'label') else str(node)
        
        # Logic Initialization
        self.pomodoro_session = pomodoro_session if pomodoro_session else TimerEngine()
        # Use provided global trackers
        self.active_tracker = active_tracker
        self.word_tracker = word_tracker
        self.previous_phase = self.pomodoro_session.phase
        self.show_percentages = show_percentages
        
        # Ensure they are running (MainWindow should have started them, but check/start is safe if idempotent)
        if not self.active_tracker.is_running:
             self.active_tracker.start()
        if not self.word_tracker.is_running:
             self.word_tracker.start()
        
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(1000) # Update every second
        
        # Stats per Intention Tracking state
        total_sec, active_sec = self.active_tracker.get_stats()
        self.last_active_sec = active_sec
        self.last_words, self.last_chars = self.word_tracker.get_stats()
        self.afk_active = self.pomodoro_session.afk_mode # AFK Focus Override - Sync with global state
        self.deep_focus_active = False # Distraction Control Override
        
        # Distraction Warning Popup
        self.distraction_warning = DistractionWarning(parent=self)
        self.distraction_warning.add_allowed_requested.connect(self.add_allowed_window)
        
        # Restriction Feature Initialization
        self._load_restriction_config()
        # Initialize engine state from config if not already set (e.g. if switching nodes)
        # Note: self.restriction_armed is still used for local UI tracking if needed, 
        # but we primary use self.pomodoro_session.restriction_armed
        self.restricted_keywords = ["facebook", "spank", "antigravity", "zoechip", "youtube"]
        self._load_restriction_config() # Re-load to get keywords and potentially 'armed' state
        
        self.restrict_timer = QTimer(self)
        self.restrict_timer.timeout.connect(self._check_restrictions)
        self.restrict_timer.start(2000) # Reduced to every 2 seconds for performance
        
        # Internal Whitelist
        self.INTERNAL_WHITELIST = ["Evidence of Growth", "Focus Statistics", "Distraction Warning", "Pomodoro"]
        
        # Consistent ToolTip Styling
        self.setStyleSheet(self.styleSheet() + f"""
            QToolTip {{
                background-color: {CARD_BG_COLOR};
                color: {TEXT_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                padding: 0px;
                font-family: 'Segoe UI';
            }}
        """)
        
        # UI Setup
        self.setStyleSheet(f"""
            QWidget#MainContent {{
                background-color: {BG_COLOR};
                font-family: 'Segoe UI', sans-serif;
            }}
            QFrame {{
                background-color: {CARD_BG_COLOR};
                border-radius: 12px;
                border: 1px solid #333;
            }}
            QLabel {{
                color: #ffffff;
                background-color: transparent;
            }}
            QPushButton {{
                background-color: #2a2a35;
                border: 1px solid #3a3a45;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
            }}
            QPushButton:hover {{
                background-color: #3a3a45;
            }}
            QLineEdit {{
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }}
            QListWidget {{
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #ffffff;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-bottom: 1px solid #333;
            }}
            QListWidget::item:selected {{
                background-color: #3e3e4a;
                border-left: 3px solid {PRIMARY_COLOR};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: #33333d;
            }}
        """)

        self.setObjectName("MainContent")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Header (Title + Expand Button) ---
        header_layout = QHBoxLayout()
        
        title = QLabel(f"{node_label}")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.btn_mark_solved = QPushButton("✓ Mark Solved")
        self.btn_mark_solved.setStyleSheet(f"background-color: #1b5e20; border: 1px solid #2e7d32; color: {SECONDARY_COLOR};")
        self.btn_mark_solved.clicked.connect(self.on_mark_solved)
        header_layout.addWidget(self.btn_mark_solved)
        
        if not self.show_percentages:
            self.btn_mark_solved.hide()
        
        self.btn_expand = QPushButton("⛶")
        self.btn_expand.setToolTip("Expand/Restore")
        self.btn_expand.setCheckable(True)
        self.btn_expand.clicked.connect(self.toggle_expand_requested.emit)
        header_layout.addWidget(self.btn_expand)

        layout.addLayout(header_layout)
        
        # Initial Button State
        self.update_solved_button()
        
        # Divider
        self.add_divider(layout)

        # --- Stats Section (Top Row) ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.lbl_stats = {} # Dictionary to store labels
        
        stats_layout.addWidget(self.create_mini_stat_widget("Total", "00:00:00", "#4CAF50", "total"))
        stats_layout.addWidget(self.create_mini_stat_widget("Active", "00:00:00", "#2196F3", "active"))
        stats_layout.addWidget(self.create_mini_stat_widget("Words", "0", "#E91E63", "words"))
        stats_layout.addWidget(self.create_mini_stat_widget("Chars", "0", "#9C27B0", "chars"))
        
        layout.addLayout(stats_layout)
        
        self.add_divider(layout)

        # --- Main Focus Timer (Center) ---
        timer_container = QWidget()
        timer_layout = QVBoxLayout(timer_container)
        timer_layout.setSpacing(10) # increased spacing
        
        intention_row = QHBoxLayout()
        intention_row.addStretch()
        
        self.lbl_current_intention = QLabel("Ready to Focus")
        self.lbl_current_intention.setFont(QFont("Segoe UI", 12))
        self.lbl_current_intention.setStyleSheet("color: #e0e0e0; padding: 5px;")
        self.lbl_current_intention.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_current_intention.setWordWrap(True)
        intention_row.addWidget(self.lbl_current_intention)
        
        intention_row.addSpacing(15)
        
        # Cycle Progress Column
        cycle_col = QVBoxLayout()
        cycle_col.setSpacing(2)
        
        cycle_header = QHBoxLayout()
        self.lbl_cycle_count = QLabel("Cycle 0")
        self.lbl_cycle_count.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.lbl_cycle_count.setStyleSheet("color: #2196F3;")
        cycle_header.addWidget(self.lbl_cycle_count)
        cycle_header.addStretch()
        
        self.lbl_cycle_perc = QLabel("0%")
        self.lbl_cycle_perc.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.lbl_cycle_perc.setStyleSheet("color: #2196F3;")
        cycle_header.addWidget(self.lbl_cycle_perc)
        cycle_col.addLayout(cycle_header)

        self.cycle_bar = QFrame()
        self.cycle_bar.setFixedHeight(8)
        self.cycle_bar.setFixedWidth(80)
        self.cycle_bar.setStyleSheet(f"background-color: #333; border: none; border-radius: 4px;")
        self.cycle_fill = QFrame(self.cycle_bar)
        self.cycle_fill.setFixedHeight(8)
        self.cycle_fill.setFixedWidth(0)
        self.cycle_fill.setStyleSheet(f"background-color: #2196F3; border-radius: 4px;") # Electric Blue
        cycle_col.addWidget(self.cycle_bar)
        
        intention_row.addLayout(cycle_col)
        intention_row.addSpacing(15)
        
        # Life Progress Circle (Moved here below stats)
        self.life_circle = RotatingProgressCircle()
        if not self.show_percentages:
            self.life_circle.hide()
        intention_row.addWidget(self.life_circle)
        
        intention_row.addStretch()
        timer_layout.addLayout(intention_row)
        
        # --- Timer Display ---
        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        self.lbl_timer.setStyleSheet(f"color: {PRIMARY_COLOR};") # Orange Focus Color
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel("FOCUS")
        self.lbl_status.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.lbl_status.setStyleSheet("color: #666; letter-spacing: 2px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        timer_layout.addWidget(self.lbl_timer)
        timer_layout.addWidget(self.lbl_status)
        
        # Controls - Single "Completed" Button
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        self.btn_complete = QPushButton("Completed")
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR}; 
                color: white; 
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {SECONDARY_COLOR};
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: #2a2a35;
                color: #555;
            }}
        """)
        self.btn_complete.clicked.connect(self.complete_current_intention)
        self.btn_complete.setEnabled(False) # Disabled initially until Intention is added
        controls_layout.addWidget(self.btn_complete)
        
        timer_layout.addLayout(controls_layout)
        
        # Session Control Buttons (Pause, Stop, Skip)
        extra_controls_layout = QHBoxLayout()
        extra_controls_layout.setSpacing(10)

        self.btn_afk = QPushButton("AFK")
        self.btn_afk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_afk.setStyleSheet("""
            QPushButton {
                background-color: #f39c12; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #2a2a35;
                color: #555;
            }
        """)
        self.btn_afk.clicked.connect(self.toggle_pause)
        self.btn_afk.setEnabled(False)
        
        # Initialize AFK button state from persisted mode
        if self.afk_active:
            self.btn_afk.setText("STOP AFK")
            self.btn_afk.setToolTip("Stop AFK Focus and return to normal idle detection.")
        else:
            self.btn_afk.setText("AFK")
            self.btn_afk.setToolTip("Start AFK Focus: keep timer running while reading or researching.")
            
        extra_controls_layout.addWidget(self.btn_afk)

        self.btn_deep_focus = QPushButton("Deep Focus")
        self.btn_deep_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deep_focus.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #2a2a35;
                color: #555;
            }
        """)
        self.btn_deep_focus.clicked.connect(self.toggle_deep_focus) # Linked button
        self.btn_deep_focus.setEnabled(False)
        extra_controls_layout.addWidget(self.btn_deep_focus)

        self.btn_progress = QPushButton("Progress")
        self.btn_progress.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_progress.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2471a3;
            }
            QPushButton:disabled {
                background-color: #2a2a35;
                color: #555;
            }
        """)
        self.btn_progress.clicked.connect(self.toggle_graphs_requested.emit)
        self.btn_progress.setEnabled(False)
        extra_controls_layout.addWidget(self.btn_progress)

        self.btn_restrict = QPushButton("Restrict")
        self.btn_restrict.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restrict.setStyleSheet(f"""
            QPushButton {{
                background-color: #2c3e50; 
                color: white; 
                font-weight: bold;
                padding: 8px;
                border: 1px solid #34495e;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #34495e;
            }}
        """)
        self.btn_restrict.clicked.connect(self.handle_restrict_click)
        extra_controls_layout.addWidget(self.btn_restrict)



        timer_layout.addLayout(extra_controls_layout)
        
        layout.addWidget(timer_container)
        
        self.add_divider(layout)
        
        # --- Intentions Section ---
        intentions_label = QLabel("What I am willing to do")
        intentions_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        intentions_label.setStyleSheet("color: #888;")
        layout.addWidget(intentions_label)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.intention_input = QLineEdit()
        self.intention_input.setPlaceholderText("Take the smallest step possible...")
        self.intention_input.returnPressed.connect(self.add_intention) 
        input_layout.addWidget(self.intention_input)
        
        self.btn_add_intention = QPushButton("+")
        self.btn_add_intention.setFixedWidth(30)
        self.btn_add_intention.clicked.connect(self.add_intention)
        input_layout.addWidget(self.btn_add_intention)

        layout.addLayout(input_layout)
        
        # Disable input if "My Life"
        if self.node.label == "My Life":
            self.intention_input.setEnabled(False)
            self.intention_input.setPlaceholderText("Aggregate view - select a sub-node to add task")
            self.btn_add_intention.setEnabled(False)
            self.btn_add_intention.setStyleSheet("background-color: #1a1a1a; color: #444;")
        
        # List Area
        self.intentions_list = QListWidget()
        self.intentions_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.intentions_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #333;
                padding: 4px;
                background-color: transparent;
            }

            QListWidget::item:selected {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 152, 0, 140), stop:1 rgba(43, 43, 43, 0));
                border-left: 6px solid #FF9800;
            }
            QListWidget::item:selected:!active {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255, 152, 0, 40), stop:1 rgba(43, 43, 43, 0));
                border-left: 6px solid #FF9800;
            }
        """)
        self.intentions_list.currentItemChanged.connect(self.update_active_intention)
        self.intentions_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.intentions_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.intentions_list)

        # Load existing intentions
        self._is_loading = True
        self.load_intentions()
        self.intentions_list.setCurrentRow(-1) # Ensure nothing is selected on load
        self._is_loading = False
    
    def clear_intentions(self):
        # Archive stats from all intentions before clearing
        for i in range(self.intentions_list.count()):
            item = self.intentions_list.item(i)
            stats = item.data(Qt.ItemDataRole.UserRole + 1)
            source_node = item.data(Qt.ItemDataRole.UserRole + 2)
            
            # Determine which node to archive stats to
            target_node = source_node if source_node else self.node
            if target_node.parent is None:
                # Skip archiving to root - stats should go to source nodes
                continue
                
            if stats:
                # Ensure archived_stats exists
                if not hasattr(target_node, 'archived_stats'):
                    target_node.archived_stats = {"time": 0, "words": 0, "chars": 0}
                target_node.archived_stats["time"] += stats.get("time", 0)
                target_node.archived_stats["words"] += stats.get("words", 0)
                target_node.archived_stats["chars"] += stats.get("chars", 0)

        self.intentions_list.clear()
        self.node.intentions = []
        
        # Update UI state
        self.lbl_current_intention.setText("Ready to Focus")
        self.btn_complete.setEnabled(False)
        
        self.update_ui()
        self.save_intentions_to_node()

    def show_context_menu(self, position: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2b2b2b; color: white; border: 1px solid #444; }
            QMenu::item:selected { background-color: #3d3d3d; }
        """)
        
        item = self.intentions_list.itemAt(position)
        
        if item:
            action_clear = QAction("Clear", self)
            action_clear.triggered.connect(lambda: self.remove_intention(item))
            menu.addAction(action_clear)
        
        # Always show Clear All
        action_clear_all = QAction("Clear All", self)
        action_clear_all.triggered.connect(self.clear_intentions)
        menu.addAction(action_clear_all)
        
        menu.exec(self.intentions_list.mapToGlobal(position))

    def has_incomplete_intentions(self):
        # Check if there's any item that is NOT completed
        count = self.intentions_list.count()
        for i in range(count):
            item = self.intentions_list.item(i)
            # We track completion by checking if widget has strikethrough logic or data
            # Since we are moving to custom widget, we should store state on the item itself
            if item.data(Qt.ItemDataRole.UserRole) != "completed":
                return True
        return False
        
    def format_dynamic_time(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"

    def update_intention_tooltip(self, item):
        stats = item.data(Qt.ItemDataRole.UserRole + 1)
        if stats is None:
             stats = {'time': 0, 'words': 0, 'chars': 0}
        
        if self.show_percentages:
            status = "Completed" if item.data(Qt.ItemDataRole.UserRole) == "completed" else "Active"
            status_color = "#4CAF50" if status == "Completed" else "#FF9800"
        else:
            status = "Information"
            status_color = TEXT_COLOR

        time_sec = stats.get('time', 0)
        time_str = self.format_dynamic_time(time_sec)
        
        # Use status-aware border color
        border_color = status_color
        
        # Wrapping in a styled div with a border to ensure it matches the node hover exactly
        tip = (f"<div style='background-color: #252526; border: 1px solid {border_color}; padding: 8px;'>"
               f"<b style='color: {status_color}; font-size: 9pt;'>{status}</b><br/>"
               f"<div style='height: 2px;'></div>"
               f"<span style='color: #cccccc; font-size: 8pt;'>"
               f"Time: {time_str}<br/>"
               f"Words: {stats.get('words', 0)}<br/>"
               f"Chars: {stats.get('chars', 0)}</span>"
               f"</div>")
        
        item.setToolTip(tip)
        
        # We NO LONGER set tooltip on children. Instead, we make the widget 
        # transparent for mouse events in add_intention_to_ui, 
        # allowing the item's native tooltip to trigger.
        widget = self.intentions_list.itemWidget(item)
        if widget:
            widget.setToolTip("") # Clear widget tooltip to avoid conflicts
            for child in widget.findChildren(QWidget):
                child.setToolTip("")
                child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def add_intention(self):
        if self.node.parent is None:
            return
        text = self.intention_input.text().strip()
        if text:
            self.add_intention_to_ui(text, "active", {'time': 0, 'words': 0, 'chars': 0}, self.node)
            self.intention_input.clear()
            self.save_intentions_to_node()

    def add_intention_to_ui(self, text, status="active", stats=None, source_node=None):
        if stats is None:
            stats = {'time': 0, 'words': 0, 'chars': 0}
        
        # Create Item
        item = QListWidgetItem(self.intentions_list)
        # container for custom widget (simplified, no delete button)
        widget = QWidget()
        widget.setObjectName("intention_container")
        widget.setStyleSheet("background: transparent;")
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        widget_layout = QHBoxLayout(widget)
        widget_layout.setContentsMargins(5, 6, 5, 6) # Smaller vertical margin
        
        # If it's from a different node (in root view), show which node
        prefix = "• "
        if self.node.parent is None and source_node and source_node != self.node:
             prefix = f"[{source_node.label}] • "
             
        lbl = QLabel(f"{prefix}{text}")
        lbl.setObjectName("intention_text")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        if status == "completed":
             lbl.setStyleSheet("color: #00E676; border: none; background: transparent; text-decoration: line-through;")
             widget.setStyleSheet("background-color: rgba(0, 230, 118, 20); border-radius: 4px;")
        else:
             lbl.setStyleSheet("color: #e0e0e0; border: none; background: transparent;")
        
        lbl.setFont(QFont("Segoe UI", 10))
        
        widget_layout.addWidget(lbl)
        widget_layout.addStretch()
        
        # Ensure it's tall enough for text + margin
        size = widget.sizeHint()
        size.setHeight(max(34, size.height() + 4)) # Compact but safe
        item.setSizeHint(size)
        item.setData(Qt.ItemDataRole.UserRole, status)
        item.setData(Qt.ItemDataRole.UserRole + 1, stats)
        item.setData(Qt.ItemDataRole.UserRole + 2, source_node) # Store source node
        item.setData(Qt.ItemDataRole.UserRole + 3, text) # Store raw text
        
        self.intentions_list.setItemWidget(item, widget)
        self.update_intention_tooltip(item)
        
        # Auto-select if none selected (Disabled during load to fulfill user request)
        if not getattr(self, '_is_loading', False) and self.intentions_list.currentRow() == -1:
            self.intentions_list.setCurrentRow(self.intentions_list.count() - 1)

    def load_intentions(self):
        is_root = self.node.parent is None
        
        if is_root:
             intentions_data = self.collect_all_intentions(self.node)
        else:
             intentions_data = [(self.node, i) for i in getattr(self.node, 'intentions', [])]
        
        for source_node, data in intentions_data:
             self.add_intention_to_ui(data['text'], data.get('status', 'active'), data.get('stats', {}), source_node)
             
        self.reorder_intentions()


    def collect_all_intentions(self, node):
        all_data = []
        # Own intentions (skip for root itself)
        if node.parent is not None:
            for i in getattr(node, 'intentions', []):
                all_data.append((node, i))
        
        # Children intentions
        for child in node.children:
            all_data.extend(self.collect_all_intentions(child))
        
        return all_data

    def save_intentions_to_node(self):
        # We need to distribute intentions back to their source nodes
        # Collect all nodes involved
        involved_nodes = set()
        if self.node.parent is None:
             # Recursively find all nodes
             def get_all(n):
                 if n.parent is not None:
                     involved_nodes.add(n)
                 for c in n.children: get_all(c)
             get_all(self.node)
        else:
             involved_nodes.add(self.node)
             
        # Clear their current intention lists locally before repopulating
        for n in involved_nodes:
            n.intentions = []
            
        # Repopulate from UI
        for i in range(self.intentions_list.count()):
            item = self.intentions_list.item(i)
            source_node = item.data(Qt.ItemDataRole.UserRole + 2)
            
            # Skip saving to root node itself
            if source_node and source_node.parent is None:
                 continue
                 
            if not source_node: 
                source_node = self.node # Fallback
            
            if source_node.parent is None:
                 continue # Double safety
            
            # If for some reason source_node is not in involved_nodes (unlikely), add it anyway
            data = {
                "text": item.data(Qt.ItemDataRole.UserRole + 3),
                "status": item.data(Qt.ItemDataRole.UserRole),
                "stats": item.data(Qt.ItemDataRole.UserRole + 1)
            }
            source_node.intentions.append(data)
            
        if self.state_manager:
            self.state_manager.save()

    def create_mini_stat_widget(self, label_text, value_text, color_hex, key=None):
        container = QWidget()
        container.setStyleSheet(f"background-color: #252530; border-radius: 4px;")
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(8, 6, 8, 6)
        v_layout.setSpacing(0)
        
        val_label = QLabel(value_text)
        val_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        val_label.setStyleSheet(f"color: {color_hex}; border: none;")
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if key:
            self.lbl_stats[key] = val_label
        
        lbl_label = QLabel(label_text.upper())
        lbl_label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        lbl_label.setStyleSheet("color: #666666; border: none;")
        lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        v_layout.addWidget(val_label)
        v_layout.addWidget(lbl_label)
        
        return container

    def add_divider(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333; margin-top: 10px; margin-bottom: 10px;")
        layout.addWidget(line)

    def remove_intention(self, item):
        # Archive stats before removing
        stats = item.data(Qt.ItemDataRole.UserRole + 1)
        source_node = item.data(Qt.ItemDataRole.UserRole + 2)
        
        # Determine which node to archive stats to
        target_node = source_node if source_node else self.node
        if target_node.parent is not None and stats:
            # Ensure archived_stats exists
            if not hasattr(target_node, 'archived_stats'):
                target_node.archived_stats = {"time": 0, "words": 0, "chars": 0}
            target_node.archived_stats["time"] += stats.get("time", 0)
            target_node.archived_stats["words"] += stats.get("words", 0)
            target_node.archived_stats["chars"] += stats.get("chars", 0)
        
        row = self.intentions_list.row(item)
        self.intentions_list.takeItem(row)
        if self.intentions_list.count() == 0:
            self.lbl_current_intention.setText("Ready to Focus")
            self.btn_complete.setEnabled(False)
        self.save_intentions_to_node()

    def complete_current_intention(self):
        # 1. Visual change for completion
        current_row = self.intentions_list.currentRow()
        if current_row < 0: return
        
        item = self.intentions_list.item(current_row)
        item.setData(Qt.ItemDataRole.UserRole, "completed")
        
        widget = self.intentions_list.itemWidget(item)
        if widget:
            lbl = widget.findChild(QLabel, "intention_text")
            if lbl:
                # Apply cross-out (strikethrough) and color change
                lbl.setStyleSheet("color: #00E676; border: none; background: transparent; text-decoration: line-through;")
                widget.setStyleSheet("background-color: rgba(0, 230, 118, 20); border-radius: 4px;")
        
        self.update_intention_tooltip(item)
        
        # 2. Re-order and Save
        self.reorder_intentions()
        self.save_intentions_to_node()
        
        # 3. Handle selection: Move to the first "active" intention automatically
        for i in range(self.intentions_list.count()):
            it = self.intentions_list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) != "completed":
                self.intentions_list.setCurrentRow(i)
                return
        
        self.intentions_list.setCurrentRow(-1) # Nothing active left

    def reorder_intentions(self):
        """Sorts intentions: Completed at TOP, Active at BOTTOM."""
        self._is_loading = True # Suppress focus start during re-sort
        
        # Store current state
        items_data = []
        current_item = self.intentions_list.currentItem()
        current_text = current_item.data(Qt.ItemDataRole.UserRole + 3) if current_item else None
        
        for i in range(self.intentions_list.count()):
            it = self.intentions_list.item(i)
            items_data.append({
                'text': it.data(Qt.ItemDataRole.UserRole + 3),
                'status': it.data(Qt.ItemDataRole.UserRole),
                'stats': it.data(Qt.ItemDataRole.UserRole + 1),
                'source': it.data(Qt.ItemDataRole.UserRole + 2)
            })
            
        # Sort: completed (0) comes before active (1)
        items_data.sort(key=lambda x: 0 if x['status'] == 'completed' else 1)
        
        # Rebuild
        self.intentions_list.clear()
        for d in items_data:
            self.add_intention_to_ui(d['text'], d['status'], d['stats'], d['source'])
            
        # Try to restore selection
        if current_text:
            for i in range(self.intentions_list.count()):
                if self.intentions_list.item(i).data(Qt.ItemDataRole.UserRole+3) == current_text:
                    self.intentions_list.setCurrentRow(i)
                    break
        
        self._is_loading = False


    def update_active_intention(self, current_item, previous_item):
        if current_item:
            is_completed = current_item.data(Qt.ItemDataRole.UserRole) == "completed"
            
            widget = self.intentions_list.itemWidget(current_item)
            text = ""
            if widget:
                lbl = widget.findChild(QLabel, "intention_text")
                if lbl:
                    text = lbl.text().replace("• ", "")
            
            self.lbl_current_intention.setText(text if text else "Intention selected")
            
            if is_completed:
                self.lbl_current_intention.setStyleSheet("color: #4CAF50; padding: 5px; font-weight: bold;")
                self.btn_complete.setEnabled(False)
                return 
            
            self.lbl_current_intention.setStyleSheet("color: #FF9800; padding: 5px; font-weight: bold;")
            self.btn_complete.setEnabled(True)
            
            # Start/Resume focus ONLY if not running
            # Flag check prevents auto-start on APP STARTUP
            if not self.pomodoro_session.is_running and not getattr(self, '_is_loading', False):
                 if self.pomodoro_session.phase == PomodoroPhase.FOCUS:
                      self.pomodoro_session.resume()
                 else:
                      self.pomodoro_session.start_focus()
                 self.focus_started.emit()

                 
        else:
            self.lbl_current_intention.setText("Ready to Focus")
            self.lbl_current_intention.setStyleSheet("color: #e0e0e0; padding: 5px;")
            self.btn_complete.setEnabled(False)

            
    def toggle_pause(self):
        self.afk_active = not self.afk_active
        self.pomodoro_session.afk_mode = self.afk_active # Sync back to global engine
        if self.afk_active:
            self.btn_afk.setText("STOP AFK")
            self.btn_afk.setToolTip("Stop AFK Focus and return to normal idle detection.")
        else:
            self.btn_afk.setText("AFK")
            self.btn_afk.setToolTip("Start AFK Focus: keep timer running while reading or researching.")

    def toggle_deep_focus(self):
        self.deep_focus_active = not self.deep_focus_active
        if not self.deep_focus_active:
             self.distraction_warning.hide()
        
    def add_allowed_window(self, title):
        if title not in self.node.allowed_windows:
            self.node.allowed_windows.append(title)
            self.state_manager.save()

    def update_ui(self):
        # 1. Update Stats
        self.active_tracker.update(force_active=self.afk_active)
        total_sec, active_sec = self.active_tracker.get_stats()
        words, chars = self.word_tracker.get_stats()
        
        if "total" in self.lbl_stats:
            self.lbl_stats["total"].setText(self.active_tracker.format_time(total_sec))
        if "active" in self.lbl_stats:
            self.lbl_stats["active"].setText(self.active_tracker.format_time(active_sec))
            
        if "words" in self.lbl_stats:
            self.lbl_stats["words"].setText(str(words))
        if "chars" in self.lbl_stats:
            self.lbl_stats["chars"].setText(str(chars))

        # Update Per-Intention Stats Deltas
        current_item = self.intentions_list.currentItem()
        is_focus = self.pomodoro_session.is_running and self.pomodoro_session.phase == PomodoroPhase.FOCUS
        # AFK Focus: Count as active even if idle_ms is high
        is_active = self.active_tracker.is_user_active() or self.afk_active

        # LOCKDOWN: Stop counting if node is already solved
        node_solved = getattr(self.node, 'status', 'neutral') == 'solved'

        if current_item and is_focus and is_active and not node_solved:
            stats = current_item.data(Qt.ItemDataRole.UserRole + 1)
            if stats:
                stats['time'] += max(0, active_sec - self.last_active_sec)
                stats['words'] += max(0, words - self.last_words)
                stats['chars'] += max(0, chars - self.last_chars)
                current_item.setData(Qt.ItemDataRole.UserRole + 1, stats)
                self.update_intention_tooltip(current_item)
        
        self.last_active_sec = active_sec
        self.last_words = words
        self.last_chars = chars
        
        # Update Cycle Logic (Refill at 8 hours)
        from Infrastructure.variables import CYCLE_TIME_LIMIT
        if is_focus and is_active and not node_solved:
             # Increment current node's cycle time
             if not hasattr(self.node, 'cycle_time'): self.node.cycle_time = 0
             if not hasattr(self.node, 'cycle_count'): self.node.cycle_count = 0
             
             self.node.cycle_time += 1
             
             if self.node.cycle_time >= CYCLE_TIME_LIMIT:
                  self.node.cycle_count += 1
                  self.node.cycle_time = max(0, self.node.cycle_time - CYCLE_TIME_LIMIT)
                  # Remote/Local Notification for cycle completion
                  if hasattr(self.window(), 'tray_manager'):
                      self.window().tray_manager.notify("Level Up!", f"You've completed an 8-hour block on '{self.node.label}'!")
        
        # Update Cycle UI
        if not hasattr(self.node, 'cycle_time'): self.node.cycle_time = 0
        if not hasattr(self.node, 'cycle_count'): self.node.cycle_count = 0
        
        cycle_perc = (self.node.cycle_time / CYCLE_TIME_LIMIT) * 100
        self.lbl_cycle_count.setText(f"Cycle {self.node.cycle_count}")
        self.lbl_cycle_perc.setText(f"{int(cycle_perc)}%")
        
        fill_width = int(80 * (cycle_perc / 100))
        self.cycle_fill.setFixedWidth(fill_width)
        
        # Periodic Auto-Save (Every ~30 seconds)
        if not hasattr(self, '_save_counter'): self._save_counter = 0
        self._save_counter += 1
        if self._save_counter >= 30:
            self.save_intentions_to_node()
            self._save_counter = 0

        # 2. Update Progress Circle
        if self.show_percentages:
            # Dynamically find the main root name
            main_root = self.roots[0] if self.roots else None
            if main_root:
                life_perc = calculate_node_percentage(main_root)
                self.life_circle.set_percentage(life_perc)
            
        # Ticking is now handled centrally by MainWindow.record_and_check
        # to ensure it never stops during UI transitions.
        
        # Check for Session End Transitions
        current_phase = self.pomodoro_session.phase
        finished = not self.pomodoro_session.is_running
        
        # 3. Handle Transitions
        # Store previous before capturing it for next tick
        prev = self.previous_phase
        
        # Determine if the session is actually COMPLETED (not just paused)
        is_completed = (self.pomodoro_session.total_seconds > 0 and 
                        self.pomodoro_session.elapsed_seconds >= self.pomodoro_session.total_seconds)
        
        # Track previous phase, but treat IDLE and PAUSED as distinct from a running phase
        self.previous_phase = self.pomodoro_session.phase if self.pomodoro_session.is_running else PomodoroPhase.IDLE
        finished = not self.pomodoro_session.is_running

        if prev == PomodoroPhase.FOCUS and finished and is_completed:
             # Focus ended - Show Popup
             if hasattr(self.parent(), 'window') and hasattr(self.parent().window(), 'orchestrator'):
                 self.parent().window().orchestrator.show_focus_end()
             elif hasattr(self.window(), 'orchestrator'):
                 self.window().orchestrator.show_focus_end()
                 
        elif prev == PomodoroPhase.BREAK and finished and is_completed:
             # Break ended - Trigger break end (Bring to top)
             if hasattr(self.window(), 'orchestrator'):
                 self.window().orchestrator.show_break_end()
            
        # Format timer MM:SS
        time_str = self.pomodoro_session.get_time_string()
        self.lbl_timer.setText(time_str)
        
        # Update Status Label and Colors
        phase = self.pomodoro_session.phase
        is_running = self.pomodoro_session.is_running
        
        if phase == PomodoroPhase.FOCUS:
            self.lbl_status.setText(f"FOCUS • Cycle {self.pomodoro_session.cycles_completed + 1}")
            self.lbl_timer.setStyleSheet(f"color: {PRIMARY_COLOR};") # Orange
            self.lbl_status.setStyleSheet(f"color: {PRIMARY_COLOR}; letter-spacing: 2px; font-weight: bold;")
        elif phase == PomodoroPhase.BREAK:
            # Show elapsed time for break (Counting UP)
            elapsed_str = self.pomodoro_session.get_time_string() # This now returns elapsed for break too
            break_type = "Long Break" if getattr(self.pomodoro_session, 'is_long_break', False) else "Short Break"
            self.lbl_status.setText(f"{break_type} (+ {elapsed_str})")
            self.lbl_timer.setText(elapsed_str) # redundant but ensures consistency
            
            self.lbl_timer.setStyleSheet("color: #4CAF50;") # Green
            self.lbl_status.setStyleSheet("color: #4CAF50; letter-spacing: 2px; font-weight: bold;")
        else:
            self.lbl_status.setText("IDLE")
            self.lbl_timer.setStyleSheet("color: #666;")
            self.lbl_status.setStyleSheet("color: #666; letter-spacing: 2px;") # Kept original line
            
        # 4. Distraction Control Monitoring (Every 1 second)
        if self.deep_focus_active and self.pomodoro_session.is_running and self.pomodoro_session.phase == PomodoroPhase.FOCUS:
             try:
                 # gw.getActiveWindow() can be heavy, but it's only once per second here
                 active_win = gw.getActiveWindow()
                 title = active_win.title if active_win and active_win.title else ""
                 
                 # Check whitelists
                 is_internal = any(w in title for w in self.INTERNAL_WHITELIST)
                 is_allowed = any(w == title for w in self.node.allowed_windows)
                 
                 if not is_internal and not is_allowed and title:
                      if not self.distraction_warning.isVisible():
                           self.distraction_warning.show_warning(title)
                 else:
                      if self.distraction_warning.isVisible():
                           self.distraction_warning.hide()
             except Exception as e:
                 print(f"PomodoroWindow: Error in distraction control: {e}")
        elif self.distraction_warning.isVisible():
             self.distraction_warning.hide()

        # 5. Update Control Button States
        is_running = self.pomodoro_session.is_running
        self.btn_afk.setEnabled(is_running)
        self.btn_deep_focus.setEnabled(is_running)
        self.btn_progress.setEnabled(is_running)
        
        if self.afk_active:
            self.btn_afk.setText("STOP AFK")
            self.btn_afk.setStyleSheet(self.btn_afk.styleSheet().replace("#f39c12", "#27ae60").replace("#e67e22", "#2ecc71"))
        else:
            self.btn_afk.setText("AFK")
            self.btn_afk.setStyleSheet(self.btn_afk.styleSheet().replace("#27ae60", "#f39c12").replace("#2ecc71", "#e67e22"))

        # Deep Focus Button Style
        if self.deep_focus_active:
            self.btn_deep_focus.setText("EXIT DEEP")
            self.btn_deep_focus.setStyleSheet(self.btn_deep_focus.styleSheet().replace("#c0392b", "#1a1a1a").replace("#e74c3c", "#333"))
        else:
            self.btn_deep_focus.setText("Deep Focus")
            self.btn_deep_focus.setStyleSheet(self.btn_deep_focus.styleSheet().replace("#1a1a1a", "#c0392b").replace("#333", "#e74c3c"))

        # 6. Update Restrict Button Style
        phase = self.pomodoro_session.phase
        if not self.pomodoro_session.restriction_armed:
            self.btn_restrict.setText("Restrict")
            self.btn_restrict.setStyleSheet("background-color: #2c3e50; color: white; border: 1px solid #34495e; border-radius: 4px; padding: 8px; font-weight: bold;")
        else:
            if phase == PomodoroPhase.FOCUS:
                self.btn_restrict.setText("ACTIVE")
                self.btn_restrict.setStyleSheet(f"background-color: {DANGER_COLOR}; color: white; border: 2px solid #ff0000; border-radius: 4px; padding: 8px; font-weight: bold;")
            elif phase == PomodoroPhase.BREAK:
                self.btn_restrict.setText("STANDBY")
                self.btn_restrict.setStyleSheet("background-color: #f39c12; color: white; border: 1px solid #e67e22; border-radius: 4px; padding: 8px; font-weight: bold;")
            else:
                self.btn_restrict.setText("ARMED")
                self.btn_restrict.setStyleSheet("background-color: #c0392b; color: white; border: 1px solid #a93226; border-radius: 4px; padding: 8px; font-weight: bold;")

        # 4. Update Solved Button
        self.update_solved_button()

        # 4. Check for completion dialogs (if you want to implement them here)
        # For now, just relying on visual timer updates.



    def on_mark_solved(self):
        self.mark_solved_requested.emit(self.node)

    def update_solved_button(self):
        if not self.show_percentages:
            return
            
        status = getattr(self.node, 'status', 'neutral')
        if status == "solved":
            self.btn_mark_solved.setText("✓ Solved")
            self.btn_mark_solved.setStyleSheet("background-color: #1b5e20; border: 1px solid #4caf50; color: #ffffff; font-weight: bold;")
        else:
            self.btn_mark_solved.setText("✓ Mark Solved")
            self.btn_mark_solved.setStyleSheet("background-color: #2a2a35; border: 1px solid #3a3a45; color: #a5d6a7;")

    def moveEvent(self, event):
        self.moved.emit()
        super().moveEvent(event)

    # --- Restriction Logic ---
    def handle_restrict_click(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QLineEdit, QPushButton, QHBoxLayout, QListWidgetItem
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Restriction Keywords")
        dialog.setFixedWidth(300)
        dialog.setStyleSheet(f"background-color: {BG_COLOR}; color: white;")
        d_layout = QVBoxLayout(dialog)
        
        kw_list = QListWidget()
        kw_list.addItems(self.restricted_keywords)
        kw_list.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #333;")
        d_layout.addWidget(kw_list)
        
        input_row = QHBoxLayout()
        new_kw = QLineEdit()
        new_kw.setPlaceholderText("keyword...")
        new_kw.setStyleSheet("background-color: #222; border: 1px solid #444; color: white; padding: 5px;")
        input_row.addWidget(new_kw)
        
        add_btn = QPushButton("Add")
        add_btn.setStyleSheet("background-color: #2a2a35; padding: 5px;")
        input_row.addWidget(add_btn)
        d_layout.addLayout(input_row)
        
        def add_kw():
            txt = new_kw.text().strip().lower()
            if txt and txt not in self.restricted_keywords:
                self.restricted_keywords.append(txt)
                kw_list.addItem(txt)
                new_kw.clear()
        
        add_btn.clicked.connect(add_kw)
        new_kw.returnPressed.connect(add_kw)
        
        is_focus_active = self.pomodoro_session.phase == PomodoroPhase.FOCUS and self.pomodoro_session.is_running

        del_btn = QPushButton("Remove Selected")
        del_btn.setStyleSheet("background-color: #442222; padding: 5px;")
        if is_focus_active:
            del_btn.setEnabled(False)
            del_btn.setToolTip("Cannot remove keywords while focus session is running.")
        
        def del_kw():
            for item in kw_list.selectedItems():
                self.restricted_keywords.remove(item.text())
                kw_list.takeItem(kw_list.row(item))
        del_btn.clicked.connect(del_kw)
        d_layout.addWidget(del_btn)

        # Action Buttons Row (Disarm + Confirm)
        action_row = QHBoxLayout()
        if self.pomodoro_session.restriction_armed:
            disarm_btn = QPushButton("DISARM")
            disarm_btn.setStyleSheet("background-color: #555; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
            if is_focus_active:
                disarm_btn.setEnabled(False)
                disarm_btn.setToolTip("Restriction cannot be disarmed while focus session is running.")
            disarm_btn.clicked.connect(lambda: (setattr(self.pomodoro_session, 'restriction_armed', False), self._save_restriction_config(), dialog.accept()))
            action_row.addWidget(disarm_btn)
            
        confirm_btn = QPushButton("CONFIRM & ARM" if not self.pomodoro_session.restriction_armed else "UPDATE & KEEP ARMED")
        confirm_btn.setStyleSheet(f"background-color: {DANGER_COLOR}; color: white; padding: 10px; font-weight: bold; border-radius: 4px;")
        confirm_btn.clicked.connect(lambda: (setattr(self.pomodoro_session, 'restriction_armed', True), self._save_restriction_config(), dialog.accept()))
        action_row.addWidget(confirm_btn)
        
        d_layout.addLayout(action_row)
        
        dialog.exec()
        self.update_ui()

    def _check_restrictions(self):
        if not self.pomodoro_session.restriction_armed: return
        if self.pomodoro_session.phase != PomodoroPhase.FOCUS: return
        if not self.pomodoro_session.is_running: return
        
        try:
            import pygetwindow as gw
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if not window.title: continue
                title = window.title.lower()
                for kw in self.restricted_keywords:
                    if kw in title:
                        print(f"[RESTRICT] Closing restricted window: {window.title}")
                        try:
                            window.close()
                        except:
                            pass
                        break
        except Exception as e:
            print(f"Restriction Error: {e}")

    def _load_restriction_config(self):
        import json
        try:
            path = os.path.join("progress_logs", "restrict_config.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.restricted_keywords = data.get("keywords", self.restricted_keywords)
                    # Sync armed state to engine
                    if "armed" in data:
                        self.pomodoro_session.restriction_armed = data.get("armed", False)
        except:
            pass

    def _save_restriction_config(self):
        import json
        try:
            os.makedirs("progress_logs", exist_ok=True)
            path = os.path.join("progress_logs", "restrict_config.json")
            with open(path, 'w') as f:
                json.dump({
                    "keywords": self.restricted_keywords,
                    "armed": self.pomodoro_session.restriction_armed
                }, f)
        except:
            pass

    def handle_resolution_click(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")
