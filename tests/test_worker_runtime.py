import asyncio
import sys
import unittest
from pathlib import Path
from unittest import mock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.modules.setdefault("yt_dlp", SimpleNamespace(YoutubeDL=object, version=SimpleNamespace(__version__="0.0.0")))

from ytdlpgui.core.worker import YtDlpWorker


class StubConfig:
    def __init__(self):
        self.config_data = {}

    def get_cookie_file(self):
        return ""

    def get_download_dir(self):
        return "/tmp/veloget-downloads"

    def get_js_engine_path(self):
        return ""


class StubDeps:
    def __init__(self):
        self.bin_dir = Path("/tmp/runtime")
        self.internal_bin_dir = Path("/tmp/internal")

    def get_ytdlp_path(self):
        return "/tmp/runtime/yt-dlp"

    def get_ffmpeg_path(self):
        return "/tmp/runtime/ffmpeg"

    def is_ffmpeg_installed(self):
        return True


class WorkerRuntimeTests(unittest.TestCase):
    def _make_worker(self):
        worker = YtDlpWorker.__new__(YtDlpWorker)
        worker.config = StubConfig()
        worker.deps = StubDeps()
        return worker

    def test_analyze_url_uses_external_ytdlp_cli(self):
        worker = self._make_worker()

        with mock.patch("ytdlpgui.core.worker.build_cli_command", return_value=["/tmp/runtime/yt-dlp", "--dump-single-json"]), \
             mock.patch("ytdlpgui.core.worker.run_json_command", return_value={"title": "Demo", "formats": []}) as run_json:
            result = worker._analyze_sync("https://www.youtube.com/watch?v=demo", "chrome", "Default")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["title"], "Demo")
        run_json.assert_called_once()

    def test_download_video_uses_external_ytdlp_cli(self):
        worker = self._make_worker()

        with mock.patch("ytdlpgui.core.worker.build_cli_command", return_value=["/tmp/runtime/yt-dlp", "https://example.com"]), \
             mock.patch("ytdlpgui.core.worker.run_download_command") as run_download:
            result = worker._download_sync(
                "https://www.youtube.com/watch?v=demo",
                "best",
                "chrome",
                "Default",
                on_log=None,
                on_progress=None,
            )

        self.assertEqual(result["status"], "success")
        run_download.assert_called_once()


if __name__ == "__main__":
    unittest.main()
