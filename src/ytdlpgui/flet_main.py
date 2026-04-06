import flet as ft
import os
import asyncio
from .ui_flet.views.downloader import DownloaderView
from .ui_flet.views.analyzer import AnalyzerView
from .ui_flet.views.splitter import SplitterView
from .ui_flet.views.settings import SettingsView
from .config import ConfigManager
from .core.app_update import AppUpdateManager
from .core.worker import YtDlpWorker

class VeloGetApp:
    def __init__(self):
        self.config = ConfigManager()
        self.app_updater = AppUpdateManager(self.config.config_dir)
        self.worker = YtDlpWorker()
        self.available_app_update = None


    async def main(self, page: ft.Page):
        self.page = page
        page.title = "VeloGet"
        # Attempt to set window icon (effective on Windows/Linux, may not work for macOS Dock in dev mode)
        page.window.icon = "logo.png" 
        page.theme_mode = ft.ThemeMode.LIGHT
        
        # Ensure window size is reasonable
        page.window.width = 1400
        page.window.height = 950
        page.window.min_width = 950

        # Handle Drag and Drop
        page.on_file_drop = self.on_file_drop
        
        # Content Area
        from .core.utils import debug_print
        debug_print("DEBUG: Initializing Views...")
        
        self.downloader_view = DownloaderView(self)
        self.analyzer_view = AnalyzerView(self)
        try:
            self.splitter_view = SplitterView(self)
        except Exception as e:
            debug_print(f"CRITICAL: Failed to create SplitterView: {e}")
            # Fallback
            self.splitter_view = ft.Text(f"Splitter View Load Error: {e}")
            
        self.settings_view = SettingsView(self)

        
        self.divider = ft.VerticalDivider(width=1)
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.DOWNLOAD, 
                    selected_icon=ft.Icons.DOWNLOAD, 
                    label="视频下载"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS, 
                    selected_icon=ft.Icons.ANALYTICS, 
                    label="频道分析"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CUT, 
                    selected_icon=ft.Icons.CUT, 
                    label="视频切割"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS, 
                    selected_icon=ft.Icons.SETTINGS, 
                    label="系统设置"
                ),
            ],
            on_change=self.on_nav_change,
        )

        self.divider = ft.VerticalDivider(width=1)
        
        # Main Content Container
        self.content_container = ft.Container(
            content=self.downloader_view, 
            expand=True, 
            padding=20
        )

        # Main Layout
        self.page.add(
            ft.Row(
                [
                    self.rail,
                    self.divider,
                    self.content_container,
                ],
                expand=True,
            )
        )
        
        self.page.update()
        await self.page.window.center()
        self.page.run_task(self.check_app_update_silently)

    def on_nav_change(self, e):
        index = e.control.selected_index
        content = self.downloader_view
        if index == 1:
            content = self.analyzer_view
        elif index == 2:
            content = self.splitter_view
        elif index == 3:
            content = self.settings_view
            
        # Robust update using direct reference
        self.content_container.content = content
        self.content_container.update()

    def on_file_drop(self, e):
        # Route file drop to active view if it supports it
        # Index 2 is Splitter
        if self.rail.selected_index == 2:
             self.splitter_view.handle_file_drop(e)

    async def check_app_update_silently(self):
        try:
            metadata = await asyncio.to_thread(self.app_updater.fetch_latest, "in_app_update")
        except Exception:
            return

        if self.app_updater.is_update_available(metadata):
            self.available_app_update = metadata
            if self.page:
                self.page.show_dialog(
                    ft.SnackBar(content=ft.Text(f"发现新版本 {metadata.version}，可前往系统设置更新"))
                )

def run():
    import sys
    app = VeloGetApp()
    
    # Correct Asset Resolution Logic
    # In Dev (Source): assets/ is in project root (../../assets relative to this file)
    # In Prod (Frozen): assets/ is usually bundled alongside executable or in _MEIPASS
    
    if getattr(sys, 'frozen', False):
        # Packaged mode
        basedir = os.path.dirname(sys.executable)
        assets = os.path.join(basedir, "assets") # Default flet build structure?
        # Flet often handles assets automatically if bundled correctly.
        # But let's try to find where they are.
        if not os.path.exists(assets):
            # Try _MEIPASS for OneFile
            if hasattr(sys, '_MEIPASS'):
                 assets = os.path.join(sys._MEIPASS, "assets")
    else:
        # Source mode: src/ytdlpgui/flet_main.py -> ../../assets
        basedir = os.path.dirname(os.path.abspath(__file__))
        assets = os.path.abspath(os.path.join(basedir, "..", "..", "assets"))

    print(f"DEBUG: Assets directory resolved to: {assets}")
    
    ft.app(target=app.main, assets_dir=assets)

if __name__ == "__main__":
    run()
