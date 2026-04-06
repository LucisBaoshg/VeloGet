from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse


SUPPORTED_SITES = ("youtube", "tiktok", "douyin", "generic")
SUPPORTED_PROFILES = ("default", "youtube", "tiktok")

TIKTOK_APP_INFO_FALLBACKS = [
    "/musical_ly/35.1.3/2023501030/0",
]

PROFILE_SITE_MAP = {
    "youtube": "youtube",
    "tiktok": "tiktok",
}


def detect_site(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":", 1)[0]

    if host == "youtu.be" or host.endswith("youtube.com"):
        return "youtube"
    if host.endswith("tiktok.com"):
        return "tiktok"
    if host.endswith("douyin.com") or host.endswith("iesdouyin.com"):
        return "douyin"
    return "generic"


def resolve_site_profile(url: str) -> str:
    site = detect_site(url)
    return PROFILE_SITE_MAP.get(site, "default")


def build_ydl_opts(
    *,
    mode: str,
    url: str,
    browser: str,
    profile: str | None = None,
    cookie_file: str | None = None,
    format_id: str | None = None,
    ffmpeg_installed: bool = False,
    download_path: Path | None = None,
    logger=None,
    progress_hooks=None,
) -> dict:
    opts = _base_mode_opts(mode, format_id, ffmpeg_installed, download_path, logger, progress_hooks)
    profile_name = resolve_site_profile(url)
    opts.update(_profile_overrides(profile_name, mode))
    _apply_cookie_options(opts, browser, profile, cookie_file)
    return opts


def _base_mode_opts(mode, format_id, ffmpeg_installed, download_path, logger, progress_hooks) -> dict:
    if mode == "analyze_video":
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreconfig": True,
            "ignore_no_formats_error": True,
            "format": "best/bestvideo+bestaudio",
            "remote_components": {"ejs": "github"},
        }

    if mode == "download_video":
        if download_path is None:
            raise ValueError("download_path is required for download_video mode")

        return {
            "outtmpl": str(Path(download_path) / "%(title)s.%(ext)s"),
            "progress_hooks": list(progress_hooks or []),
            "logger": logger,
            "no_warnings": False,
            "ignoreconfig": True,
            "remote_components": {"ejs": "github"},
            "format": _select_download_format(format_id, ffmpeg_installed),
        }

    if mode == "analyze_channel":
        return {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "ignoreconfig": True,
            "ignore_no_formats_error": True,
        }

    raise ValueError(f"Unsupported mode: {mode}")


def _select_download_format(format_id: str | None, ffmpeg_installed: bool) -> str:
    if format_id == "best":
        return "bv+ba/b" if ffmpeg_installed else "best"
    if format_id == "bestaudio":
        return "bestaudio/best"
    if format_id:
        return f"{format_id}+bestaudio/best" if ffmpeg_installed else format_id
    return "best"


def _apply_cookie_options(opts: dict, browser: str, profile: str | None, cookie_file: str | None) -> None:
    if cookie_file:
        opts["cookiefile"] = cookie_file
        opts.pop("cookiesfrombrowser", None)
        return

    opts["cookiesfrombrowser"] = (browser, profile or None, None, None)


def _profile_overrides(profile_name: str, mode: str) -> dict:
    profiles = {
        "default": {
            "analyze_video": {},
            "download_video": {},
            "analyze_channel": {},
        },
        "youtube": {
            "analyze_video": {},
            "download_video": {},
            "analyze_channel": {},
        },
        "tiktok": {
            "analyze_video": {
                "extractor_args": {
                    "tiktok": {
                        "app_info": TIKTOK_APP_INFO_FALLBACKS,
                    },
                },
            },
            "download_video": {
                "extractor_args": {
                    "tiktok": {
                        "app_info": TIKTOK_APP_INFO_FALLBACKS,
                    },
                },
            },
            "analyze_channel": {},
        },
    }
    return deepcopy(profiles.get(profile_name, profiles["default"]).get(mode, {}))
