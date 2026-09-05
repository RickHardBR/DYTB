from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.formats import (
    AUDIO_FORMATS,
    QUALITY_OPTIONS,
    clean_media_url,
    detect_platform,
    get_format_extension,
    is_audio_format,
    validate_media_url,
    validate_url,
)
from core.installer import _refresh_system_path, ensure_yt_dlp_available
from core.settings import get_default_download_dir


class DownloadError(RuntimeError):
    pass


@dataclass
class ProgressInfo:
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    total_size: str = ""
    status_text: str = ""
    raw_line: str = ""


class DownloadSession:
    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.cancel_requested = False
        self.pause_requested = False
        self.is_paused = False

    def cancel(self):
        self.cancel_requested = True
        self.pause_requested = False
        self._kill_process()

    def pause(self):
        self.pause_requested = True
        self.is_paused = True
        self._kill_process()

    def resume(self):
        self.pause_requested = False
        self.is_paused = False

    def reset(self):
        self.cancel_requested = False
        self.pause_requested = False
        self.is_paused = False
        self.process = None

    def _kill_process(self):
        if self.process is not None and self.process.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                else:
                    self.process.terminate()
            except Exception:
                try:
                    self.process.terminate()
                except Exception:
                    pass


def detect_ffmpeg() -> bool:
    _refresh_system_path()
    return shutil.which("ffmpeg") is not None


def get_download_dir() -> str:
    return get_default_download_dir()


