from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame, QPushButton, QLabel
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
import keyboard
import datetime

# --- Hexagonal Imports ---
from Infrastructure.variables import *
from Adapters.Sensors.idle_detector import IdleDetector
from Adapters.Sensors.keyboard_listener import KeyboardListener
from Core.Services.timer_engine import TimerEngine, PomodoroPhase
from Core.Services.history_recorder import HistoryRecorder
from Core.Services.node_service import NodeService
from Application.app_initializer import AppInitializer
from Application.orchestrator import Orchestrator
from Adapters.Persistence.json_repository import JsonRepository
from Adapters.UI.tray_adapter import WindowTrayManager
from PyQt6.QtGui import QIcon

# --- UI Layout Sub-components ---
from Adapters.UI.Windows.tree_canvas import Tree
from Adapters.UI.Windows.dashboard_view import PomodoroWindow
from Adapters.UI.Windows.analytics_window import GraphsWidget
from Adapters.UI.Windows.mini_status_bar import MiniStatusBar
from Adapters.UI.Windows.typewriter_window import TypeWriterWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Evidence of Growth")
        self.resize(1000, 800)
        
        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Infrastructure", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Always on Top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        # --- Global Stylesheet ---
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG_COLOR};
                color: {TEXT_COLOR};
                font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
            }}
            QSplitter::handle {{
                background-color: {BORDER_COLOR};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {BG_COLOR};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER_COLOR};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {PRIMARY_COLOR};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # 1. Initialize Adapters (Sensors / Storage)
        self.idle_detector = IdleDetector()
        self.keyboard_listener = KeyboardListener()
        self.repository = JsonRepository()
        
        self.idle_detector.start()
        self.keyboard_listener.start()
        
        # 2. Initialize Core Services
        self.timer_engine = TimerEngine(
            focus_min=FOCUS_TIME,
            short_break_min=SHORT_BREAK_TIME,
            long_break_min=LONG_BREAK_TIME,
            long_break_interval=LONG_BREAK_INTERVAL
        )
        self.history_recorder = HistoryRecorder(self.idle_detector, self.keyboard_listener)
        
        # 3. Initialize Application Layer (Bootstrapper / Orchestrator)
        self.bootstrapper = AppInitializer(self, self.repository, self.history_recorder)
        self.bootstrapper.initialize()
        
        self.orchestrator = Orchestrator(self)
        
        # 4. Initialize Infrastructure (Tray / Hotkeys)
        self._force_quit = False
        self.tray_manager = WindowTrayManager(self)
        try:
            # Safer hotkey implementation: Only trigger if BOTH ctrl and alt are physically pressed
            def safe_toggle_e():
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt'):
                    QTimer.singleShot(0, self.toggle_visibility)
            
            def safe_toggle_p():
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt'):
                    QTimer.singleShot(0, self.toggle_graphs_window)

            def safe_toggle_n():
                if keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt'):
                    QTimer.singleShot(0, self.toggle_typewriter)

            keyboard.on_press_key("e", lambda _: safe_toggle_e())
            keyboard.on_press_key("p", lambda _: safe_toggle_p())
            keyboard.on_press_key("n", lambda _: safe_toggle_n())
        except Exception as e:
            print(f"Failed to bind global hotkeys: {e}")

        # 5. Initialize Managers
        self.problems_manager = NodeService(TREE_DATA_PATH, "My Problems")
        self.values_manager = NodeService(VALUES_DATA_PATH, "My Values")
        
        # Analytics Window Setup
        self.graphs_window = GraphsWidget(self.history_recorder, self.timer_engine)
        self.graphs_window.setWindowTitle("Focus Statistics")
        self.graphs_window.resize(400, 600)
        self.graphs_window.hide()
        
        # Typewriter (The Mechanical Scribe) Integration
        self.typewriter_window = TypeWriterWindow()
        self.typewriter_window.hide()
        
        # Mini Status Bar
        self.status_bar = MiniStatusBar()
        self.status_bar.show()
        self.status_bar.visibility_changed.connect(lambda visible: self.tray_manager.status_bar_action.setChecked(visible))
        
        if hasattr(self, 'status_bar'):
             self.status_bar.add_intention_requested.connect(self.handle_mini_add_intention)
             self.status_bar.complete_intention_requested.connect(self.handle_mini_complete_intention)
             self.status_bar.clear_intentions_requested.connect(self.handle_mini_clear_intentions)
             if hasattr(self.status_bar, 'test_milestone_requested'):
                  self.status_bar.test_milestone_requested.connect(self.handle_mini_test_milestone)
        
        # Milestone tracking state
        self._milestone_word_last = 0
        self._milestone_char_last = 0
        self._milestone_time_sec = 0
        
        # Main Layout Setup
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet(f"background-color: {BG_COLOR};")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Pane (Tree)
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_header = QWidget()
        left_header.setStyleSheet(f"background-color: {BG_COLOR}; border-bottom: 1px solid #333;") 
        lh_layout = QHBoxLayout(left_header)
        lh_layout.setContentsMargins(15, 8, 15, 8)
        lh_layout.setSpacing(0)

        # Floating Pill Container
        self.switcher_container = QFrame()
        self.switcher_container.setObjectName("SwitcherContainer")
        self.switcher_container.setStyleSheet(f"""
            QFrame#SwitcherContainer {{
                background-color: #2a2a2a;
                border-radius: 18px;
                border: 1px solid #333;
            }}
        """)
        sc_layout = QHBoxLayout(self.switcher_container)
        sc_layout.setContentsMargins(4, 4, 4, 4)
        sc_layout.setSpacing(4)

        self.btn_problems = QPushButton("My Problems")
        self.btn_problems.setCheckable(True)
        self.btn_problems.setChecked(True)
        self.btn_problems.setStyleSheet(self.get_switcher_style())
        self.btn_problems.clicked.connect(self.switch_to_problems)
        sc_layout.addWidget(self.btn_problems)

        self.btn_values = QPushButton("My Values")
        self.btn_values.setCheckable(True)
        self.btn_values.setStyleSheet(self.get_switcher_style())
        self.btn_values.clicked.connect(self.switch_to_values)
        sc_layout.addWidget(self.btn_values)

        lh_layout.addWidget(self.switcher_container)
        lh_layout.addStretch()
        
        self.btn_left_expand = QPushButton("⛶")
        self.btn_left_expand.setCheckable(True)
        self.btn_left_expand.setStyleSheet(f"""
            QPushButton {{
                background-color: {CARD_BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                padding: 4px 8px;
                color: {TEXT_COLOR};
            }}
            QPushButton:hover {{
                background-color: {BORDER_COLOR};
            }}
        """)
        self.btn_left_expand.clicked.connect(self.handle_left_expand)
        lh_layout.addWidget(self.btn_left_expand)
        
        left_layout.addWidget(left_header)
        self.tree = Tree(state_manager=self.problems_manager, show_percentages=True)
        self.tree.node_double_clicked.connect(self.show_pomodoro)
        left_layout.addWidget(self.tree)
        self.splitter.addWidget(self.left_container)
        
        # Right Pane (Dashboard)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_placeholder = QLabel("Select a node to focus")
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_placeholder.setStyleSheet("color: #666; font-size: 14pt;")
        self.right_layout.addWidget(self.lbl_placeholder)
        self.splitter.addWidget(self.right_container)
        
        self.splitter.setSizes([600, 400])
        main_layout.addWidget(self.splitter)
        
        self.current_pomodoro_view = None

        # Start with default node
        initial_node = self.tree.state_manager.roots[0] if self.tree.state_manager.roots else None
        if initial_node:
             self.show_pomodoro(initial_node)

        # 6. Start Heartbeat Loop (1Hz)
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.record_and_check)
        self.heartbeat_timer.start(1000)

    def show_pomodoro(self, node):
        if self.current_pomodoro_view:
            if hasattr(self.current_pomodoro_view, 'save_intentions_to_node'):
                self.current_pomodoro_view.save_intentions_to_node()
            self.right_layout.removeWidget(self.current_pomodoro_view)
            self.current_pomodoro_view.deleteLater()
            self.current_pomodoro_view = None

        self.lbl_placeholder.hide()
        self.current_pomodoro_view = PomodoroWindow(
            node, 
            self.tree.state_manager.roots, 
            self.idle_detector, 
            self.keyboard_listener, 
            state_manager=self.tree.state_manager,
            pomodoro_session=self.timer_engine,
            show_percentages=self.tree.show_percentages,
            parent=self.right_container
        )
        
        self.current_pomodoro_view.setWindowFlags(Qt.WindowType.Widget)
        self.current_pomodoro_view.toggle_expand_requested.connect(self.handle_expand_toggle)
        self.current_pomodoro_view.close_requested.connect(self.handle_close_pomodoro)
        self.current_pomodoro_view.mark_solved_requested.connect(self.handle_node_solved)
        self.current_pomodoro_view.toggle_graphs_requested.connect(self.toggle_graphs_window)
        self.current_pomodoro_view.focus_started.connect(self.orchestrator.handle_focus_start)

        self.right_layout.addWidget(self.current_pomodoro_view)
        self.current_pomodoro_view.show()
        
        sizes = self.splitter.sizes()
        if sizes[1] == 0:
             self.splitter.setSizes([600, 400])
        
        self.btn_left_expand.setChecked(False)

    def get_switcher_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 14px;
                padding: 6px 16px;
                color: #888;
                font-size: 9pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #fff;
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QPushButton:checked {{
                background-color: {PRIMARY_COLOR};
                color: #000;
                font-weight: 800;
            }}
        """

    def switch_to_problems(self):
        if self.tree.state_manager == self.problems_manager:
            return # Already on Problems, do nothing

        # Save current state (switching from values)
        self.tree.save_state()

        self.btn_problems.setChecked(True)
        self.btn_values.setChecked(False)
        self.tree.state_manager = self.problems_manager
        self.tree.perspective_name = "problems"
        self.tree.show_percentages = True
        self.tree.build_and_layout()
        
        # Restore state from persistence
        self.tree.load_initial_view()

        # PERSIST DASHBOARD: Keep it open on the current node even if switching trees.
        # The user wants to stay focused on the task while browsing.
        pass

    def switch_to_values(self):
        if self.tree.state_manager == self.values_manager:
            return # Already on Values, do nothing

        # Save current state (switching from problems)
        self.tree.save_state()

        self.btn_values.setChecked(True)
        self.btn_problems.setChecked(False)
        self.tree.state_manager = self.values_manager
        self.tree.perspective_name = "values"
        self.tree.show_percentages = False
        self.tree.build_and_layout()
        
        # Restore state from persistence
        self.tree.load_initial_view()

        # PERSIST DASHBOARD: Keep it open on the current node even if switching trees.
        pass

    def handle_left_expand(self):
        sizes = self.splitter.sizes()
        total_width = sum(sizes)
        if sizes[1] > 0:
            self.splitter.setSizes([total_width, 0])
        else:
            self.splitter.setSizes([int(total_width * 0.6), int(total_width * 0.4)])
        
    def handle_expand_toggle(self):
        sizes = self.splitter.sizes()
        total_width = sum(sizes)
        if sizes[0] >= 50:
            self.splitter.setSizes([0, total_width])
        else:
            self.splitter.setSizes([int(total_width * 0.6), int(total_width * 0.4)])

    def handle_close_pomodoro(self):
        if self.current_pomodoro_view:
            self.right_layout.removeWidget(self.current_pomodoro_view)
            self.current_pomodoro_view.deleteLater()
            self.current_pomodoro_view = None
        self.lbl_placeholder.show()
        
    def handle_node_solved(self):
        if self.tree.active_node:
            current_status = getattr(self.tree.active_node, 'status', 'neutral')
            new_status = "neutral" if current_status == "solved" else "solved"
            self.tree.state_manager.update_node_status(self.tree.active_node, new_status)
            self.tree.build_and_layout()

    def show_graphs_window(self):
        if self.graphs_window:
            # Force "Small View" (non-maximized)
            self.graphs_window.setWindowState(self.graphs_window.windowState() & ~Qt.WindowState.WindowMaximized)
            self.graphs_window.showNormal()
            self.graphs_window.resize(600, 400) # Force a standard small size
            self.graphs_window.show()
            self.graphs_window.raise_()
            self.graphs_window.activateWindow()

    def toggle_graphs_window(self):
        if not self.graphs_window:
            return
            
        # If it's visible and NOT minimized, hide it. 
        # If it's minimized or hidden, show it as small.
        if self.graphs_window.isVisible() and not self.graphs_window.isMinimized():
            self.graphs_window.hide()
        else:
            self.show_graphs_window()

    def record_and_check(self):
        try:
            # 1. Autosave Heartbeat (Every 60 seconds)
            if not hasattr(self, '_autosave_tick'):
                self._autosave_tick = 0
            self._autosave_tick += 1
            if self._autosave_tick >= 60:
                self._autosave_tick = 0
                if hasattr(self, 'bootstrapper'):
                    self.bootstrapper.autosave()

            # 2. Update active time sensors
            afk = self.timer_engine.afk_mode
            is_active = self.idle_detector.is_user_active() or afk
            self.idle_detector.update(force_active=afk)
            
            # --- Synchronized Heartbeat ---
            if self.timer_engine.phase == PomodoroPhase.FOCUS:
                if not is_active:
                    self.timer_engine.pause()
                else:
                    # Focus continues as long as user is active, no matter if intention is selected
                    self.timer_engine.resume()
            
            # 3. Time-Series Context Recording
            # Persist node label based on the CURRENT NODE, not timer state.
            # This prevents spurious vertical lines when timer pauses/resumes on the same node.
            current_label = None
            intention_label = None
            if self.current_pomodoro_view:
                node = self.current_pomodoro_view.node
                current_label = node.label if hasattr(node, 'label') else str(node)
                # Skip root node labels
                if current_label in ("My Problems", "My Values"):
                    current_label = None
                
                # Extract Intention Label
                item = self.current_pomodoro_view.intentions_list.currentItem()
                if item:
                    intention_label = item.data(Qt.ItemDataRole.UserRole + 3)
                
            self.history_recorder.record(node_label=current_label, intention_label=intention_label)
            
            # 4. Global Timer Ticking
            self.timer_engine.tick()

            # --- Mini Status Bar Update ---
            if hasattr(self, 'status_bar'):
                t_str = self.timer_engine.get_time_string()
                
                # Determine Color based on Phase
                phase = self.timer_engine.phase
                if phase == PomodoroPhase.FOCUS:
                    p_color = PRIMARY_COLOR
                elif phase == PomodoroPhase.BREAK:
                    p_color = SECONDARY_COLOR
                else:
                    p_color = "rgba(255, 255, 255, 0.1)"
                
                # Fetch internal word tracker stats
                daily_w, daily_c = self.keyboard_listener.get_stats()
                sess_w, sess_c = self.keyboard_listener.get_session_stats()
                
                # --- Milestone Celebrations ---
                if self.timer_engine.phase == PomodoroPhase.FOCUS and self.timer_engine.is_running:
                    # 1. 100 Word Milestone
                    if sess_w > 0 and sess_w // 100 > self._milestone_word_last // 100:
                         self.status_bar.trigger_celebration("🏆 100 Words Reached!")
                    self._milestone_word_last = sess_w
                    
                    # 2. 1000 Character Milestone
                    if sess_c > 0 and sess_c // 1000 > self._milestone_char_last // 1000:
                         self.status_bar.trigger_celebration("✨ 1000 Chars Milestone!")
                    self._milestone_char_last = sess_c
                    
                    # 3. 10 Minute Milestone
                    if self.timer_engine.elapsed_seconds > 0 and self.timer_engine.elapsed_seconds % 600 == 0:
                         self.status_bar.trigger_celebration("🧘 10 Min Deep Focus!")
                
                # Update Intention Text from synchronized labels
                self.status_bar.update_state(
                    timer_text=t_str,
                    intention_text=intention_label if intention_label else current_label,
                    phase_color=p_color,
                    is_running=self.timer_engine.is_running,
                    words=daily_w,
                    chars=daily_c,
                    session_words=sess_w,
                    session_chars=sess_c
                )
                
                # Sync Remote List if visible
                if self.status_bar.remote.isVisible() and self.current_pomodoro_view:
                    node = self.current_pomodoro_view.node
                    self.status_bar.remote.update_list(getattr(node, 'intentions', []))
            
            # 5. Midnight Transition Check
            today = datetime.date.today().isoformat()
            if hasattr(self, 'bootstrapper') and self.bootstrapper.last_reset_date != today:
                self.bootstrapper.perform_runtime_reset()
        except Exception as e:
            print(f"MainWindow: Error in heartbeat: {e}")

    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.show()
            self.activateWindow()
            self.raise_()

    def toggle_typewriter(self):
        if not hasattr(self, 'typewriter_window'):
            return
            
        if self.typewriter_window.isVisible():
            self.typewriter_window.save_text()
            self.typewriter_window.hide()
        else:
            self.typewriter_window.showFullScreen()
            self.typewriter_window.raise_()
            self.typewriter_window.activateWindow()
            self.typewriter_window.editor.setFocus()


    def closeEvent(self, event):
        if not getattr(self, '_force_quit', False):
            self.hide()
            event.ignore()
            return

        # --- Hardcore Enforcement: Shutdown if quit during focus ---
        if self.timer_engine.phase == PomodoroPhase.FOCUS and self.timer_engine.is_running and self.timer_engine.restriction_armed:
            import os
            print("[HARDCORE] Focus session active and restricted. Triggering system shutdown penalty.")
            os.system("shutdown /s /t 0")
            # Usually shutdown takes effect immediately, but ensure we don't proceed with normal quit
            return

        if self.current_pomodoro_view:
            self.current_pomodoro_view.save_intentions_to_node()
            
        if hasattr(self, 'bootstrapper'):
            # This handles Stats, History, Tree State, and Perspective Data
            self.bootstrapper.save_on_exit()
            
        super().closeEvent(event)
        QCoreApplication.quit()

    # --- Mini Status Bar Relay Methods ---
    def handle_mini_add_intention(self):
        """Bring app to front and focus the intention input."""
        self.toggle_visibility() # Show app
        if self.current_pomodoro_view:
             self.current_pomodoro_view.intention_input.setFocus()

    def handle_mini_test_milestone(self):
        """Manually trigger a celebration for testing."""
        if hasattr(self, 'status_bar'):
             self.status_bar.trigger_celebration("🚀 Test Milestone!")

    def handle_mini_complete_intention(self):
        """Relay complete command to active view."""
        if self.current_pomodoro_view:
             self.current_pomodoro_view.complete_current_intention()

    def handle_mini_clear_intentions(self):
        """Relay clear command to active view."""
        if self.current_pomodoro_view:
             self.current_pomodoro_view.clear_intentions()