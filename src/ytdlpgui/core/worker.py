
import os
import json
import asyncio
from pathlib import Path

from ..config import ConfigManager
from .utils import get_environ_with_js_engine, debug_print
from .dependency import DependencyManager
from .site_profiles import build_ydl_opts, detect_site
from .ytdlp_cli import build_cli_command, run_json_command, run_download_command

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
        
        import sys
        if sys.platform == 'win32':
             common_paths = [local_bin, internal_bin]
        else:
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

    def _runtime_env(self):
        env = os.environ.copy()
        js_path = self.config.get_js_engine_path()
        if js_path:
            env.update(get_environ_with_js_engine(js_path))
        return env

    def _get_ytdlp_path(self):
        path = self.deps.get_ytdlp_path()
        if not path:
            raise RuntimeError("yt-dlp 未安装，请先完成首次运行时依赖安装")
        return path

    def _build_cli_for_mode(
        self,
        *,
        mode,
        url,
        browser,
        profile,
        cookie_file,
        format_id=None,
        download_path=None,
        logger=None,
        progress_hooks=None,
    ):
        opts = build_ydl_opts(
            mode=mode,
            url=url,
            browser=browser,
            profile=profile,
            cookie_file=cookie_file,
            format_id=format_id,
            ffmpeg_installed=self.deps.is_ffmpeg_installed(),
            download_path=download_path,
            logger=logger,
            progress_hooks=progress_hooks,
        )
        command = build_cli_command(
            ytdlp_path=self._get_ytdlp_path(),
            url=url,
            mode=mode,
            opts=opts,
            ffmpeg_path=self.deps.get_ffmpeg_path(),
        )
        return opts, command

    async def analyze_url(self, url, browser, profile=None):
        # Run blocking analysis in a thread
        return await asyncio.to_thread(self._analyze_sync, url, browser, profile)

    def _analyze_sync(self, url, browser, profile):
        self._setup_env()

        cookie_file = self.config.get_cookie_file()
        if cookie_file and os.path.exists(cookie_file):
            debug_print(f"Using Manual Cookie File: {cookie_file}")
        else:
            cookie_file = None

        debug_print(f"Detected Site Profile: {detect_site(url)}")
        _ydl_opts, command = self._build_cli_for_mode(
            mode="analyze_video",
            url=url,
            browser=browser,
            profile=profile,
            cookie_file=cookie_file,
        )

        try:
            info = run_json_command(command, env=self._runtime_env())
            return {"status": "success", "data": info}
        except Exception as e:
            err_msg = str(e)
            debug_print(f"Analyze Error: {err_msg}")

            if "could not copy chrome cookie database" in err_msg.lower():
                import sys
                if sys.platform == 'darwin':
                    return {
                        "status": "error", 
                        "error": "【Cookie 读取失败 (macOS)】\n\n原因：无法访问浏览器数据库。\n\n解决方案：\n1. ⚠️ 请授予 VeloGet '完全磁盘访问权限' (系统设置 -> 隐私与安全)\n2. 确保 Profile 选择正确 (尝试 'Default')\n3. 退出 Chrome 浏览器后重试"
                    }
                else:
                    return {
                        "status": "error", 
                        "error": "【浏览器被占用】\n\nWindows 下无法读取运行中的 Chrome Cookie。\n\n解决方案：\n1. 完全退出 Chrome 浏览器\n2. 或在上方切换为【Firefox】"
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

            if "[douyin]" in err_msg.lower() and "fresh cookies" in err_msg.lower():
                return {
                    "status": "error",
                    "error": "【Douyin Cookie 过期】\n\n抖音检测到 Cookie 失效。\n\n解决方案：\n1. 打开 Firefox 浏览器\n2. 访问 douyin.com 并登录\n3. 随便刷几个视频以刷新 Token\n4. 关闭浏览器后重试"
                }
                 
            return {"status": "error", "error": err_msg}

    async def download_video(self, url, format_id, browser, profile, on_log=None, on_progress=None):
        return await asyncio.to_thread(
            self._download_sync, url, format_id, browser, profile, on_log, on_progress
        )

    def _download_sync(self, url, format_id, browser, profile, on_log, on_progress):
        self._setup_env()
        
        debug_print(f"Download Request: URL={url}, FormatID={format_id}")
        debug_print(f"Browser Config: {browser} (Profile: {profile})")
        debug_print(f"FFmpeg Detected: {self.deps.is_ffmpeg_installed()}")
        
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

        cookie_file = self.config.get_cookie_file()
        if cookie_file and os.path.exists(cookie_file):
            debug_print(f"Using Manual Cookie File: {cookie_file}")
        else:
            cookie_file = None

        debug_print(f"Detected Site Profile: {detect_site(url)}")
        ydl_opts, command = self._build_cli_for_mode(
            mode="download_video",
            url=url,
            browser=browser,
            profile=profile,
            cookie_file=cookie_file,
            format_id=format_id,
            download_path=download_path,
            logger=ProgressLogger(on_log),
            progress_hooks=[progress_hook],
        )
        debug_print(f"Yt-dlp Options Format: {ydl_opts.get('format')}")

        try:
            run_download_command(
                command,
                env=self._runtime_env(),
                on_log=on_log,
                on_progress=on_progress,
            )
            return {"status": "success"}
        except Exception as e:
            err_msg = str(e)
            debug_print(f"Download Error: {err_msg}")
            
            # Check for verification need
            is_verification = "Sign in to confirm" in err_msg or "429" in err_msg
            
            # Check for specific known errors
            if "could not copy chrome cookie database" in err_msg.lower():
                 import sys
                 if sys.platform == 'darwin':
                     return {
                        "status": "error", 
                        "error": "【Cookie 读取失败 (macOS)】\n\n原因：无法访问浏览器数据库。\n\n解决方案：\n1. ⚠️ 请授予 VeloGet '完全磁盘访问权限' (系统设置 -> 隐私与安全)\n2. 确保 Profile 选择正确\n3. 退出 Chrome 浏览器后重试"
                    }
                 else:
                     return {
                        "status": "error", 
                        "error": "【浏览器被占用】\n\n无法读取 Chrome Cookie，因为浏览器正在运行。\n\n请尝试：\n1. 完全关闭 Chrome 浏览器\n2. 再次点击下载"
                    }
            if "failed to decrypt with dpapi" in err_msg.lower():
                 return {
                    "status": "error",
                    "error": "【解密失败】\n\n无法解密 Chrome Cookie (DPAPI 错误)。通常是因为 Windows 权限问题。\n\n建议：\n1. 尝试使用 Firefox 浏览器\n2. 或不使用 Cookie 下载"
                }

            if "[douyin]" in err_msg.lower() and "fresh cookies" in err_msg.lower():
                # Check if we are using a manual file
                if self.config.get_cookie_file():
                     return {
                        "status": "error", 
                        "error": "【Cookie 文件已过期】\n\n您指定的 cookies.txt 似乎已经失效。\n\n解决方案：\n1. 请在浏览器中重新登录抖音\n2. 重新导出 cookies.txt\n3. 在设置中重新选择该文件"
                    }
                else:
                    return {
                        "status": "error", 
                        "error": "【Douyin Cookie 过期】\n\n抖音检测到 Cookie 失效。\n\n解决方案：\n1. 打开 Firefox 浏览器\n2. 访问 douyin.com 并登录\n3. 随便刷几个视频以刷新 Token\n4. 关闭浏览器后重试"
                    }
                
            return {"status": "error", "error": err_msg, "verification_required": is_verification}

    async def analyze_channel(self, url, browser, profile=None):
        return await asyncio.to_thread(self._analyze_channel_sync, url, browser, profile)

    def _analyze_channel_sync(self, url, browser, profile):
        self._setup_env()

        cookie_file = self.config.get_cookie_file()
        if cookie_file and os.path.exists(cookie_file):
            debug_print(f"Using Manual Cookie File: {cookie_file}")
        else:
            cookie_file = None

        debug_print(f"Detected Site Profile: {detect_site(url)}")
        _ydl_opts, command = self._build_cli_for_mode(
            mode="analyze_channel",
            url=url,
            browser=browser,
            profile=profile,
            cookie_file=cookie_file,
        )

        try:
            info = run_json_command(command, env=self._runtime_env())

            entries = list(info.get('entries', []))
            debug_print(f"Channel Root Entries: {len(entries)}")

            if len(entries) < 10:
                tabs_to_scan = []
                found_types = set()

                for entry in entries:
                    title = entry.get('title', '')
                    entry_url = entry.get('url', '')
                    debug_print(f"Checking Tab: {title} | {entry_url}")

                    if not entry_url:
                        continue

                    if entry_url.endswith('/videos'):
                        tabs_to_scan.append(('Video', entry_url))
                        found_types.add('Video')
                    elif entry_url.endswith('/shorts'):
                        tabs_to_scan.append(('Short', entry_url))
                        found_types.add('Short')
                    elif entry_url.endswith('/streams'):
                        tabs_to_scan.append(('Live', entry_url))
                        found_types.add('Live')

                base_url = url.rstrip('/')
                if 'Video' not in found_types:
                    debug_print("Adding implicit /videos tab")
                    tabs_to_scan.append(('Video', f"{base_url}/videos"))
                if 'Short' not in found_types:
                    debug_print("Adding implicit /shorts tab")
                    tabs_to_scan.append(('Short', f"{base_url}/shorts"))
                if 'Live' not in found_types:
                    debug_print("Adding implicit /streams tab")
                    tabs_to_scan.append(('Live', f"{base_url}/streams"))

                all_entries = []
                if tabs_to_scan:
                    debug_print(f"Scanning Tabs: {tabs_to_scan}")
                    for v_type, tab_url in tabs_to_scan:
                        try:
                            debug_print(f"Fetching {v_type} from {tab_url}")
                            _tab_opts, tab_command = self._build_cli_for_mode(
                                mode="analyze_channel",
                                url=tab_url,
                                browser=browser,
                                profile=profile,
                                cookie_file=cookie_file,
                            )
                            tab_info = run_json_command(tab_command, env=self._runtime_env())
                            tab_entries = list(tab_info.get('entries', []))
                            for video in tab_entries:
                                video['original_type'] = v_type
                            debug_print(f"Found {len(tab_entries)} {v_type}s")
                            all_entries.extend(tab_entries)
                        except Exception as e:
                            debug_print(f"Failed to fetch {v_type} tab: {e}")

                if all_entries:
                    info['entries'] = all_entries
                    debug_print(f"Total Combined Entries: {len(all_entries)}")
                else:
                    debug_print("No entries found in recursive scan.")

            return {"status": "success", "data": info}
        except Exception as e:
            err_msg = str(e)
            debug_print(f"Channel Analyze Error: {err_msg}")
            # Reuse error handling logic if needed, or stick to simple propagation
            return {"status": "error", "error": err_msg}

    async def enrich_with_api(self, video_list, api_key):
        return await asyncio.to_thread(self._enrich_with_api_sync, video_list, api_key)
        
    def _enrich_with_api_sync(self, video_list, api_key):
        """
        Batch fetch metadata from YouTube Data API v3 videos endpoint.
        Up to 50 IDs per request.
        """
        import requests
        
        if not video_list or not api_key:
            return video_list

        base_url = "https://www.googleapis.com/youtube/v3/videos"
        enriched_list = []
        
        # Create a map for quick lookup and preservation of other data
        # Only enrich items that have an ID
        id_map = {v.get('id'): v for v in video_list if v.get('id')}
        all_ids = list(id_map.keys())
        
        # Chunk IDs into batches of 50
        chunks = [all_ids[i:i + 50] for i in range(0, len(all_ids), 50)]
        debug_print(f"Enriching {len(all_ids)} videos via API in {len(chunks)} batches...")
        
        for i, chunk in enumerate(chunks):
            try:
                ids_str = ",".join(chunk)
                params = {
                    'part': 'snippet,contentDetails,statistics',
                    'id': ids_str,
                    'key': api_key
                }
                resp = requests.get(base_url, params=params, timeout=10)
                data = resp.json()
                
                if 'items' in data:
                    for item in data['items']:
                        vid = item.get('id')
                        if vid in id_map:
                            snippet = item.get('snippet', {})
                            stats = item.get('statistics', {})
                            content = item.get('contentDetails', {})
                            
                            # Merge API data into existing dict
                            v_data = id_map[vid]
                            v_data['title'] = snippet.get('title', v_data.get('title'))
                            # Date: 2023-01-01T12:00:00Z -> 20230101 (to match yt-dlp format mostly, or keep ISO?)
                            # Let's keep raw ISO for app to parse, or convert to YYYYMMDD?
                            # App expects 'upload_date' as YYYYMMDD string usually from yt-dlp.
                            # API gives ISO. Let's provide both or standardise.
                            # Let's simple keep standard ISO in a new field 'upload_date_iso' or override 'upload_date' if we parse it.
                            # Standard yt-dlp 'upload_date' is '20230101'.
                            pub_at = snippet.get('publishedAt', '')
                            if pub_at:
                                v_data['upload_date'] = pub_at.replace('-', '').replace(':', '').split('T')[0]
                            
                            # Duration: PT1M30S -> seconds?
                            # yt-dlp gives seconds (int). 
                            # Parsing ISO8601 duration is annoying without isodate lib.
                            # Simple regex or keeping as string?
                            # App logic: if isinstance(raw_dur, (int, float)): ... else: duration = str(raw_dur)
                            # So we can leave it as ISO string if we handle it in App, OR parse it.
                            # Let's parse simply if possible, or just pass 'duration_iso'.
                            v_data['duration'] = self._parse_iso_duration(content.get('duration', ''))
                            
                            v_data['view_count'] = stats.get('viewCount', v_data.get('view_count'))
                            v_data['like_count'] = stats.get('likeCount', 0)
                            v_data['comment_count'] = stats.get('commentCount', 0)
                            v_data['description'] = snippet.get('description', '')
                            v_data['tags'] = snippet.get('tags', [])
                            
            except Exception as e:
                debug_print(f"API Batch {i} failed: {e}")
                
        return list(id_map.values())

    def _parse_iso_duration(self, duration_str):
        """Simple ISO 8601 duration parser (PT1H2M10S -> seconds)"""
        import re
        if not duration_str: return 0
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)?S)?', duration_str)
        if not match: return 0
        h = int(match.group(1) or 0)
        m = int(match.group(2) or 0)
        s = int(match.group(3) or 0)
        return h * 3600 + m * 60 + s
