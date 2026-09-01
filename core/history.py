from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


HISTORY_FILE = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "DYTB" / "history.json"
MAX_HISTORY_ITEMS = 100


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_history() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError):
        return []


def save_history(entries: list[dict]) -> None:
    _ensure_parent(HISTORY_FILE)
    with HISTORY_FILE.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)


def add_to_history(
    url: str,
    title: str,
    output_format: str,
    quality: str,
    output_path: str,
    file_size_mb: float | None = None,
) -> None:
    entries = load_history()
    
    # Se não foi passado tamanho explicitamente, tenta obter do arquivo gerado
    if file_size_mb is None and os.path.exists(output_path):
        try:
            file_size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)
        except Exception:
            file_size_mb = None

    entry = {
        "url": url,
        "title": title or Path(output_path).stem,
        "format": output_format,
        "quality": quality,
        "path": output_path,
        "size_mb": file_size_mb,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }
    entries.insert(0, entry)
    if len(entries) > MAX_HISTORY_ITEMS:
        entries = entries[:MAX_HISTORY_ITEMS]
    save_history(entries)


def clear_history() -> None:
    save_history([])


def remove_from_history(index: int) -> None:
    entries = load_history()
    if 0 <= index < len(entries):
        entries.pop(index)
        save_history(entries)
