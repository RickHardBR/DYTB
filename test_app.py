from __future__ import annotations

import unittest
from pathlib import Path

from core.downloader import (
    build_ytdlp_command,
    format_friendly_error,
    parse_progress_line,
    sanitize_filename,
)
from core.formats import (
    FORMAT_OPTIONS,
    QUALITY_OPTIONS,
    clean_media_url,
    clean_youtube_url,
    detect_platform,
    extract_urls,
    get_format_extension,
    is_audio_format,
    validate_media_url,
    validate_url,
)
from core.history import add_to_history, clear_history, load_history, remove_from_history
from core.queue_manager import DownloadItem, DownloadQueueManager
from core.settings import get_browser_cookies, set_browser_cookies


class TestDYTB(unittest.TestCase):
    def test_url_validation(self):
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(validate_url("https://vimeo.com/123456789"))
        self.assertTrue(validate_url("https://www.tiktok.com/@user/video/12345"))
        self.assertTrue(validate_url("https://example.com/stream/playlist.m3u8"))
        self.assertFalse(validate_url("htp:/invalido"))
        self.assertFalse(validate_url(""))

    def test_platform_detection(self):
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=123"), "YouTube")
        self.assertEqual(detect_platform("https://vimeo.com/76979871"), "Vimeo")
        self.assertEqual(detect_platform("https://www.tiktok.com/@creator/video/1234"), "TikTok")
        self.assertEqual(detect_platform("https://www.instagram.com/reel/C12345/"), "Instagram")
        self.assertEqual(detect_platform("https://x.com/user/status/123"), "Twitter / X")
        self.assertEqual(detect_platform("https://web.dio.me/course/video-aula"), "DIO")
        self.assertEqual(detect_platform("https://hotmart.com/member/lesson/1"), "Hotmart / EAD")
        self.assertEqual(detect_platform("https://cdn.example.com/live/index.m3u8"), "HLS Stream (.m3u8)")
        self.assertEqual(detect_platform("https://cdn.example.com/live/manifest.mpd"), "DASH Stream (.mpd)")
        self.assertEqual(detect_platform("https://example.com/video.mp4"), "Vídeo Direto")

    def test_clean_instagram_and_vimeo_url(self):
        # Instagram plural route /reels/
        insta_plural = "https://www.instagram.com/reels/DcWKgodRBLd/?igsh=MWF5..."
        self.assertEqual(clean_media_url(insta_plural), "https://www.instagram.com/reel/DcWKgodRBLd/")

        # Vimeo embed route
        vimeo_embed = "https://player.vimeo.com/video/76979871?h=abcdef"
        self.assertEqual(clean_media_url(vimeo_embed), "https://player.vimeo.com/video/76979871?h=abcdef")

    def test_browser_cookies_injection(self):
        set_browser_cookies("chrome")
        self.assertEqual(get_browser_cookies(), "chrome")
        cmd = build_ytdlp_command("https://vimeo.com/76979871", "mp4")
        self.assertIn("--cookies-from-browser", cmd)
        self.assertIn("chrome", cmd)
        self.assertIn("--referer", cmd)
        set_browser_cookies("none")

    def test_clean_youtube_url(self):
        # Link com rádio/mix fornecido pelo usuário
        mix_url = "https://www.youtube.com/watch?v=0PkbdbJLfeM&list=RD0PkbdbJLfeM&start_radio=1"
        cleaned = clean_youtube_url(mix_url)
        self.assertEqual(cleaned, "https://www.youtube.com/watch?v=0PkbdbJLfeM")

        # Link com parâmetros de tempo e tracking
        tracking_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&feature=shared"
        self.assertEqual(clean_youtube_url(tracking_url), "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # Link encurtado com mix
        short_url = "https://youtu.be/0PkbdbJLfeM?list=RD0PkbdbJLfeM"
        self.assertEqual(clean_youtube_url(short_url), "https://www.youtube.com/watch?v=0PkbdbJLfeM")

    def test_extract_urls(self):
        text = """
        https://www.youtube.com/watch?v=0PkbdbJLfeM&list=RD0PkbdbJLfeM&start_radio=1
        https://vimeo.com/76979871
        https://www.tiktok.com/@test/video/1234?igsh=abcd123
        https://cdn.site.com/video.m3u8
        texto invalido
        https://www.youtube.com/watch?v=0PkbdbJLfeM
        """
        urls = extract_urls(text)
        self.assertEqual(len(urls), 4)
        self.assertIn("https://www.youtube.com/watch?v=0PkbdbJLfeM", urls)
        self.assertIn("https://player.vimeo.com/video/76979871", urls)
        self.assertIn("https://www.tiktok.com/@test/video/1234", urls)
        self.assertIn("https://cdn.site.com/video.m3u8", urls)

    def test_queue_manager_add_and_counts(self):
        qm = DownloadQueueManager()
        self.assertEqual(qm.get_counts()["total"], 0)

        item1 = qm.add_item("https://youtu.be/1", "mp4", "1080p")
        self.assertEqual(qm.get_counts()["total"], 1)
        self.assertEqual(qm.get_counts()["pending"], 1)

        added = qm.add_items(["https://youtu.be/2", "https://youtu.be/3"], "mp3", "best")
        self.assertEqual(len(added), 2)
        self.assertEqual(qm.get_counts()["total"], 3)
        self.assertEqual(qm.get_counts()["pending"], 3)

        qm.cancel_item(item1.id)
        self.assertEqual(qm.get_counts()["cancelled"], 1)
        self.assertEqual(qm.get_counts()["pending"], 2)

        qm.cancel_all()
        self.assertEqual(qm.get_counts()["cancelled"], 3)

        qm.clear_completed()
        self.assertEqual(qm.get_counts()["total"], 0)

    def test_formats_and_extensions(self):

        self.assertTrue(is_audio_format("mp3"))
        self.assertTrue(is_audio_format("wav"))
        self.assertTrue(is_audio_format("m4a"))
        self.assertFalse(is_audio_format("mp4"))
        self.assertFalse(is_audio_format("webm"))
        self.assertFalse(is_audio_format("mkv"))

        self.assertEqual(get_format_extension("mp4"), "mp4")
        self.assertEqual(get_format_extension("mp3"), "mp3")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename('video: "teste"/algo*?'), "video testealgo")
        self.assertEqual(sanitize_filename("nome_limpo"), "nome_limpo")

    def test_build_ytdlp_command_mp4_720p(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cmd = build_ytdlp_command(url, "mp4", quality="720p")
        
        self.assertTrue("yt-dlp" in cmd[0].lower())
        self.assertIn("--no-keep-video", cmd)
        self.assertIn("--windows-filenames", cmd)
        self.assertIn("-f", cmd)
        
        # Encontra o argumento de formato
        fmt_idx = cmd.index("-f") + 1
        fmt_str = cmd[fmt_idx]
        self.assertIn("height<=720", fmt_str)
        self.assertIn("ext=mp4", fmt_str)
        self.assertIn(url, cmd)

    def test_build_ytdlp_command_mp3(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cmd = build_ytdlp_command(url, "mp3")
        
        self.assertIn("--extract-audio", cmd)
        self.assertIn("--audio-format", cmd)
        self.assertIn("mp3", cmd)
        self.assertIn(url, cmd)

    def test_build_ytdlp_command_custom_name(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cmd = build_ytdlp_command(url, "mp4", custom_name="meu_video_personalizado")
        
        output_idx = cmd.index("--output") + 1
        output_path = cmd[output_idx]
        self.assertTrue(output_path.endswith("meu_video_personalizado.%(ext)s"))

    def test_parse_progress_line(self):
        line = "[download]  45.2% of 15.30MiB at 2.45MiB/s ETA 00:03"
        info = parse_progress_line(line)
        self.assertAlmostEqual(info.percent, 45.2, places=1)
        self.assertEqual(info.speed, "2.45MiB/s")
        self.assertEqual(info.eta, "00:03")
        self.assertEqual(info.total_size, "15.30MiB")
        self.assertIn("45.2%", info.status_text)

        line_template = "[download]  15.2% of 3.29MiB at 9.78MiB/s ETA 00:00"
        info_tmpl = parse_progress_line(line_template)
        self.assertAlmostEqual(info_tmpl.percent, 15.2, places=1)
        self.assertEqual(info_tmpl.speed, "9.78MiB/s")
        self.assertEqual(info_tmpl.eta, "00:00")
        self.assertEqual(info_tmpl.total_size, "3.29MiB")

        merge_line = "[Merger] Merging formats into 'video.mp4'"
        info_merge = parse_progress_line(merge_line)
        self.assertEqual(info_merge.percent, 99.0)
        self.assertIn("Mesclando", info_merge.status_text)

    def test_history_crud(self):
        clear_history()
        self.assertEqual(len(load_history()), 0)

        add_to_history(
            url="https://youtu.be/123",
            title="Video Teste",
            output_format="mp4",
            quality="1080p",
            output_path="C:/Downloads/Video Teste.mp4",
            file_size_mb=25.5,
        )

        entries = load_history()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Video Teste")
        self.assertEqual(entries[0]["format"], "mp4")
        self.assertEqual(entries[0]["size_mb"], 25.5)

        remove_from_history(0)
        self.assertEqual(len(load_history()), 0)

    def test_friendly_error_formatting(self):
        # Caso de login/conteúdo privado
        login_err = "ERROR: [vimeo] 1222710784: The web client only works when logged-in. Use --cookies, --cookies-from-browser"
        t, s, g = format_friendly_error(login_err, "Vimeo")
        self.assertEqual(t, "Conteúdo Restrito / Exige Login")
        self.assertIn("exige login", s)
        self.assertIn("Configurações", g)

        # Caso de banco de cookies travado
        cookie_lock = "ERROR: Could not copy Chrome cookie database in C:/Users/... Permission denied"
        t2, s2, g2 = format_friendly_error(cookie_lock)
        self.assertEqual(t2, "Navegador Bloqueando Cookies")
        self.assertIn("navegador está aberto", s2)

        # Caso 404
        not_found = "ERROR: [generic] HTTP Error 404: Not Found"
        t3, s3, g3 = format_friendly_error(not_found, "Instagram")
        self.assertEqual(t3, "Vídeo Não Encontrado")


if __name__ == "__main__":
    unittest.main()
