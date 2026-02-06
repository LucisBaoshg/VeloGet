import flet as ft
import asyncio

class DownloaderView(ft.Column):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.worker = app_instance.worker
        self.config = app_instance.config
        self.expand = True
        self.spacing = 20
        self.video_info = None # Store analyzed video info
        self.selected_format_id = None
        
        self.init_ui()

    def did_mount(self):
        # Load profiles for initial browser selection
        self.on_browser_change(None)

    def on_browser_change(self, e):
        """Update profile dropdown when browser changes"""
        browser = self.browser_dropdown.value
        if not browser: return
        
        from ...core.utils import get_browser_profiles
        
        def update_profiles():
            try:
                profiles = get_browser_profiles(browser)
                options = []
                default_val = None
                
                for p in profiles:
                    display = p['name']
                    pid = p['id']
                    label = f"{display} ({pid})" if display != pid else display
                    options.append(ft.dropdown.Option(pid, label))
                    
                    if pid == self.config.config_data.get('last_profile'):
                        default_val = pid
                        
                if not default_val and options:
                    default_val = options[0].key
                    
                self.profile_dropdown.options = options
                self.profile_dropdown.value = default_val
                self.profile_dropdown.update()
                
            except Exception as ex:
                from ...core.utils import debug_print
                debug_print(f"Profile scan error: {ex}")
        
        import threading
        threading.Thread(target=update_profiles, daemon=True).start()

    def init_ui(self):
        from ...core.utils import debug_print
        debug_print("DEBUG: Initializing DownloaderView with TABLE layout")
        # Header
        self.controls.append(
            ft.Text("视频下载器", size=28, weight=ft.FontWeight.BOLD)
        )
        self.controls.append(
            ft.Text("输入视频链接以开始下载", color=ft.Colors.GREY_600)
        )
        
        # --- Step 1: Input Area ---
        self.url_input = ft.TextField(
            label="视频链接",
            hint_text="在此处粘贴 URL (YouTube, Bilibili, TikTok 等)",
            prefix_icon=ft.Icons.LINK,
            border_radius=10,
            on_submit=self.analyze_url, # Allow enter key
            expand=True  # Expand to fill available space
        )
        
        # Clear button logic
        def clear_url(e):
            self.url_input.value = ""
            self.url_input.focus()
            self.url_input.update()

        self.clear_btn = ft.IconButton(
            icon=ft.Icons.CLEAR,
            tooltip="清空",
            on_click=clear_url
        )
        
        self.url_input.suffix = self.clear_btn

        self.analyze_btn = ft.ElevatedButton(
            "解析链接",
            icon=ft.Icons.ANALYTICS,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=20,
            ),
            on_click=self.analyze_url
        )
        
        # Advanced Options (Browser/Profile)
        self.browser_dropdown = ft.Dropdown(
            label="浏览器类型",
            value=self.config.config_data.get('last_browser', 'chrome'),
            options=[
                ft.dropdown.Option("chrome", "Google Chrome"),
                ft.dropdown.Option("firefox", "Mozilla Firefox"),
                ft.dropdown.Option("edge", "Microsoft Edge"),
                ft.dropdown.Option("safari", "Safari"),
                ft.dropdown.Option("brave", "Brave"),
                ft.dropdown.Option("chromium", "Chromium"),
            ],
            width=200,
            border_radius=10,
        )
        # Assign event handler after init to avoid keyword argument error in some Flet versions
        self.browser_dropdown.on_change = self.on_browser_change
        
        self.profile_dropdown = ft.Dropdown(
            label="用户配置文件 (Profile)",
            value=self.config.config_data.get('last_profile', 'Default'),
            options=[ft.dropdown.Option("Default", "默认")],
            expand=True,
            border_radius=10,
            hint_text="选择已登录的账号"
        )
        
        self.advanced_expander = ft.ExpansionTile(
            title=ft.Text("高级选项 (浏览器配置)", size=14, color=ft.Colors.GREY_700),
            subtitle=ft.Text("配置 Cookie 来源浏览器以解决登录/会员限制", size=12, color=ft.Colors.GREY_500),
            collapsed_text_color=ft.Colors.GREY_700,
            icon_color=ft.Colors.GREY_700,
            controls=[
                ft.Container(
                    content=ft.Row([
                        self.browser_dropdown,
                        self.profile_dropdown
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(top=25, left=10, right=10, bottom=10)
                )
            ]
        )

        self.input_card = ft.Container(
            content=ft.Column([
                ft.Row([self.url_input, self.analyze_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=ft.Colors.OUTLINE_VARIANT),
                self.advanced_expander
            ], spacing=20),
            padding=25,
            border_radius=15,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self.controls.append(self.input_card)
        
        # --- Step 2: Selection Area (Hidden by default) ---
        self.video_title = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        
        # Format Table
        self.format_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("清晰度")),
                ft.DataColumn(ft.Text("格式")),
                ft.DataColumn(ft.Text("大小 (估)")),
                ft.DataColumn(ft.Text("编码")),
                ft.DataColumn(ft.Text("操作")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            vertical_lines=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            data_row_min_height=50, # More breathing room for rows
            heading_row_height=50,
            column_spacing=20, 
        )
        
        self.cancel_btn = ft.OutlinedButton("取消 / 返回", on_click=self.reset_ui)

        self.selection_card = ft.Container(
            content=ft.Column([
                self.video_title,
                ft.Text("请选择下载格式：", color=ft.Colors.GREY_700),
                ft.Container(
                    content=self.format_table,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=10,
                    padding=10, # Increased padding
                    height=400, # Increased height
                ),
                ft.Row([self.cancel_btn], alignment=ft.MainAxisAlignment.END)
            ], spacing=25), # Increased spacing
            padding=30, # Increased padding
            border_radius=15,
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            visible=False # Hidden initially
        )
        self.controls.append(self.selection_card)
        
        # Status Area
        self.status_text = ft.Text("就绪", color=ft.Colors.GREY)
        self.progress_bar = ft.ProgressBar(value=0, color=ft.Colors.BLUE, bgcolor=ft.Colors.GREY_200, visible=False)
        
        self.controls.append(
            ft.Column([
                self.status_text,
                self.progress_bar
            ], spacing=5)
        )

    async def analyze_url(self, e):
        url = self.url_input.value
        if not url:
            self.url_input.error_text = "请输入链接"
            self.url_input.update()
            return
        
        self.url_input.error_text = None
        self.analyze_btn.disabled = True
        self.status_text.value = "正在解析视频信息..."
        self.progress_bar.visible = True
        self.progress_bar.value = None
        self.update()
        
        browser = self.browser_dropdown.value
        profile = self.profile_dropdown.value
        
        # Save config
        self.config.config_data['last_browser'] = browser
        self.config.config_data['last_profile'] = profile
        self.config.save()

        try:
            # Fetch video details using robust analyze_url
            result = await self.worker.analyze_url(url, browser, profile)
            
            if result.get("status") == "success":
                info = result.get("data")
                self.video_info = info
                self.show_selection_ui(info)
                self.status_text.value = "解析成功，请选择格式"
            else:
                error_msg = result.get("error", "未知错误")
                self.status_text.value = f"解析失败: {error_msg}"
                
        except Exception as ex:
            self.status_text.value = f"解析错误: {str(ex)}"
            
        self.analyze_btn.disabled = False
        self.progress_bar.visible = False
        self.update()

    def show_selection_ui(self, info):
        self.video_title.value = info.get('title', '未知标题')
        
        # Parse formats
        formats = info.get('formats', [])
        self.populate_format_table(formats)
        
        self.input_card.visible = False
        self.selection_card.visible = True
        self.update()

    def populate_format_table(self, formats):
        self.format_table.rows.clear()
        
        # Process formats
        # We want to group by resolution but keep unique entries if extensions differ
        # Filter logic:
        # 1. Video streams (vcodec != none)
        # 2. Audio only streams (vcodec == none)
        
        # Helper to format size
        def fmt_size(bytes_val):
            if not bytes_val: return "未知"
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024: return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} TB"

        # Unique choices
        choices = []
        
        # 1. Best Video + Audio (Synthetic)
        choices.append({
            "id": "best",
            "quality": "🌟 最佳画质 (Best)",
            "ext": "mp4/mkv",
            "size": "Auto",
            "codec": "Auto",
            "color": ft.Colors.GREEN_700
        })
        
        # 2. Best Audio (Synthetic)
        choices.append({
            "id": "bestaudio",
            "quality": "🎵 仅音频 (Best Audio)",
            "ext": "mp3/m4a",
            "size": "Auto",
            "codec": "Audio Only",
            "color": ft.Colors.BLUE_700
        })
        
        # 3. Specific Video Formats (Grouped by Height)
        # Sort by height desc
        video_formats = sorted(
            [f for f in formats if f.get('vcodec') != 'none' and f.get('height')],
            key=lambda x: x.get('height', 0), 
            reverse=True
        )
        
        seen_qualities = set()
        for f in video_formats:
            height = f.get('height')
            if not height: continue
            
            # Simple grouping: e.g. "1080p"
            # We assume we can merge bestaudio into this video stream
            quality_label = f"{height}p"
            
            # Avoid dupes if user just wants "1080p"
            # But maybe show mp4 vs webm?
            ext = f.get('ext')
            key = f"{height}-{ext}"
            
            # Only add if distinct enough or top quality
            if key in seen_qualities: continue
            seen_qualities.add(key)
            
            size = f.get('filesize') or f.get('filesize_approx')
            vcodec = f.get('vcodec', 'unknown')
            if 'av01' in vcodec: vcodec = 'AV1'
            elif 'vp9' in vcodec: vcodec = 'VP9'
            elif 'avc1' in vcodec: vcodec = 'H.264'
            
            choices.append({
                "id": f.get('format_id'), # This is the video stream ID
                "quality": quality_label,
                "ext": ext,
                "size": fmt_size(size),
                "codec": vcodec,
                "color": ft.Colors.BLACK
            })
            
            if len(choices) > 15: break # Limit list

        # Add rows
        for c in choices:
            is_special = c['id'] in ['best', 'bestaudio']
            
            row = ft.DataRow(cells=[
                ft.DataCell(ft.Text(c['quality'], color=c['color'], weight=ft.FontWeight.BOLD if is_special else ft.FontWeight.NORMAL)),
                ft.DataCell(ft.Text(c['ext'])),
                ft.DataCell(ft.Text(c['size'])),
                ft.DataCell(ft.Text(c['codec'])),
                ft.DataCell(
                    ft.ElevatedButton(
                        "下载", 
                        icon=ft.Icons.DOWNLOAD, 
                        height=30,
                        style=ft.ButtonStyle(padding=5),
                        on_click=lambda e, fid=c['id']: self.trigger_download(fid)
                    )
                ),
            ])
            self.format_table.rows.append(row)

    def trigger_download(self, format_id):
        self.selected_format_id = format_id
        self.start_download()

    def reset_ui(self, e):
        self.input_card.visible = True
        self.selection_card.visible = False
        self.status_text.value = "就绪"
        self.video_info = None
        self.update()

    def start_download(self):
        if not self.video_info or not self.selected_format_id: return
        
        # Disable all buttons in table? 
        # Easier to just switch to progress view or disable inputs
        self.status_text.value = "准备下载..."
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.update()
        
        url = self.url_input.value
        format_id = self.selected_format_id
        browser = self.browser_dropdown.value
        profile = self.profile_dropdown.value
        
        # Handle async execution
        asyncio.create_task(self._run_download_task(url, format_id, browser, profile))

    async def _run_download_task(self, url, format_id, browser, profile):
        def on_log(msg):
            if msg.startswith('[download]'):
                self.status_text.value = msg
                self.status_text.update()
                
        def on_progress(val):
            self.progress_bar.value = val / 100.0
            self.progress_bar.update()

        try:
            await self.worker.download_video(
                url, format_id, browser, profile, 
                on_log=on_log, 
                on_progress=on_progress
            )
            self.status_text.value = "下载完成 ✅"
            self.progress_bar.value = 1.0
            
        except Exception as ex:
            self.status_text.value = f"下载错误: {str(ex)}"
            self.progress_bar.value = 0
            
        # Re-enable UI?
        # self.reset_ui(None) # Optional
        self.update()
