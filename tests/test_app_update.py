import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ytdlpgui.core import app_update


class VersionTests(unittest.TestCase):
    def test_detect_platform_arch_for_macos_arm64(self):
        platform_name, arch = app_update.detect_platform_arch("darwin", "arm64")

        self.assertEqual(platform_name, "macos")
        self.assertEqual(arch, "arm64")

    def test_detect_platform_arch_for_windows_amd64(self):
        platform_name, arch = app_update.detect_platform_arch("win32", "AMD64")

        self.assertEqual(platform_name, "windows")
        self.assertEqual(arch, "x64")

    def test_detect_platform_arch_rejects_unknown_platform(self):
        with self.assertRaises(ValueError):
            app_update.detect_platform_arch("plan9", "x86_64")

    def test_version_comparison_only_accepts_newer_versions(self):
        self.assertTrue(app_update.is_version_newer("1.0.2", "1.0.1"))
        self.assertFalse(app_update.is_version_newer("1.0.1", "1.0.1"))
        self.assertFalse(app_update.is_version_newer("1.0.0", "1.0.1"))


class ReleaseAssetTests(unittest.TestCase):
    def test_build_release_filenames_for_macos(self):
        assets = app_update.build_release_filenames("veloget", "1.2.3", "macos", "arm64")

        self.assertEqual(assets.installer, "veloget-1.2.3-macos-arm64.dmg")
        self.assertEqual(assets.in_app_update, "veloget-1.2.3-macos-arm64.app.tar.gz")

    def test_build_release_filenames_for_windows(self):
        assets = app_update.build_release_filenames("veloget", "1.2.3", "windows", "x64")

        self.assertEqual(assets.installer, "veloget-1.2.3-windows-x64.zip")
        self.assertEqual(assets.in_app_update, "veloget-1.2.3-windows-x64.app.tar.gz")


class MetadataTests(unittest.TestCase):
    def test_parse_update_metadata_from_service_response(self):
        payload = {
            "app_id": "veloget",
            "version": "1.2.3",
            "published_at": "2026-04-03T11:24:00Z",
            "synced_at": "2026-04-03 11:48:31",
            "notes": "- Fix updater",
            "platform": "windows",
            "arch": "x64",
            "kind": "in_app_update",
            "filename": "veloget-1.2.3-windows-x64.app.tar.gz",
            "sha256": "abc123",
            "size": 1024,
            "download_url": "http://example.com/download",
        }

        metadata = app_update.UpdateMetadata.from_dict(payload)

        self.assertEqual(metadata.app_id, "veloget")
        self.assertEqual(metadata.version, "1.2.3")
        self.assertEqual(metadata.kind, "in_app_update")
        self.assertEqual(metadata.filename, "veloget-1.2.3-windows-x64.app.tar.gz")

    def test_parse_update_metadata_defaults_kind_to_installer(self):
        payload = {
            "app_id": "veloget",
            "version": "1.2.3",
            "platform": "windows",
            "arch": "x64",
            "filename": "veloget-1.2.3-windows-x64.zip",
            "sha256": "abc123",
            "size": 1024,
            "download_url": "http://example.com/download",
        }

        metadata = app_update.UpdateMetadata.from_dict(payload)

        self.assertEqual(metadata.kind, "installer")


class PendingUpdateTests(unittest.TestCase):
    def test_pending_update_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "pending_update.json"
            pending = app_update.PendingUpdate(
                version="1.2.3",
                package_kind="in_app_update",
                staging_dir=Path(tmp) / "staging" / "1.2.3",
                package_path=Path(tmp) / "downloads" / "veloget.tar.gz",
                target_path=Path("/Applications/VeloGet.app"),
                executable_path=Path("/Applications/VeloGet.app/Contents/MacOS/VeloGet"),
            )

            app_update.save_pending_update(state_path, pending)
            loaded = app_update.load_pending_update(state_path)

            self.assertEqual(loaded.version, "1.2.3")
            self.assertEqual(loaded.package_kind, "in_app_update")
            self.assertEqual(loaded.target_path, Path("/Applications/VeloGet.app"))
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["version"],
                "1.2.3",
            )

    def test_load_pending_update_returns_none_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"

            self.assertIsNone(app_update.load_pending_update(missing))

    def test_render_windows_update_script_replaces_install_dir(self):
        pending = app_update.PendingUpdate(
            version="1.2.3",
            package_kind="in_app_update",
            staging_dir=Path(r"C:\Temp\veloget\1.2.3"),
            package_path=Path(r"C:\Temp\veloget\1.2.3\package.tar.gz"),
            target_path=Path(r"C:\Apps\VeloGet"),
            executable_path=Path(r"C:\Apps\VeloGet\VeloGet.exe"),
        )

        script = app_update.render_update_script("windows", pending, current_pid=4321)

        self.assertIn("Wait-Process -Id 4321", script)
        self.assertIn("Remove-Item -Path $targetPath\\*", script)
        self.assertIn("Start-Process -FilePath $executablePath", script)

    def test_render_macos_update_script_replaces_app_bundle(self):
        pending = app_update.PendingUpdate(
            version="1.2.3",
            package_kind="in_app_update",
            staging_dir=Path("/tmp/veloget/1.2.3"),
            package_path=Path("/tmp/veloget/1.2.3/package.tar.gz"),
            target_path=Path("/Applications/VeloGet.app"),
            executable_path=Path("/Applications/VeloGet.app/Contents/MacOS/VeloGet"),
        )

        script = app_update.render_update_script("macos", pending, current_pid=4321)

        self.assertIn("while kill -0 4321", script)
        self.assertIn('rm -rf "/Applications/VeloGet.app"', script)
        self.assertIn('open "/Applications/VeloGet.app"', script)


if __name__ == "__main__":
    unittest.main()
