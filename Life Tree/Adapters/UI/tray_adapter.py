from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QCoreApplication
import os

class WindowTrayManager:
    def __init__(self, main_window, app_name="Evidence of Growth"):
        self.main_window = main_window
        self.app_name = app_name
        
        # Create Tray Icon
        self.tray_icon = QSystemTrayIcon(self.main_window)
        
        # Set Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Infrastructure", "icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Create a simple colored fallback icon in memory
            from PyQt6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#4CAF50")) # Green for "Life"
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, 32, 32, 8, 8)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))


        # Create Menu
        self.menu = QMenu()
        
        self.open_action = QAction("Open App", self.main_window)
        self.open_action.triggered.connect(self.restore_window)
        self.menu.addAction(self.open_action)
        
        self.menu.addSeparator()
        
        self.status_bar_action = QAction("Status Bar", self.main_window)
        self.status_bar_action.setCheckable(True)
        self.status_bar_action.setChecked(True)
        self.status_bar_action.triggered.connect(self.toggle_status_bar)
        self.menu.addAction(self.status_bar_action)

        self.menu.addSeparator()
        
        self.quit_action = QAction("Quit", self.main_window)
        self.quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip(self.app_name)
        
        # Double-click behavior
        self.tray_icon.activated.connect(self.on_activated)
        
        self.tray_icon.show()

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click usually restoration
            self.restore_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_window()

    def restore_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def minimize_to_tray(self):
        self.main_window.hide()

    def quit_app(self):
        # We need to bypass the minimize-to-tray logic in closeEvent
        self.main_window._force_quit = True
        self.main_window.close()

    def toggle_status_bar(self):
        if hasattr(self.main_window, 'status_bar'):
            if self.main_window.status_bar.isVisible():
                self.main_window.status_bar.hide()
                self.status_bar_action.setChecked(False)
            else:
                self.main_window.status_bar.show()
                self.status_bar_action.setChecked(True)

    def notify(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
