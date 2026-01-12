from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os

class ValuesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Core Values")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        # Dark theme
        self.setStyleSheet("background-color: #1a1a1a; color: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Locate values.png in Database folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_dir, "Database", "values.png")
        
        # Create a scroll area to handle potential image overflow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        # Label to hold the image
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            # We display at full size inside the scroll area
            self.img_label.setPixmap(pixmap)
        else:
            self.img_label.setText(f"Image not found at:\n{img_path}")
            self.img_label.setStyleSheet("color: #ff5555; font-size: 14pt;")
            
        scroll.setWidget(self.img_label)
        layout.addWidget(scroll)
