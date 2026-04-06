import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_APP_ID = os.getenv("VELOGET_APP_ID", "veloget")
DEFAULT_MIRROR_BASE_URL = os.getenv(
    "VELOGET_UPDATE_BASE_URL",
    "http://tc-github-mirror.ite.tool4seller.com",
).rstrip("/")


@dataclass(frozen=True)
class ReleaseAssetNames:
    installer: str
    in_app_update: str


@dataclass(frozen=True)
class UpdateMetadata:
    app_id: str
    version: str
    platform: str
    arch: str
    filename: str
    sha256: str
    size: int
    download_url: str
    kind: str = "installer"
    notes: str = ""
    published_at: str = ""
    synced_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict):
        return cls(
            app_id=payload["app_id"],
            version=payload["version"],
            platform=payload["platform"],
            arch=payload["arch"],
            filename=payload["filename"],
            sha256=payload["sha256"],
            size=int(payload["size"]),
            download_url=payload["download_url"],
            kind=payload.get("kind", "installer"),
            notes=payload.get("notes", ""),
            published_at=payload.get("published_at", ""),
            synced_at=payload.get("synced_at", ""),
        )


@dataclass(frozen=True)
class PendingUpdate:
    version: str
    package_kind: str
    staging_dir: Path
    package_path: Path
    target_path: Path
    executable_path: Path | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload

    @classmethod
    def from_dict(cls, payload: dict):
        return cls(
            version=payload["version"],
            package_kind=payload["package_kind"],
            staging_dir=Path(payload["staging_dir"]),
            package_path=Path(payload["package_path"]),
            target_path=Path(payload["target_path"]),
            executable_path=Path(payload["executable_path"]) if payload.get("executable_path") else None,
        )


