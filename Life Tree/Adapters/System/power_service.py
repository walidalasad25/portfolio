import ctypes
import time
import threading

class PowerService:
    """
    Handles system power operations like turning off the monitor.
    Uses Windows SendMessage API.
    """
    WM_SYSCOMMAND = 0x0112
    SC_MONITORPOWER = 0xF170
    
    @staticmethod
    def blackout_monitor(duration_secs=10):
        """
        Turns off the monitor for a set duration, pulsing the 'Off' command
        to ensure it stays off even if mouse/keyboard are touched.
        Uses PostMessage (non-blocking) to prevent hanging if other apps are slow.
        """
        def run():
            start_time = time.time()
            # Stop pulsing 1.5 seconds early to let the system prepare for wakeup
            while time.time() - start_time < (duration_secs - 1.5):
                # 2 = Power Off
                try:
                    # PostMessageW is non-blocking (doesn't wait for other apps to process)
                    ctypes.windll.user32.PostMessageW(
                        0xFFFF, 
                        PowerService.WM_SYSCOMMAND,
                        PowerService.SC_MONITORPOWER,
                        2
                    )
                except Exception as e:
                    print(f"PowerService: Error sending monitor off command: {e}")
                
                time.sleep(1) # Pulse every second
            
            # Final buffer wait
            time.sleep(1.5)

            # --- Wake up the monitor ---
            try:
                # 1. Broadly notify system we need the display
                # ES_DISPLAY_REQUIRED (0x2) | ES_SYSTEM_REQUIRED (0x1) | ES_CONTINUOUS (0x80000000)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)

                # 2. Pulsed Wake Sequence (Try multiple times to ensure detection)
                for _ in range(5):
                    # Send the formal Power On command (-1)
                    ctypes.windll.user32.PostMessageW(
                        0xFFFF,
                        PowerService.WM_SYSCOMMAND,
                        PowerService.SC_MONITORPOWER,
                        -1
                    )
                    
                    # Mouse: Move 20 pixels and back (increased distance)
                    ctypes.windll.user32.mouse_event(0x0001, 10, 10, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.mouse_event(0x0001, -10, -10, 0, 0)
                    
                    # Keyboard: Tap Left Shift (VK_SHIFT = 0x10)
                    ctypes.windll.user32.keybd_event(0x10, 0, 0, 0) # Press
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(0x10, 0, 0x0002, 0) # Release (KEYEVENTF_KEYUP)
                    
                    time.sleep(0.2) # Wait between pulses

                # Reset execution state to normal
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

            except Exception as e:
                print(f"PowerService: Error sending monitor wake sequence: {e}")

            
        # Run in a background thread to prevent UI freezing
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
