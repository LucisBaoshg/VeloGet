import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ytdlpgui.core.site_profiles import build_ydl_opts
from ytdlpgui.core.ytdlp_cli import build_cli_command, parse_download_progress


class YtDlpCliTests(unittest.TestCase):
    def test_analyze_video_command_uses_dump_single_json_and_browser_cookies(self):
        opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.tiktok.com/@demo/video/1",
            browser="chrome",
            profile="Default",
        )

        command = build_cli_command(
            ytdlp_path="/tmp/bin/yt-dlp",
            url="https://www.tiktok.com/@demo/video/1",
            mode="analyze_video",
            opts=opts,
            ffmpeg_path=None,
        )

        self.assertEqual(command[0], "/tmp/bin/yt-dlp")
        self.assertIn("--dump-single-json", command)
        self.assertIn("--cookies-from-browser", command)
        self.assertIn("chrome:Default", command)
        self.assertIn("--extractor-args", command)
        self.assertIn("tiktok:app_info=/musical_ly/35.1.3/2023501030/0", command)

    def test_download_command_uses_output_template_and_ffmpeg_location(self):
        opts = build_ydl_opts(
            mode="download_video",
            url="https://www.youtube.com/watch?v=demo",
            browser="firefox",
            profile="default-release",
            format_id="137",
            ffmpeg_installed=True,
            download_path=Path("/tmp/downloads"),
        )

        command = build_cli_command(
            ytdlp_path="C:/runtime/yt-dlp.exe",
            url="https://www.youtube.com/watch?v=demo",
            mode="download_video",
            opts=opts,
            ffmpeg_path="C:/runtime/ffmpeg.exe",
        )

        self.assertIn("--format", command)
        self.assertIn("137+bestaudio/best", command)
        self.assertIn("--output", command)
        self.assertIn("/tmp/downloads/%(title)s.%(ext)s", command)
        self.assertIn("--ffmpeg-location", command)
        self.assertIn("C:/runtime/ffmpeg.exe", command)

    def test_parse_download_progress_extracts_percent(self):
        self.assertEqual(parse_download_progress("[download]  42.3% of 10.00MiB at 1.00MiB/s ETA 00:05"), 42.3)
        self.assertIsNone(parse_download_progress("[download] Destination: demo.mp4"))


if __name__ == "__main__":
    unittest.main()
