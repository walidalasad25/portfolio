from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect, QLineEdit, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QPixmap, QFont
import os, random
from Infrastructure.variables import PRIMARY_COLOR, BASE_DIR

class MilestoneParticle(QLabel):
    def __init__(self, parent, start_pos):
        super().__init__(parent)
        self.setText(random.choice(["🪙", "✨", "💰", "🌟", "⭐", "💍"]))
        size = random.randint(12, 22)
        self.setStyleSheet(f"background: transparent; font-size: {size}pt;")
        self.move(int(start_pos.x()), int(start_pos.y()))
        
        # Physics setup: High energy burst
        self.vx = random.uniform(-20, 20)
        self.vy = random.uniform(-25, -5) 
        self.gravity = 0.8
        self.opacity = 1.0
        self.life = 1.0 # 100% life
        
        self.show()

    def update_physics(self):
        self.vx *= 0.98 # Friction
        self.vy += self.gravity
        self.move(int(self.x() + self.vx), int(self.y() + self.vy))
        
        self.life -= 0.02
        if self.life <= 0:
            self.hide()
            self.deleteLater()
            return False
        
        # Fade out
        self.opacity = self.life
        alpha = int(self.opacity * 255)
        self.setStyleSheet(f"background: transparent; font-size: 14pt; color: rgba(255,215,0,{alpha});")
        return True

class IntentionRemote(QWidget):
    task_added = pyqtSignal(str)
    task_completed = pyqtSignal(int) # index
    
    def __init__(self, parent=None):
        super().__init__(None) # Standalone window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 400)
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Glass Frame
        self.frame = QFrame()
        self.frame.setObjectName("RemoteFrame")
        from Infrastructure.variables import BG_COLOR, PRIMARY_COLOR, CARD_BG_COLOR
        self.frame.setStyleSheet(f"""
            QFrame#RemoteFrame {{
                background-color: rgba(30, 30, 30, 245);
                border: 1px solid rgba(255, 152, 0, 0.3);
                border-radius: 20px;
            }}
            QListWidget {{
                background: transparent;
                border: none;
                color: white;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 152, 0, 0.2);
                border-left: 3px solid {PRIMARY_COLOR};
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                padding: 8px;
                color: white;
                font-size: 10pt;
            }}
        """)
        
        self.container_layout = QVBoxLayout(self.frame)
        self.container_layout.setContentsMargins(15, 15, 15, 15)
        self.container_layout.setSpacing(10)
        
        header = QLabel("What I am willing to do")
        header.setStyleSheet("color: rgba(255,255,255,0.5); font-weight: bold; font-size: 8pt; text-transform: uppercase;")
        self.container_layout.addWidget(header)
        
        # Add Area
        add_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("New intention...")
        self.input.returnPressed.connect(self.on_add)
        add_layout.addWidget(self.input)
        
        btn_add = QPushButton("+")
        btn_add.setFixedSize(30, 30)
        btn_add.setStyleSheet(f"background: {PRIMARY_COLOR}; color: black; font-weight: bold; border-radius: 15px;")
        btn_add.clicked.connect(self.on_add)
        add_layout.addWidget(btn_add)
        self.container_layout.addLayout(add_layout)
        
        # List Area
        self.list = QListWidget()
        self.container_layout.addWidget(self.list)
        
        self.layout.addWidget(self.frame)
        
        # Auto-focus input when shown
    def showEvent(self, event):
        self.input.setFocus()
        super().showEvent(event)

    def on_add(self):
        text = self.input.text().strip()
        if text:
            self.task_added.emit(text)
            self.input.clear()

    def update_list(self, intentions):
        """Update the UI list from data."""
        self.list.clear()
        for i, task in enumerate(intentions):
            item = QListWidgetItem(self.list)
            text = task.get('text', '')
            status = task.get('status', 'active')
            
            # Simple item widget with complete button
            widget = QWidget()
            w_layout = QHBoxLayout(widget)
            w_layout.setContentsMargins(5, 2, 5, 2)
            
            lbl = QLabel(text)
            lbl.setStyleSheet("color: white;" if status != "completed" else "color: #4CAF50; text-decoration: line-through;")
            w_layout.addWidget(lbl)
            w_layout.addStretch()
            
            if status != "completed":
                btn = QPushButton("✓")
                btn.setFixedSize(24, 24)
                btn.setStyleSheet("background: rgba(76, 175, 80, 0.2); color: #4CAF50; border-radius: 12px; border: 1px solid rgba(76, 175, 80, 0.3);")
                # closure for capture
                idx = i
                btn.clicked.connect(lambda _, x=idx: self.task_completed.emit(x))
                w_layout.addWidget(btn)
                
            item.setSizeHint(widget.sizeHint())
            self.list.setItemWidget(item, widget)

    def leaveEvent(self, event):
        # Optional: Close on mouse leave if desired, or keep open
        pass
        
    def focusOutEvent(self, event):
        self.hide() # Close when clicking elsewhere
        super().focusOutEvent(event)

