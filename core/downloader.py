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
from core.settings import get_browser_cookies, get_cookies_file, get_default_download_dir


class DownloadError(RuntimeError):
    def __init__(self, message: str, title: str = "Erro no Download", summary: str = "", help_text: str = "", raw_error: str = ""):
        super().__init__(message)
        self.title = title
        self.summary = summary or message
        self.help_text = help_text
        self.raw_error = raw_error or message


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


def format_friendly_error(raw_error: str, platform: str = "") -> tuple[str, str, str]:
    """
    Analisa o log de erro retornado pelo yt-dlp/extrator e retorna uma tupla:
    (titulo_amigavel, resumo_curto, guia_solucao_passo_a_passo)
    """
    err_lower = raw_error.lower()
    plat_name = platform or "da plataforma"

    # Caso 1: Login Obrigatório / Conteúdo Privado
    if any(k in err_lower for k in ["only works when logged-in", "requires authentication", "empty media response", "login required", "account is private", "this video is private", "members-only", "sign in to confirm"]):
        title = "Conteúdo Restrito / Exige Login"
        summary = f"Este vídeo exige login ou permissão de acesso ({plat_name})."
        guide = (
            f"O vídeo informado está configurado como privado, restrito ou requer autenticação de usuário no {plat_name}.\n\n"
            "Como resolver:\n"
            "1. Clique no ícone de Configurações (⚙) no topo do DYTB.\n"
            "2. No campo 'Cookies do Navegador', selecione o navegador onde você já está conectado à sua conta (ex: Chrome, Edge, Firefox).\n"
            "3. Caso o seu navegador esteja aberto no Windows, feche-o antes de iniciar o download OU exporte um arquivo 'cookies.txt' e selecione-o em Configurações.\n"
            "4. Tente realizar o download novamente."
        )
        return title, summary, guide

    # Caso 2: Banco de Cookies Bloqueado pelo Navegador Aberto
    if any(k in err_lower for k in ["could not copy", "cookie database", "permission denied", "cookie file is locked"]):
        title = "Navegador Bloqueando Cookies"
        summary = "O navegador está aberto e impedindo a leitura da sessão de login."
        guide = (
            "O navegador selecionado está em execução no Windows e bloqueou o acesso ao arquivo de cookies por segurança.\n\n"
            "Como resolver:\n"
            "1. Feche todas as janelas abertas do seu navegador (ex: Google Chrome / Edge) e clique para baixar novamente, OU\n"
            "2. Instale uma extensão de exportação de cookies (como 'Get cookies.txt LOCALLY'), salve um arquivo 'cookies.txt' e importe-o em Configurações > Arquivo de Cookies."
        )
        return title, summary, guide

    # Caso 3: Vídeo Não Encontrado / Removido / 404
    if any(k in err_lower for k in ["video unavailable", "this video is unavailable", "http error 404", "not found", "is not available", "video has been removed", "404 not found"]):
        title = "Vídeo Não Encontrado"
        summary = "O vídeo não existe, foi excluído ou o link informado está incorreto."
        guide = (
            f"A plataforma ({plat_name}) informou que o conteúdo não foi localizado no endereço fornecido.\n\n"
            "Como resolver:\n"
            "1. Verifique se o link foi copiado por completo e sem caracteres extras.\n"
            "2. Abra o link em uma janela anônima do navegador para verificar se o vídeo ainda está no ar publicamente."
        )
        return title, summary, guide

    # Caso 4: Bloqueio 403 Forbidden / Anti-Bot / Rate Limit
    if any(k in err_lower for k in ["http error 403", "forbidden", "bot detection", "cloudflare", "challenge"]):
        title = "Acesso Bloqueado pela Plataforma (403)"
        summary = f"Acesso temporariamente bloqueado pelo servidor do {plat_name}."
        guide = (
            f"O servidor do {plat_name} bloqueou a requisição direta por suspeita de automação ou limite de taxa.\n\n"
            "Como resolver:\n"
            "1. Configure os cookies do seu navegador nas Configurações para validar que você é um usuário real.\n"
            "2. Aguarde 1 a 2 minutos antes de tentar novamente."
        )
        return title, summary, guide

    # Caso 5: URL de página de curso EAD / Hotmart Club
    if "unsupported url" in err_lower and any(p in err_lower for p in ["hotmart", "dio.me", "pandavideo"]):
        title = "Página de Curso EAD / Stream HLS"
        summary = "A página da aula usa streaming dinâmico (.m3u8)."
        guide = (
            f"A plataforma ({plat_name}) entrega os vídeos das aulas através de streams fragmentados (.m3u8) em vez de links diretos de página.\n\n"
            "Como baixar essa aula no DYTB:\n"
            "1. Na página da aula no seu navegador, pressione F12 (Ferramentas do Desenvolvedor).\n"
            "2. Clique na aba 'Rede' (Network) e digite 'm3u8' no campo de filtro.\n"
            "3. Dê Play no vídeo (ou avance alguns segundos).\n"
            "4. Clique com o botão direito no link que aparecer (ex: master.m3u8) e selecione 'Copiar link'.\n"
            "5. Cole o link no DYTB e clique em Baixar (o DYTB baixa e junta todos os fragmentos em 1080p Full HD automaticamente!)."
        )
        return title, summary, guide

    # Caso 6: FFmpeg Ausente
    if "ffmpeg" in err_lower and ("not found" in err_lower or "necessário" in err_lower or "missing" in err_lower):
        title = "FFmpeg Não Encontrado"
        summary = "O FFmpeg é necessário para converter ou mesclar o arquivo."
        guide = (
            "O aplicativo necessita do utilitário FFmpeg para extrair faixas de áudio (MP3/WAV/M4A) e combinar vídeos de alta definição.\n\n"
            "Como resolver:\n"
            "1. Execute o instalador oficial do aplicativo ('DYTB_Setup.exe') que configura o FFmpeg automaticamente, ou\n"
            "2. Instale manualmente via terminal com o comando: winget install Gyan.FFmpeg"
        )
        return title, summary, guide

    # Caso 7: Erro de Rede / Conexão / Timeout
    if any(k in err_lower for k in ["timed out", "connection refused", "network is unreachable", "getaddrinfo failed", "sslerror", "winerror 10060"]):
        title = "Falha de Conexão com a Internet"
        summary = "Não foi possível estabelecer contato com os servidores da plataforma."
        guide = (
            "Ocorreu uma falha de comunicação de rede durante a transferência.\n\n"
            "Como resolver:\n"
            "1. Verifique se a sua conexão com a internet está ativa e estável.\n"
            "2. Verifique se programas de firewall ou antivírus estão restringindo o tráfego do aplicativo."
        )
        return title, summary, guide

    # Caso Padrão Genérico
    # Extrai primeira linha limpa de erro
    clean_lines = [line.replace("ERROR:", "").replace("error:", "").strip() for line in raw_error.splitlines() if line.strip()]
    first_meaningful = clean_lines[0] if clean_lines else "Falha ao processar o download"
    if len(first_meaningful) > 90:
        first_meaningful = first_meaningful[:87] + "..."

    title = "Erro no Processamento"
    summary = first_meaningful
    guide = (
        f"Não foi possível concluir o download com os parâmetros fornecidos.\n\n"
        "Detalhes da resposta do extrator:\n"
        f"{raw_error}\n\n"
        "Recomendações:\n"
        "• Verifique se o formato e a qualidade escolhidos são compatíveis com o vídeo.\n"
        "• Caso o conteúdo seja de um curso fechado ou plataforma privada, ative os Cookies do Navegador em Configurações."
    )
    return title, summary, guide


