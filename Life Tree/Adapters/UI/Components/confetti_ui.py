from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
import random

class ConfettiWidget(QWidget):
    def __init__(self, parent=None, particles=120):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.particles = []
        self.colors = [
             QColor("#FF6B6B"), QColor("#4ECDC4"), QColor("#45B7D1"), 
             QColor("#FFA07A"), QColor("#98D8C8"), QColor("#F7DC6F"), 
             QColor("#BB8FCE"), QColor("#85C1E2")
        ]
        
        # Initialize particles
        self.width_range = 800  # Default fallback
        self.height_range = 600
        
        # We'll spawn random particles but position them properly in resizeEvent or paint
        for _ in range(particles):
            self.particles.append(self._create_particle())
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16) # ~60 FPS

    def _create_particle(self):
        return {
            "x": random.randint(0, self.width()),
            "y": random.randint(-self.height(), 0),
            "size": random.randint(6, 12),
            "color": random.choice(self.colors),
            "vx": random.uniform(-1, 1),
            "vy": random.uniform(1, 3)
        }

    def resizeEvent(self, event):
        # Respond to resize if needed? 
        # Actually particles are already independent.
        super().resizeEvent(event)

    def _animate(self):
        gravity = 0.1
        h = self.height()
        w = self.width()
        
        active_particles = False
        
        for p in self.particles:
            p["vy"] += gravity
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            
            # Bounce sides
            if p["x"] <= 0 or p["x"] >= w:
                p["vx"] *= -0.8
                p["x"] = max(0, min(w, p["x"]))
                
            # Bounce bottom
            if p["y"] >= h - p["size"]:
                p["vy"] *= -0.6
                p["y"] = h - p["size"]
                
                # Friction
                p["vx"] *= 0.95
                
            if p["y"] < h: # Still visible/moving
                 active_particles = True
                 
        self.update() # Trigger repaint
        
        # Optimization: Stop timer if all settled? 
        # For now, continuous loop is safer for simple effect.

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for p in self.particles:
            painter.setBrush(QBrush(p["color"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(p["x"]), int(p["y"]), p["size"], p["size"])
