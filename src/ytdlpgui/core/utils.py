
import sys
import os
import glob
import shutil
from pathlib import Path

def debug_print(message):
    print(f"[DEBUG] {message}")

def get_ytdlp_command():
    """
    Constructs the command to run yt-dlp.
    In a frozen (packaged) environment, or if running from source with yt-dlp installed,
    running as a module `python -m yt_dlp` is most robust.
    """
    # 1. Try to invoke via current python executable (works for venv and packaged apps)
    # We use a list format suitable for subprocess.run/Popen(..., shell=False)
    return [sys.executable, "-m", "yt_dlp"]

def scan_chrome_profiles():
    """扫描 macOS 上的 Chrome 配置文件"""
    profiles = ["Default"]
    if sys.platform != "darwin":
        return profiles

    chrome_root = Path.home() / "Library/Application Support/Google/Chrome"
    if not chrome_root.exists():
        return profiles

    # 查找 "Profile *" 文件夹
    profile_dirs = glob.glob(str(chrome_root / "Profile *"))
    for p in profile_dirs:
        dir_name = os.path.basename(p)
        profiles.append(dir_name)
    
    return sorted(profiles)

def get_environ_with_js_engine(js_engine_path_override=None):
    """Ensure JS Engine (Node/Deno) is in the PATH for yt-dlp to use"""
    env = os.environ.copy()
    
    # 移除 PyInstaller/Briefcase 添加的临时的 _MEIPASS 路径，
    # 避免子进程继承此环境导致混乱（虽然 python -m 一般没事）
    if '_MEIPASS' in env: del env['_MEIPASS']
    
    # 确保 PATH 包含 /usr/local/bin 等常用路径 (macOS GUI app 默认 PATH 很短)
    default_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    current_path = env.get("PATH", "")
    
    # 构建新 PATH
    new_path_parts = []
    
    if js_engine_path_override:
        debug_print(f"Using configured JS Engine path: {js_engine_path_override}")
        new_path_parts.append(js_engine_path_override)
        
    new_path_parts.extend(default_paths)
    new_path_parts.append(current_path)
    
    # 去重并连接
    # (简单连接即可，shell 会处理)
    env["PATH"] = ":".join(new_path_parts)
    
    return env
