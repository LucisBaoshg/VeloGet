import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

# --- Crash Logging Setup ---
# Redirect stdout/stderr to a log file for debugging "White Screen" issues
# This is critical because Windows GUI apps swallow console output.
log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "veloget_debug.log")

def log_message(msg):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

# Hook uncaught exceptions
def exception_handler(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_message(f"CRASH: {err_msg}")
    # Also try to show a native message box if possible (optional, but helpful)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"App Crashed:\n{err_msg}", "VeloGet Error", 0x10)
    except:
        pass
    sys.exit(1)

sys.excepthook = exception_handler

# Redirect standard streams if frozen (packaged)
# if getattr(sys, 'frozen', False):
#     sys.stdout = open(log_file, "a", encoding="utf-8", buffering=1)
#     sys.stderr = sys.stdout

# ALWAYS redirect for debugging now
sys.stdout = open(log_file, "a", encoding="utf-8", buffering=1)
sys.stderr = sys.stdout

log_message("Application Starting...")
log_message(f"CWD: {os.getcwd()}")
log_message(f"Executable: {sys.executable}")

# --- 1. Update Override Logic ---
# Check if there is a downloaded update in ~/.ytdlpgui/updates
# Structure: ~/.ytdlpgui/updates/yt_dlp/__init__.py
# We need to add ~/.ytdlpgui/updates to sys.path BEFORE anything else
user_home = Path.home()
updates_dir = user_home / ".ytdlpgui" / "updates"
if updates_dir.exists() and (updates_dir / "yt_dlp").exists():
    # Insert at position 0 to override bundled versions
    sys.path.insert(0, str(updates_dir))
    # print(f"DEBUG: Loaded yt-dlp update from {updates_dir}")

# --- 2. Add src to path ---
# Add the 'src' directory to sys.path to allow importing 'ytdlpgui' as a package
# This ensures that relative imports inside the package work correctly.
base_path = Path(__file__).parent
src_path = base_path / "src"
sys.path.insert(0, str(src_path))

# Import the 'run' function from the flet_main module inside the package
from ytdlpgui.flet_main import run

if __name__ == "__main__":
    run()
