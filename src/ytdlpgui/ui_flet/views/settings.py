import flet as ft
import asyncio
import os

class SettingsView(ft.Column):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.config = app_instance.config
        # We need worker to get deps manager
        self.deps = app_instance.worker.deps
        self.app_updater = app_instance.app_updater
        
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        self.spacing = 20
        
        self.init_ui()

    def did_mount(self):
        # Initial checks
        if self.app.page:
             self.app.page.run_task(self.check_env)
             self.app.page.run_task(self.refresh_app_update_status)

    def will_unmount(self):
        pass

    def init_ui(self):
        # Create persistent pickers - REMOVED for imperative API
        # self.dir_picker = ft.FilePicker()
        # self.dir_picker.on_result = self.on_dir_picked
        # self.cookie_picker = ft.FilePicker()
        # self.cookie_picker.on_result = self.on_cookie_picked
        
        # Add them to controls so they are mounted
        # self.controls.extend([self.dir_picker, self.cookie_picker])
        
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
        self.ytdlp_status = ft.Text("检测中...", color=ft.Colors.GREY)
        self.deno_status = ft.Text("检测中...", color=ft.Colors.GREY)
        
        self.ffmpeg_btn = ft.OutlinedButton("安装 FFmpeg / FFprobe", on_click=lambda e: self.install_component("FFmpeg / FFprobe", self.deps.install_ffmpeg))
        self.ytdlp_btn = ft.OutlinedButton("安装 yt-dlp", on_click=lambda e: self.install_component("yt-dlp", self.deps.install_ytdlp))
        self.deno_btn = ft.OutlinedButton("安装 Deno", on_click=lambda e: self.install_component("Deno", self.deps.install_deno))
        
        # Version
        self.version_text = ft.Text("当前内核版本: 检测中...")
        self.update_btn = ft.FilledButton("更新 yt-dlp", icon=ft.Icons.UPDATE, on_click=self.update_kernel)
        self.app_version_text = ft.Text(f"当前应用版本: {self.app_updater.current_version}")
        self.app_update_status = ft.Text("应用更新状态：未检查", color=ft.Colors.GREY)
        self.app_update_btn = ft.FilledButton(
            "检查应用更新",
            icon=ft.Icons.SYSTEM_UPDATE_ALT,
            on_click=self.check_app_update,
        )

        self.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("FFmpeg:", weight=ft.FontWeight.BOLD), self.ffmpeg_status, self.ffmpeg_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([ft.Text("yt-dlp:", weight=ft.FontWeight.BOLD), self.ytdlp_status, self.ytdlp_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([ft.Text("Deno引擎:", weight=ft.FontWeight.BOLD), self.deno_status, self.deno_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([self.version_text, self.update_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Row([self.app_version_text, self.app_update_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.app_update_status,
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
        ff_ver, ffprobe_ver, ytdlp_ver, deno_ver = await asyncio.to_thread(self._get_env_status)
        
        if self.page:  # Check if page is still available before updating
            if ff_ver and ffprobe_ver:
                self.ffmpeg_status.value = f"已安装 ({ff_ver})"
                self.ffmpeg_status.color = ft.Colors.GREEN
                self.ffmpeg_btn.disabled = True
                self.ffmpeg_btn.text = "已就绪"
            else:
                self.ffmpeg_status.value = "未安装完整"
                self.ffmpeg_status.color = ft.Colors.RED
                self.ffmpeg_btn.disabled = False

            if ytdlp_ver:
                self.ytdlp_status.value = f"已安装 ({ytdlp_ver})"
                self.ytdlp_status.color = ft.Colors.GREEN
                self.ytdlp_btn.disabled = True
                self.ytdlp_btn.text = "已就绪"
                self.version_text.value = f"当前内核版本: {ytdlp_ver}"
            else:
                self.ytdlp_status.value = "未安装"
                self.ytdlp_status.color = ft.Colors.RED
                self.ytdlp_btn.disabled = False
                self.version_text.value = "当前内核版本: 未安装"
                
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
        ffprobe = self.deps.get_ffprobe_version() if self.deps.is_ffprobe_installed() else None
        ytdlp = self.deps.get_ytdlp_version() if self.deps.is_ytdlp_installed() else None
        deno = self.deps.get_deno_version() if self.deps.is_deno_installed() else None
        return ff, ffprobe, ytdlp, deno

    async def select_dir(self, e):
        path = await ft.FilePicker().get_directory_path()
        if path:
            self.config.set_download_dir(path)
            self.dir_input.value = path
            self.dir_input.update()

    async def select_cookie(self, e):
        files = await ft.FilePicker().pick_files(allow_multiple=False, allowed_extensions=["txt"])
        if files and len(files) > 0:
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

    def _set_app_update_status(self, message, color=ft.Colors.GREY):
        self.app_update_status.value = f"应用更新状态：{message}"
        self.app_update_status.color = color
        self.app_update_status.update()

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
            latest_ver = await self.deps.get_latest_ytdlp_version()
            current_ver = self.deps.get_ytdlp_version()
            
            if current_ver and latest_ver == current_ver:
                self._show_snack(f"当前已是最新版本 ({current_ver})")
                self.update_btn.disabled = False
                self.update_btn.text = "更新 yt-dlp"
                self.update()
                return

            self.update_btn.text = f"正在更新至 {latest_ver}..."
            self.update()
            
            await self.deps.install_ytdlp()
            await self.check_env()
            self._show_snack(f"内核更新成功 ({latest_ver or self.deps.get_ytdlp_version()})")
            
        except Exception as ex:
            self._show_snack(f"更新失败: {str(ex)}")
            
        self.update_btn.disabled = False
        self.update_btn.text = "更新 yt-dlp"
        self.update()

    async def refresh_app_update_status(self):
        metadata = self.app.available_app_update
        if metadata and self.app_updater.is_update_available(metadata):
            self._set_app_update_status(f"发现新版本 {metadata.version}", ft.Colors.GREEN)

    async def check_app_update(self, e):
        self.app_update_btn.disabled = True
        self.app_update_btn.text = "检查中..."
        self.update()

        try:
            metadata = await asyncio.to_thread(self.app_updater.fetch_latest, "in_app_update")
            self.app.available_app_update = metadata

            if not self.app_updater.is_update_available(metadata):
                self._set_app_update_status("当前已是最新版本", ft.Colors.GREEN)
                self._show_snack(f"当前已是最新版本 ({self.app_updater.current_version})")
                return

            self._set_app_update_status(f"发现新版本 {metadata.version}", ft.Colors.GREEN)
            self._show_app_update_dialog(metadata)
        except Exception as ex:
            self._set_app_update_status("检查失败", ft.Colors.RED)
            self._show_snack(f"应用更新检查失败: {str(ex)}")
        finally:
            self.app_update_btn.disabled = False
            self.app_update_btn.text = "检查应用更新"
            self.update()

    def _show_app_update_dialog(self, metadata):
        notes = metadata.notes.strip() or "本版本未提供更新说明。"
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"发现新版本 {metadata.version}"),
            content=ft.Column(
                [
                    ft.Text(f"发布时间：{metadata.published_at or '未知'}"),
                    ft.Text(f"更新包：{metadata.filename}"),
                    ft.Text("更新说明："),
                    ft.Text(notes, selectable=True),
                ],
                tight=True,
                spacing=10,
            ),
            actions=[
                ft.TextButton("稍后", on_click=lambda e: self._close_dialog(dialog)),
                ft.FilledButton(
                    "下载并安装",
                    on_click=lambda e: self._start_app_update_from_dialog(dialog, metadata),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app.page.show_dialog(dialog)

    def _close_dialog(self, dialog):
        if dialog.open:
            dialog.open = False
            self.app.page.update()

    def _start_app_update_from_dialog(self, dialog, metadata):
        self._close_dialog(dialog)
        self.app.page.run_task(self.download_and_apply_app_update, metadata)

    async def download_and_apply_app_update(self, metadata):
        self.app_update_btn.disabled = True
        self.app_update_btn.text = "下载更新中..."
        self._set_app_update_status(f"正在下载 {metadata.version}", ft.Colors.PRIMARY)
        self.update()

        try:
            pending = await asyncio.to_thread(self.app_updater.stage_in_app_update, metadata)
            self._set_app_update_status(f"已准备安装 {metadata.version}", ft.Colors.GREEN)
            self._show_snack("更新已下载完成，应用即将退出并安装")
            await asyncio.sleep(1)
            await asyncio.to_thread(self.app_updater.launch_pending_update, pending, os.getpid())
            os._exit(0)
        except Exception as ex:
            self._set_app_update_status("安装失败", ft.Colors.RED)
            self._show_snack(f"应用更新失败: {str(ex)}")
            self.app_update_btn.disabled = False
            self.app_update_btn.text = "检查应用更新"
            self.update()
