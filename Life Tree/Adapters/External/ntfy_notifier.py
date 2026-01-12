import urllib.request
import threading
from Infrastructure.variables import NTFY_ENABLED, NTFY_TOPIC, NTFY_SERVER, NTFY_PRIORITY_DEFAULT

class NtfyNotifier:
    """
    Adapter for remote notifications via ntfy.sh.
    """
    @staticmethod
    def send(title, message, tags=None, priority=None):
        if not NTFY_ENABLED or not NTFY_TOPIC:
            return

        # Use a thread to avoid blocking the UI
        thread = threading.Thread(
            target=NtfyNotifier._do_send,
            args=(title, message, tags, priority),
            daemon=True
        )
        thread.start()

    @staticmethod
    def _do_send(title, message, tags, priority):
        try:
            url = f"{NTFY_SERVER.rstrip('/')}/{NTFY_TOPIC}"
            
            # Combine title and message into body
            body = (f"{title}\n\n{message}").encode("utf-8")
            
            req = urllib.request.Request(url, data=body, method="POST")
            
            # Safe headers (handle emojis if any)
            def _header_safe(s):
                if not s: return ""
                try:
                    s.encode("latin-1")
                    return s
                except UnicodeEncodeError:
                    return s.encode("latin-1", "ignore").decode("latin-1")

            req.add_header("Title", _header_safe(title))
            req.add_header("Priority", str(priority if priority is not None else NTFY_PRIORITY_DEFAULT))
            
            if tags:
                req.add_header("Tags", _header_safe(tags))

            with urllib.request.urlopen(req, timeout=5) as resp:
                pass # Success
                
        except Exception as e:
            print(f"NtfyNotifier: Failed to send notification: {e}")
