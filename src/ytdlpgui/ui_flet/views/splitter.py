import flet as ft
import asyncio
import os
from ...core.splitter import MediaSplitter
from ...core.utils import debug_print

class SplitterView(ft.Column):
    def __init__(self, app_instance):
        super().__init__()
        try:
            debug_print("DEBUG: Initializing SplitterView...")
            self.app = app_instance
            self.config = app_instance.config
            self.splitter = MediaSplitter(self.config)
            self.expand = True
            self.spacing = 20
            self.selected_file = None
            
            # Initialize FilePicker here but add to page overlay in did_mount usually, 
            # or add to controls. Let's try adding to controls first as before but safer.
            self.file_picker = ft.FilePicker()
            self.file_picker.on_result = self.on_file_picked
            
            self.init_ui()
            debug_print("DEBUG: SplitterView initialized successfully")
        except Exception as e:
            debug_print(f"ERROR: SplitterView init failed: {e}")
            import traceback
            debug_print(traceback.format_exc())

    def did_mount(self):
        # FilePicker is already in controls, so no need to add to overlay
        pass

    def will_unmount(self):
        pass

    async def handle_pick_files(self, e):
        # Use new Flet imperative API as requested by user
        debug_print("DEBUG: Using imperative FilePicker.pick_files()")
        files = await ft.FilePicker().pick_files(allow_multiple=False)
        if files and len(files) > 0:
            file_path = files[0].path
            self.selected_file = file_path
            self.file_path_text.value = file_path
            self.file_path_text.update()
            self.status_text.value = "已选择文件，准备切割"
            self.status_text.update()

    def init_ui(self):
        # Header
        self.controls.append(
            ft.Text("多媒体切割器", size=28, weight=ft.FontWeight.BOLD)
        )
        self.controls.append(
            ft.Text("选择视频或音频文件，按指定时长切割", color=ft.Colors.GREY_600)
        )

        # File Picker
        # Removed persistent picker as we use imperative API
        # self.file_picker = ft.FilePicker()
        # self.file_picker.on_result = self.on_file_picked

        # --- Input Area ---
        # We need to add file_picker to the page overlays or controls. 
        # Since we are a control, we can't easily add to page.overlay from __init__.
        # But we can add it to our controls, Flet handles it. 
        # Actually, FilePicker is a non-visual control, usually added to page.overlay.
        # But in a view, we can add it to the view's controls and it works.
        # self.controls.append(self.file_picker) # Moved to did_mount/overlay

        # --- Input Area ---
        self.file_path_text = ft.TextField(
            label="文件路径",
            read_only=True,
            expand=True,
            icon=ft.Icons.VIDEO_FILE
        )

        self.select_btn = ft.ElevatedButton(
            "选择文件",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self.handle_pick_files
        )

        self.duration_input = ft.TextField(
            label="切割时长 (秒)",
            value="60",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
            suffix=ft.Text("秒"),
            icon=ft.Icons.TIMER
        )

        self.start_btn = ft.ElevatedButton(
            "开始切割",
            icon=ft.Icons.CUT,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=20,
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
            ),
            on_click=self.start_split
        )

        self.input_card = ft.Container(
            content=ft.Column([
                ft.Row([self.file_path_text, self.select_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.duration_input], alignment=ft.MainAxisAlignment.START),
                ft.Divider(color=ft.Colors.OUTLINE_VARIANT),
                ft.Row([self.start_btn], alignment=ft.MainAxisAlignment.END),
            ], spacing=20),
            padding=25,
            border_radius=15,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self.controls.append(self.input_card)

        # --- Status Area ---
        self.status_text = ft.Text("就绪", color=ft.Colors.GREY)
        self.progress_bar = ft.ProgressBar(value=0, color=ft.Colors.BLUE, bgcolor=ft.Colors.GREY_200, visible=False)
        self.log_view = ft.ListView(
            expand=True, 
            spacing=10, 
            padding=10, 
            auto_scroll=True,
            height=200
        )
        self.log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            bgcolor=ft.Colors.BLACK12,
            visible=False
        )

        self.controls.append(
            ft.Column([
                self.status_text,
                self.progress_bar,
                self.log_container
            ], spacing=10)
        )

    def on_file_picked(self, e):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            self.selected_file = file_path
            self.file_path_text.value = file_path
            self.file_path_text.update()
            self.status_text.value = "已选择文件，准备切割"
            self.status_text.update()
        else:
            # User cancelled
            pass

    async def start_split(self, e):
        if not self.selected_file:
            self.status_text.value = "请先选择文件！"
            self.status_text.color = ft.Colors.RED
            self.status_text.update()
            return

        try:
            duration = int(self.duration_input.value)
            if duration <= 0: raise ValueError
        except:
            self.duration_input.error_text = "请输入有效的正整数"
            self.duration_input.update()
            return

        self.duration_input.error_text = None
        self.start_btn.disabled = True
        self.select_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = None # Indeterminate if calculation fails
        self.log_container.visible = True
        self.log_view.controls.clear()
        self.update()

        def on_log(msg):
            self.log_view.controls.append(ft.Text(msg, size=12, font_family="Consolas"))
            self.log_view.update()

        def on_progress(percent):
            self.progress_bar.value = percent / 100.0
            self.progress_bar.update()

        try:
            self.status_text.value = "正在处理..."
            self.status_text.color = ft.Colors.BLUE
            self.status_text.update()

            output_dir = await self.splitter.split_media(
                self.selected_file,
                duration,
                on_log=on_log,
                on_progress=on_progress
            )

            self.status_text.value = f"切割完成！已保存至: {output_dir}"
            self.status_text.color = ft.Colors.GREEN
            self.progress_bar.value = 1.0
            
            # Add open folder button?
            self.log_view.controls.append(ft.Text(f"SUCCESS: Output directory: {output_dir}", color=ft.Colors.GREEN))

        except Exception as ex:
            self.status_text.value = f"错误: {str(ex)}"
            self.status_text.color = ft.Colors.RED
            self.log_view.controls.append(ft.Text(f"ERROR: {str(ex)}", color=ft.Colors.RED))
        
        self.start_btn.disabled = False
        self.select_btn.disabled = False
        self.update()

    def handle_file_drop(self, e):
        # Handle file drop from main page
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            self.selected_file = file_path
            self.file_path_text.value = file_path
            self.file_path_text.update()
            self.status_text.value = "已获取拖入文件"
            self.status_text.update()