def build_ytdlp_command(
    url: str,
    output_format: str,
    quality: str = "best",
    custom_name: str | None = None,
    fallback_youtube_client: bool = False,
    save_dir: str | None = None,
    disable_browser_cookies: bool = False,
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
        "--no-check-certificates",
        "--geo-bypass",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--compat-options",
        "no-youtube-unavailable-videos",
        "--output",
        output_path,
        "--print",
        "after_move:filepath",
    ]

    # Injeção de Cookies (Prioridade: Arquivo cookies.txt > Sessão de Navegador)
    cookies_file = get_cookies_file()
    if cookies_file and os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])
    elif not disable_browser_cookies:
        browser_cookie = get_browser_cookies()
        if browser_cookie and browser_cookie != "none":
            cmd.extend(["--cookies-from-browser", browser_cookie])

    # Referer para plataformas com restrição de domínio / embed
    if platform == "Vimeo":
        cmd.extend(["--referer", "https://vimeo.com/"])
    elif platform in ("Hotmart / EAD", "DIO", "Panda Video"):
        if "hotmart" in clean_url.lower():
            cmd.extend([
                "--referer", "https://player.hotmart.com/",
                "--add-header", "Origin: https://player.hotmart.com",
            ])
        else:
            cmd.extend(["--referer", clean_url])

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
                "Instale o FFmpeg ou execute o instalador do aplicativo.",
                title="FFmpeg Ausente",
                summary="FFmpeg não encontrado para extrair áudio.",
            )
        cmd.append("--extract-audio")
        if target_fmt == "mp3":
            cmd.extend(["--audio-format", "mp3", "--audio-quality", "0"])
        elif target_fmt == "wav":
            cmd.extend(["--audio-format", "wav"])
        elif target_fmt == "m4a":
            cmd.extend(["--audio-format", "m4a"])
    else:
        # Formatos de Vídeo: mp4, webm, mkv com seleção resiliente
        height_limit = QUALITY_OPTIONS.get(quality, {}).get("height")
        
        if target_fmt == "mp4":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}][ext=mp4]/"
                    f"best[height<={height_limit}]/"
                    f"best"
                )
            else:
                fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo*+bestaudio/best[ext=mp4]/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "mp4"])

        elif target_fmt == "webm":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}][ext=webm]+bestaudio[ext=webm]/"
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}][ext=webm]/"
                    f"best[height<={height_limit}]/"
                    f"best"
                )
            else:
                fmt_str = "bestvideo[ext=webm]+bestaudio[ext=webm]/bestvideo*+bestaudio/best[ext=webm]/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "webm"])

        elif target_fmt == "mkv":
            if height_limit:
                fmt_str = (
                    f"bestvideo[height<={height_limit}]+bestaudio/"
                    f"best[height<={height_limit}]/"
                    f"best"
                )
            else:
                fmt_str = "bestvideo*+bestaudio/best"
            
            cmd.extend(["-f", fmt_str])
            if has_ffmpeg:
                cmd.extend(["--merge-output-format", "mkv"])

    cmd.append(clean_url)
    return cmd


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

    detected_plat = detect_platform(url)
    disable_cookies_fallback = False
    last_raw_error = ""

    for attempt_index in range(1, 4):
        fallback_yt = attempt_index == 2 and detected_plat == "YouTube"

        if on_progress is not None:
            if attempt_index == 1:
                on_progress(ProgressInfo(percent=1.0, status_text="Conectando e obtendo dados do vídeo..."))
            elif disable_cookies_fallback:
                on_progress(ProgressInfo(percent=2.0, status_text="Tentando download direto sem cookies..."))
            elif fallback_yt:
                on_progress(ProgressInfo(percent=3.0, status_text="Tentando método alternativo de conexão..."))

        cmd = build_ytdlp_command(
            url=url,
            output_format=output_format,
            quality=quality,
            custom_name=custom_name,
            fallback_youtube_client=fallback_yt,
            save_dir=save_dir,
            disable_browser_cookies=disable_cookies_fallback,
        )

        last_recorded_path: str | None = None
        creationflags = 0
        startupinfo = None
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
                raise DownloadError("Download cancelado pelo usuário.", title="Cancelado", summary="Download cancelado pelo usuário.")
            if session is not None and session.pause_requested:
                session._kill_process()
                raise DownloadError("Download pausado pelo usuário.", title="Pausado", summary="Download pausado pelo usuário.")

            if process.stdout is None:
                break
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if line:
                    output_lines.append(line)
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
            raise DownloadError(
                "O download foi concluído, mas o arquivo final não pôde ser localizado.",
                title="Arquivo Não Localizado",
                summary="Download concluído mas arquivo final não encontrado.",
            )

        recent_output = "\n".join(output_lines[-12:]) if output_lines else "Nenhum log gerado pelo extrator."
        last_raw_error = recent_output

        # Se falhou por banco de cookies bloqueado pelo navegador aberto, tenta novamente sem cookies
        if ("Could not copy" in recent_output and "cookie database" in recent_output) or ("only works when logged-in" in recent_output.lower() and detected_plat == "Vimeo"):
            if not disable_cookies_fallback:
                disable_cookies_fallback = True
                continue

        # Se o YouTube pediu reload de player client
        if "The page needs to be reloaded" in recent_output or "player_client" in recent_output.lower():
            if attempt_index == 1:
                continue

        # Se não for possível recuperar por fallback automático, interrompe e diagnostica
        break

    # Diagnóstico amigável e detalhado do erro
    title, summary, guide = format_friendly_error(last_raw_error, platform=detected_plat)
    raise DownloadError(
        message=summary,
        title=title,
        summary=summary,
        help_text=guide,
        raw_error=last_raw_error,
    )


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
        raise DownloadError(
            "O executável yt-dlp não foi encontrado. Verifique a instalação.",
            title="yt-dlp Ausente",
            summary="O executável yt-dlp não foi encontrado.",
        ) from exc
    except RuntimeError as exc:
        if isinstance(exc, DownloadError):
            raise exc
        raise DownloadError(str(exc)) from exc
