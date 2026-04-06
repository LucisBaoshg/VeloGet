#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence


BUNDLE_SUFFIXES = (".framework", ".bundle", ".appex", ".xpc")
FILE_BATCH_SIZE = 200


def chunked(items: Sequence[Path], size: int) -> Iterable[list[Path]]:
    for index in range(0, len(items), size):
        yield list(items[index : index + size])


def iter_regular_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )


def describe_files(paths: Sequence[Path]) -> str:
    completed = subprocess.run(
        ["file", *[str(path) for path in paths]],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def discover_macho_files(
    app_path: Path,
    describe_files_func: Callable[[Sequence[Path]], str] = describe_files,
) -> list[Path]:
    macho_files: list[Path] = []
    files = iter_regular_files(app_path)
    for batch in chunked(files, FILE_BATCH_SIZE):
        output = describe_files_func(batch)
        for line in output.splitlines():
            file_path, _, description = line.partition(":")
            if "Mach-O" not in description:
                continue
            if " (for architecture " in file_path:
                continue
            macho_files.append(Path(file_path).resolve())
    return sorted(set(macho_files), key=path_sort_key, reverse=True)


def path_sort_key(path: Path) -> tuple[int, str]:
    return (len(path.parts), str(path))


def discover_bundle_dirs(app_path: Path) -> list[Path]:
    bundle_dirs = [
        path
        for path in app_path.rglob("*")
        if path.is_dir()
        and not path.is_symlink()
        and path.name.endswith(BUNDLE_SUFFIXES)
    ]
    return sorted(bundle_dirs, key=path_sort_key, reverse=True)


def dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def build_sign_plan(app_path: Path, macho_files: Sequence[Path]) -> list[Path]:
    app_path = app_path.resolve()
    normalized_macho_files = sorted(
        {path.resolve() for path in macho_files},
        key=path_sort_key,
        reverse=True,
    )
    bundle_dirs = [path.resolve() for path in discover_bundle_dirs(app_path)]
    return dedupe_paths([*normalized_macho_files, *bundle_dirs, app_path])


def codesign(path: Path, identity: str) -> None:
    subprocess.run(
        [
            "codesign",
            "--force",
            "--options",
            "runtime",
            "--timestamp",
            "--sign",
            identity,
            str(path),
        ],
        check=True,
    )


def verify_signature(app_path: Path) -> None:
    subprocess.run(
        [
            "codesign",
            "--verify",
            "--deep",
            "--strict",
            "--verbose=2",
            str(app_path),
        ],
        check=True,
    )


def sign_app(app_path: Path, identity: str) -> list[Path]:
    macho_files = discover_macho_files(app_path)
    sign_plan = build_sign_plan(app_path, macho_files)
    for path in sign_plan:
        print(f"Signing {path}")
        codesign(path, identity)
    verify_signature(app_path)
    return sign_plan


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively sign nested Mach-O binaries in a macOS app bundle."
    )
    parser.add_argument("--app", required=True, help="Path to the .app bundle.")
    parser.add_argument(
        "--identity",
        required=True,
        help="Apple signing identity, for example Developer ID Application: Example Corp (TEAMID).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    app_path = Path(args.app).expanduser().resolve()
    if not app_path.is_dir():
        raise FileNotFoundError(f"App bundle not found: {app_path}")
    if app_path.suffix != ".app":
        raise ValueError(f"Expected a .app bundle, got: {app_path}")

    sign_app(app_path, args.identity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
