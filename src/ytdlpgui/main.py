
import sys
import traceback
from pathlib import Path

def main():
    try:
        # Debug Log
        log_file = Path.home() / "ytdlpgui_debug.log"
        with open(log_file, "a") as f:
            f.write("--- App Launching ---\n")
        
        from .app import main as app_main
        app = app_main()
        app.main_loop()
        return app
    except Exception:
        log_file = Path.home() / "ytdlpgui_crash.log"
        with open(log_file, "w") as f:
            f.write(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main().main_loop()
