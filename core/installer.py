from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import winreg


def _refresh_system_path() -> None:
    """Recarrega o PATH fresco do Registro do Windows (HKCU e HKLM) e diretórios conhecidos."""
    if os.name != "nt":
        return

    paths_to_add: list[str] = []

    # 1. Prioridade Máxima: Pastas de binários embutidos no pacote ou locais do app
    if hasattr(sys, "_MEIPASS"):
        meipass = sys._MEIPASS
        paths_to_add.append(os.path.join(meipass, "bin"))
        paths_to_add.append(meipass)

    app_root = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths_to_add.append(os.path.join(app_root, "bin"))
    paths_to_add.append(app_root)

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            user_path, _ = winreg.QueryValueEx(key, "Path")
            paths_to_add.extend([p.strip() for p in user_path.split(";") if p.strip()])
    except Exception:
        pass

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
            paths_to_add.extend([p.strip() for p in sys_path.split(";") if p.strip()])
    except Exception:
        pass

    # Inclui caminhos comuns de scripts Python e links do WinGet
    user_profile = os.environ.get("USERPROFILE", "")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")

    additional_candidates = [
        os.path.join(local_app_data, "Microsoft", "WinGet", "Links"),
        os.path.join(app_data, "Python", "Python312", "Scripts"),
        os.path.join(app_data, "Python", "Python311", "Scripts"),
        os.path.join(app_data, "Python", "Python310", "Scripts"),
        os.path.join(local_app_data, "Programs", "Python", "Python312", "Scripts"),
        os.path.join(local_app_data, "Programs", "Python", "Python311", "Scripts"),
        os.path.join(local_app_data, "Programs", "Python", "Python310", "Scripts"),
        "C:\\Python312\\Scripts",
        "C:\\Python311\\Scripts",
        "C:\\Python310\\Scripts",
        os.path.join(program_files, "FFmpeg", "bin"),
        os.path.join(program_files, "ffmpeg", "bin"),
    ]

    # Verificar pasta de pacotes do winget para ffmpeg
    winget_pkg_dir = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(winget_pkg_dir):
        try:
            for entry in os.scandir(winget_pkg_dir):
                if "ffmpeg" in entry.name.lower() and entry.is_dir():
                    bin_candidate = os.path.join(entry.path, "ffmpeg-8.1.1-essentials_build", "bin")
                    if os.path.isdir(bin_candidate):
                        additional_candidates.append(bin_candidate)
                    for sub in os.scandir(entry.path):
                        if sub.is_dir() and "bin" in os.listdir(sub.path):
                            additional_candidates.append(os.path.join(sub.path, "bin"))
        except Exception:
            pass

    for candidate in additional_candidates:
        if candidate and os.path.isdir(candidate) and candidate not in paths_to_add:
            paths_to_add.append(candidate)

    current_path = os.environ.get("PATH", "")
    new_path_entries = [p for p in paths_to_add if p and os.path.isdir(p) and p not in current_path]
    if new_path_entries:
        os.environ["PATH"] = os.pathsep.join(new_path_entries) + os.pathsep + current_path


def is_yt_dlp_installed() -> bool:
    _refresh_system_path()
    return shutil.which("yt-dlp") is not None


def is_ffmpeg_installed() -> bool:
    _refresh_system_path()
    return shutil.which("ffmpeg") is not None


def launch_admin_install(package_id: str = "yt-dlp.yt-dlp") -> bool:
    """Abre um terminal administrativo e instala o pacote via winget."""
    try:
        install_args = (
            f"install --id {package_id} -e --source winget "
            "--accept-source-agreements --accept-package-agreements"
        )
        powershell_cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Start-Process",
            "-Verb",
            "RunAs",
            "-FilePath",
            "winget",
            "-ArgumentList",
            install_args,
        ]
        result = subprocess.run(powershell_cmd, capture_output=True, text=True, shell=False)
        if result.returncode == 0:
            return True
        output = (result.stderr or "") + "\n" + (result.stdout or "")
        return "requires elevation" in output.lower() or "elevated" in output.lower()
    except Exception:
        return False


def ensure_yt_dlp_available() -> None:
    if not is_yt_dlp_installed():
        raise RuntimeError(
            "O yt-dlp não está instalado. Instale via winget ou use o assistente do aplicativo."
        )


def wait_for_install(check_func, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if check_func():
            return True
        time.sleep(1)
    return check_func()
