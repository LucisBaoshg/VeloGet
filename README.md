# 通用视频下载器 (yt-dlp GUI)

基于 [Toga](https://beeware.org/project/projects/libraries/toga/) 和 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 开发的跨平台视频下载器 GUI。

## 开发环境

推荐使用 Python 3.10+。

```bash
# 创建虚拟环境
python3 -m venv venv-new
source venv-new/bin/activate

# 安装依赖
pip install briefcase toga yt-dlp
```

## 运行应用

```bash
# 源码运行
briefcase dev
```

## 打包 (macOS)

本项目使用 [Briefcase](https://briefcase.readthedocs.io/) 进行打包。

### 1. 打包并生成 .app

```bash
briefcase package macOS app
```

### 2. 生成 DMG 安装包

#### 方法 A: 本地测试 (Ad-hoc 签名)
仅供本机测试使用，发给其他人可能会提示损坏。

```bash
briefcase package macOS app --adhoc-sign
```

#### 方法 B: 正式发布 (Apple 开发者签名)
需要有效的 Apple 开发者账号和证书。

1. 列出可用的签名身份：
   ```bash
   security find-identity -p codesigning -v
   ```

2. 使用证书打包（替换 `YOUR_IDENTITY` 为证书名称或哈希，例如 "Developer ID Application: Tapcash Inc"）：
   ```bash
   briefcase package macOS app --identity "YOUR_IDENTITY"
   ```

Briefcase 会自动处理签名和公证 (Notarization) 流程。如果公证成功，生成的 DMG 文件即可分发。

## 文件说明

- `src/ytdlpgui`: 源代码目录
- `pyproject.toml`: Briefcase 项目配置文件
- `dist/`: 打包输出目录
