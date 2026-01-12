from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class BreakEndPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Stay on top, frameless, and tool window (no taskbar icon)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QFrame#card {
                background-color: #1e1e2e;
                border: 2px solid #2196F3;
                border-radius: 20px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI';
                background: transparent;
            }
            QPushButton {
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton#start {
                background-color: #2196F3;
                color: white;
            }
            QPushButton#start:hover {
                background-color: #1e88e5;
            }
            QPushButton#idle {
                background-color: #313244;
                color: #cdd6f4;
            }
            QPushButton#idle:hover {
                background-color: #45475a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)

        # Title
        title = QLabel("Break is over!")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # Question
        msg = QLabel("Ready to start focusing again?")
        msg.setFont(QFont("Segoe UI", 12))
        msg.setStyleSheet("color: #bac2de;")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(msg)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_no = QPushButton("Not Yet (Idle)")
        self.btn_no.setObjectName("idle")
        self.btn_no.clicked.connect(self.reject)
        
        self.btn_yes = QPushButton("Yes, Start!")
        self.btn_yes.setObjectName("start")
        self.btn_yes.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_no)
        btn_layout.addWidget(self.btn_yes)
        
        card_layout.addLayout(btn_layout)
        layout.addWidget(self.card)

        self.setFixedSize(380, 220)
