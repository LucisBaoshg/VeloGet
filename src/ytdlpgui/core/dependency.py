import os
import shutil
import zipfile
import tarfile
import urllib.request
import ssl
import stat
from pathlib import Path
import asyncio

class DependencyManager:
    def __init__(self, config_manager):
        self.config = config_manager
        # ~/.ytdlpgui/bin
        self.bin_dir = self.config.config_dir / "bin"
        
        # Bundled bin dir (src/ytdlpgui/_internal)
        # Assuming this file is in src/ytdlpgui/core/dependency.py
        self.internal_bin_dir = Path(__file__).parent.parent / "_internal"
        
        self._ensure_bin_dir()

    def _ensure_bin_dir(self):
        if not self.bin_dir.exists():
            self.bin_dir.mkdir(parents=True, exist_ok=True)

    def get_ffmpeg_path(self):
        # 1. Custom local bin
        local_ffmpeg = self.bin_dir / "ffmpeg"
        if local_ffmpeg.exists() and os.access(local_ffmpeg, os.X_OK):
            return str(local_ffmpeg)
            
        # 1.5 Bundled bin (Windows/Mac packaged)
        # Check both "ffmpeg" and "ffmpeg.exe"
        bundled_ffmpeg = self.internal_bin_dir / "ffmpeg"
        if bundled_ffmpeg.exists():
             return str(bundled_ffmpeg)
        bundled_ffmpeg_exe = self.internal_bin_dir / "ffmpeg.exe"
        if bundled_ffmpeg_exe.exists():
             return str(bundled_ffmpeg_exe)
        
        # 2. System path (fallback)
        return shutil.which("ffmpeg")

    def get_deno_path(self):
        # 1. Custom local bin
        local_deno = self.bin_dir / "deno"
        if local_deno.exists() and os.access(local_deno, os.X_OK):
            return str(local_deno)
        
        # 2. System path (fallback) - reusing config logic effectively
        # But here we just want the binary path
        return shutil.which("deno")

    def is_ffmpeg_installed(self):
        return self.get_ffmpeg_path() is not None

    def is_deno_installed(self):
        return self.get_deno_path() is not None

    async def install_ffmpeg(self, progress_callback=None):
        # Valid for macOS ARM64 (Apple Silicon) as target is restricted
        # Using martin-riedl.de (Reliable static builds for macOS)
        # Snapshot build is usually fine, or we can pick a release.
        # Direct ZIP link:
        url = "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/snapshot/ffmpeg.zip"
        await self._download_and_extract(url, "ffmpeg", progress_callback)

    def get_ffmpeg_version(self):
        path = self.get_ffmpeg_path()
        if not path: return None
        try:
             # Just read first line of output
             import subprocess
             result = subprocess.run([path, "-version"], capture_output=True, text=True)
             if result.returncode == 0:
                 return result.stdout.splitlines()[0]
        except:
            return "Unknown Version"
        return "Unknown Version"

    def get_deno_version(self):
        path = self.get_deno_path()
        if not path: return None
        try:
             import subprocess
             result = subprocess.run([path, "--version"], capture_output=True, text=True)
             if result.returncode == 0:
                 return result.stdout.splitlines()[0] # "deno 1.x.x"
        except:
            return "Unknown Version"
        return "Unknown Version"

    async def install_deno(self, progress_callback=None):
        # Official Deno release
        url = "https://github.com/denoland/deno/releases/latest/download/deno-aarch64-apple-darwin.zip"
        await self._download_and_extract(url, "deno", progress_callback)

    async def get_latest_ytdlp_version(self, url=None, timeout=30):
        """Fetches the latest version string from PyPI JSON API"""
        if not url:
            url = "https://pypi.org/pypi/yt-dlp/json"
        
        # Use simple urllib request
        import json
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        def fetch():
            try:
                # Add headers to avoid some blocking
                req = urllib.request.Request(url, headers={
                     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
                    data = json.load(response)
                    return data['info']['version']
            except Exception as e:
                print(f"Version Check Error ({url}): {e}")
                return None

        return await asyncio.to_thread(fetch)

    async def _download_and_extract(self, url, binary_name, progress_callback):
        dest_zip = self.bin_dir / f"{binary_name}.zip"
        
        # SSL Context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        def download_chunked():
            with urllib.request.urlopen(url, context=ctx) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(dest_zip, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if progress_callback and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            # Run callback on main thread if possible, or just call it (thread safety handled by caller)
                            progress_callback(percent, f"Downloading {binary_name}...")

        await asyncio.to_thread(download_chunked)
        
        if progress_callback:
            progress_callback(100, f"Extracting {binary_name}...")

        # Extract
        def extract():
            with zipfile.ZipFile(dest_zip, 'r') as zip_ref:
                zip_ref.extractall(self.bin_dir)
            
            # Cleanup
            dest_zip.unlink()

            # Chmod +x
            bin_path = self.bin_dir / binary_name
            if bin_path.exists():
                st = os.stat(bin_path)
                os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
        
        await asyncio.to_thread(extract)

    async def _download_file(self, url, dest_path: Path, progress_callback):
        # Generic download helper
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        def download_chunked():
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            with urllib.request.urlopen(req, context=ctx) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(dest_path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer: break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if progress_callback and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            # Simply call callback, caller handles thread safety
                            progress_callback(percent, f"Downloading...")

        await asyncio.to_thread(download_chunked)

    async def update_ytdlp(self, progress_callback=None):
        """Downloads latest yt-dlp source and extracts to updates dir with mirrors support"""
        import shutil
        self.updates_dir = self.config.config_dir / "updates"
        self.updates_dir.mkdir(parents=True, exist_ok=True)
        
        urls = [
            "https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip",
            # Mirror 1 (Common for China)
            "https://kgithub.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip",
            # Mirror 2
            "https://hub.nuaa.cf/yt-dlp/yt-dlp/archive/refs/heads/master.zip"
        ]
        
        archive_path = self.updates_dir / "ytdlp_update.zip"
        last_error = None

        for url in urls:
            try:
                if progress_callback: progress_callback(0, f"Downloading from {url.split('/')[2]}...")
                
                await self._download_file(url, archive_path, progress_callback)
                
                # Check file header magic number
                if not archive_path.exists() or archive_path.stat().st_size < 100:
                    raise Exception("Download failed (File too small or empty)")
                    
                with open(archive_path, 'rb') as f:
                    header = f.read(4)
                    if header != b'PK\x03\x04':
                        raise Exception(f"Invalid Zip Header: {header}")

                if progress_callback: progress_callback(90, "Installing update...")
                
                # Extract
                def install():
                    import zipfile
                    try:
                        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                            zip_ref.extractall(self.updates_dir)
                    except zipfile.BadZipFile:
                        raise Exception("Corrupt Zip File")
                    
                    extracted_root = next(self.updates_dir.glob("yt-dlp-*"))
                    source_pkg = extracted_root / "yt_dlp"
                    target_pkg = self.updates_dir / "yt_dlp"
                    
                    if target_pkg.exists():
                        shutil.rmtree(target_pkg)
                        
                    shutil.move(str(source_pkg), str(target_pkg))
                    shutil.rmtree(extracted_root)
                    archive_path.unlink()

                await asyncio.to_thread(install)
                return # Success!
                
            except Exception as e:
                last_error = e
                if archive_path.exists(): archive_path.unlink()
                continue # Try next mirror

        # If all failed
        raise last_error or Exception("All download mirrors failed")
