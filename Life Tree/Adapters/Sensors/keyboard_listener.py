import keyboard

class KeyboardListener:
    """
    Adapter for monitoring global keyboard metrics.
    """
    def __init__(self):
        self.total_words = 0
        self.total_chars = 0
        self.current_word = ""
        self.is_running = False
        self._hook = None
        
        # Session Baselining
        self.session_words_start = 0
        self.session_chars_start = 0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        try:
            self._hook = keyboard.on_press(self._on_key_press)
        except Exception as e:
            print(f"KeyboardListener: Failed to start keyboard hook: {e}")

    def stop(self):
        if self.is_running:
            self.is_running = False
            self._flush_word()
            try:
                if self._hook:
                    keyboard.unhook(self._hook)
            except Exception as e:
                print(f"KeyboardListener: Failed to stop keyboard hook: {e}")
            self._hook = None

    def reset(self):
        self.total_words = 0
        self.total_chars = 0
        self.current_word = ""
        self.session_words_start = 0
        self.session_chars_start = 0

    def start_session(self):
        """Mark the start of a session (e.g. Focus) to track relative growth."""
        self.session_words_start = self.total_words
        self.session_chars_start = self.total_chars

    def _on_key_press(self, event):
        if not self.is_running:
            return
        
        name = event.name
        if len(name) == 1 and name.isprintable():
            self.current_word += name
        elif name in ("space", "enter"):
            self._flush_word()

    def _flush_word(self):
        if self.current_word.strip():
            w = self.current_word.strip()
            self.total_words += 1
            self.total_chars += len(w)
        self.current_word = ""

    def get_stats(self):
        return self.total_words, self.total_chars

    def get_session_stats(self):
        return self.total_words - self.session_words_start, self.total_chars - self.session_chars_start
