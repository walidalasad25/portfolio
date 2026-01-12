from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient
from PyQt6.QtCore import Qt, QTimer, QRectF
import math

class RotatingProgressCircle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.percentage = 0
        self.angle = 0
        self.setFixedSize(60, 60) # Compact size
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.rotate)
        # Slow, smooth rotation
        self.animation_timer.start(30) 
        
    def rotate(self):
        self.angle = (self.angle + 2) % 360
        self.update()
        
    def set_percentage(self, value):
        self.percentage = value
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        side = min(self.width(), self.height())
        pen_width = 4
        rect = QRectF(pen_width, pen_width, side - pen_width*2, side - pen_width*2)
        
        # 1. Background Track
        painter.setPen(QPen(QColor("#333333"), pen_width))
        painter.drawEllipse(rect)
        
        # 2. Rotating Progress Ring
        # We rotate the start angle of the arc to make it physically spin
        start_angle = (90 - self.angle) * 16
        span_angle = int(-max(self.percentage, 5) * 3.6 * 16)
        
        # Use a simpler gradient that follows the rotation
        gradient = QConicalGradient(rect.center(), 90 - self.angle)
        gradient.setColorAt(0, QColor("#4CAF50")) # Bright Green
        gradient.setColorAt(0.7, QColor("#1b5e20")) # Fade to Dark
        gradient.setColorAt(1.0, QColor("#4CAF50"))
        
        progress_pen = QPen(gradient, pen_width)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)
        
        painter.drawArc(rect, start_angle, span_angle)
        
        # 3. Text
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text = f"{int(self.percentage)}%"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
