import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import asyncio

class SettingsWindow(toga.Window):
    def __init__(self, app_instance):
        super().__init__(title="配置与环境", size=(450, 300))
        self.app_instance = app_instance
        # Worker has `deps` (DependencyManager)
        self.deps = app_instance.worker.deps 
        self.init_ui()

    def init_ui(self):
        self.config = self.app_instance.config
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20))
        
        # --- 1. General Settings ---
        main_box.add(toga.Label("通用设置", style=Pack(font_weight='bold', font_size=14, padding_bottom=10)))
        
        # Download Directory
        dir_box = toga.Box(style=Pack(direction=ROW, alignment="center", padding_bottom=15))
        dir_box.add(toga.Label("下载目录:", style=Pack(width=70)))
        
        self.dir_input = toga.TextInput(readonly=True, style=Pack(flex=1, padding=(0, 10)))
        self.dir_input.value = self.config.get_download_dir()
        
        browse_btn = toga.Button("更改...", on_press=self.select_download_dir)
        dir_box.add(self.dir_input)
        dir_box.add(browse_btn)
        main_box.add(dir_box)
        
        main_box.add(toga.Divider(style=Pack(padding_bottom=15)))

        # --- 2. Environment ---
        main_box.add(toga.Label("运行环境检测", style=Pack(padding_bottom=10, font_weight='bold', font_size=14)))

        # FFmpeg
        ffmpeg_box = toga.Box(style=Pack(direction=ROW, padding=5, alignment="center"))
        self.ffmpeg_label = toga.Label("FFmpeg: 检测中...", style=Pack(flex=1))
        self.ffmpeg_btn = toga.Button("安装", on_press=self.install_ffmpeg, style=Pack(width=80), enabled=False) # Initially disabled
        ffmpeg_box.add(self.ffmpeg_label)
        ffmpeg_box.add(self.ffmpeg_btn)
        main_box.add(ffmpeg_box)

        # Deno
        deno_box = toga.Box(style=Pack(direction=ROW, padding=5, alignment="center"))
        self.deno_label = toga.Label("Deno: 检测中...", style=Pack(flex=1))
        self.deno_btn = toga.Button("安装", on_press=self.install_deno, style=Pack(width=80), enabled=False) # Initially disabled
        deno_box.add(self.deno_label)
        deno_box.add(self.deno_btn)
        main_box.add(deno_box)
        
        # Info
        main_box.add(toga.Divider(style=Pack(padding=(15, 0))))
        info_lbl = toga.Label("所有组件将安装到 ~/.ytdlpgui/bin，不影响系统环境。", 
                              style=Pack(padding=(10, 0), font_size=11, color='#666666'))
        main_box.add(info_lbl)
        
        main_box.add(toga.Divider(style=Pack(padding=(15, 0))))
        
        # --- 2b. Cookie Injection (for Douyin etc) ---
        main_box.add(toga.Label("Cookie 注入 (解决 Douyin 报错)", style=Pack(padding_bottom=10, font_weight='bold', font_size=14)))
        
        cookie_box = toga.Box(style=Pack(direction=ROW, alignment="center", padding_bottom=5))
        cookie_box.add(toga.Label("Cookie File:", style=Pack(width=70)))
        
        self.cookie_input = toga.TextInput(readonly=True, placeholder="未选择 (使用默认浏览器)", style=Pack(flex=1, padding=(0, 10)))
        self.cookie_input.value = self.config.get_cookie_file()
        
        cookie_browse_btn = toga.Button("选择...", on_press=self.select_cookie_file)
        cookie_clear_btn = toga.Button("清除", on_press=self.clear_cookie_file, style=Pack(padding_left=5))
        
        cookie_box.add(self.cookie_input)
        cookie_box.add(cookie_browse_btn)
        cookie_box.add(cookie_clear_btn)
        main_box.add(cookie_box)
        
        cookie_info = toga.Label("注意: 设置此项后将忽略上方浏览器选择，强制使用该 cookies.txt", 
                               style=Pack(padding=(0, 0, 10, 0), font_size=11, color='#666666'))
        main_box.add(cookie_info)
        
        main_box.add(toga.Divider(style=Pack(padding_bottom=15)))

        # --- 3. Run Environment ---
        # --- 3. Kernel Updates ---
        import yt_dlp
        self.current_version = yt_dlp.version.__version__
        
        kernel_box = toga.Box(style=Pack(direction=COLUMN, padding_top=15))
        
        # Advanced Settings Row
        settings_box = toga.Box(style=Pack(direction=ROW, alignment="center", padding_bottom=5))
        
        # Source Selection
        self.sources = {
            "官方源 (Generic)": "https://pypi.org/pypi/yt-dlp/json",
            "清华源 (Tsinghua)": "https://pypi.tuna.tsinghua.edu.cn/pypi/yt-dlp/json",
            "阿里源 (Aliyun)": "https://mirrors.aliyun.com/pypi/yt-dlp/json"
        }
        # Invert map for lookup
        self.source_urls = {v: k for k, v in self.sources.items()}
        
        saved_key = self.app_instance.config.get_update_source()
        # Map saved key (e.g. 'official') to display label if needed, 
        # but simplified: let's just store the URL or a simple key.
        # Let's map legacy 'official' to the full URL or just use keys.
        # To be safe, let's just select based on what's in config or default to Tsinghua since user asked.
        
        # Simplified: We store the KEY name in config for display consistency using `on_change`
        
        self.source_select = toga.Selection(
            items=list(self.sources.keys()),
            style=Pack(width=140),
            on_change=self.on_source_change
        )
        
        # Set selection
        current_source_key = self.config.get_update_source()
        if current_source_key in self.sources:
             self.source_select.value = current_source_key
        elif current_source_key == "official": # Legacy migration
             self.source_select.value = "官方源 (Generic)"
        else:
             self.source_select.value = "官方源 (Generic)" # Fallback

        settings_box.add(toga.Label("源:", style=Pack(padding_right=5)))
        settings_box.add(self.source_select)
        
        # Removed Timeout input as per user request (default 30s in code)
        
        kernel_box.add(settings_box)

        self.version_label = toga.Label(f"当前版本: {self.current_version} (准备检查...)", style=Pack(font_weight='bold', padding_bottom=5))
        kernel_box.add(self.version_label)
        
        update_box = toga.Box(style=Pack(direction=ROW, padding_top=5, alignment="center"))
        # Initial state: Checking...
        self.update_btn = toga.Button("请稍候...", on_press=self.update_kernel, enabled=False)
        update_box.add(self.update_btn)
        kernel_box.add(update_box)
        main_box.add(kernel_box)
        
        main_box.add(toga.Divider(style=Pack(padding=(10, 0))))

        # Progress Section
        self.progress_label = toga.Label("就绪", style=Pack(padding_top=5, font_size=11))
        self.progress = toga.ProgressBar(style=Pack(padding_top=5, flex=1))
        main_box.add(self.progress_label)
        main_box.add(self.progress)
        
        # Trigger check with delay to let UI render
        asyncio.create_task(self.check_for_updates())
        asyncio.create_task(self.update_env_status())
        
        self.content = main_box

    async def update_env_status(self):
        # Run subprocess checks in thread to avoid blocking UI
        loop = asyncio.get_running_loop()
        
        def get_status():
            ff_ver = self.deps.get_ffmpeg_version() if self.deps.is_ffmpeg_installed() else None
            deno_ver = self.deps.get_deno_version() if self.deps.is_deno_installed() else None
            return ff_ver, deno_ver

        ff_ver, deno_ver = await asyncio.to_thread(get_status)

        # Update UI on main thread
        def update_ui():
            if ff_ver:
                self.ffmpeg_label.text = f"FFmpeg: ✅ 已安装 ({ff_ver})"
                self.ffmpeg_btn.text = "已安装"
                self.ffmpeg_btn.enabled = False
            else:
                self.ffmpeg_label.text = "FFmpeg: ❌ 未安装 (将自动降级画质)"
                self.ffmpeg_btn.text = "安装"
                self.ffmpeg_btn.enabled = True
                
            if deno_ver:
                if "Unknown" in deno_ver:
                     self.deno_label.text = f"Deno: ⚠️ 已安装 (未知版本)"
                     self.deno_btn.text = "重新安装"
                     self.deno_btn.enabled = True
                else:
                     self.deno_label.text = f"Deno: ✅ 已安装 ({deno_ver})"
                     self.deno_btn.text = "已安装"
                     self.deno_btn.enabled = False
            else:
                self.deno_label.text = "Deno: ❌ 未安装 (推荐)"
                self.deno_btn.text = "安装"
                self.deno_btn.enabled = True

        loop.call_soon_threadsafe(update_ui)
            
    # Legacy sync method removed or kept as empty if referenced elsewhere (unlikely)
    def refresh_status(self):
        asyncio.create_task(self.update_env_status())

    async def select_download_dir(self, widget):
        try:
            path = await self.app_instance.main_window.select_folder_dialog("选择下载目录")
            if path:
                self.config.set_download_dir(str(path))
                self.dir_input.value = str(path)
        except ValueError:
            pass # User cancelled

    async def select_cookie_file(self, widget):
        try:
            # Filter for txt files or all files
            path = await self.app_instance.main_window.open_file_dialog("选择 cookies.txt", file_types=["txt"])
            if path:
                self.config.set_cookie_file(str(path))
                self.cookie_input.value = str(path)
        except ValueError:
            pass # User cancelled

    def clear_cookie_file(self, widget):
        self.config.set_cookie_file("")
        self.cookie_input.value = ""

    async def install_ffmpeg(self, widget):
        await self._install_task("ffmpeg", self.deps.install_ffmpeg)

    async def install_deno(self, widget):
        await self._install_task("deno", self.deps.install_deno)

    async def _install_task(self, name, install_func):
        self.ffmpeg_btn.enabled = False
        self.deno_btn.enabled = False
        self.progress.value = 0
        self.progress_label.text = f"正在下载 {name}..."
        
        # Helper for thread-safe UI update
        loop = asyncio.get_running_loop()
        def on_progress(p, msg):
             loop.call_soon_threadsafe(lambda: setattr(self.progress, 'value', p))
             loop.call_soon_threadsafe(lambda: setattr(self.progress_label, 'text', msg))

        try:
            await install_func(progress_callback=on_progress)
            self.progress_label.text = f"{name} 安装成功！"
            # Refresh to lock buttons
            self.refresh_status()
        except Exception as e:
            self.progress_label.text = f"安装失败: {str(e)}"
            # Re-enable buttons on failure
            self.refresh_status()

    async def update_kernel(self, widget):
        self.update_btn.enabled = False
        self.progress.value = 0
        self.progress_label.text = "正在更新内核..."
        
        loop = asyncio.get_running_loop()
        def on_progress(p, msg):
             loop.call_soon_threadsafe(lambda: setattr(self.progress, 'value', p))
             loop.call_soon_threadsafe(lambda: setattr(self.progress_label, 'text', msg))

        try:
            await self.deps.update_ytdlp(progress_callback=on_progress)
            self.progress_label.text = "更新成功！请重启 App 生效。"
            self.app_instance.main_window.info_dialog("更新成功", "新内核已就绪，请重启应用程序以生效。")
            
            # Re-check version after update
            await self.check_for_updates()
            
        except Exception as e:
            self.progress_label.text = f"更新失败: {str(e)}"
            self.update_btn.enabled = True

    def on_source_change(self, widget):
        key = widget.value
        self.config.set_update_source(key)
        # Trigger re-check
        self.version_label.text = f"核心版本: {self.current_version} (切换源检测中...)"
        asyncio.create_task(self.check_for_updates())

    # Timeout handler removed

    def _normalize_version(self, v_str):
        # normalize '2025.12.08' to '2025.12.8' for comparison
        # Simple method: split by dot, convert to int
        try:
            return [int(x) for x in v_str.split('.')]
        except:
            return v_str 

    async def check_for_updates(self):
        # Get config
        source_label = self.config.get_update_source()
        if source_label not in self.sources:
            source_label = "官方源 (Generic)"
        
        url = self.sources.get(source_label, "https://pypi.org/pypi/yt-dlp/json")
        timeout = 30 # Hardcoded 30s as requested
        
        # Ensure UI updates on main thread to be safe, though Toga usually handles await return fine.
        loop = asyncio.get_running_loop()
        def update_ui(label_text, btn_text, btn_enabled):
            self.version_label.text = label_text
            self.update_btn.text = btn_text
            self.update_btn.enabled = btn_enabled

        loop.call_soon_threadsafe(lambda: update_ui(f"核心版本: {self.current_version} (正在连接 '{source_label}'...)", "检查中...", False))
        
        latest = await self.deps.get_latest_ytdlp_version(url=url, timeout=timeout)
        
        if not latest:
            loop.call_soon_threadsafe(lambda: update_ui(f"核心版本: {self.current_version} (连接超时或失败)", "强制更新", True))
            return

        # Compare using normalized list
        norm_latest = self._normalize_version(latest)
        norm_current = self._normalize_version(self.current_version)

        if norm_latest != norm_current:
            is_newer = False
            try:
                if norm_latest > norm_current: is_newer = True
            except:
                pass
            
            if is_newer:
                 loop.call_soon_threadsafe(lambda: update_ui(f"核心版本: {self.current_version} -> 新版本: {latest}", f"更新至 {latest}", True))
            else:
                 # Version string different but logically not newer (or equal/older)
                 loop.call_soon_threadsafe(lambda: update_ui(f"核心版本: {self.current_version} (已是最新)", "已是最新", False))
        else:
            loop.call_soon_threadsafe(lambda: update_ui(f"核心版本: {self.current_version} (已是最新)", "已是最新", False))
