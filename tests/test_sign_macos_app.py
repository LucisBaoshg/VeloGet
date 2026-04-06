import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path("tools/sign_macos_app.py")


def load_module():
    spec = importlib.util.spec_from_file_location("sign_macos_app", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SignMacOSAppTests(unittest.TestCase):
    def test_script_exists(self):
        self.assertTrue(SCRIPT_PATH.exists())

    def test_discover_macho_files_ignores_file_architecture_detail_lines(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            app_path = Path(temp_dir) / "VeloGet.app"
            extension_path = (
                app_path
                / "Contents"
                / "Frameworks"
                / "serious_python_darwin.framework"
                / "Versions"
                / "A"
                / "Resources"
                / "python.bundle"
                / "Contents"
                / "Resources"
                / "stdlib"
                / "lib-dynload"
                / "_socket.cpython-312-darwin.so"
            )
            text_file = app_path / "Contents" / "Resources" / "README.txt"

            extension_path.parent.mkdir(parents=True, exist_ok=True)
            extension_path.write_bytes(b"binary")
            text_file.parent.mkdir(parents=True, exist_ok=True)
            text_file.write_text("hello", encoding="utf-8")

            def fake_describe_files(_paths):
                return "\n".join(
                    [
                        f"{extension_path}: Mach-O universal binary with 2 architectures: [x86_64:Mach-O 64-bit bundle x86_64] [arm64:Mach-O 64-bit bundle arm64]",
                        f"{extension_path} (for architecture x86_64): Mach-O 64-bit bundle x86_64",
                        f"{extension_path} (for architecture arm64): Mach-O 64-bit bundle arm64",
                        f"{text_file}: ASCII text",
                    ]
                )

            macho_files = module.discover_macho_files(
                app_path,
                describe_files_func=fake_describe_files,
            )

            self.assertEqual(macho_files, [extension_path.resolve()])

    def test_build_sign_plan_signs_nested_macho_before_bundles_and_app(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            app_path = Path(temp_dir) / "VeloGet.app"
            app_binary = app_path / "Contents" / "MacOS" / "VeloGet"
            framework_root = app_path / "Contents" / "Frameworks" / "serious_python_darwin.framework"
            framework_binary = framework_root / "Versions" / "A" / "serious_python_darwin"
            python_bundle = (
                framework_root
                / "Versions"
                / "A"
                / "Resources"
                / "python.bundle"
            )
            socket_extension = (
                python_bundle
                / "Contents"
                / "Resources"
                / "stdlib"
                / "lib-dynload"
                / "_socket.cpython-312-darwin.so"
            )

            for path in (app_binary, framework_binary, socket_extension):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"binary")

            plan = module.build_sign_plan(
                app_path,
                macho_files=[app_binary, framework_binary, socket_extension],
            )

            socket_extension = socket_extension.resolve()
            python_bundle = python_bundle.resolve()
            framework_binary = framework_binary.resolve()
            framework_root = framework_root.resolve()
            app_binary = app_binary.resolve()
            app_path = app_path.resolve()

            self.assertLess(plan.index(socket_extension), plan.index(python_bundle))
            self.assertLess(plan.index(framework_binary), plan.index(framework_root))
            self.assertLess(plan.index(app_binary), plan.index(app_path))
            self.assertEqual(plan[-1], app_path)


if __name__ == "__main__":
    unittest.main()
