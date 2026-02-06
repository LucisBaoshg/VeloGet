
import sys
import os
import glob
import shutil
from pathlib import Path

# Safe Logger for Windows GUI (No Console)
def debug_print(message):
    try:
        if sys.stdout is not None:
             print(f"[DEBUG] {message}")
    except Exception:
        pass # Ignore print errors in no-console mode

def get_ytdlp_command():
    """
    Constructs the command to run yt-dlp.
    In a frozen (packaged) environment, or if running from source with yt-dlp installed,
    running as a module `python -m yt_dlp` is most robust.
    """
    # 1. Try to invoke via current python executable (works for venv and packaged apps)
    # We use a list format suitable for subprocess.run/Popen(..., shell=False)
    return [sys.executable, "-m", "yt_dlp"]

def get_browser_profiles(browser_name):
    """
    Get list of profiles for a given browser.
    Returns list of dict: {'name': 'Display Name', 'id': 'Profile Folder Name'}
    """
    browser_name = browser_name.lower()
    if 'firefox' in browser_name:
        return _get_firefox_profiles()
    
    # Chromium based
    return _get_chromium_profiles(browser_name)

def _get_chromium_base_path(browser_name):
    """Get User Data directory for Chromium browsers"""
    import sys
    home = Path.home()
    
    if sys.platform == "darwin":
        base = home / "Library/Application Support"
        if "chrome" in browser_name: return base / "Google/Chrome"
        if "edge" in browser_name: return base / "Microsoft Edge"
        if "brave" in browser_name: return base / "BraveSoftware/Brave-Browser"
        if "chromium" in browser_name: return base / "Chromium"
        
    elif sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data: return None
        base = Path(local_app_data)
        if "chrome" in browser_name: return base / "Google" / "Chrome" / "User Data"
        if "edge" in browser_name: return base / "Microsoft" / "Edge" / "User Data"
        if "brave" in browser_name: return base / "BraveSoftware" / "Brave-Browser" / "User Data"
        if "chromium" in browser_name: return base / "Chromium" / "User Data"
        
    return None

def _get_chromium_profiles(browser_name):
    """Parse Local State JSON to find profiles"""
    import json
    
    base_path = _get_chromium_base_path(browser_name)
    if not base_path or not base_path.exists():
        return [{"name": "Default", "id": "Default"}] # Fallback
        
    profiles = []
    
    # 1. Try to read Local State (The correct way)
    local_state = base_path / "Local State"
    if local_state.exists():
        try:
            with open(local_state, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            info_cache = data.get("profile", {}).get("info_cache", {})
            for dir_name, info in info_cache.items():
                # info["name"] is the display name (e.g. "Person 1", "Work")
                # dir_name is the folder name (e.g. "Profile 1")
                display_name = info.get("name", dir_name)
                profiles.append({"name": display_name, "id": dir_name})
                
        except Exception as e:
            debug_print(f"Error parsing Local State: {e}")
            
    # 2. Fallback: Scan directories if Local State failed or is empty
    if not profiles:
        debug_print("Local State empty or failed, scanning directories...")
        if (base_path / "Default").exists():
            profiles.append({"name": "Default", "id": "Default"})
        
        for p in glob.glob(str(base_path / "Profile *")):
            d_name = os.path.basename(p)
            profiles.append({"name": d_name, "id": d_name})
            
    # 3. Sort (Default first, then alphabetical)
    profiles.sort(key=lambda x: (x['id'] != 'Default', x['name']))
    return profiles

def _get_firefox_profiles():
    """Parse profiles.ini for Firefox"""
    import configparser
    import sys
    
    profiles = []
    base_path = None
    home = Path.home()
    
    if sys.platform == "darwin":
        base_path = home / "Library/Application Support/Firefox"
    elif sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base_path = Path(app_data) / "Mozilla" / "Firefox"
            
    if not base_path or not base_path.exists():
        return [{"name": "default", "id": "default"}]
        
    ini_path = base_path / "profiles.ini"
    if ini_path.exists():
        try:
            cfg = configparser.ConfigParser()
            cfg.read(ini_path)
            for section in cfg.sections():
                if section.startswith("Profile"):
                    name = cfg.get(section, "Name", fallback=section)
                    path = cfg.get(section, "Path", fallback=name)
                    # For Firefox, yt-dlp usually takes the profile NAME, not path, 
                    # BUT specific path handling is tricky. 
                    # yt-dlp --cookies-from-browser firefox:PROFILE_NAME
                    profiles.append({"name": name, "id": name}) 
        except Exception as e:
            debug_print(f"Error parsing profiles.ini: {e}")
            
    if not profiles:
        profiles.append({"name": "default", "id": "default"})
        
    return profiles

def get_environ_with_js_engine(js_engine_path_override=None):
    """Ensure JS Engine (Node/Deno) is in the PATH for yt-dlp to use"""
    env = os.environ.copy()
    
    # 移除 PyInstaller/Briefcase 添加的临时的 _MEIPASS 路径，
    # 避免子进程继承此环境导致混乱（虽然 python -m 一般没事）
    if '_MEIPASS' in env: del env['_MEIPASS']
    
    # 确保 PATH 包含 /usr/local/bin 等常用路径 (macOS GUI app 默认 PATH 很短)
    default_paths = []
    if sys.platform != "win32":
        default_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    
    current_path = env.get("PATH", "")
    
    # 构建新 PATH
    new_path_parts = []
    
    if js_engine_path_override:
        debug_print(f"Using configured JS Engine path: {js_engine_path_override}")
        new_path_parts.append(str(js_engine_path_override))
        
    new_path_parts.extend(default_paths)
    new_path_parts.append(current_path)
    
    # 去重并连接 (使用 os.pathsep 自动适配 : 或 ;)
    env["PATH"] = os.pathsep.join(new_path_parts)
    
    return env