class MiniStatusBar(QWidget):
    close_requested = pyqtSignal()
    visibility_changed = pyqtSignal(bool)
    
    # Intention Actions
    add_intention_requested = pyqtSignal()
    complete_intention_requested = pyqtSignal()
    clear_intentions_requested = pyqtSignal()
    test_milestone_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # The Remote Window instance
        self.remote = IntentionRemote(self)
        self.remote.hide()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.drag_position = QPoint()
        self.particles = []
        
        self.init_ui()
        # The window must be large enough for particles to fly, 
        # but the layout will keep the bar itself compact.
        self.resize(800, 300) 
        
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Glass Container (This is the ACTUAL bar)
        self.container = QFrame()
        self.container.setObjectName("GlassContainer")
        self.container.setFixedHeight(42) # Only fix height, allow width to be dynamic
        self.container.setMinimumWidth(220) # Minimum base width
        
        # Move glow to the internal container
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(20)
        self.glow.setColor(QColor(PRIMARY_COLOR))
        self.glow.setOffset(0, 0)
        self.glow.setEnabled(False)
        self.container.setGraphicsEffect(self.glow)
        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(15, 0, 15, 0)
        self.container_layout.setSpacing(12)
        
        self.main_layout.addWidget(self.container)
        
        # Ensure the parent widget itself is totally invisible
        self.setStyleSheet("background: transparent; border: none;")
        
        # App Icon
        self.lbl_icon = QLabel()
        icon_path = os.path.join(BASE_DIR, "Infrastructure", "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.lbl_icon.setPixmap(pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_icon.setText("🌱") # Fallback
        self.lbl_icon.setStyleSheet("background: transparent;")
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.container_layout.addWidget(self.lbl_icon)
        
        # Timer Label
        self.lbl_timer = QLabel("00:00")
        self.lbl_timer.setStyleSheet("""
            color: #ffffff;
            font-size: 11pt;
            font-weight: bold;
            font-family: 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        """)
        self.lbl_timer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.container_layout.addWidget(self.lbl_timer)
        
        # Separator
        self.sep = QFrame()
        self.sep.setFixedWidth(1)
        self.sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); margin: 8px 0;")
        self.container_layout.addWidget(self.sep)
        
        # Intention Text (Non-interactive display)
        self.btn_intention = QLabel("Planting a seed...")
        self.btn_intention.setStyleSheet("""
            color: rgba(255, 255, 255, 0.7);
            font-size: 9pt;
            background: transparent;
            border: none;
            padding: 4px 0px;
        """)
        self.btn_intention.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.container_layout.addWidget(self.btn_intention)

        # Milestone Announcement (Hidden by default)
        self.lbl_milestone = QLabel("")
        self.lbl_milestone.setStyleSheet(f"""
            color: {PRIMARY_COLOR};
            font-weight: bold;
            font-size: 9pt;
            background: transparent;
        """)
        self.lbl_milestone.hide()
        self.container_layout.addWidget(self.lbl_milestone)

        # Stats Pill Container (Glass Effect)
        self.stats_pill = QFrame()
        self.stats_pill.setObjectName("StatsPill")
        self.stats_pill.setStyleSheet(f"""
            QFrame#StatsPill {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 2px 10px;
            }}
        """)
        self.stats_pill.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.stats_layout_inner = QHBoxLayout(self.stats_pill)
        self.stats_layout_inner.setContentsMargins(6, 2, 6, 2)
        self.stats_layout_inner.setSpacing(12)
        
        # Word Stats
        self.lbl_words = QLabel("✍️ 0")
        self.lbl_words.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_words.setStyleSheet(f"""
            color: {PRIMARY_COLOR};
            font-size: 9pt;
            font-weight: bold;
            background: transparent;
        """)
        self.stats_layout_inner.addWidget(self.lbl_words)
        
        # Char Stats
        self.lbl_chars = QLabel("✨ 0")
        self.lbl_chars.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_chars.setStyleSheet("""
            color: rgba(255, 255, 255, 0.7);
            font-size: 8pt;
            background: transparent;
        """)
        self.stats_layout_inner.addWidget(self.lbl_chars)
        
        self.container_layout.addWidget(self.stats_pill)
        
        # Spacer before close button
        self.container_layout.addSpacing(5)
        
        # Close Button
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide_window) 
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: rgba(255, 255, 255, 0.5);
                font-size: 14pt;
                border: none;
                background: transparent;
                margin-bottom: 2px;
            }
            QPushButton:hover {
                color: #ff5555;
            }
        """)
        self.container_layout.addWidget(self.btn_close)
        
        # Final Stylesheet for the container
        self.container.setStyleSheet("""
            QFrame#GlassContainer {
                background-color: rgba(30, 30, 30, 220);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 18px;
            }
        """)

    def hide_window(self):
        self.hide()
        self.visibility_changed.emit(False)

    def show_window(self):
        self.show()
        self.visibility_changed.emit(True)

    def show_intention_menu(self):
        """Action disabled to keep status bar as display-only."""
        pass

    def trigger_celebration(self, message):
        """Show milestone message and trigger a gold coin explosion."""
        self.lbl_milestone.setText(message)
        self.lbl_milestone.show()
        self.btn_intention.hide()
        
        # Explosion center: Middle of the glass container
        c_geom = self.container.geometry()
        center = QPoint(
            int(c_geom.x() + c_geom.width() / 2),
            int(c_geom.y() + c_geom.height() / 2)
        )
        
        # Spawn particles (coins, sparkles, gold)
        for _ in range(60):
            p = MilestoneParticle(self, center)
            self.particles.append(p)
        
        # Start animation
        if not hasattr(self, '_particle_timer'):
            self._particle_timer = QTimer(self)
            self._particle_timer.timeout.connect(self._update_particles)
        self._particle_timer.start(20) # 50fps
        
        QTimer.singleShot(4000, self._stop_celebration)

    def _update_particles(self):
        alive_particles = []
        for p in self.particles:
            if p.update_physics():
                alive_particles.append(p)
        self.particles = alive_particles
        if not self.particles:
            self._particle_timer.stop()

    def _stop_celebration(self):
        self.glow.setEnabled(False)
        self.lbl_milestone.hide()
        self.btn_intention.show()
        # Border will be restored by next update_state heartbeat

    def update_state(self, timer_text, intention_text, phase_color, is_running, words=0, chars=0, session_words=0, session_chars=0):
        self.lbl_timer.setText(timer_text)
        self.btn_intention.setText(intention_text if intention_text else "No Active Intention")
        
        # Display: Daily Total (+Session Growth)
        word_text = f"✍️ {words}"
        if session_words > 0:
            word_text += f" <span style='font-size: 8pt; color: #ffab40;'>+{session_words}</span>"
        
        char_text = f"✨ {chars}"
        if session_chars > 0:
            char_text += f" <span style='font-size: 8pt; color: #ffffff;'>+{session_chars}</span>"
            
        self.lbl_words.setText(word_text)
        self.lbl_chars.setText(char_text)
        
        # Update border color based on phase
        self.container.setStyleSheet(f"""
            QFrame#GlassContainer {{
                background-color: rgba(30, 30, 30, 220);
                border: 1px solid {phase_color};
                border-radius: 18px;
            }}
        """)
        
        if not is_running:
            self.lbl_timer.setStyleSheet("color: #888; font-size: 11pt; font-weight: bold; background: transparent;")
        else:
            self.lbl_timer.setStyleSheet("color: #fff; font-size: 11pt; font-weight: bold; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # We only want to drag if clicking on the bar itself
            if self.container.geometry().contains(event.pos()):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                self.drag_position = QPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if not self.drag_position.isNull():
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()

    def paintEvent(self, event):
        # Allow custom styling if needed via paint event
        super().paintEvent(event)
