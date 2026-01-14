
import json
import os
import shutil
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # 使用 ~/.ytdlpgui/config.json 存储配置
        self.config_dir = Path.home() / ".ytdlpgui"
        self.config_file = self.config_dir / "config.json"
        self.config_data = {}
        
        self._ensure_config()
        self._load()

    def _ensure_config(self):
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            # 默认配置
            default_config = {
                "js_engine_path": "",
                "download_dir": str(Path.home() / "Downloads"),
                "last_browser": "chrome",
                "last_profile": "Default",
                "cookie_file": ""
            }
            self._save_data(default_config)

    def _load(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        except Exception:
            self.config_data = {}

    def _save_data(self, data):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def save(self):
        self._save_data(self.config_data)

    def get_js_engine_path(self):
        # 1. Check user config
        path = self.config_data.get("js_engine_path")
        if path and os.path.exists(path):
            return path

        # 2. Check environment PATH and common locations explicitly
        # macOS apps often have stripped PATH, so we must check common dirs manually.
        search_paths = [
            "/opt/homebrew/bin", 
            "/usr/local/bin", 
            os.path.expanduser("~/.deno/bin"),
            os.path.expanduser("~/.nvm/versions/node"), # Rough check
        ]
        
        # Helper to check specific binary
        def check_bin(name):
             # First check system PATH
             res = shutil.which(name)
             if res: return os.path.dirname(res)
             
             # Then check common paths
             for p in search_paths:
                 full_p = os.path.join(p, name)
                 if os.path.exists(full_p) and os.access(full_p, os.X_OK):
                     return p
             return None

        # Check Deno (Priority)
        deno_path = check_bin("deno")
        if deno_path: return deno_path

        # Check Node
        node_path = check_bin("node")
        if node_path: return node_path
            
        return None

    def set_js_engine_path(self, path):
        self.config_data["js_engine_path"] = path
        self.save()

    def get_download_dir(self):
        return self.config_data.get("download_dir", str(Path.home() / "Downloads"))

    def set_download_dir(self, path):
        self.config_data["download_dir"] = path
        self.save()

    def get_last_browser(self):
        return self.config_data.get("last_browser", "chrome")

    def set_last_browser(self, browser):
        self.config_data["last_browser"] = browser
        self.save()

    def get_last_profile(self):
        return self.config_data.get("last_profile", "Default")

    def set_last_profile(self, profile):
        self.config_data["last_profile"] = profile
        self.save()

    def get_update_source(self):
        # Returns specific URL or a key. Let's return the key 'official', 'tsinghua'
        return self.config_data.get("update_source", "official")

    def set_update_source(self, source_key):
        self.config_data["update_source"] = source_key
        self.save()

    def get_update_timeout(self):
        return self.config_data.get("update_timeout", 30)

    def set_update_timeout(self, seconds: int):
        self.config_data["update_timeout"] = seconds
        self.save()

    def get_cookie_file(self):
        return self.config_data.get("cookie_file", "")

    def set_cookie_file(self, path):
        self.config_data["cookie_file"] = path
        self.save()
