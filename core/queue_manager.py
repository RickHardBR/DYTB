from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.downloader import (
    DownloadError,
    DownloadSession,
    ProgressInfo,
    download_media,
)
from core.formats import detect_platform
from core.history import add_to_history


@dataclass
class DownloadItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    output_format: str = "mp4"
    quality: str = "best"
    save_dir: str = ""
    custom_name: str | None = None
    platform: str = "Web"
    status: str = "pending"  # pending, downloading, completed, error, cancelled
    progress: ProgressInfo = field(default_factory=ProgressInfo)
    title: str = ""
    output_path: str | None = None
    error_message: str | None = None
    error_title: str = ""
    error_summary: str = ""
    error_help: str = ""
    raw_error: str = ""
    session: DownloadSession = field(default_factory=DownloadSession)

    @property
    def display_name(self) -> str:
        if self.custom_name and self.custom_name.strip():
            return self.custom_name.strip()
        if self.title and self.title.strip():
            return self.title.strip()
        if self.output_path:
            return Path(self.output_path).name
        return self.url


class DownloadQueueManager:
    def __init__(
        self,
        on_item_updated: Callable[[DownloadItem], None] | None = None,
        on_queue_finished: Callable[[], None] | None = None,
    ):
        self.items: list[DownloadItem] = []
        self._lock = threading.Lock()
        self._is_running = False
        self._worker_thread: threading.Thread | None = None
        self.current_item: DownloadItem | None = None
        self.on_item_updated = on_item_updated
        self.on_queue_finished = on_queue_finished

    @property
    def is_running(self) -> bool:
        return self._is_running

    def add_item(
        self,
        url: str,
        output_format: str = "mp4",
        quality: str = "best",
        save_dir: str = "",
        custom_name: str | None = None,
    ) -> DownloadItem:
        detected_plat = detect_platform(url)
        item = DownloadItem(
            url=url,
            output_format=output_format,
            quality=quality,
            save_dir=save_dir,
            custom_name=custom_name,
            platform=detected_plat,
            title=custom_name or "Aguardando download...",
        )
        with self._lock:
            self.items.append(item)

        self._notify_update(item)
        return item

    def add_items(
        self,
        urls: list[str],
        output_format: str = "mp4",
        quality: str = "best",
        save_dir: str = "",
    ) -> list[DownloadItem]:
        added: list[DownloadItem] = []
        with self._lock:
            for url in urls:
                item = DownloadItem(
                    url=url,
                    output_format=output_format,
                    quality=quality,
                    save_dir=save_dir,
                    platform=detect_platform(url),
                    title="Aguardando na fila...",
                )
                self.items.append(item)
                added.append(item)

        for item in added:
            self._notify_update(item)

        return added

    def start(self):
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def cancel_item(self, item_id: str):
        target: DownloadItem | None = None
        with self._lock:
            for it in self.items:
                if it.id == item_id:
                    target = it
                    break

            if not target:
                return

            if target.status == "downloading":
                target.session.cancel()
                target.status = "cancelled"
            elif target.status == "pending":
                target.status = "cancelled"
                target.progress.status_text = "Cancelado"

        self._notify_update(target)

    def cancel_all(self):
        targets: list[DownloadItem] = []
        with self._lock:
            for it in self.items:
                if it.status == "downloading":
                    it.session.cancel()
                    it.status = "cancelled"
                elif it.status == "pending":
                    it.status = "cancelled"
                    it.progress.status_text = "Cancelado"
                targets.append(it)

        for it in targets:
            self._notify_update(it)

    def clear_completed(self):
        with self._lock:
            self.items = [it for it in self.items if it.status not in ("completed", "cancelled", "error")]

    def get_counts(self) -> dict[str, int]:
        with self._lock:
            total = len(self.items)
            completed = sum(1 for it in self.items if it.status == "completed")
            downloading = sum(1 for it in self.items if it.status == "downloading")
            pending = sum(1 for it in self.items if it.status == "pending")
            error = sum(1 for it in self.items if it.status == "error")
            cancelled = sum(1 for it in self.items if it.status == "cancelled")
            return {
                "total": total,
                "completed": completed,
                "downloading": downloading,
                "pending": pending,
                "error": error,
                "cancelled": cancelled,
            }

    def _notify_update(self, item: DownloadItem):
        if self.on_item_updated:
            try:
                self.on_item_updated(item)
            except Exception:
                pass

    def _worker_loop(self):
        while True:
            next_item: DownloadItem | None = None
            with self._lock:
                for it in self.items:
                    if it.status == "pending":
                        next_item = it
                        break

                if next_item is None:
                    self._is_running = False
                    self.current_item = None
                    break

                self.current_item = next_item
                next_item.status = "downloading"
                next_item.progress.status_text = "Iniciando..."

            self._notify_update(next_item)

            def handle_progress(info: ProgressInfo):
                next_item.progress = info
                if not next_item.title or next_item.title in ("Aguardando download...", "Aguardando na fila..."):
                    if info.status_text and not info.status_text.startswith("Baixando"):
                        next_item.title = info.status_text
                self._notify_update(next_item)

            try:
                output_file = download_media(
                    url=next_item.url,
                    output_format=next_item.output_format,
                    quality=next_item.quality,
                    custom_name=next_item.custom_name,
                    on_progress=handle_progress,
                    save_dir=next_item.save_dir,
                    session=next_item.session,
                )

                if next_item.session.cancel_requested:
                    next_item.status = "cancelled"
                    next_item.progress.status_text = "Cancelado pelo usuário"
                else:
                    next_item.status = "completed"
                    next_item.output_path = output_file
                    file_stem = Path(output_file).stem
                    next_item.title = file_stem
                    next_item.progress.percent = 100.0
                    next_item.progress.status_text = "Concluído"

                    # Adiciona ao histórico
                    add_to_history(
                        url=next_item.url,
                        title=file_stem,
                        output_format=next_item.output_format,
                        quality=next_item.quality,
                        output_path=output_file,
                    )

            except DownloadError as exc:
                if next_item.session.cancel_requested:
                    next_item.status = "cancelled"
                    next_item.progress.status_text = "Cancelado pelo usuário"
                else:
                    next_item.status = "error"
                    next_item.error_message = str(exc)
                    next_item.error_title = getattr(exc, "title", "Erro no Download")
                    next_item.error_summary = getattr(exc, "summary", str(exc))
                    next_item.error_help = getattr(exc, "help_text", "")
                    next_item.raw_error = getattr(exc, "raw_error", str(exc))
                    next_item.progress.status_text = next_item.error_summary

            except Exception as exc:
                from core.downloader import format_friendly_error
                title, summary, guide = format_friendly_error(str(exc), platform=next_item.platform)
                next_item.status = "error"
                next_item.error_message = str(exc)
                next_item.error_title = title
                next_item.error_summary = summary
                next_item.error_help = guide
                next_item.raw_error = str(exc)
                next_item.progress.status_text = summary

            self._notify_update(next_item)

        if self.on_queue_finished:
            try:
                self.on_queue_finished()
            except Exception:
                pass
