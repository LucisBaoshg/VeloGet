from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/release.yml")


def test_release_workflow_uses_supported_macos_runner_labels():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "os: macos-15-intel" in workflow
    assert "os: macos-13" not in workflow


def test_release_workflow_forces_node24_for_javascript_actions():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in workflow


def test_release_workflow_skips_apple_signing_when_secrets_are_missing():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "id: apple_signing" in workflow
    assert "APPLE_SIGNING_ENABLED=true" in workflow
    assert "APPLE_SIGNING_ENABLED=false" in workflow
    assert "steps.apple_signing.outputs.enabled == 'true'" in workflow


def test_release_workflow_notarizes_a_zip_archive_instead_of_raw_app_bundle():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'APP_ZIP_PATH="dist/veloget-${VERSION}-macos-${ARCH}.app.zip"' in workflow
    assert 'ditto -c -k --keepParent "$APP_PATH" "$APP_ZIP_PATH"' in workflow
    assert 'xcrun notarytool submit "$APP_ZIP_PATH" \\' in workflow
    assert 'xcrun notarytool submit "$APP_PATH" \\' not in workflow


def test_release_workflow_removes_pod_symlinks_before_codesign():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'find "$APP_PATH" -type l -name ".pod" -print -delete' in workflow
