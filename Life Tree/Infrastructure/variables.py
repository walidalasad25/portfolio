import os

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "Database")

# Ensure Database directory exists
if not os.path.exists(DATABASE_DIR):
    os.makedirs(DATABASE_DIR)

TREE_DATA_PATH = os.path.join(DATABASE_DIR, "tree_data.json")
VALUES_DATA_PATH = os.path.join(DATABASE_DIR, "values_data.json")
FOCUS_DATA_PATH = os.path.join(DATABASE_DIR, "focus_data.json")
STATS_HISTORY_PATH = os.path.join(DATABASE_DIR, "stats_history.json")
APP_STATE_PATH = os.path.join(DATABASE_DIR, "app_state.json")
SESSION_LOGS_PATH = os.path.join(DATABASE_DIR, "session_logs.json")

# --- Timing Configuration (Minutes) ---
FOCUS_TIME = 25
SHORT_BREAK_TIME = 5
LONG_BREAK_TIME = 15
LONG_BREAK_INTERVAL = 4 # Number of focus sessions before a long break

# --- Idle Detection (Seconds) ---
IDLE_THRESHOLD_SECONDS = 25

# --- Cycle Configuration ---
CYCLE_TIME_LIMIT = 28800 # 8 hours in seconds

# --- Graph Configuration ---
GRAPH_FOCUS_WINDOW_MINS = 25
GRAPH_UPDATE_INTERVAL_MS = 1000

# --- UI Styling ---
PRIMARY_COLOR = "#FF9800"  # Classic Orange
SECONDARY_COLOR = "#4CAF50" # Classic Green
ACCENT_COLOR = "#FF9800"
DANGER_COLOR = "#F44336"    # Red
BG_COLOR = "#1e1e1e"        # Charcoal
CARD_BG_COLOR = "#252526"   # Dark Grey
TEXT_COLOR = "#FFFFFF"      # White
BORDER_COLOR = "#333333"    # Muted Border
# --- Remote Notifications (ntfy) ---
NTFY_ENABLED = True
NTFY_TOPIC = "Evidence_of_growth" 
NTFY_SERVER = "https://ntfy.sh"
NTFY_PRIORITY_DEFAULT = 3
NTFY_PRIORITY_URGENT = 5

# --- Mini Status Bar ---
# Updates are now real-time (1Hz heartbeat)
