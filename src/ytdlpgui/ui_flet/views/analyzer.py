import flet as ft
import asyncio

class AnalyzerView(ft.Column):
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.worker = app_instance.worker
        self.config = app_instance.config
        
        self.expand = True
        self.spacing = 20
        
        self.init_ui()

    def did_mount(self):
        # Load profiles for initial browser selection
        self.on_browser_change(None)

    def on_browser_change(self, e):
        """Update profile dropdown when browser changes"""
        browser = self.browser_dropdown.value
        if not browser: return
        
        # Run scan in background thread to avoid UI freeze
        # But we need utils import first.
        # Since logic is small, we can import here or in file top. 
        # Ideally view shouldn't depend on utils directly but worker.
        # However, for simplicity let's use a thread wrapper here.
        # Or better: let the worker expose this method? 
        # Actually worker.py is for heavy tasks. Let's just import utils here.
        
        from ...core.utils import get_browser_profiles
        
        def update_profiles():
            try:
                profiles = get_browser_profiles(browser)
                options = []
                default_val = None
                
                for p in profiles:
                    # Show: "Person 1 (Profile 1)" if they differ, else "Person 1"
                    display = p['name']
                    pid = p['id']
                    label = f"{display} ({pid})" if display != pid else display
                    options.append(ft.dropdown.Option(pid, label))
                    
                    # Try to preserve previous selection if it exists in new list
                    if pid == self.config.config_data.get('last_profile'):
                        default_val = pid
                        
                # Fallback to first profile if previous not found
                if not default_val and options:
                    default_val = options[0].key
                    
                self.profile_dropdown.options = options
                self.profile_dropdown.value = default_val
                self.profile_dropdown.update()
                
            except Exception as ex:
                print(f"Profile scan error: {ex}")
        
        # Run in thread
        import threading
        threading.Thread(target=update_profiles, daemon=True).start()

    def init_ui(self):
        self.controls.append(ft.Text("频道分析器", size=28, weight=ft.FontWeight.BOLD))
        
        # Input Area
        self.url_input = ft.TextField(
            label="频道/播放列表 URL",
            hint_text="粘贴链接以分析视频列表",
            prefix_icon=ft.Icons.LINK,
            border_radius=10,
            expand=True
        )
        
        self.analyze_btn = ft.ElevatedButton(
            "开始分析",
            icon=ft.Icons.SEARCH,
            style=ft.ButtonStyle(padding=20, shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=self.start_analysis
        )
        
        self.deep_switch = ft.Switch(label="深度分析 (慢速)")
        
        api_key = self.config.get_youtube_api_key()
        api_text = "✅ API 加速生效中" if api_key else "⚠️ 未配置 API (推荐)"
        api_color = ft.Colors.GREEN if api_key else ft.Colors.ORANGE
        self.api_label = ft.Text(api_text, color=api_color, size=12)
        
        # --- Advanced Options (Browser/Profile) ---
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
        self.browser_dropdown.on_change = self.on_browser_change
        
        self.profile_dropdown = ft.Dropdown(
            label="用户配置文件 (Profile)",
            value=self.config.config_data.get('last_profile', 'Default'),
            options=[ft.dropdown.Option("Default", "默认")],
            expand=True,
            border_radius=10,
            hint_text="选择已登录的账号"
        )
        
        # Expander for Advanced Settings
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
                    # Increase top padding to prevent label clipping
                    padding=ft.padding.only(left=10, right=10, bottom=10, top=25)
                )
            ]
        )
        
        self.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([self.url_input, self.analyze_btn]),
                    ft.Row([self.deep_switch, self.api_label], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(color=ft.Colors.OUTLINE_VARIANT),
                    self.advanced_expander
                ]),
                padding=20,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=15
            )
        )
        
        # Results Table
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("标题")),
                ft.DataColumn(ft.Text("时长"), numeric=True),
                ft.DataColumn(ft.Text("观看数"), numeric=True),
                ft.DataColumn(ft.Text("发布时间")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
            vertical_lines=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        )
        
        self.table_container = ft.Column(
            [self.data_table], 
            scroll=ft.ScrollMode.AUTO, 
            expand=True
        )
        
        self.controls.append(self.table_container)
        
        # Footer
        self.status_text = ft.Text("就绪", color=ft.Colors.GREY)
        self.export_btn = ft.OutlinedButton("导出 CSV", icon=ft.Icons.SAVE, disabled=True, on_click=self.export_data)
        
        self.controls.append(
            ft.Row([self.status_text, self.export_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        
        self.channel_data = []
        self.channel_title = "analysis" # Store channel title for export

    def set_file_picker(self, picker):
        """Deprecated: Dependency Injection no longer used."""
        pass


    async def start_analysis(self, e):
        url = self.url_input.value
        if not url:
            self.url_input.error_text = "请输入链接"
            self.url_input.update()
            return
            
        self.url_input.error_text = None
        self.analyze_btn.disabled = True
        self.export_btn.disabled = True
        self.status_text.value = "正在分析..."
        self.update()
        
        # Get Browser/Profile from inputs
        browser = self.browser_dropdown.value
        profile = self.profile_dropdown.value
        
        # Save last used settings
        self.config.config_data['last_browser'] = browser
        self.config.config_data['last_profile'] = profile
        self.config.save()
        
        try:
            # 1. Fetch
            result = await self.worker.analyze_channel(url, browser, profile)
            
            if result['status'] == 'success':
                # Store channel title for export filename
                self.channel_title = result['data'].get('title', 'analysis')
                
                entries = result['data'].get('entries', [])
                self.status_text.value = f"发现 {len(entries)} 个视频，处理中..."
                self.update()
                
                # API Enrichment logic... (Simplified for POC)
                api_key = self.config.get_youtube_api_key()
                if api_key:
                    entries = await self.worker.enrich_with_api(entries, api_key)
                
                self.channel_data = entries
                self.update_table(entries)
                self.status_text.value = f"分析完成: {len(entries)} 个条目"
                self.export_btn.disabled = False
            else:
                self.status_text.value = f"失败: {result.get('error')}"
                
        except Exception as ex:
            self.status_text.value = f"错误: {str(ex)}"
            
        self.analyze_btn.disabled = False
        self.update()

    def update_table(self, entries):
        self.data_table.rows.clear()
        
        # Update columns to show a bit more info in UI, but keep it responsive
        self.data_table.columns = [
            ft.DataColumn(ft.Text("标题")),
            ft.DataColumn(ft.Text("发布时间")),
            ft.DataColumn(ft.Text("观看数"), numeric=True),
            ft.DataColumn(ft.Text("点赞"), numeric=True),
            ft.DataColumn(ft.Text("时长"), numeric=True),
        ]
        
        for v in entries:
            # Format duration
            dur = v.get('duration') or 0
            m, s = divmod(int(dur), 60)
            h, m = divmod(m, 60)
            dur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            
            self.data_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(v.get('title', 'N/A'), width=300, no_wrap=True, tooltip=v.get('title'))),
                    ft.DataCell(ft.Text(str(v.get('upload_date', 'N/A')))),
                    ft.DataCell(ft.Text(str(v.get('view_count', 0)))),
                    ft.DataCell(ft.Text(str(v.get('like_count', 0)))),
                    ft.DataCell(ft.Text(dur_str)),
                ])
            )
        self.update()

    def _show_snack(self, message):
        # Use show_dialog as per SnackBar docstring for this version
        self.app.page.show_dialog(ft.SnackBar(content=ft.Text(message)))

    async def export_data(self, e):
        # Use configured download directory or default to Downloads
        initial_dir = self.config.get_download_dir()
        if not initial_dir:
             import os
             initial_dir = os.path.expanduser("~/Downloads")
        
        # Determine filename based on channel/playlist title
        channel_name = self.channel_title
        
        # Sanitize filename: remove illegal chars and replace spaces with underscores
        import re
        # First strip illegal chars
        channel_name = re.sub(r'[\\/*?:"<>|]', "", channel_name)
        # Then collapse spaces to underscores
        channel_name = re.sub(r'\s+', "_", channel_name)
        
        channel_name = f"@{channel_name}_analysis"

        # New API style for Flet >= 0.80.0
        path = await ft.FilePicker().save_file(
            allowed_extensions=["csv"],
            file_name=f"{channel_name}.csv",
            initial_directory=initial_dir,
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        
        if not path:
            return
            
        import csv
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Full columns as requested
                headers = [
                    'Title', 'Published', 'Views', 'Likes', 'Comments', 
                    'Duration', 'Type', 'Tags', 'Description', 'URL'
                ]
                writer.writerow(headers)
                
                for v in self.channel_data:
                    # Duration format for CSV (seconds or string? Let's use seconds for analysis)
                    # Or human readable? Requested format implied simple columns.
                    # Let's write raw duration in seconds for analysis, or human readable?
                    # The prompt didn't specify, but raw seconds is better for Excel analysis.
                    # However, to match previous "Duration" column logic, maybe text.
                    # I will stick to Raw Seconds or ISO string. Let's use Seconds.
                    
                    # Tags list to string
                    tags = v.get('tags') or []
                    tags_str = ",".join(tags) if isinstance(tags, list) else str(tags)
                    
                    writer.writerow([
                        v.get('title'),
                        v.get('upload_date'),
                        v.get('view_count'),
                        v.get('like_count', 0),
                        v.get('comment_count', 0),
                        v.get('duration'), # Seconds
                        v.get('original_type', 'Video'), # Extracted in worker
                        tags_str,
                        v.get('description', '')[:500], # Truncate desc to avoid massive CSVs? No, keep it.
                        v.get('url') or v.get('webpage_url') or f"https://youtu.be/{v.get('id')}"
                    ])
            self._show_snack(f"导出成功: {path}")
        except PermissionError:
            self._show_snack(f"保存失败: 文件可能被占用(如Excel打开中)或无写入权限")
        except Exception as ex:
            self._show_snack(f"导出失败: {str(ex)}")


