from __future__ import annotations

import json
import re
import subprocess


PROGRESS_RE = re.compile(r"\[download\]\s+(?P<percent>\d+(?:\.\d+)?)%")


def build_cli_command(
    *,
    ytdlp_path: str,
    url: str,
    mode: str,
    opts: dict,
    ffmpeg_path: str | None,
) -> list[str]:
    command = [ytdlp_path]

    if opts.get("ignoreconfig"):
        command.append("--ignore-config")
    if opts.get("no_warnings"):
        command.append("--no-warnings")
    if opts.get("quiet"):
        command.append("--quiet")
    if opts.get("ignore_no_formats_error"):
        command.append("--ignore-no-formats-error")
    if opts.get("extract_flat"):
        command.append("--flat-playlist")
    if opts.get("format"):
        command.extend(["--format", opts["format"]])
    if opts.get("outtmpl"):
        command.extend(["--output", opts["outtmpl"]])
    if ffmpeg_path:
        command.extend(["--ffmpeg-location", ffmpeg_path])

    cookie_file = opts.get("cookiefile")
    if cookie_file:
        command.extend(["--cookies", cookie_file])
    elif opts.get("cookiesfrombrowser"):
        browser, profile, *_rest = opts["cookiesfrombrowser"]
        browser_value = browser if not profile else f"{browser}:{profile}"
        command.extend(["--cookies-from-browser", browser_value])

    extractor_args = opts.get("extractor_args") or {}
    for extractor, values in extractor_args.items():
        parts = [f"{key}={','.join(val) if isinstance(val, list) else val}" for key, val in values.items()]
        command.extend(["--extractor-args", f"{extractor}:{';'.join(parts)}"])

    if mode in {"analyze_video", "analyze_channel"}:
        command.append("--dump-single-json")
    else:
        command.extend(["--newline", "--progress"])

    command.append(url)
    return command


def parse_download_progress(line: str) -> float | None:
    match = PROGRESS_RE.search(line)
    if not match:
        return None
    return float(match.group("percent"))


def run_json_command(command: list[str], *, env: dict | None = None) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or "yt-dlp command failed")

    payload = result.stdout.strip().splitlines()
    if not payload:
        raise RuntimeError("yt-dlp returned no JSON output")
    return json.loads(payload[-1])


def run_download_command(
    command: list[str],
    *,
    env: dict | None = None,
    on_log=None,
    on_progress=None,
):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        if on_log:
            on_log(line)
        percent = parse_download_progress(line)
        if percent is not None and on_progress:
            on_progress(percent)

    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed with exit code {process.returncode}")
