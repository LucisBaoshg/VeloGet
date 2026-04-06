import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ytdlpgui.core.site_profiles import (
    SUPPORTED_PROFILES,
    build_ydl_opts,
    detect_site,
    resolve_site_profile,
)


class DetectSiteTests(unittest.TestCase):
    def test_detects_youtube_urls(self):
        self.assertEqual(detect_site("https://www.youtube.com/watch?v=abc123"), "youtube")
        self.assertEqual(detect_site("https://youtu.be/abc123"), "youtube")

    def test_detects_tiktok_urls(self):
        self.assertEqual(detect_site("https://www.tiktok.com/@user/video/123"), "tiktok")

    def test_detects_douyin_urls(self):
        self.assertEqual(detect_site("https://www.douyin.com/video/123"), "douyin")

    def test_falls_back_to_generic_for_unknown_sites(self):
        self.assertEqual(detect_site("https://www.bilibili.com/video/BV1xx"), "generic")


class ResolveSiteProfileTests(unittest.TestCase):
    def test_supported_profiles_include_tiktok(self):
        self.assertEqual(SUPPORTED_PROFILES, ("default", "youtube", "tiktok"))

    def test_youtube_urls_use_youtube_profile(self):
        self.assertEqual(resolve_site_profile("https://www.youtube.com/watch?v=abc123"), "youtube")
        self.assertEqual(resolve_site_profile("https://youtu.be/abc123"), "youtube")

    def test_tiktok_urls_use_tiktok_profile(self):
        self.assertEqual(resolve_site_profile("https://www.tiktok.com/@user/video/123"), "tiktok")

    def test_non_youtube_non_tiktok_urls_fall_back_to_default_profile(self):
        self.assertEqual(resolve_site_profile("https://www.douyin.com/video/123"), "default")
        self.assertEqual(resolve_site_profile("https://www.bilibili.com/video/BV1xx"), "default")


class BuildYdlOptsTests(unittest.TestCase):
    def test_youtube_and_default_profiles_are_behaviorally_identical_for_analyze_video(self):
        youtube_opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
        )
        default_opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.bilibili.com/video/BV1xx",
            browser="chrome",
            profile="Default",
        )

        self.assertEqual(youtube_opts, default_opts)

    def test_analyze_video_matches_current_defaults(self):
        opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.tiktok.com/@user/video/123",
            browser="chrome",
            profile="Default",
        )

        self.assertTrue(opts["quiet"])
        self.assertTrue(opts["no_warnings"])
        self.assertFalse(opts["extract_flat"])
        self.assertTrue(opts["ignoreconfig"])
        self.assertTrue(opts["ignore_no_formats_error"])
        self.assertEqual(opts["format"], "best/bestvideo+bestaudio")
        self.assertEqual(opts["remote_components"], {"ejs": "github"})
        self.assertEqual(opts["cookiesfrombrowser"], ("chrome", "Default", None, None))
        self.assertEqual(
            opts["extractor_args"]["tiktok"]["app_info"],
            ["/musical_ly/35.1.3/2023501030/0"],
        )

    def test_tiktok_profile_differs_from_youtube_profile(self):
        youtube_opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
        )
        tiktok_opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.tiktok.com/@user/video/123",
            browser="chrome",
            profile="Default",
        )

        self.assertNotIn("extractor_args", youtube_opts)
        self.assertIn("extractor_args", tiktok_opts)

    def test_download_video_uses_tiktok_extractor_args(self):
        opts = build_ydl_opts(
            mode="download_video",
            url="https://www.tiktok.com/@user/video/123",
            browser="chrome",
            profile="Default",
            format_id="best",
            ffmpeg_installed=True,
            download_path=Path("/tmp/downloads"),
        )

        self.assertEqual(
            opts["extractor_args"]["tiktok"]["app_info"],
            ["/musical_ly/35.1.3/2023501030/0"],
        )

    def test_cookie_file_takes_precedence_over_browser_cookies(self):
        opts = build_ydl_opts(
            mode="analyze_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
            cookie_file="/tmp/cookies.txt",
        )

        self.assertEqual(opts["cookiefile"], "/tmp/cookies.txt")
        self.assertNotIn("cookiesfrombrowser", opts)

    def test_download_best_with_ffmpeg_prefers_muxed_selector(self):
        opts = build_ydl_opts(
            mode="download_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
            format_id="best",
            ffmpeg_installed=True,
            download_path=Path("/tmp/downloads"),
            logger=object(),
            progress_hooks=[object()],
        )

        self.assertEqual(opts["format"], "bv+ba/b")
        self.assertEqual(opts["outtmpl"], "/tmp/downloads/%(title)s.%(ext)s")
        self.assertFalse(opts["no_warnings"])
        self.assertTrue(opts["ignoreconfig"])
        self.assertEqual(opts["remote_components"], {"ejs": "github"})

    def test_download_best_without_ffmpeg_falls_back_to_single_file(self):
        opts = build_ydl_opts(
            mode="download_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
            format_id="best",
            ffmpeg_installed=False,
            download_path=Path("/tmp/downloads"),
        )

        self.assertEqual(opts["format"], "best")

    def test_download_specific_format_depends_on_ffmpeg(self):
        opts_with_ffmpeg = build_ydl_opts(
            mode="download_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
            format_id="137",
            ffmpeg_installed=True,
            download_path=Path("/tmp/downloads"),
        )
        opts_without_ffmpeg = build_ydl_opts(
            mode="download_video",
            url="https://www.youtube.com/watch?v=abc123",
            browser="chrome",
            profile="Default",
            format_id="137",
            ffmpeg_installed=False,
            download_path=Path("/tmp/downloads"),
        )

        self.assertEqual(opts_with_ffmpeg["format"], "137+bestaudio/best")
        self.assertEqual(opts_without_ffmpeg["format"], "137")

    def test_channel_analysis_matches_current_defaults(self):
        opts = build_ydl_opts(
            mode="analyze_channel",
            url="https://www.youtube.com/@openai/videos",
            browser="firefox",
            profile="default",
        )

        self.assertTrue(opts["quiet"])
        self.assertTrue(opts["no_warnings"])
        self.assertTrue(opts["extract_flat"])
        self.assertTrue(opts["ignoreconfig"])
        self.assertTrue(opts["ignore_no_formats_error"])
        self.assertEqual(opts["cookiesfrombrowser"], ("firefox", "default", None, None))
        self.assertNotIn("remote_components", opts)


if __name__ == "__main__":
    unittest.main()
