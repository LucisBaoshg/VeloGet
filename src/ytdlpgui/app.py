
import asyncio
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import gc # Moved to top level for global access

from .config import ConfigManager
from .core.worker import YtDlpWorker
from .core.utils import scan_chrome_profiles

class YtDlpGUI(toga.App):
    def startup(self):
        # 0. Hot-Swap yt-dlp override
        import sys
        import os
        # gc import moved to top level
        from pathlib import Path
        
        updates_dir = Path.home() / ".ytdlpgui" / "updates"
        if updates_dir.exists():
            # Prepend to sys.path so we load the updated version
            sys.path.insert(0, str(updates_dir))

        # Debug Log
        log_file = Path.home() / "ytdlpgui_debug.log"
        log_file = Path.home() / "ytdlpgui_debug.log"
        with open(log_file, "a") as f:
            f.write("--- Toga App Startup Begin ---\n")

        try:
            self.config = ConfigManager()
            with open(log_file, "a") as f: f.write("Config init done\n")
            
            self.worker = YtDlpWorker()
            with open(log_file, "a") as f: f.write("Worker init done\n")
            
            # --- UI Components ---
            
            # 1. Browser/Profile Selection
            self.browser_select = toga.Selection(items=['chrome', 'firefox', 'safari'], on_change=self.on_browser_change)
            self.browser_select.value = self.config.get_last_browser()
            
            self.profile_select = toga.Selection(items=['Default']) # Updated dynamically
            self.update_profiles()
            self.profile_select.value = self.config.get_last_profile()
            
            top_box = toga.Box(style=Pack(direction=ROW, padding=10, alignment="center")) # Increased padding
            top_box.add(toga.Label("Browser:", style=Pack(padding_right=10)))
            top_box.add(self.browser_select)
            self.browser_select.style.padding_right = 10 
            top_box.add(self.profile_select)
            
            # Flexible spacer
            top_box.add(toga.Box(style=Pack(flex=1)))
            
            # Settings Button
            settings_btn = toga.Button("⚙️ 设置", on_press=self.open_settings, style=Pack(padding_left=10))
            top_box.add(settings_btn)

            # 2. URL Input
            self.url_input = toga.TextInput(placeholder="在此处粘贴视频 URL", style=Pack(flex=1))
            analyze_btn = toga.Button("分析链接", on_press=self.analyze_link)
            
            url_box = toga.Box(style=Pack(direction=ROW, padding=5))
            url_box.add(self.url_input)
            url_box.add(analyze_btn)
            
            # 3. Format List (Table)
            # Columns: ID, Format, Resolution, Size
            self.format_table = toga.Table(
                headings=["ID", "格式", "分辨率", "大小"],
                style=Pack(flex=1, padding=5),
                multiple_select=False
            )
            
            # 4. Download Status
            self.progress_bar = toga.ProgressBar(max=100, style=Pack(padding=5, flex=1))
            self.status_label = toga.Label("就绪", style=Pack(padding=5))
            download_btn = toga.Button("开始下载", on_press=self.download_video)
            
            status_box = toga.Box(style=Pack(direction=ROW, padding=5, alignment="center"))
            status_box.add(self.progress_bar)
            status_box.add(download_btn)
            
            # Main Layout
            main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))
            main_box.add(top_box)
            main_box.add(url_box)
            main_box.add(self.format_table)
            main_box.add(self.status_label)
            main_box.add(status_box)

            self.main_window = toga.MainWindow(title="VeloGet")
            self.main_window.content = main_box
            self.main_window.show()
            
            with open(log_file, "a") as f:
                f.write("--- Toga App Startup Finished ---\n")

        except Exception as e:
            import traceback
            with open(log_file, "a") as f:
                f.write(f"Startup Error: {e}\n")
                f.write(traceback.format_exc())
            raise e
        
    def update_profiles(self):
        if self.browser_select.value == 'chrome':
            profiles = scan_chrome_profiles()
            self.profile_select.items = profiles
        else:
            self.profile_select.items = []

    def on_browser_change(self, widget):
        self.update_profiles()
        self.config.set_last_browser(widget.value)

    def open_settings(self, widget):
        try:
            from .settings import SettingsWindow
            # Force GC to clean up any old windows on main thread
            gc.collect()
            # Keep specific reference to prevent GC issues
            self.settings_window = SettingsWindow(self)
            self.settings_window.show()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.main_window.error_dialog("无法打开设置", f"错误详情:\n{str(e)}")

    async def analyze_link(self, widget):
        url = self.url_input.value.strip()
        if not url:
            self.main_window.error_dialog("错误", "请输入视频链接")
            return

        self.status_label.text = "正在分析..."
        widget.enabled = False
        self.format_table.data = [] # Clear table
        
        # Run async analysis
        browser = self.browser_select.value
        profile = self.profile_select.value if self.profile_select.items else None
        
        # Force GC to clean up any old UI objects before threading
        gc.collect()
        
        result = await self.worker.analyze_url(url, browser, profile)
        
        widget.enabled = True
        
        if result['status'] == 'success':
            self.status_label.text = "分析完成，请选择格式下载"
            self.populate_table(result['data'])
            self.config.set_last_profile(profile)
        else:
            self.status_label.text = "分析失败"
            self.main_window.error_dialog("分析失败", result.get('error', '未知错误'))

    def populate_table(self, info):
        formats = info.get('formats', [])
        # Simple data processing similar to previous logic
        # Sort best to worst
        formats.sort(key=lambda x: x.get('tbr', 0) or 0, reverse=True)
        
        data = []
        # Add "Best" option
        data.append(("best", "自动最佳", "Best", "N/A"))
        
        seen_ids = set()
        for f in formats:
            fid = f.get('format_id')
            if fid in seen_ids: continue
            seen_ids.add(fid)
            
            # Simple filters (video only or best audio)
            if f.get('vcodec') == 'none' and f.get('acodec') == 'none': continue
            
            note = f.get('format_note', '')
            ext = f.get('ext', '')
            res = f"{f.get('width', '?')}x{f.get('height', '?')}"
            size = f"{int(f.get('filesize', 0)/1024/1024)}MB" if f.get('filesize') else "N/A"
            
            label = f"{ext} {note}"
            data.append((fid, label, res, size))
            
        self.format_table.data = data
        if data:
            # Toga tables don't support "selecting" row 0 programmatically easily in older versions, 
            # but user can click.
            pass

    async def download_video(self, widget):
        url = self.url_input.value.strip()
        selection = self.format_table.selection
        if not url or not selection:
            self.main_window.error_dialog("提示", "请确保已有URL并选择了下载格式")
            return

        selected_row = selection # selection returns the row object (which acts like a tuple/namedtuple)
        format_id = selected_row.id if hasattr(selected_row, 'id') else selected_row[0] # Try attribute or index
        
        self.status_label.text = "准备下载..."
        widget.enabled = False
        self.progress_bar.value = 0
        
        def on_log(msg):
             # Toga is not thread-safe for UI updates directly from bg thread usually, 
             # but asyncio.to_thread runs in thread.
             # However, this runs in the context of `await`, need to be careful.
             # Ideally we dispatch to main thread. Toga doesn't have `call_on_main_thread` exposed easily?
             # Toga updates are usually fine if triggered from async loop running on main thread.
             pass 

        def on_progress(percent):
            # Update progress bar
            # We must schedule this on UI loop if coming from thread
            # Toga 0.4+ integration with asyncio should handle this if we await properly
            # But the callback is called from the thread inside yt-dlp.
            # We strictly need `self.app.loop.call_soon_threadsafe` or `toga.App.app.loop...`
            # Since we are inside an App method, `asyncio.get_running_loop()` might work if we are in the loop.
            # But the callback is from a thread.
            # We will use formatting to keep it simple.
            pass

        # Since passing callbacks from thread to asyncio UI is tricky without valid `call_soon_threadsafe` reference
        # (available via `asyncio.get_event_loop()`), we implement a simple poller or wrapper? 
        # For simplicity, let's redefine callbacks to use self.main_window.app.loop.call_soon_threadsafe
        
        loop = asyncio.get_running_loop()
        
        def safe_progress(p):
            loop.call_soon_threadsafe(lambda: setattr(self.progress_bar, 'value', p))
            loop.call_soon_threadsafe(lambda: setattr(self.status_label, 'text', f"下载中... {p:.1f}%"))
            
        browser = self.browser_select.value
        profile = self.profile_select.value
        
        # Force GC to clean up any old UI objects before threading
        gc.collect()
        
        result = await self.worker.download_video(url, format_id, browser, profile, on_progress=safe_progress)
        
        widget.enabled = True
        if result['status'] == 'success':
            self.status_label.text = "下载完成！"
            self.progress_bar.value = 100
        else:
            self.status_label.text = "下载出错"
            self.main_window.error_dialog("下载错误", result.get('error', '未知错误'))

def main():
    return YtDlpGUI()
