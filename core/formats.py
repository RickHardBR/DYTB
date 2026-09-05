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


def clean_youtube_url(url: str) -> str:
    """Remove parâmetros desnecessários de rádio, mix, tracking e timestamps de URLs do YouTube."""
    if not url:
        return ""
    
    cleaned = url.strip()

    # Caso 1: URL padrão youtube.com/watch?v=ID ou m.youtube.com/watch?v=ID
    v_match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", cleaned)
    if v_match:
        video_id = v_match.group(1)
        # Se contiver parâmetros de mix do YouTube (RD...) ou rádio, extrai apenas o vídeo limpo
        if "list=rd" in cleaned.lower() or "start_radio=" in cleaned.lower() or "index=" in cleaned.lower():
            return f"https://www.youtube.com/watch?v={video_id}"
        # Se for apenas o vídeo com parâmetros de tracking/timestamp
        if "playlist?list=" not in cleaned.lower():
            return f"https://www.youtube.com/watch?v={video_id}"

    # Caso 2: URL curta youtu.be/ID
    short_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", cleaned)
    if short_match:
        video_id = short_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"

    return cleaned


def extract_urls(text: str) -> list[str]:
    """Extrai, limpa e valida URLs do YouTube a partir de um bloco de texto (linhas, espaços ou vírgulas)."""
    if not text:
        return []
    # Divide por quebras de linha, vírgulas, ponto-e-vírgula ou espaços múltiplos
    raw_tokens = re.split(r"[\r\n,;\s]+", text.strip())
    valid_urls: list[str] = []
    seen = set()
    for token in raw_tokens:
        token = token.strip()
        if token and validate_url(token):
            cleaned = clean_youtube_url(token)
            if cleaned not in seen:
                valid_urls.append(cleaned)
                seen.add(cleaned)
    return valid_urls


