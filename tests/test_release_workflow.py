import unittest
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/release.yml")


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_uses_supported_macos_runner_labels(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("os: macos-15-intel", workflow)
        self.assertNotIn("os: macos-13", workflow)

    def test_release_workflow_forces_node24_for_javascript_actions(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true", workflow)

    def test_release_workflow_skips_apple_signing_when_secrets_are_missing(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("id: apple_signing", workflow)
        self.assertIn("APPLE_SIGNING_ENABLED=true", workflow)
        self.assertIn("APPLE_SIGNING_ENABLED=false", workflow)
        self.assertIn("steps.apple_signing.outputs.enabled == 'true'", workflow)

    def test_release_workflow_notarizes_a_zip_archive_instead_of_raw_app_bundle(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn('APP_ZIP_PATH="dist/veloget-${VERSION}-macos-${ARCH}.app.zip"', workflow)
        self.assertIn('ditto -c -k --keepParent "$APP_PATH" "$APP_ZIP_PATH"', workflow)
        self.assertIn('xcrun notarytool submit "$APP_ZIP_PATH" \\', workflow)
        self.assertNotIn('xcrun notarytool submit "$APP_PATH" \\', workflow)

    def test_release_workflow_removes_pod_symlinks_before_codesign(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn('find "$APP_PATH" -type l | while read -r link_path; do', workflow)
        self.assertIn('link_target="$(readlink "$link_path")"', workflow)
        self.assertIn("resolved_target=\"$(python -c 'from pathlib import Path; import sys;", workflow)
        self.assertIn('Removing invalid symlink: $link_path -> $link_target', workflow)

    def test_release_workflow_uses_explicit_nested_macho_signing_helper(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'python tools/sign_macos_app.py --app "$APP_PATH" --identity "$APPLE_SIGNING_IDENTITY"',
            workflow,
        )
        self.assertNotIn(
            'codesign --force --deep --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"',
            workflow,
        )

    def test_release_workflow_no_longer_prepares_internal_runtime_binaries(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertNotIn("Prepare Windows internal binaries", workflow)
        self.assertNotIn("src/ytdlpgui/_internal", workflow)

    def test_release_build_excludes_internal_runtime_directory(self):
        build_script = Path("build_release.sh").read_text(encoding="utf-8")
        windows_script = Path("build_release_win.ps1").read_text(encoding="utf-8")

        self.assertIn("src/ytdlpgui/_internal", build_script)
        self.assertIn("src/ytdlpgui/_internal", windows_script)

    def test_project_dependencies_no_longer_embed_ytdlp(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertNotIn("yt-dlp", pyproject)
        self.assertNotIn("yt-dlp", requirements)


if __name__ == "__main__":
    unittest.main()
