
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLineEdit, QPushButton, QLabel, QStatusBar, QMainWindow,
                               QComboBox, QTextEdit, QMessageBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QProgressBar, QDialog, QFileDialog)
from PySide6.QtCore import Qt, QUrl, QByteArray
from PySide6.QtGui import QFont, QDesktopServices, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from ..core.worker import AnalyzeThread, DownloadThread
from ..core.utils import scan_chrome_profiles
from ..config import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.config = config
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        
        # JS Engine Path
        layout.addWidget(QLabel("JS 引擎路径 (Deno/Node):"))
        node_layout = QHBoxLayout()
        self.node_edit = QLineEdit(self.config.get_js_engine_path() or "")
        btn_node = QPushButton("选择...")
        btn_node.clicked.connect(self.choose_node)
        node_layout.addWidget(self.node_edit)
        node_layout.addWidget(btn_node)
        layout.addLayout(node_layout)
        
        # Download Dir
        layout.addWidget(QLabel("默认下载目录:"))
        dl_layout = QHBoxLayout()
        self.dl_edit = QLineEdit(self.config.get_download_dir())
        btn_dl = QPushButton("选择...")
        btn_dl.clicked.connect(self.choose_dl)
        dl_layout.addWidget(self.dl_edit)
        dl_layout.addWidget(btn_dl)
        layout.addLayout(dl_layout)
        
        # Save Btn
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)
        
    def choose_node(self):
        d = QFileDialog.getExistingDirectory(self, "选择包含 deno/node 可执行文件的文件夹")
        if d: self.node_edit.setText(d)

    def choose_dl(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录")
        if d: self.dl_edit.setText(d)
        
    def save(self):
        self.config.set_js_engine_path(self.node_edit.text())
        self.config.set_download_dir(self.dl_edit.text())
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setWindowTitle("通用视频下载器 (Pro)")
        self.setGeometry(100, 100, 800, 700)

        # Network Manager for thumbnails
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self.on_thumb_downloaded)

        # 1. 顶部控制栏
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("在此处粘贴视频 URL (https://...)")
        
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["chrome", "firefox", "safari", "edge", "brave", "opera"])
        self.browser_combo.setFixedWidth(100)
        self.browser_combo.setCurrentText(self.config.get_last_browser())
        
        self.profile_combo = QComboBox()
        self.profile_combo.setEditable(True) 
        self.profile_combo.setPlaceholderText("Profile")
        self.profile_combo.setFixedWidth(150)
        self.profile_combo.setCurrentText(self.config.get_last_profile())
        
        self.analyze_btn = QPushButton("1. 分析链接")
        self.analyze_btn.clicked.connect(self.start_analysis)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.clicked.connect(self.open_settings)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Browser:"))
        control_layout.addWidget(self.browser_combo)
        control_layout.addWidget(self.profile_combo)
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.analyze_btn)
        control_layout.addWidget(self.settings_btn)

        # 2. 视频信息 & 缩略图区域
        info_layout = QHBoxLayout()
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90) # 16:9 ratio
        self.thumb_label.setStyleSheet("border: 1px solid #ccc; background: #eee;")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setText("No Thumbnail")
        
        self.info_text = QLabel("等待分析...")
        self.info_text.setWordWrap(True)
        self.info_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        info_layout.addWidget(self.thumb_label)
        info_layout.addWidget(self.info_text, 1)

        # 3. 格式选择列表
        self.format_table = QTableWidget()
        self.format_table.setColumnCount(5)
        self.format_table.setHorizontalHeaderLabels(["ID", "格式", "分辨率", "大小", "操作"])
        self.format_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.format_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.format_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # 4. 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")

        # 5. 日志区域
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(100)
        self.log_output.setFont(QFont("Menlo", 12))

        # 6. 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 布局组合
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(control_layout)
        layout.addLayout(info_layout)
        layout.addWidget(QLabel("可用格式列表:"))
        layout.addWidget(self.format_table)
        layout.addWidget(QLabel("下载进度:"))
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("运行日志:"))
        layout.addWidget(self.log_output)
        self.setCentralWidget(central)
        
        self.threads = [] 
        
        self.refresh_profiles()

    def refresh_profiles(self):
        """自动扫描并填充 Profile"""
        try:
            detected = scan_chrome_profiles()
            self.profile_combo.clear()
            self.profile_combo.addItems(detected)
            # Restore selection if possible
            last = self.config.get_last_profile()
            if last in detected:
                self.profile_combo.setCurrentText(last)
                
            self.status_bar.showMessage(f"已自动加载 {len(detected)} 个 Profile", 3000)
        except Exception as e:
            print(f"Profile scan error: {e}")

    def open_settings(self):
        d = SettingsDialog(self.config, self)
        d.exec()

    def closeEvent(self, event):
        # Save config
        self.config.set_last_browser(self.browser_combo.currentText())
        self.config.set_last_profile(self.profile_combo.currentText())
        super().closeEvent(event)

    def start_analysis(self):
        url = self.url_input.text().strip()
        if not url: return
        
        self.log_output.clear()
        self.format_table.setRowCount(0)
        self.analyze_btn.setEnabled(False)
        self.status_bar.showMessage("正在分析视频信息...", 0)
        self.progress_bar.setValue(0)
        self.thumb_label.setText("Loading...")
        self.info_text.setText("分析中...")
        
        browser = self.browser_combo.currentText()
        profile = self.profile_combo.currentText()
        
        worker = AnalyzeThread(url, browser, profile if profile else None)
        worker.analysis_finished.connect(self.on_analysis_success)
        worker.analysis_failed.connect(self.on_analysis_fail)
        worker.finished.connect(lambda: self.analyze_btn.setEnabled(True))
        worker.start()
        self.threads.append(worker)

    def on_analysis_success(self, info):
        self.status_bar.showMessage(f"分析成功: {info.get('title', 'Unknown')}", 5000)
        
        title = info.get('title', '无标题')
        duration = info.get('duration_string', 'N/A')
        self.info_text.setText(f"<b>{title}</b><br>时长: {duration}")
        
        # Load Thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            self.nam.get(QNetworkRequest(QUrl(thumb_url)))
        
        self.log_output.append(f"标题: {title}")
        
        formats = info.get('formats', [])
        valid_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
        valid_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        
        self.format_table.setRowCount(len(valid_formats) + 1)
        self.add_table_row(0, "best", "最佳画质 (MP4)", "Auto", "Auto")

        for i, f in enumerate(valid_formats):
            fid = f.get('format_id')
            ext = f.get('ext')
            res = f"{f.get('width')}x{f.get('height')}"
            filesize = f.get('filesize') or f.get('filesize_approx')
            size_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else "N/A"
            note = f.get('format_note', '')
            desc = f"{ext.upper()} {note}"
            self.add_table_row(i + 1, fid, desc, res, size_str)

    def on_thumb_downloaded(self, reply):
        if reply.error():
            print(reply.errorString())
            return
        
        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.thumb_label.setPixmap(pixmap.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def add_table_row(self, row, fid, fmt_name, res, size):
        self.format_table.setItem(row, 0, QTableWidgetItem(fid))
        self.format_table.setItem(row, 1, QTableWidgetItem(fmt_name))
        self.format_table.setItem(row, 2, QTableWidgetItem(res))
        self.format_table.setItem(row, 3, QTableWidgetItem(size))
        
        btn = QPushButton("下载此格式")
        btn.clicked.connect(lambda: self.start_download(fid))
        self.format_table.setCellWidget(row, 4, btn)

    def on_analysis_fail(self, err):
        self.status_bar.showMessage("分析失败", 5000)
        self.log_output.append(err)
        QMessageBox.critical(self, "错误", f"无法获取视频信息：\n{err}")

    def start_download(self, format_id):
        url = self.url_input.text()
        browser = self.browser_combo.currentText()
        profile = self.profile_combo.currentText()
        
        self.status_bar.showMessage(f"开始下载 (Format: {format_id})...")
        self.log_output.append(f"=== 开始下载 Format ID: {format_id} ===")
        self.progress_bar.setValue(0)
        
        worker = DownloadThread(url, format_id, browser, profile if profile else None)
        worker.log_updated.connect(self.log_output.append)
        worker.task_finished.connect(self.on_download_finished)
        worker.verification_required.connect(self.on_verify_req)
        worker.progress_updated.connect(self.update_progress)
        worker.start()
        self.threads.append(worker)

    def update_progress(self, info):
        self.progress_bar.setValue(int(info['percent']))
        
    def on_download_finished(self, msg):
        self.status_bar.showMessage(msg, 5000)
        self.progress_bar.setValue(100) 
        if "成功" in msg:
            QMessageBox.information(self, "完成", msg)

    def on_verify_req(self, url):
        reply = QMessageBox.warning(self, "需验证", "YouTube 需要人机验证。\n点击确定打开浏览器。", QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            QDesktopServices.openUrl(QUrl(url))
