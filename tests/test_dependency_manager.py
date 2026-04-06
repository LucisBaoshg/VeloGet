import tempfile
import unittest
from pathlib import Path
import sys
import asyncio
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ytdlpgui.core.dependency import DependencyManager


class StubConfig:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir


class DependencyManagerTests(unittest.TestCase):
    def test_missing_runtime_components_reports_ffmpeg_ffprobe_and_ytdlp(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DependencyManager(StubConfig(Path(tmp)))
            manager.internal_bin_dir = Path(tmp) / "empty-internal"

            with mock.patch("shutil.which", return_value=None):
                self.assertEqual(
                    manager.get_missing_runtime_components(),
                    ["ffmpeg", "ffprobe", "yt-dlp"],
                )

    def test_get_ytdlp_path_prefers_local_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DependencyManager(StubConfig(Path(tmp)))
            local_ytdlp = manager.bin_dir / "yt-dlp"
            local_ytdlp.write_text("#!/bin/sh\n", encoding="utf-8")
            local_ytdlp.chmod(0o755)

            self.assertEqual(manager.get_ytdlp_path(), str(local_ytdlp))

    def test_install_ffmpeg_uses_updated_macos_ffprobe_archive_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DependencyManager(StubConfig(Path(tmp)))

            with mock.patch.object(sys, "platform", "darwin"):
                with mock.patch.object(
                    manager,
                    "_download_and_extract",
                    new_callable=mock.AsyncMock,
                ) as download_and_extract:
                    asyncio.run(manager.install_ffmpeg())

            download_and_extract.assert_has_awaits(
                [
                    mock.call(
                        "https://evermeet.cx/ffmpeg/getrelease/zip",
                        "ffmpeg",
                        None,
                    ),
                    mock.call(
                        "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip",
                        "ffprobe",
                        None,
                    ),
                ]
            )


if __name__ == "__main__":
    unittest.main()
