from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

class DistractionWarning(QWidget):
    add_allowed_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.current_distraction_title = ""
        
        layout = QVBoxLayout(self)
        
        # Container for styling
        self.container = QWidget()
        self.container.setObjectName("WarningContainer")
        self.container.setMinimumSize(400, 200)
        self.container.setStyleSheet("""
            QWidget#WarningContainer {
                background-color: rgba(30, 30, 35, 240);
                border: 2px solid #ff5252;
                border-radius: 12px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(20)
        
        # Icon/Label
        icon_label = QLabel("⚠️")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFont(QFont("Segoe UI", 32))
        container_layout.addWidget(icon_label)
        
        # Message
        msg = QLabel("You are distracted.\nHow about getting back to work?!")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;")
        msg.setWordWrap(True)
        container_layout.addWidget(msg)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_allow = QPushButton("Allow this window")
        self.btn_allow.setStyleSheet("""
            QPushButton {
                background-color: #383842;
                color: #d4d4d4;
                border: 1px solid #555;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a58;
            }
        """)
        self.btn_allow.clicked.connect(self.on_allow_clicked)
        btn_layout.addWidget(self.btn_allow)
        
        container_layout.addLayout(btn_layout)
        layout.addWidget(self.container)
        
        self.setFixedSize(450, 280)

    def on_allow_clicked(self):
        if self.current_distraction_title:
            self.add_allowed_requested.emit(self.current_distraction_title)
            self.hide()

    def show_warning(self, window_title):
        self.current_distraction_title = window_title
        # Center on screen
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
