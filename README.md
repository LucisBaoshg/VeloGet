# VeloGet - 极简且强大的视频下载器

**VeloGet** 是一款基于 [Flet](https://flet.dev) (UI) 和 [yt-dlp](https://github.com/yt-dlp/yt-dlp) (内核) 开发的现代化跨平台视频下载工具。

版本: **1.0.2**

## ✨ 核心特性

- **🚀 极度轻量**: 经过深度优化，App 体积仅约 200MB (DMG 约 138MB)。
- **📦 开箱即用**: 内置 `FFmpeg` 和 `yt-dlp` 二进制文件，用户无需配置任何环境。
- **📺 全能下载**: 支持 YouTube (含 4K/8K)、Bilibili、TikTok 等数千个网站。
- **📊 频道分析**: 支持批量解析频道/播放列表，支持 YouTube Data API 加速，可导出详细 CSV 数据（文件名自动包含频道名称）。
- **🔐 会员支持**:
    - **智能 Profile 扫描**: 自动识别 Chrome/Edge/Firefox 的用户配置文件 (Profile)，无需手动查找路径。
    - **Cookie 注入**: 支持读取本地浏览器 Cookie 或导入 `cookies.txt` 以下载会员视频。
- **🔄 双通道更新**: 支持 `yt-dlp` 内核更新，也支持桌面应用通过内网 GitHub 镜像服务进行应用内更新。

## 🛠 开发环境

推荐使用 Python 3.10+ (开发环境使用 3.12)。

### 1. 初始化环境
```bash
# 创建虚拟环境
python3 -m venv venv-new
source venv-new/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行应用 (源码模式)
```bash
python main.py
```

## 📦 打包与发布

项目现在使用 GitHub Release 作为统一发布源，并为内网镜像服务提供两类稳定产物：

- `installer`: 安装包，供用户手动下载安装
- `in_app_update`: 应用内更新包，供客户端下载后自动替换

默认 `appId` 为 `veloget`，镜像服务地址为：

- `http://tc-github-mirror.ite.tool4seller.com`

发布产物命名规则：

```text
veloget-{version}-macos-{arch}.dmg
veloget-{version}-macos-{arch}.app.tar.gz
veloget-{version}-windows-x64.zip
veloget-{version}-windows-x64.app.tar.gz
```

其中：

- `.dmg` / `.zip` 对应 `kind=installer`
- `.app.tar.gz` 对应 `kind=in_app_update`

### macOS
使用一键构建脚本：
```bash
./build_release.sh
```
产物位于 `dist/`，包含：

- `veloget-{version}-macos-{arch}.dmg`
- `veloget-{version}-macos-{arch}.app.tar.gz`

### Windows
使用 PowerShell 构建脚本：
```powershell
.\build_release_win.ps1
```
**注意**: 
1. 脚本会自动检查 `src/ytdlpgui/_internal/ffmpeg.exe`。如果不存在，构建出的应用将提示用户手动安装 FFmpeg，或你可以手动下载 `ffmpeg.exe` 放入该目录以集成到应用中。
2. 产物位于 `dist/`，包含：

- `veloget-{version}-windows-x64.zip`
- `veloget-{version}-windows-x64.app.tar.gz`

### 手动构建 (如果不使用脚本)
必须使用 `--exclude` 参数防止体积膨胀：
```bash
# macOS
flet build macos \
    --yes \
    --no-rich-output \
    --project VeloGet \
    --product VeloGet \
    --org com.lucifer \
    --copyright "Copyright (c) 2026 Lucifer" \
    --exclude venv-new venv-final build dist .git .github

# Windows
flet build windows \
    --yes \
    --no-rich-output \
    --project VeloGet \
    --product VeloGet \
    --org com.lucifer \
    --copyright "Copyright (c) 2026 Lucifer" \
    --exclude venv-new venv-final build dist .git .github
```

## 🚀 GitHub Release 发版

推荐使用 tag 发版：

```bash
git tag v1.0.2
git push origin v1.0.2
```

仓库中的 [`.github/workflows/release.yml`](/Volumes/Acer/Dev/ytdlpgui/.github/workflows/release.yml) 会：

- 校验 tag 版本与 [`pyproject.toml`](/Volumes/Acer/Dev/ytdlpgui/pyproject.toml) 一致
- 构建 macOS 与 Windows 产物
- macOS 产物执行签名、公证与 stapling
- 上传到 GitHub Release

内网镜像服务再从 GitHub Release 同步这些最终发布产物。

macOS Release 依赖以下 GitHub Actions secrets：

- `APPLE_CERTIFICATE_P12`
  填 base64 后的 `.p12` 内容。你提供的 `/Users/lucifer/Desktop/t4s-developer-id.p12.base64.txt` 就是这个 secret 的值。
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_SIGNING_IDENTITY`
- `APPLE_TEAM_ID`
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`

## 🔄 应用更新接入

桌面应用不再直接访问 GitHub Release，而是通过内网镜像服务查询和下载更新：

```text
GET /updates/veloget/latest?platform={platform}&arch={arch}&kind={kind}
```

当前应用已接入：

- 启动时静默检查应用新版本
- 设置页手动“检查应用更新”
- 下载 `in_app_update` 包
- 校验 `sha256`
- 下载完成后退出当前进程并执行平台更新脚本

当前约定：

- macOS 使用 `macos` + `arm64/x64`
- Windows 使用 `windows` + `x64`
- 应用内更新默认请求 `kind=in_app_update`
- 用户手动下载安装可请求 `kind=installer`

## 💿 用户安装指南

### macOS
由于应用未进行 Apple 开发者签名，用户安装时需要绕过安全限制：
1.  双击 `.dmg` 文件，将 **VeloGet** 拖入 **Applications** 文件夹。
2.  在“应用程序”中找到 VeloGet。
3.  **右键点击** 图标 -> 选择 **“打开”**。
4.  在弹出的警告框中点击 **“打开”** (Open Anyway)。

### Windows
1.  解压下载的 zip 包。
2.  双击 `VeloGet.exe` 即可运行。
3.  首次运行若提示缺少 FFmpeg，应用会自动尝试下载，或请按照提示安装。

### 常见问题 (FAQ)

**Q: 提示 "Cookie 读取失败" 或 "could not find chrome cookies database"?**
A: 
- **macOS**: 请确保 VeloGet 已获得**完全磁盘访问权限**（系统设置 -> 隐私与安全）。
- **Windows**: 请确保**完全退出** Chrome 浏览器（因为 Chrome 运行时会锁定数据库文件）。
- 确保 Profile 选择正确。

**Q: Windows 下提示 "解密失败" (Decryption failed)?**
A: Windows 的安全机制 (DPAPI) 限制了第三方应用读取 Chrome Cookie。
建议：
1. 使用 **Firefox** 浏览器 (VeloGet 对 Firefox 的支持更好)。
2. 或手动导出 `cookies.txt` 并要在设置中加载。

## 📂 项目结构

- `src/ytdlpgui`: 源代码根目录
  - `_internal`: 内置二进制文件 (ffmpeg, yt-dlp)
  - `core`: 核心业务逻辑 (下载、分析、依赖管理、Profile扫描)
  - `ui_flet`: Flet UI 界面代码
    - `views`: 各个页面视图 (下载器、分析器、设置)
- `main.py`: 应用启动入口
- `build_release.sh`: 自动化构建脚本
- `requirements.txt`: 生产环境依赖
- `AI_CONTEXT.md`: AI 辅助开发上下文记录
