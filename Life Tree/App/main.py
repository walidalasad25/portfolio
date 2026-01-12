from PyQt6.QtWidgets import QApplication
import sys
import os

# Add the project root to sys.path to allow absolute imports like 'Core.Entities'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Adapters.UI.Windows.main_window import MainWindow
import threading

def main():
    # start_values_server() # Values server removed for portfolio version
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Prevent app from exiting when main window is hidden
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()