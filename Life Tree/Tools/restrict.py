import time
import threading
import pygetwindow as gw
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# Global flag to control the background thread
running = True

def create_image():
    """Generates a simple red circle icon for the system tray."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), (30, 30, 30)) # Dark background
    dc = ImageDraw.Draw(image)
    # Draw a red circle to represent restriction
    dc.ellipse([8, 8, 56, 56], fill=(255, 0, 0), outline=(200, 0, 0))
    return image

def restriction_loop():
    """Background thread that continuously closes restricted windows."""
    global running
    RESTRICTED_KEYWORDS = ["facebook","spank","antigravity","zoechip"]
    
    print(f"[RESTRICER] Background monitoring started. Target: {', '.join(RESTRICTED_KEYWORDS)}")
    
    while running:
        try:
            # Get every open window on the system
            all_windows = gw.getAllWindows()
            
            for window in all_windows:
                if not window.title:
                    continue
                
                title = window.title.lower()
                for keyword in RESTRICTED_KEYWORDS:
                    if keyword.lower() in title:
                        print(f"[ACCESS DENIED] Closing: '{window.title}'")
                        try:
                            window.close()
                        except Exception as e:
                            print(f"[ERROR] Could not close: {e}")
                        break
        except Exception as e:
            # Log error but keep the thread alive
            print(f"[THREAD ERROR] {e}")
            
        # Check 5 times per second
        time.sleep(0.2)
    
    print("[RESTRICER] Background monitoring stopped.")

def on_quit(icon, item):
    """Callback when 'Quit' is selected from the tray menu."""
    global running
    running = False
    icon.stop()

def main():
    # 1. Start the restriction logic in a background thread
    monitor_thread = threading.Thread(target=restriction_loop, daemon=True)
    monitor_thread.start()

    # 2. Setup the System Tray Icon
    icon_image = create_image()
    menu = pystray.Menu(
        item('Status: ARMED', lambda: None, enabled=False),
        item('Quit Restricter', on_quit)
    )
    
    icon = pystray.Icon("Restricter", icon_image, "Website Restricter", menu)
    
    print("========================================")
    print("   WEBSITE RESTRICER WITH TRAY")
    print("========================================")
    print("The script is now running in your system tray.")
    print("Look for the Red Circle icon to Quit.")
    print("========================================\n")
    
    # 3. Run the icon (this blocks the main thread)
    icon.run()

if __name__ == "__main__":
    main()
