import sys
import os
from pathlib import Path

# Fix: Redirect stdout/stderr to devnull if we are frozen and have no console
# This prevents "OSError: [Errno 9] Bad file descriptor" on Windows GUI apps
if getattr(sys, 'frozen', False) and sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

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
