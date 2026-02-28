import os
import subprocess
import re
import asyncio
from pathlib import Path
from .dependency import DependencyManager
from .utils import debug_print

class MediaSplitter:
    def __init__(self, config_manager):
        self.config = config_manager
        self.deps = DependencyManager(self.config)

    async def split_media(self, input_path, segment_seconds, on_log=None, on_progress=None):
        return await asyncio.to_thread(
            self._split_media_sync, input_path, segment_seconds, on_log, on_progress
        )

    def _split_media_sync(self, input_path, segment_seconds, on_log, on_progress):
        ffmpeg_path = self.deps.get_ffmpeg_path()
        if not ffmpeg_path:
            raise Exception("FFmpeg not found. Please ensure FFmpeg is installed.")

        input_file = Path(input_path)
        if not input_file.exists():
            raise Exception(f"Input file not found: {input_path}")

        # Create output directory
        # Structure: parent_dir / filename_splits / segment_%03d.ext
        output_dir = input_file.parent / f"{input_file.stem}_splits"
        output_dir.mkdir(parents=True, exist_ok=True)

        file_ext = input_file.suffix.lstrip('.')
        output_pattern = str(output_dir / f"segment_%03d.{file_ext}")

        # Get total duration for progress calculation
        total_duration = self._get_duration(ffmpeg_path, str(input_file))
        
        cmd = [
            ffmpeg_path,
            "-i", str(input_file),
            "-c", "copy",
            "-map", "0",
            "-f", "segment",
            "-segment_time", str(segment_seconds),
            "-reset_timestamps", "1",
            "-y", # Overwrite existing
            output_pattern
        ]

        debug_print(f"Running Split Command: {' '.join(cmd)}")
        if on_log: on_log(f"Starting split: {input_file.name} -> {output_dir}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace' # Prevent decoding errors
        )

        if process.stdout is None:
             raise Exception("Failed to capture ffmpeg output")

        # Parse FFmpeg output for progress
        # Output example: "time=00:00:15.50"
        duration_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")

        for line in process.stdout:
            line = line.strip()
            if not line: continue
            
            # debug_print(f"FFmpeg: {line}")
            if on_log: on_log(line)

            # Progress calculation
            if total_duration > 0 and on_progress:
                match = duration_pattern.search(line)
                if match:
                    h, m, s = match.groups()
                    current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = min(99.0, (current_seconds / total_duration) * 100)
                    on_progress(percent)

        return_code = process.wait()
        
        if return_code != 0:
            raise Exception(f"FFmpeg failed with exit code {return_code}")

        if on_progress: on_progress(100)
        return str(output_dir)

    def _get_duration(self, ffmpeg_path, input_path):
        """Get video duration in seconds using ffmpeg"""
        try:
            cmd = [ffmpeg_path, "-i", input_path]
            # FFmpeg prints info to stderr
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            
            # Duration: 00:02:15.50, ...
            match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception as e:
            debug_print(f"Failed to get duration: {e}")
        return 0
