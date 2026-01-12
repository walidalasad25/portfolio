from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from Adapters.UI.Components.confetti_ui import ConfettiWidget

class SessionReviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.outcome = None
        
        self.setStyleSheet("""
            QFrame#card {
                background-color: #252530;
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
                padding: 15px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                min-width: 180px;
            }
            QPushButton#did_it {
                background-color: #2e7d32;
                color: #a5d6a7;
            }
            QPushButton#did_it:hover {
                background-color: #388e3c;
            }
            QPushButton#tried {
                background-color: #c62828;
                color: #ef9a9a;
            }
            QPushButton#tried:hover {
                background-color: #d32f2f;
            }
            QPushButton#close {
                background-color: #444;
                color: #ddd;
                min-width: 100px;
                padding: 10px;
            }
            QPushButton#close:hover {
                background-color: #555;
                color: white;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("card")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(40, 40, 40, 40)
        self.card_layout.setSpacing(25)

        # Content Container (Swappable)
        self.content_layout = QVBoxLayout()
        self.card_layout.addLayout(self.content_layout)

        self.layout.addWidget(self.card)
        
        # Confetti Overlay (Initially hidden/none)
        self.confetti = None

        self.setFixedSize(550, 350)
        self.show_question()

    def show_question(self):
        # Clear existing
        self._clear_layout(self.content_layout)
        
        # Title
        title = QLabel("Session Finished")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title)

        # Main Question
        question = QLabel("How did it go?")
        question.setFont(QFont("Segoe UI", 16))
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(question)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        self.btn_tried = QPushButton("Didn't but tried")
        self.btn_tried.setObjectName("tried")
        self.btn_tried.clicked.connect(self.handle_tried)
        
        self.btn_did_it = QPushButton("Did it")
        self.btn_did_it.setObjectName("did_it")
        self.btn_did_it.clicked.connect(self.handle_did_it)
        
        btn_layout.addWidget(self.btn_tried)
        btn_layout.addWidget(self.btn_did_it)
        
        self.content_layout.addLayout(btn_layout)

    def handle_did_it(self):
        self.outcome = "success"
        self.show_result(
            title="Success! 🎉",
            subtitle="Nice confetti! I did it, which is great, but it's secondary!",
            show_confetti=True
        )

    def handle_tried(self):
        self.outcome = "tried"
        self.show_result(
            title="Well, that's secondary.",
            subtitle="You showed up and tried. That counts.",
            show_confetti=False
        )

    def show_result(self, title, subtitle, show_confetti):
        self._clear_layout(self.content_layout)
        
        if show_confetti:
            self.confetti = ConfettiWidget(self)
            self.confetti.resize(self.size())
            self.confetti.show()
            self.confetti.raise_()

        # Title
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if show_confetti: lbl_title.setStyleSheet("color: #FFD700;") # Gold
        self.content_layout.addWidget(lbl_title)
        
        # Subtitle
        lbl_sub = QLabel(subtitle)
        lbl_sub.setFont(QFont("Segoe UI", 12))
        lbl_sub.setStyleSheet("color: #ccc;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        self.content_layout.addWidget(lbl_sub)

        # Inspirational Text (The core message)
        inspiration = (
            "The only things that matter are the time I spent on it, "
            "the pain I embraced, the characters, and the words I wrote. "
            "It's not about the outcome, it's about the journey and experience."
        )
        lbl_insp = QLabel(inspiration)
        font_insp = QFont("Segoe UI", 11)
        font_insp.setItalic(True)
        lbl_insp.setFont(font_insp)
        
        lbl_insp.setStyleSheet("color: #aaa; margin-top: 10px;")
        lbl_insp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_insp.setWordWrap(True)
        self.content_layout.addWidget(lbl_insp)

        # OK Button
        btn_ok = QPushButton("OK")
        btn_ok.setObjectName("close")
        btn_ok.clicked.connect(self.accept)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addStretch()
        self.content_layout.addLayout(btn_row)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def resizeEvent(self, event):
        if self.confetti:
            self.confetti.resize(event.size())
        super().resizeEvent(event)

    def get_outcome(self):
        return self.outcome
