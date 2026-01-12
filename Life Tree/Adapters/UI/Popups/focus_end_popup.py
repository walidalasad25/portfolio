from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class FocusEndPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Container style
        self.setStyleSheet("""
            QFrame#card {
                background-color: #252530;
                border: 2px solid #4CAF50;
                border-radius: 15px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI';
                background: transparent;
            }
        """)

        # Main Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(15)

        # Title
        title = QLabel("Focus Session Finished!")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Your break has started automatically.")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #aaaaaa;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        # Status
        status_row = QHBoxLayout()
        status_label = QLabel("⏸ BREAK ACTIVE")
        status_label.setStyleSheet("color: #4CAF50; font-weight: bold; letter-spacing: 1px;")
        status_row.addStretch()
        status_row.addWidget(status_label)
        status_row.addStretch()
        card_layout.addLayout(status_row)
        
        root_layout.addWidget(self.card)
        self.setFixedSize(400, 180)

    def show_on_top(self):
        """Force the window to the front and stay on top."""
        self.show()
        self.raise_()
        self.activateWindow()
