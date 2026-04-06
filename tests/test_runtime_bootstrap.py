import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ytdlpgui.core.runtime_bootstrap import runtime_setup_required


class StubDeps:
    def __init__(self, missing):
        self._missing = missing

    def get_missing_runtime_components(self):
        return list(self._missing)


class RuntimeBootstrapTests(unittest.TestCase):
    def test_runtime_setup_required_when_components_are_missing(self):
        self.assertTrue(runtime_setup_required(StubDeps(["ffmpeg"])))

    def test_runtime_setup_not_required_when_runtime_is_ready(self):
        self.assertFalse(runtime_setup_required(StubDeps([])))


if __name__ == "__main__":
    unittest.main()
