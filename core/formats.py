from __future__ import annotations

import re

AUDIO_FORMATS = {"mp3", "wav", "m4a"}
VIDEO_FORMATS = {"mp4", "webm", "mkv"}

FORMAT_OPTIONS = {
    "mp4": {"label": "Vídeo MP4 (.mp4)", "icon": "", "ext": "mp4", "type": "video"},
    "webm": {"label": "Vídeo WebM (.webm)", "icon": "", "ext": "webm", "type": "video"},
    "mkv": {"label": "Vídeo MKV (.mkv)", "icon": "", "ext": "mkv", "type": "video"},
    "mp3": {"label": "Áudio MP3 (.mp3)", "icon": "", "ext": "mp3", "type": "audio"},
    "m4a": {"label": "Áudio M4A / AAC (.m4a)", "icon": "", "ext": "m4a", "type": "audio"},
    "wav": {"label": "Áudio WAV (.wav)", "icon": "", "ext": "wav", "type": "audio"},
}

QUALITY_OPTIONS = {
    "best": {"label": "Melhor qualidade disponível", "height": None},
    "1080p": {"label": "1080p (Full HD)", "height": 1080},
    "720p": {"label": "720p (HD)", "height": 720},
    "480p": {"label": "480p (SD)", "height": 480},
    "360p": {"label": "360p (Baixa)", "height": 360},
}


def is_audio_format(fmt: str) -> bool:
    return fmt.lower() in AUDIO_FORMATS


def get_format_extension(fmt: str) -> str:
    return FORMAT_OPTIONS.get(fmt.lower(), {}).get("ext", fmt.lower())


def get_format_label(fmt: str) -> str:
    return FORMAT_OPTIONS.get(fmt.lower(), {}).get("label", fmt)


def get_quality_label(quality: str) -> str:
    return QUALITY_OPTIONS.get(quality, {}).get("label", quality)


def is_playlist_url(url: str) -> bool:
    cleaned = url.strip().lower()
    return any(keyword in cleaned for keyword in ["playlist?list=", "&list=", "channel/", "/playlists"])


def validate_url(url: str) -> bool:
    pattern = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)[^\s]*$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url.strip()))