def detect_platform_arch(sys_platform: str | None = None, machine: str | None = None) -> tuple[str, str]:
    raw_platform = (sys_platform or sys.platform).lower()
    raw_machine = (machine or platform.machine()).lower()

    if raw_platform.startswith("darwin"):
        platform_name = "macos"
    elif raw_platform.startswith("win"):
        platform_name = "windows"
    elif raw_platform.startswith("linux"):
        platform_name = "linux"
    else:
        raise ValueError(f"Unsupported platform: {raw_platform}")

    arch_aliases = {
        "x86_64": "x64",
        "amd64": "x64",
        "x64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    arch = arch_aliases.get(raw_machine)
    if not arch:
        raise ValueError(f"Unsupported architecture: {raw_machine}")
    return platform_name, arch


def _version_key(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version)
    return tuple(int(part) for part in parts)


def is_version_newer(remote_version: str, current_version: str) -> bool:
    return _version_key(remote_version) > _version_key(current_version)


def build_release_filenames(app_id: str, version: str, platform_name: str, arch: str) -> ReleaseAssetNames:
    base = f"{app_id}-{version}-{platform_name}-{arch}"
    installer_ext = {
        "macos": ".dmg",
        "windows": ".zip",
        "linux": ".tar.gz",
    }.get(platform_name)
    if not installer_ext:
        raise ValueError(f"Unsupported installer platform: {platform_name}")
    return ReleaseAssetNames(
        installer=f"{base}{installer_ext}",
        in_app_update=f"{base}.app.tar.gz",
    )


def save_pending_update(state_path: Path, pending: PendingUpdate):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(pending.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_pending_update(state_path: Path) -> PendingUpdate | None:
    if not state_path.exists():
        return None
    return PendingUpdate.from_dict(json.loads(state_path.read_text(encoding="utf-8")))


def get_current_app_version() -> str:
    try:
        from importlib.metadata import version

        return version("VeloGet")
    except Exception:
        project_root = Path(__file__).resolve().parents[3]
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib
            with pyproject_path.open("rb") as handle:
                return tomllib.load(handle)["project"]["version"]
    return "0.0.0"


def get_default_runtime_paths() -> tuple[Path, Path | None]:
    executable_path = Path(sys.executable).resolve()
    platform_name, _arch = detect_platform_arch()
    if platform_name == "macos":
        app_root = next((parent for parent in executable_path.parents if parent.suffix == ".app"), executable_path)
        return app_root, executable_path
    return executable_path.parent, executable_path


def build_latest_url(
    app_id: str,
    platform_name: str,
    arch: str,
    kind: str = "installer",
    base_url: str = DEFAULT_MIRROR_BASE_URL,
) -> str:
    query = urllib.parse.urlencode(
        {
            "platform": platform_name,
            "arch": arch,
            "kind": kind,
        }
    )
    return f"{base_url}/updates/{app_id}/latest?{query}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_tar_gz(archive_path: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(destination)


def resolve_payload_root(staging_dir: Path, platform_name: str) -> Path:
    if not staging_dir.exists():
        if platform_name == "macos":
            return staging_dir / "VeloGet.app"
        return staging_dir
    if platform_name == "macos":
        app_bundles = list(staging_dir.glob("*.app"))
        if len(app_bundles) == 1:
            return app_bundles[0]
    children = [child for child in staging_dir.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return staging_dir


def render_update_script(platform_name: str, pending: PendingUpdate, current_pid: int) -> str:
    payload_root = resolve_payload_root(pending.staging_dir, platform_name)
    if platform_name == "windows":
        return f"""$ErrorActionPreference = "Stop"
$payloadPath = "{payload_root}"
$targetPath = "{pending.target_path}"
$executablePath = "{pending.executable_path}"

Wait-Process -Id {current_pid}
Start-Sleep -Seconds 2
if (Test-Path $targetPath) {{
    Remove-Item -Path $targetPath\\* -Recurse -Force
}} else {{
    New-Item -Path $targetPath -ItemType Directory | Out-Null
}}
Copy-Item -Path "$payloadPath\\*" -Destination $targetPath -Recurse -Force
Start-Sleep -Seconds 1
Start-Process -FilePath $executablePath
"""

    if platform_name == "macos":
        target_parent = pending.target_path.parent
        return f"""#!/bin/bash
set -e

while kill -0 {current_pid} 2>/dev/null; do
  sleep 1
done

rm -rf "{pending.target_path}"
mkdir -p "{target_parent}"
cp -R "{payload_root}" "{pending.target_path}"
open "{pending.target_path}"
"""

    raise ValueError(f"Unsupported platform for update script: {platform_name}")


class MirrorUpdateClient:
    def __init__(self, app_id: str = DEFAULT_APP_ID, base_url: str = DEFAULT_MIRROR_BASE_URL, timeout: int = 15):
        self.app_id = app_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_latest(self, platform_name: str, arch: str, kind: str = "installer") -> UpdateMetadata:
        url = build_latest_url(self.app_id, platform_name, arch, kind=kind, base_url=self.base_url)
        request = urllib.request.Request(url, headers={"User-Agent": "VeloGet-Updater/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return UpdateMetadata.from_dict(json.load(response))

    def download_update(self, metadata: UpdateMetadata, destination: Path, chunk_size: int = 1024 * 1024):
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(metadata.download_url, headers={"User-Agent": "VeloGet-Updater/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response, destination.open("wb") as output:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                output.write(chunk)

        actual_sha256 = sha256_file(destination)
        if actual_sha256.lower() != metadata.sha256.lower():
            raise ValueError(
                f"sha256 mismatch: expected {metadata.sha256.lower()}, got {actual_sha256.lower()}"
            )


def create_temp_update_script(content: str, suffix: str) -> Path:
    fd, temp_path = tempfile.mkstemp(prefix="veloget-update-", suffix=suffix)
    os.close(fd)
    script_path = Path(temp_path)
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(0o700)
    return script_path


class AppUpdateManager:
    def __init__(
        self,
        config_dir: Path,
        app_id: str = DEFAULT_APP_ID,
        base_url: str = DEFAULT_MIRROR_BASE_URL,
        current_version: str | None = None,
    ):
        self.config_dir = Path(config_dir)
        self.app_id = app_id
        self.client = MirrorUpdateClient(app_id=app_id, base_url=base_url)
        self.current_version = current_version or get_current_app_version()
        self.platform_name, self.arch = detect_platform_arch()
        self.target_path, self.executable_path = get_default_runtime_paths()
        self.update_root = self.config_dir / "app_updates"
        self.downloads_dir = self.update_root / "downloads"
        self.staging_root = self.update_root / "staging"
        self.pending_state_path = self.update_root / "pending_update.json"

    def fetch_latest(self, kind: str = "in_app_update") -> UpdateMetadata:
        return self.client.fetch_latest(self.platform_name, self.arch, kind=kind)

    def is_update_available(self, metadata: UpdateMetadata) -> bool:
        return is_version_newer(metadata.version, self.current_version)

    def stage_in_app_update(self, metadata: UpdateMetadata) -> PendingUpdate:
        package_path = self.downloads_dir / metadata.filename
        staging_dir = self.staging_root / metadata.version / "payload"

        if staging_dir.parent.exists():
            shutil.rmtree(staging_dir.parent)
        staging_dir.mkdir(parents=True, exist_ok=True)

        self.client.download_update(metadata, package_path)
        extract_tar_gz(package_path, staging_dir)

        pending = PendingUpdate(
            version=metadata.version,
            package_kind=metadata.kind,
            staging_dir=staging_dir,
            package_path=package_path,
            target_path=self.target_path,
            executable_path=self.executable_path,
        )
        save_pending_update(self.pending_state_path, pending)
        return pending

    def get_pending_update(self) -> PendingUpdate | None:
        return load_pending_update(self.pending_state_path)

    def clear_pending_update(self):
        if self.pending_state_path.exists():
            self.pending_state_path.unlink()

    def launch_pending_update(self, pending: PendingUpdate, current_pid: int | None = None):
        current_pid = current_pid or os.getpid()
        script_body = render_update_script(self.platform_name, pending, current_pid=current_pid)
        suffix = ".ps1" if self.platform_name == "windows" else ".sh"
        script_path = create_temp_update_script(script_body, suffix=suffix)

        if self.platform_name == "windows":
            subprocess.Popen(
                [
                    "powershell",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                close_fds=True,
            )
            return script_path

        subprocess.Popen(
            ["/bin/bash", str(script_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        return script_path
