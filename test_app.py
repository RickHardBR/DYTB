from __future__ import annotations

import unittest
from pathlib import Path

from core.downloader import build_ytdlp_command, parse_progress_line, sanitize_filename
from core.formats import (
    FORMAT_OPTIONS,
    QUALITY_OPTIONS,
    get_format_extension,
    is_audio_format,
    validate_url,
)
from core.history import add_to_history, clear_history, load_history, remove_from_history


class TestDYTB(unittest.TestCase):
    def test_url_validation(self):
        self.assertTrue(validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertTrue(validate_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(validate_url("http://m.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertFalse(validate_url("https://example.com/video"))
        self.assertFalse(validate_url(""))

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


if __name__ == "__main__":
    unittest.main()
