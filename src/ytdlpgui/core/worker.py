
import os
import json
import asyncio
from pathlib import Path
import yt_dlp

from ..config import ConfigManager
from .utils import get_environ_with_js_engine, debug_print
from .dependency import DependencyManager

class ProgressLogger:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def debug(self, msg):
        if not msg.startswith('[debug] '):
            self.emit(msg)

    def info(self, msg):
        self.emit(msg)

    def warning(self, msg):
        self.emit(f"WARNING: {msg}")

    def error(self, msg):
        self.emit(f"ERROR: {msg}")

    def emit(self, msg):
        if self.log_callback:
            # Call callback in a thread-safe way if needed, 
            # but in asyncio loop typically we just call it.
            # Toga might need call_on_main_thread if this runs in background thread.
            # But asyncio.to_thread runs in thread, so we should be careful.
            # Ideally the callback handles UI dispatch.
            self.log_callback(msg)

class YtDlpWorker:
    def __init__(self):
        self.config = ConfigManager()
        self.deps = DependencyManager(self.config)

    def _setup_env(self):
        # 1. Inject local bin (~/.ytdlpgui/bin)
        # 2. Inject common system paths (/opt/homebrew/bin ...)
        
        local_bin = str(self.deps.bin_dir)
        internal_bin = str(self.deps.internal_bin_dir)
        common_paths = [local_bin, internal_bin, "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
        current_path = os.environ.get("PATH", "")
        
        new_paths = []
        for p in common_paths:
            if p not in current_path:
                new_paths.append(p)
        
        if new_paths:
             os.environ["PATH"] = os.pathsep.join(new_paths) + os.pathsep + current_path
             debug_print(f"Augmented PATH: {os.environ['PATH']}")

        js_path = self.config.get_js_engine_path()
        if js_path:
            debug_print(f"Using JS Engine Path: {js_path}")
            # get_environ_with_js_engine already handles PATH injection for JS, 
            # but we made sure global PATH is also decent above.
            os.environ.update(get_environ_with_js_engine(js_path))

    async def analyze_url(self, url, browser, profile=None):
        # Run blocking analysis in a thread
        return await asyncio.to_thread(self._analyze_sync, url, browser, profile)

    def _analyze_sync(self, url, browser, profile):
        self._setup_env()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreconfig': True, # Ignore user's yt-dlp.conf
            'ignore_no_formats_error': True,
            # Use a generic format selection that shouldn't fail
            'format': 'best/bestvideo+bestaudio',
        }

        if profile:
            ydl_opts['cookiesfrombrowser'] = (browser, profile, None, None)
        else:
            ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {"status": "success", "data": info}
        except Exception as e:
            err_msg = str(e)
            debug_print(f"Analyze Error: {err_msg}")

            if "could not copy chrome cookie database" in err_msg.lower():
                return {
                    "status": "error", 
                    "error": "【浏览器被占用】\n\nWindows 下无法读取运行中的 Chrome Cookie。\n\n解决方案：\n1. 推荐：在上方切换为【Firefox】(无需关闭浏览器)\n2. 或者：完全退出 Chrome 后重试"
                }
            if "failed to decrypt with dpapi" in err_msg.lower():
                return {
                    "status": "error",
                    "error": "【Cookie 解密失败】\n\nWindows 安全限制导致无法读取 Chrome 数据。\n\n请务必：\n使用【Firefox】浏览器进行下载 (需先安装并登录)"
                }
            if "browser" in err_msg.lower() and "found" in err_msg.lower(): 
                 # Handle "Could not find browser" or similar
                 return {
                    "status": "error",
                    "error": f"【未找到浏览器】\n\n系统未检测到 {browser}。\n\n请先安装 {browser} 浏览器并登录 YouTube。"
                 }
                 
            return {"status": "error", "error": err_msg}

    async def download_video(self, url, format_id, browser, profile, on_log=None, on_progress=None):
        return await asyncio.to_thread(
            self._download_sync, url, format_id, browser, profile, on_log, on_progress
        )

    def _download_sync(self, url, format_id, browser, profile, on_log, on_progress):
        self._setup_env()
        
        download_path = Path(self.config.get_download_dir())
        download_path.mkdir(parents=True, exist_ok=True)

        # Progress hook for yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    if total and on_progress:
                        percent = (downloaded / total) * 100
                        on_progress(percent)
                except:
                    pass

        ydl_opts = {
            'logger': ProgressLogger(on_log),
            'progress_hooks': [progress_hook],
            'paths': {'home': str(download_path)},
            'outtmpl': '%(title)s [%(id)s].%(ext)s',
            'merge_output_format': 'mp4',
            'ignoreconfig': True,
        }

        if format_id == "best":
            # Smart Fallback Logic
            if self.deps.is_ffmpeg_installed():
                ydl_opts['format'] = "bv*+ba/b" # Best video+audio (Requires Merge)
            else:
                ydl_opts['format'] = "best" # Best single file (No Merge) - usually 720p
        else:
            # If specific format selected
            base_fmt = f"{self.format_id}+bestaudio/best" if hasattr(self, 'format_id') else f"{format_id}+bestaudio/best"
            
            # If ffmpeg missing, we cannot do "+bestaudio" merge safely unless we know format_id is a complete file.
            # But usually user selects a video-only stream from the table.
            # If user selects a video-only stream and no ffmpeg -> it will download video only (no audio).
            # We should probably warn user or fallback? 
            # For now, let's respect the selection but log generic fallback if it fails?
            # Actually, robust way:
            if self.deps.is_ffmpeg_installed():
                 ydl_opts['format'] = base_fmt
            else:
                 # Without ffmpeg, we can't merge. 
                 # If format_id represents a video-only stream, downloading it results in silent video.
                 # If we force 'best', we ignore user selection.
                 # Let's trust yt-dlp to try, but if it fails, it fails.
                 # OR: we essentially force 'w' (worst)? No.
                 # Let's keep strict selection but removing the merge intent if possible?
                 # No, `format_id+bestaudio` IS a merge request.
                 # So if no ffmpeg, we must strip `+bestaudio`
                 ydl_opts['format'] = format_id

        if profile:
            ydl_opts['cookiesfrombrowser'] = (browser, profile, None, None)
        else:
            ydl_opts['cookiesfrombrowser'] = (browser, None, None, None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return {"status": "success"}
        except Exception as e:
            err_msg = str(e)
            debug_print(f"Download Error: {err_msg}")
            
            # Check for verification need
            is_verification = "Sign in to confirm" in err_msg or "429" in err_msg
            
            # Check for specific known errors
            if "could not copy chrome cookie database" in err_msg.lower():
                 return {
                    "status": "error", 
                    "error": "【浏览器被占用】\n\n无法读取 Chrome Cookie，因为浏览器正在运行。\n\n请尝试：\n1. 完全关闭 Chrome 浏览器\n2. 再次点击下载"
                }
            if "failed to decrypt with dpapi" in err_msg.lower():
                 return {
                    "status": "error",
                    "error": "【解密失败】\n\n无法解密 Chrome Cookie (DPAPI 错误)。通常是因为 Windows 权限问题。\n\n建议：\n1. 尝试使用 Firefox 浏览器\n2. 或不使用 Cookie 下载"
                }
                
            return {"status": "error", "error": err_msg, "verification_required": is_verification}
            return {"status": "error", "error": str(e)}
