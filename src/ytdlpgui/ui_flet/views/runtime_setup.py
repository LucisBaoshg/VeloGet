import asyncio
import flet as ft


class RuntimeSetupView(ft.Column):
    def __init__(self, app_instance, on_ready):
        super().__init__()
        self.app = app_instance
        self.deps = app_instance.worker.deps
        self.on_ready = on_ready

        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.spacing = 20

        self._build_ui()

    def did_mount(self):
        if self.page:
            self.page.run_task(self.install_runtime)

    def _build_ui(self):
        self.title_text = ft.Text("正在准备运行时组件", size=30, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(
            "首次启动需要联网下载 FFmpeg / FFprobe / yt-dlp，安装完成后才可继续使用。",
            color=ft.Colors.GREY_700,
            text_align=ft.TextAlign.CENTER,
        )
        self.status_text = ft.Text("等待开始...", color=ft.Colors.GREY)
        self.progress_bar = ft.ProgressBar(width=420, value=0)
        self.log_view = ft.ListView(height=180, width=720, spacing=8, auto_scroll=True)
        self.retry_btn = ft.FilledButton("重试安装", visible=False, on_click=self.retry_install)

        self.controls.append(
            ft.Container(
                width=760,
                padding=30,
                border_radius=18,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                content=ft.Column(
                    [
                        self.title_text,
                        self.subtitle_text,
                        self.status_text,
                        self.progress_bar,
                        ft.Container(
                            height=200,
                            border_radius=12,
                            padding=10,
                            bgcolor=ft.Colors.SURFACE,
                            content=self.log_view,
                        ),
                        ft.Row([self.retry_btn], alignment=ft.MainAxisAlignment.END),
                    ],
                    spacing=18,
                ),
            )
        )

    def _append_log(self, message):
        self.log_view.controls.append(ft.Text(message, size=12))
        if self.page:
            self.log_view.update()

    def retry_install(self, e):
        self.retry_btn.visible = False
        self.retry_btn.update()
        self.page.run_task(self.install_runtime)

    async def _install_component(self, label, installer):
        self._append_log(f"开始安装 {label}...")

        def on_progress(percent, message):
            self.status_text.value = message
            self.progress_bar.value = max(0, min(1, percent / 100.0))
            if self.page:
                self.status_text.update()
                self.progress_bar.update()

        await installer(progress_callback=on_progress)
        self._append_log(f"{label} 安装完成")

    async def install_runtime(self):
        self.status_text.value = "检查依赖状态..."
        self.progress_bar.value = 0
        self.update()

        missing = self.deps.get_missing_runtime_components()
        if not missing:
            await self._finish()
            return

        try:
            if "ffmpeg" in missing or "ffprobe" in missing:
                await self._install_component("FFmpeg / FFprobe", self.deps.install_ffmpeg)
            if "yt-dlp" in missing:
                await self._install_component("yt-dlp", self.deps.install_ytdlp)

            self.status_text.value = "运行时安装完成，正在进入应用..."
            self.progress_bar.value = 1
            self.update()
            await self._finish()
        except Exception as exc:
            self.status_text.value = f"安装失败：{exc}"
            self.progress_bar.value = 0
            self.retry_btn.visible = True
            self._append_log(f"安装失败：{exc}")
            self.update()

    async def _finish(self):
        result = self.on_ready()
        if asyncio.iscoroutine(result):
            await result
