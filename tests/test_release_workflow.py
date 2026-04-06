from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/release.yml")


def test_release_workflow_uses_supported_macos_runner_labels():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "os: macos-15-intel" in workflow
    assert "os: macos-13" not in workflow


def test_release_workflow_forces_node24_for_javascript_actions():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true" in workflow