def sanitize_filename(filename: str) -> str:
    """Remove caracteres ilegais para nomes de arquivos no Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def build_ytdlp_command(
    url: str,
    output_format: str,
    quality: str = "best",
    custom_name: str | None = None,
    fallback_youtube_client: bool = False,
    save_dir: str | None = None,
) -> list[str]:
    if not validate_media_url(url):
        raise DownloadError("URL inválida. Cole um link válido de vídeo, plataforma ou stream.")

    clean_url = clean_media_url(url)
    platform = detect_platform(clean_url)
    download_dir = save_dir or get_download_dir()
    os.makedirs(download_dir, exist_ok=True)

    _refresh_system_path()
    has_ffmpeg = detect_ffmpeg()
    ffmpeg_bin = shutil.which("ffmpeg")
    ytdlp_bin = shutil.which("yt-dlp") or "yt-dlp"

    # Template do nome do arquivo
    if custom_name and custom_name.strip():
        clean_name = sanitize_filename(custom_name.strip())
        output_template = f"{clean_name}.%(ext)s"
    else:
        output_template = "%(title)s.%(ext)s"

    output_path = os.path.join(download_dir, output_template)

    cmd = [
        ytdlp_bin,
        "--newline",
        "--progress",
        "--progress-template",
        "download:[download] %(progress._percent_str)s of %(progress._total_bytes_str|progress._total_bytes_estimate_str)s at %(progress._speed_str)s ETA %(progress._eta_str)s",
        "--no-warnings",
        "--windows-filenames",
        "--no-keep-video",
        "--no-playlist",
        "--concurrent-fragments",
        "5",
        "--hls-prefer-native",
        "--retries",
        "5",
        "--fragment-retries",
        "10",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--compat-options",
        "no-youtube-unavailable-videos",
        "--output",
        output_path,
        "--print",
        "after_move:filepath",
    ]

    if ffmpeg_bin:
        cmd.extend(["--ffmpeg-location", os.path.dirname(ffmpeg_bin)])

    if platform == "YouTube" and fallback_youtube_client:
        cmd.extend([
            "--extractor-args",
            "youtube:player_client=android,web",
        ])

    target_fmt = output_format.lower()

    if is_audio_format(target_fmt):
        if not has_ffmpeg:
            raise DownloadError(
                "O FFmpeg é necessário para extrair áudio nos formatos MP3/WAV/M4A. "
                "Instale o FFmpeg ou execute o instalador do aplicativo."
            )
        cmd.append("--extract-audio")
        if target_fmt == "mp3":
            cmd.extend(["--audio-format", "mp3", "--audio-quality", "0"])
        elif target_fmt == "wav":
            cmd.extend(["--audio-format", "wav"])
        elif target_fmt == "m4a":
            cmd.extend(["--audio-format", "m4a"])
    else:
        # Formatos de Vídeo: mp4, webm, mkv
        height_limit = QUALITY_OPTIONS.get(quality, {}).get("height")
        
        if target_fmt == "mp4":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}][ext=mp4]/best[height<={height_limit}]/best"
                )
            else:
                fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "mp4"])

        elif target_fmt == "webm":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}][ext=webm]+bestaudio[ext=webm]/"
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}][ext=webm]/best[height<={height_limit}]/best"
                )
            else:
                fmt_str = "bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo+bestaudio/best[ext=webm]/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "webm"])

        elif target_fmt == "mkv":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}]/best"
                )
            else:
                fmt_str = "bestvideo+bestaudio/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "mkv"])

    cmd.append(clean_url)
    return cmd


PROGRESS_PERCENT_REGEX = re.compile(r"(\d+(?:\.\d+)?)%")
SPEED_REGEX = re.compile(r"at\s+([^\s]+(?:iB/s|B/s|k/s|M/s))", re.IGNORECASE)
ETA_REGEX = re.compile(r"ETA\s+(\d+:\d+(?::\d+)?)", re.IGNORECASE)
SIZE_REGEX = re.compile(r"of\s+~?([^\s]+(?:iB|B))", re.IGNORECASE)


def parse_progress_line(line: str) -> ProgressInfo:
    info = ProgressInfo(raw_line=line)

    percent_match = PROGRESS_PERCENT_REGEX.search(line)
    if percent_match:
        try:
            info.percent = float(percent_match.group(1))
        except ValueError:
            info.percent = 0.0

    speed_match = SPEED_REGEX.search(line)
    if speed_match:
        val = speed_match.group(1)
        if "Unknown" not in val and "NA" not in val:
            info.speed = val

    eta_match = ETA_REGEX.search(line)
    if eta_match:
        val = eta_match.group(1)
        if "Unknown" not in val and "NA" not in val:
            info.eta = val

    size_match = SIZE_REGEX.search(line)
    if size_match:
        val = size_match.group(1)
        if "Unknown" not in val and "NA" not in val:
            info.total_size = val

    if "[download]" in line:
        if info.percent > 0:
            status_parts = [f"Baixando: {info.percent:.1f}%"]
            if info.total_size:
                status_parts.append(f"de {info.total_size}")
            if info.speed:
                status_parts.append(f"({info.speed})")
            if info.eta:
                status_parts.append(f"ETA: {info.eta}")
            info.status_text = " ".join(status_parts)
        elif "Destination:" in line:
            dest_name = os.path.basename(line.split("Destination:", 1)[1].strip())
            info.status_text = f"Iniciando: {dest_name}"
        elif "100%" in line or "100.0%" in line:
            info.status_text = "Download finalizado, processando..."
            info.percent = 100.0
        else:
            info.status_text = line
    elif "[Merger]" in line or "Merging formats" in line:
        info.status_text = "Mesclando faixas de áudio e vídeo..."
        info.percent = 99.0
    elif "[ExtractAudio]" in line:
        info.status_text = "Extraindo e convertendo faixa de áudio..."
        info.percent = 99.0
    elif "[Fixup" in line or "[VideoRemuxer]" in line:
        info.status_text = "Ajustando contêiner de saída..."
        info.percent = 99.0
    else:
        info.status_text = line

    return info


def run_download(
    url: str,
    output_format: str,
    quality: str = "best",
    custom_name: str | None = None,
    on_progress: Callable[[ProgressInfo], None] | None = None,
    save_dir: str | None = None,
    session: DownloadSession | None = None,
) -> str:
    ensure_yt_dlp_available()

    if session is not None:
        session.reset()

    commands = [
        build_ytdlp_command(
            url, output_format, quality=quality, custom_name=custom_name, fallback_youtube_client=False, save_dir=save_dir
        ),
        build_ytdlp_command(
            url, output_format, quality=quality, custom_name=custom_name, fallback_youtube_client=True, save_dir=save_dir
        ),
    ]

    last_recorded_path: str | None = None

    for attempt_index, cmd in enumerate(commands, start=1):
        if on_progress is not None:
            if attempt_index == 2:
                on_progress(ProgressInfo(percent=5.0, status_text="Tentando método alternativo de conexão com o YouTube..."))
            else:
                on_progress(ProgressInfo(percent=1.0, status_text="Conectando e obtendo dados do vídeo..."))

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

        if session is not None:
            session.process = process

        output_lines: list[str] = []
        while True:
            if session is not None and session.cancel_requested:
                session._kill_process()
                raise DownloadError("Download cancelado pelo usuário.")
            if session is not None and session.pause_requested:
                session._kill_process()
                raise DownloadError("Download pausado pelo usuário.")

            if process.stdout is None:
                break
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if line:
                    output_lines.append(line)
                    # Verifica se a linha é um caminho de arquivo final emitido pelo --print after_move:filepath
                    if os.path.isabs(line) and os.path.exists(line):
                        last_recorded_path = line
                    elif "[download] Destination:" in line:
                        candidate = line.split("[download] Destination:", 1)[1].strip()
                        if os.path.exists(candidate):
                            last_recorded_path = candidate
                    elif "[Merger] Merging formats into" in line:
                        candidate = line.split("Merging formats into", 1)[1].strip().strip('"\'')
                        if os.path.exists(candidate):
                            last_recorded_path = candidate
                    elif "[ExtractAudio] Destination:" in line:
                        candidate = line.split("[ExtractAudio] Destination:", 1)[1].strip()
                        if os.path.exists(candidate):
                            last_recorded_path = candidate

                    if on_progress is not None:
                        prog_info = parse_progress_line(line)
                        on_progress(prog_info)

        returncode = process.wait()
        if returncode == 0:
            if last_recorded_path and os.path.exists(last_recorded_path):
                return last_recorded_path
            
            resolved = _resolve_downloaded_file(output_format, save_dir)
            if resolved:
                return resolved
            raise DownloadError("O download foi concluído, mas o arquivo final não pôde ser localizado.")

        recent_output = "\n".join(output_lines[-10:])
        if "The page needs to be reloaded" in recent_output or "player_client" in recent_output.lower():
            if attempt_index == 1:
                continue

        if "UNSUPPORTED_URL" in recent_output or "unable to download webpage" in recent_output.lower():
            raise DownloadError("Não foi possível acessar o link. Verifique se a URL está correta e se o vídeo está público.")
        if "ffmpeg" in recent_output.lower() and "not found" in recent_output.lower():
            raise DownloadError("O FFmpeg não foi encontrado. Instale-o para converter e mesclar vídeos/áudios.")
        raise DownloadError(f"Erro ao baixar o conteúdo:\n\n{recent_output}")

    raise DownloadError("Não foi possível concluir o download após tentar métodos alternativos.")


def _resolve_downloaded_file(output_format: str, save_dir: str | None = None) -> str | None:
    download_dir = save_dir or get_download_dir()
    if not os.path.exists(download_dir):
        return None

    target_ext = get_format_extension(output_format).lower()
    candidates: list[str] = []

    for filename in os.listdir(download_dir):
        if filename.lower().endswith(f".{target_ext}"):
            candidates.append(os.path.join(download_dir, filename))

    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def download_media(
    url: str,
    output_format: str,
    quality: str = "best",
    custom_name: str | None = None,
    on_progress: Callable[[ProgressInfo], None] | None = None,
    save_dir: str | None = None,
    session: DownloadSession | None = None,
) -> str:
    try:
        return run_download(
            url,
            output_format,
            quality=quality,
            custom_name=custom_name,
            on_progress=on_progress,
            save_dir=save_dir,
            session=session,
        )
    except FileNotFoundError as exc:
        raise DownloadError("O executável yt-dlp não foi encontrado. Verifique a instalação.") from exc
    except RuntimeError as exc:
        raise DownloadError(str(exc)) from exc
