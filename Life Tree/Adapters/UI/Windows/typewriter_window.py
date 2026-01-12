"""
TypeWriter Window - A Mechanical Scribe for Life Tree
Integrated via Ctrl+Alt+N hotkey.
"""
import os
import random
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPlainTextEdit, QFrame
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtGui import QTextCursor, QFont, QColor, QPainter

# --- Paths ---
from Infrastructure.variables import BASE_DIR, DATABASE_DIR

ASSETS_DIR = os.path.join(BASE_DIR, "Assets", "TypeWriter")
ASSET_PATH = os.path.join(ASSETS_DIR, "assets")
STYLE_PATH = os.path.join(ASSETS_DIR, "styles.css")
DRAFT_PATH = os.path.join(DATABASE_DIR, "typewriter_draft.txt")


class TypeWriter(QPlainTextEdit):
    """A mechanical typewriter editor with sound effects and permanent ink."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("typewriter_engine")
        
        # MECHANICAL MODE: Fixed layout settings
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setUndoRedoEnabled(False)
        self.setOverwriteMode(False)  # Manual overwrite handling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # CURSOR: Hide default, we draw our own
        self.setCursorWidth(0)
        self.BELL_COL = 72
        
        # FONT SYNC: Ensure Python metrics match CSS
        font = QFont("Courier New", 38)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        
        # PALETTE: Selection visibility
        palette = self.palette()
        palette.setColor(palette.ColorGroup.All, palette.ColorRole.Highlight, QColor(226, 223, 218))
        self.setPalette(palette)
        
        # SOUNDS: Lazy-loaded for performance
        self._sounds_loaded = False
        self.sounds = {'key': [], 'space': None, 'return': None, 'backspace': None, 'bell': None}

    def _ensure_sounds_loaded(self):
        """Lazy load sounds only when first needed."""
        if self._sounds_loaded:
            return
        self._sounds_loaded = True
        
        for i in range(1, 4):
            path = os.path.join(ASSET_PATH, f"key{i}.wav")
            if os.path.exists(path):
                self.sounds['key'].append(self._create_sound(path))
        
        if not self.sounds['key']:
            fallback = os.path.join(ASSET_PATH, "key.wav")
            if os.path.exists(fallback):
                self.sounds['key'].append(self._create_sound(fallback))
        
        self.sounds['space'] = self._create_sound(os.path.join(ASSET_PATH, "space.wav"))
        self.sounds['return'] = self._create_sound(os.path.join(ASSET_PATH, "return.wav"))
        self.sounds['backspace'] = self._create_sound(os.path.join(ASSET_PATH, "backspace.wav"))
        self.sounds['bell'] = self._create_sound(os.path.join(ASSET_PATH, "bell.wav"))

    def _create_sound(self, path):
        if os.path.exists(path):
            sound = QSoundEffect()
            sound.setSource(QUrl.fromLocalFile(path))
            sound.setVolume(0.5)
            return sound
        return None

    def play_sound_effect(self, sound_type):
        self._ensure_sounds_loaded()
        sound = None
        if sound_type == 'key':
            valid_keys = [s for s in self.sounds['key'] if s is not None]
            if valid_keys:
                sound = random.choice(valid_keys)
        else:
            sound = self.sounds.get(sound_type)
        
        if sound and sound.status() != QSoundEffect.Status.Error:
            sound.play()

    def centerCursor(self):
        """Keeps the active line in the vertical center of the screen."""
        self.ensureCursorVisible()
        cursor = self.textCursor()
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value() + 
            self.cursorRect(cursor).top() - 
            self.viewport().height() // 2
        )

    def keyPressEvent(self, event):
        key = event.key()
        char = event.text()
        cursor = self.textCursor()
        col_num = cursor.columnNumber()

        # 1. CARRIAGE RETURN
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.play_sound_effect('return')
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertBlock()
            self.setTextCursor(cursor)
            self.centerCursor()
            self._autosave()
            return

        # 2. BACKSPACE (Carriage Back - no delete)
        if key == Qt.Key.Key_Backspace:
            if col_num > 0:
                self.play_sound_effect('backspace')
                cursor.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(cursor)
            return

        # 3. MECHANICAL STRIKE - Printable chars without modifiers
        has_modifier = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)
        if char and char.isprintable() and len(char) == 1 and not has_modifier:
            self.play_sound_effect('key')
            
            if col_num == self.BELL_COL:
                self.play_sound_effect('bell')
            
            # MECHANICAL OVERWRITE: Delete existing char before insert
            if not cursor.atBlockEnd():
                cursor.deleteChar()
            cursor.insertText(char)
            
            self.centerCursor()
            self._autosave()
            return
            
        elif key == Qt.Key.Key_Space:
            self.play_sound_effect('space')
            super().keyPressEvent(event)
            self.centerCursor()
            self._autosave()
        else:
            super().keyPressEvent(event)

    def _autosave(self):
        """Trigger save on the parent window."""
        main_win = self.window()
        if hasattr(main_win, 'save_text'):
            main_win.save_text()

    def paintEvent(self, event):
        # Native text rendering (handles multi-line correctly)
        super().paintEvent(event)
        
        # CUSTOM CURSOR (The Carriage Marker)
        if self.hasFocus():
            painter = QPainter(self.viewport())
            cursor_rect = self.cursorRect()
            painter.fillRect(cursor_rect.left(), cursor_rect.top(), 4, cursor_rect.height(), QColor(140, 20, 20))
            painter.end()

    # Disable mouse cursor repositioning for mechanical feel
    def mousePressEvent(self, event): pass
    def mouseMoveEvent(self, event): pass


class TypeWriterWindow(QMainWindow):
    """The full-screen typewriter window, toggled by Ctrl+Alt+N."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Mechanical Scribe")
        self.setMinimumSize(900, 700)
        
        # Central Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Paper Area
        self.paper = QFrame()
        self.paper.setObjectName("paper_area")
        self.paper_layout = QVBoxLayout(self.paper)
        
        self.editor = TypeWriter(self.paper)
        self.paper_layout.addWidget(self.editor)
        self.layout.addWidget(self.paper)

        self._load_stylesheet()

    def showEvent(self, event):
        """Load text only when window is shown (lazy loading for performance)."""
        super().showEvent(event)
        if not hasattr(self, '_text_loaded'):
            self._text_loaded = True
            self._load_text()

    def _load_text(self):
        if os.path.exists(DRAFT_PATH):
            with open(DRAFT_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                self.editor.setPlainText(content)
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.editor.setTextCursor(cursor)
                self.editor.centerCursor()

    def save_text(self):
        with open(DRAFT_PATH, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())

    def _load_stylesheet(self):
        if os.path.exists(STYLE_PATH):
            with open(STYLE_PATH, "r") as f:
                self.setStyleSheet(f.read())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.save_text()
            self.hide()  # Hide instead of close for instant re-open
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.save_text()
        event.accept()
