import flet as ft
import asyncio
import yt_dlp

class SettingsView(ft.Column):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.config = app_instance.config
        # We need worker to get deps manager
        self.deps = app_instance.worker.deps
        
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 20
        
        self.init_ui()

    def did_mount(self):
        # Initial checks
        if self.app.page:
             self.app.page.run_task(self.check_env)

    def will_unmount(self):
        pass

    def init_ui(self):
        self.controls.append(ft.Text("系统设置", size=28, weight=ft.FontWeight.BOLD))
        
        # 1. General Settings
        self.controls.append(ft.Text("基础配置", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY))
        
        self.dir_input = ft.TextField(
            label="下载目录",
            value=self.config.get_download_dir(),
            read_only=True,
            expand=True,
            border_radius=10
        )
        
        self.controls.append(
            ft.Container(
                content=ft.Row([
                    self.dir_input,
                    ft.ElevatedButton("更改目录", icon=ft.Icons.FOLDER_OPEN, on_click=self.select_dir)
                ]),
                padding=15,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=10
            )
        )
        
        # 2. Advanced
        self.controls.append(ft.Text("高级功能", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY))
        
        self.api_key_input = ft.TextField(
            label="YouTube Data API Key (可选)",
            hint_text="配置 API Key 可加速列表获取",
            value=self.config.get_youtube_api_key(),
            password=True,
            can_reveal_password=True,
            on_change=lambda e: self.config.set_youtube_api_key(e.control.value),
            border_radius=10
        )
        
        self.cookie_input = ft.TextField(
            label="Cookie 文件路径 (Netscape 格式)",
            value=self.config.get_cookie_file(),
            read_only=True,
            expand=True,
            border_radius=10
        )
        
        self.controls.append(
            ft.Container(
                content=ft.Column([
                    self.api_key_input,
                    ft.Row([
                        self.cookie_input,
                        ft.IconButton(ft.Icons.FILE_UPLOAD, tooltip="选择文件", on_click=self.select_cookie),
                        ft.IconButton(ft.Icons.CLEAR, tooltip="清除", on_click=self.clear_cookie)
                    ])
                ], spacing=15),
                padding=15,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=10
            )
        )
        
        # 3. Environment & Updates
        self.controls.append(ft.Text("环境与更新", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY))
        
        # Status indicators
        self.ffmpeg_status = ft.Text("检测中...", color=ft.Colors.GREY)
        self.deno_status = ft.Text("检测中...", color=ft.Colors.GREY)
        
        self.ffmpeg_btn = ft.OutlinedButton("安装 FFmpeg", on_click=lambda e: self.install_component("FFmpeg", self.deps.install_ffmpeg))
        self.deno_btn = ft.OutlinedButton("安装 Deno", on_click=lambda e: self.install_component("Deno", self.deps.install_deno))
        
        # Version
        current_ver = yt_dlp.version.__version__
        self.version_text = ft.Text(f"当前内核版本: {current_ver}")
        self.update_btn = ft.FilledButton("检查更新", icon=ft.Icons.UPDATE, on_click=self.update_kernel)
        
        self.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("FFmpeg:", weight=ft.FontWeight.BOLD), self.ffmpeg_status, self.ffmpeg_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([ft.Text("Deno引擎:", weight=ft.FontWeight.BOLD), self.deno_status, self.deno_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([self.version_text, self.update_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]),
                padding=15,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=10
            )
        )
        
    def set_pickers(self, dir_picker, cookie_picker):
        """Deprecated: Dependency Injection no longer used. Pickers are lazy-loaded."""
        pass


    async def check_env(self):
        # Run checks in thread
        ff_ver, deno_ver = await asyncio.to_thread(self._get_env_status)
        
        if self.page:  # Check if page is still available before updating
            if ff_ver:
                self.ffmpeg_status.value = f"已安装 ({ff_ver})"
                self.ffmpeg_status.color = ft.Colors.GREEN
                self.ffmpeg_btn.disabled = True
                self.ffmpeg_btn.text = "已就绪"
            else:
                self.ffmpeg_status.value = "未安装"
                self.ffmpeg_status.color = ft.Colors.RED
                self.ffmpeg_btn.disabled = False
                
            if deno_ver:
                self.deno_status.value = f"已安装 ({deno_ver})"
                self.deno_status.color = ft.Colors.GREEN
                self.deno_btn.disabled = True
                self.deno_btn.text = "已就绪"
            else:
                self.deno_status.value = "未安装"
                self.deno_status.color = ft.Colors.RED
                self.deno_btn.disabled = False
                
            self.update()

    def _get_env_status(self):
        ff = self.deps.get_ffmpeg_version() if self.deps.is_ffmpeg_installed() else None
        deno = self.deps.get_deno_version() if self.deps.is_deno_installed() else None
        return ff, deno

    async def select_dir(self, e):
        # New API style for Flet >= 0.80.0
        # No overlay needed, just await the result
        path = await ft.FilePicker().get_directory_path()
        if path:
            self.config.set_download_dir(path)
            self.dir_input.value = path
            self.dir_input.update()

    async def select_cookie(self, e):
        # New API style
        files = await ft.FilePicker().pick_files(allow_multiple=False, allowed_extensions=["txt"])
        if files:
            path = files[0].path
            self.config.set_cookie_file(path)
            self.cookie_input.value = path
            self.cookie_input.update()

    def clear_cookie(self, e):
        self.config.set_cookie_file("")
        self.cookie_input.value = ""
        self.cookie_input.update()

    def _show_snack(self, message):
        # Use show_dialog as per SnackBar docstring for this version
        self.app.page.show_dialog(ft.SnackBar(content=ft.Text(message)))

    async def install_component(self, name, func):
        self._show_snack(f"开始安装 {name}...")
        try:
            await func()
            self._show_snack(f"{name} 安装成功！")
            await self.check_env()
        except Exception as e:
            self._show_snack(f"安装失败: {str(e)}")

    async def update_kernel(self, e):
        self.update_btn.disabled = True
        self.update_btn.text = "检查中..."
        self.update()
        
        try:
            # 1. Check version first
            latest_ver = await self.deps.get_latest_ytdlp_version()
            current_ver = yt_dlp.version.__version__
            
            if latest_ver == current_ver:
                self._show_snack(f"当前已是最新版本 ({current_ver})")
                self.update_btn.disabled = False
                self.update_btn.text = "检查更新"
                self.update()
                return

            # 2. Update if new version available
            self.update_btn.text = f"正在更新至 {latest_ver}..."
            self.update()
            
            await self.deps.update_ytdlp()
            self._show_snack(f"内核更新成功 ({latest_ver})，请重启应用生效")
            
        except Exception as ex:
            self._show_snack(f"更新失败: {str(ex)}")
            
        self.update_btn.disabled = False
        self.update_btn.text = "检查更新"
        self.update()
