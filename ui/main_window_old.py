from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import customtkinter as ctk

from core.downloader import DownloadError, DownloadSession, download_media, get_download_dir
from core.settings import get_default_download_dir, set_default_download_dir
from ui.dialogs import DestinationDialog, ErrorDialog, ProgressDialog


class MainWindow:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ctk.CTkFrame(parent, corner_radius=18, fg_color="#101922")
        self.frame.pack(fill="both", expand=True, padx=18, pady=18)

        self.frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.frame,
            text="DYTB Downloader",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 8))

        subtitle = ctk.CTkLabel(
            self.frame,
            text="Baixe vídeos do YouTube e converta para MP4 ou MP3 em poucos passos.",
            text_color="#aaaaaa",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 18))

        url_label = ctk.CTkLabel(self.frame, text="Link do vídeo", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        url_label.grid(row=2, column=0, sticky="w", padx=24, pady=(0, 8))

        self.url_entry = ctk.CTkEntry(
            self.frame,
            placeholder_text="Cole aqui o link do vídeo do YouTube",
            height=42,
            border_width=1,
            corner_radius=12,
        )
        self.url_entry.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 16))

        format_label = ctk.CTkLabel(self.frame, text="Formato", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        format_label.grid(row=4, column=0, sticky="w", padx=24, pady=(0, 10))

        self.format_var = ctk.StringVar(value="mp4")
        self.format_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.format_frame.grid(row=5, column=0, sticky="w", padx=24, pady=(0, 10))

        self.mp4_radio = ctk.CTkRadioButton(self.format_frame, text="Vídeo (.mp4)", variable=self.format_var, value="mp4")
        self.mp4_radio.pack(side="left", padx=(0, 18))

        self.mp3_radio = ctk.CTkRadioButton(self.format_frame, text="Apenas áudio (.mp3)", variable=self.format_var, value="mp3")
        self.mp3_radio.pack(side="left")

        self.destination_label = ctk.CTkLabel(
            self.frame,
            text=f"Pasta de destino: {get_default_download_dir()}",
            text_color="#b7c4d4",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=600,
        )
        self.destination_label.grid(row=6, column=0, sticky="w", padx=24, pady=(0, 8))

        action_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        action_row.grid(row=7, column=0, sticky="w", padx=24, pady=(0, 8))

        self.change_folder_button = ctk.CTkButton(
            action_row,
            text="Escolher pasta",
            height=32,
            width=160,
            command=self._choose_destination,
            fg_color="#1f2d3d",
            hover_color="#29384f",
        )
        self.change_folder_button.pack(side="left", padx=(0, 12))

        self.open_folder_button = ctk.CTkButton(
            action_row,
            text="Abrir pasta",
            height=32,
            width=140,
            command=self._open_download_folder,
            fg_color="#243b55",
            hover_color="#2e4d6b",
        )
        self.open_folder_button.pack(side="left")

        self.last_file_label = ctk.CTkLabel(
            self.frame,
            text="Último arquivo: nenhum download ainda",
            text_color="#94a6bb",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=600,
        )
        self.last_file_label.grid(row=8, column=0, sticky="w", padx=24, pady=(0, 8))

        self.download_button = ctk.CTkButton(
            self.frame,
            text="Baixar",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._handle_download,
        )
        self.download_button.grid(row=9, column=0, sticky="ew", padx=24, pady=(16, 12))

        self.status_label = ctk.CTkLabel(
            self.frame,
            text="",
            text_color="#b7c4d4",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=600,
        )
        self.status_label.grid(row=10, column=0, sticky="w", padx=24, pady=(0, 16))

        self.last_download_path = None
        self.is_downloading = False
        self.current_session: DownloadSession | None = None
        self.current_dialog: ProgressDialog | None = None

    def _set_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.download_button.configure(state=state)
        self.url_entry.configure(state=state)
        self.mp4_radio.configure(state=state)
        self.mp3_radio.configure(state=state)
        self.change_folder_button.configure(state=state)
        self.open_folder_button.configure(state=state)

    def _reset_download_state(self):
        self.is_downloading = False
        self.current_session = None
        self.current_dialog = None
        self._set_controls_enabled(True)

    def _set_destination(self, path: str):
        path = str(Path(path).expanduser())
        set_default_download_dir(path)
        self.destination_label.configure(text=f"Pasta de destino: {path}")
        self.status_label.configure(text=f"Pasta padrão salva: {path}")

    def _open_download_folder(self):
        destination = get_default_download_dir()
        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)
        try:
            subprocess.Popen(["explorer", destination])
        except Exception:
            self.status_label.configure(text=f"Não foi possível abrir a pasta: {destination}")

    def _open_last_download(self):
        if not self.last_download_path or not os.path.exists(self.last_download_path):
            self.status_label.configure(text="Ainda não existe um arquivo baixado para abrir.")
            return
        try:
            subprocess.Popen(["explorer", "/select,", self.last_download_path])
        except Exception:
            self.status_label.configure(text=f"Não foi possível abrir o arquivo: {self.last_download_path}")

    def _choose_destination(self):
        from tkinter import filedialog

        chosen_dir = filedialog.askdirectory(
            title="Escolha a pasta para salvar os downloads",
            initialdir=get_default_download_dir(),
        )
        if not chosen_dir:
            return

        self._set_destination(chosen_dir)

    def _handle_download(self):
        url = self.url_entry.get().strip()
        if not url:
            ErrorDialog(self.parent, "Campo obrigatório", "Cole um link do YouTube antes de iniciar o download.")
            return

        current_destination = get_default_download_dir()
        self.status_label.configure(text=f"Usando esta pasta: {current_destination}")

        DestinationDialog(
            self.parent,
            current_destination,
            on_keep=lambda: self._start_download(url, current_destination),
            on_change=lambda: self._choose_destination_and_download(url),
        )

    def _choose_destination_and_download(self, url: str):
        from tkinter import filedialog

        chosen_dir = filedialog.askdirectory(
            title="Escolha a nova pasta para salvar os downloads",
            initialdir=get_default_download_dir(),
        )
        if not chosen_dir:
            self.status_label.configure(text="Nenhuma pasta foi escolhida. Mantendo a pasta atual.")
            return

        self._set_destination(chosen_dir)
        self._start_download(url, chosen_dir)

    def _start_download(self, url: str, destination: str):
        if self.is_downloading:
            return

        format_choice = self.format_var.get()
        dialog = ProgressDialog(self.parent)
        dialog.set_callbacks(on_pause=self._pause_download, on_cancel=self._cancel_download)
        self.current_dialog = dialog
        self.current_session = DownloadSession()
        self.is_downloading = True
        self._set_controls_enabled(False)
        self.status_label.configure(text=f"Preparando download em: {destination}")

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)

        def worker():
            try:
                output_file = download_media(
                    url,
                    format_choice,
                    on_progress=lambda msg: self._set_status(dialog, msg),
                    save_dir=destination,
                    session=self.current_session,
                )
                self.parent.after(0, lambda: self._download_finished(dialog, output_file))
            except DownloadError as exc:
                if self.current_session is not None and (self.current_session.cancel_requested or self.current_session.pause_requested):
                    self.parent.after(0, lambda: self._download_stopped(dialog, "pausado" if self.current_session.pause_requested else "cancelado"))
                    return
                self.parent.after(0, lambda: self._download_failed(dialog, str(exc)))
            except Exception as exc:  # pragma: no cover
                self.parent.after(0, lambda: self._download_failed(dialog, f"Erro inesperado: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _pause_download(self):
        if not self.is_downloading or self.current_session is None:
            return
        self.current_session.pause()
        if self.current_dialog is not None:
            self.current_dialog.set_status("Download pausado pelo usuário.")
        self.status_label.configure(text="Download pausado. Você pode iniciar outro link quando quiser.")

    def _cancel_download(self):
        if not self.is_downloading or self.current_session is None:
            return
        self.current_session.cancel()
        if self.current_dialog is not None:
            self.current_dialog.set_status("Cancelando download...")
        self.status_label.configure(text="Cancelando download...")
        self.parent.after(150, lambda: self._download_stopped(self.current_dialog, "cancelado"))

    def _set_status(self, dialog: ProgressDialog, message: str):
        dialog.set_status(message)

    def _download_stopped(self, dialog: ProgressDialog | None, action: str):
        if dialog is not None and dialog.winfo_exists():
            dialog.close()
        self._reset_download_state()
        self.status_label.configure(text=f"Download {action}. Você pode inserir outro link.")

    def _download_finished(self, dialog: ProgressDialog, output_file: str):
        if dialog.winfo_exists():
            dialog.close()
        self._reset_download_state()
        self.last_download_path = output_file
        self.last_file_label.configure(text=f"Último arquivo: {output_file}")
        self.status_label.configure(text=f"Download concluído: {output_file}")
        self.url_entry.delete(0, "end")

    def _download_failed(self, dialog: ProgressDialog, message: str):
        if dialog.winfo_exists():
            dialog.close()
        self._reset_download_state()
        ErrorDialog(self.parent, "Erro no download", message)
        self.status_label.configure(text="Falha no download. Verifique o link e a conexão.")
