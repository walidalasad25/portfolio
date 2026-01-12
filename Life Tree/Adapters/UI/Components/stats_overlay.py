from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class StatsOverlay(QWidget):
    def __init__(self, active_tracker, word_tracker, parent=None):
        super().__init__(parent)
        self.active_tracker = active_tracker
        self.word_tracker = word_tracker
        
        # Ensure it stays on top/visible if parent is a View
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Let clicks pass through to map
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False) # Ensure background draws
        
        # UI Setup
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 200); /* Semi-transparent dark */
                border-radius: 10px;
                border: 1px solid #444;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                background-color: transparent;
                border: none;
            }
            .ValueLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
            .TitleLabel {
                font-size: 12px;
                color: #aaaaaa;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(20)
        
        # Active Time
        self.lbl_active_time = self.create_stat_widget(layout, "ACTIVE TIME")
        
        # Words
        self.lbl_words = self.create_stat_widget(layout, "WORDS")
        
        # Chars
        self.lbl_chars = self.create_stat_widget(layout, "CHARS")
        
        # Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)
        
        self.update_stats()
        
    def create_stat_widget(self, parent_layout, title):
        container = QWidget()
        container.setStyleSheet("background-color: transparent; border: none;")
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "TitleLabel")
        
        lbl_value = QLabel("--")
        lbl_value.setProperty("class", "ValueLabel")
        
        v_layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(lbl_value, alignment=Qt.AlignmentFlag.AlignCenter)
        
        parent_layout.addWidget(container)
        return lbl_value
        
    def update_stats(self):
        # Active Time
        self.active_tracker.update() # Ensure it's fresh
        total, active = self.active_tracker.get_stats()
        time_str = self.active_tracker.format_time(active)
        self.lbl_active_time.setText(time_str)
        
        # Word/Char
        words, chars = self.word_tracker.get_stats()
        self.lbl_words.setText(str(words))
        self.lbl_chars.setText(str(chars))
