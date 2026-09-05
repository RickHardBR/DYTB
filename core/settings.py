from __future__ import annotations

import json
import os
from pathlib import Path


SETTINGS_FILE = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "DYTB" / "settings.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {
            "download_dir": str(DEFAULT_DOWNLOAD_DIR),
            "default_format": "mp4",
            "default_quality": "best",
            "use_custom_names": False,
            "auto_open_folder": False,
        }
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {
                "download_dir": str(DEFAULT_DOWNLOAD_DIR),
                "default_format": "mp4",
                "default_quality": "best",
                "use_custom_names": False,
                "auto_open_folder": False,
            }
        if not data.get("download_dir"):
            data["download_dir"] = str(DEFAULT_DOWNLOAD_DIR)
        if not data.get("default_format"):
            data["default_format"] = "mp4"
        if not data.get("default_quality"):
            data["default_quality"] = "best"
        if "use_custom_names" not in data:
            data["use_custom_names"] = False
        if "auto_open_folder" not in data:
            data["auto_open_folder"] = False
        return data
    except (json.JSONDecodeError, OSError):
        return {
            "download_dir": str(DEFAULT_DOWNLOAD_DIR),
            "default_format": "mp4",
            "default_quality": "best",
            "use_custom_names": False,
            "auto_open_folder": False,
        }


def save_settings(data: dict) -> None:
    _ensure_parent(SETTINGS_FILE)
    with SETTINGS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def get_default_download_dir() -> str:
    value = load_settings().get("download_dir", str(DEFAULT_DOWNLOAD_DIR))
    return str(Path(value).expanduser())


def set_default_download_dir(path: str) -> str:
    normalized = str(Path(path).expanduser())
    settings = load_settings()
    settings["download_dir"] = normalized
    save_settings(settings)
    return normalized


def get_default_format() -> str:
    return load_settings().get("default_format", "mp4")


def set_default_format(fmt: str) -> None:
    settings = load_settings()
    settings["default_format"] = fmt
    save_settings(settings)


def get_default_quality() -> str:
    return load_settings().get("default_quality", "best")


def set_default_quality(quality: str) -> None:
    settings = load_settings()
    settings["default_quality"] = quality
    save_settings(settings)


def get_use_custom_names() -> bool:
    return load_settings().get("use_custom_names", False)


def set_use_custom_names(enabled: bool) -> None:
    settings = load_settings()
    settings["use_custom_names"] = enabled
    save_settings(settings)


def get_auto_open_folder() -> bool:
    return load_settings().get("auto_open_folder", False)


def set_auto_open_folder(enabled: bool) -> None:
    settings = load_settings()
    settings["auto_open_folder"] = enabled
    save_settings(settings)


def get_browser_cookies() -> str:
    """Retorna o navegador selecionado para autenticação em vídeos privados ('none', 'chrome', 'edge', 'firefox', 'brave', 'opera')."""
    return load_settings().get("browser_cookies", "none")


def set_browser_cookies(browser: str) -> None:
    settings = load_settings()
    settings["browser_cookies"] = browser
    save_settings(settings)


def get_cookies_file() -> str | None:
    """Retorna o caminho de um arquivo cookies.txt se configurado ou se existir cookies.txt na raiz."""
    configured = load_settings().get("cookies_file")
    if configured and os.path.exists(configured):
        return configured
    local_cookie = Path("cookies.txt")
    if local_cookie.exists():
        return str(local_cookie.resolve())
    return None


def set_cookies_file(file_path: str | None) -> None:
    settings = load_settings()
    settings["cookies_file"] = file_path or ""
    save_settings(settings)



