from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core.downloader import (
    DownloadError,
    DownloadSession,
    ProgressInfo,
    download_media,
    get_download_dir,
)
from core.formats import (
    FORMAT_OPTIONS,
    QUALITY_OPTIONS,
    is_audio_format,
    is_playlist_url,
    validate_url,
)
from core.history import add_to_history
from core.installer import is_yt_dlp_installed, launch_admin_install
from core.settings import (
    get_auto_open_folder,
    get_default_download_dir,
    get_default_format,
    get_default_quality,
    get_use_custom_names,
    set_default_download_dir,
)
from ui.about_dialog import AboutDialog
from ui.dialogs import CustomNameDialog, DestinationDialog, ErrorDialog, InstallRequiredDialog, ProgressDialog
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow


class MainWindow:
    def __init__(self, parent: ctk.CTk):
        self.parent = parent
        self.frame = ctk.CTkFrame(parent, corner_radius=18, fg_color="#101923")
        self.frame.pack(fill="both", expand=True, padx=18, pady=18)

        self.last_download_path: str | None = None
        self.is_downloading = False
        self.current_session: DownloadSession | None = None
        self.current_dialog: ProgressDialog | None = None

        self._build_ui()

    def _build_ui(self):
        # 1. Barra Superior de Menu
        menubar = ctk.CTkFrame(self.frame, fg_color="transparent", height=32)
        menubar.pack(fill="x", padx=24, pady=(16, 8))

        settings_btn = ctk.CTkButton(
            menubar,
            text="Configurações",
            height=30,
            width=120,
            command=self._open_settings,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        settings_btn.pack(side="left", padx=(0, 8))

        history_btn = ctk.CTkButton(
            menubar,
            text="Histórico",
            height=30,
            width=110,
            command=self._open_history,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        history_btn.pack(side="left", padx=(0, 8))

        about_btn = ctk.CTkButton(
            menubar,
            text="Sobre",
            height=30,
            width=80,
            command=self._open_about,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        about_btn.pack(side="left")

        # 2. Título e Subtítulo
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="DYTB Downloader",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        title_lbl.pack(fill="x", padx=24, pady=(12, 2))

        subtitle_lbl = ctk.CTkLabel(
            self.frame,
            text="Baixe vídeos e áudios do YouTube com máxima fidelidade, qualidade e rapidez.",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
            anchor="w",
        )
        subtitle_lbl.pack(fill="x", padx=24, pady=(0, 16))

        # 3. Campo de URL com Botão Colar
        url_label = ctk.CTkLabel(
            self.frame,
            text="Link do Vídeo",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        )
        url_label.pack(fill="x", padx=24, pady=(0, 6))

        url_input_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=24, pady=(0, 14))

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="Cole o link do YouTube aqui (ex: https://www.youtube.com/watch?v=...)",
            height=44,
            corner_radius=10,
            border_width=1,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = ctk.CTkButton(
            url_input_frame,
            text="Colar",
            width=80,
            height=44,
            corner_radius=10,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_clipboard,
        )
        paste_btn.pack(side="right")

        # 4. Formato e Qualidade
        fmt_qual_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        fmt_qual_frame.pack(fill="x", padx=24, pady=(0, 14))
        fmt_qual_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            fmt_qual_frame,
            text="Formato de Saída",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            fmt_qual_frame,
            text="Qualidade / Resolução",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 6))

        format_labels = [v["label"] for v in FORMAT_OPTIONS.values()]
        initial_fmt_key = get_default_format()
        initial_fmt_label = FORMAT_OPTIONS.get(initial_fmt_key, {}).get("label", format_labels[0])
        self.format_var = ctk.StringVar(value=initial_fmt_label)

        self.format_menu = ctk.CTkOptionMenu(
            fmt_qual_frame,
            values=format_labels,
            variable=self.format_var,
            height=40,
            corner_radius=10,
            command=self._on_format_selected,
        )
        self.format_menu.grid(row=1, column=0, sticky="ew")

        quality_labels = [v["label"] for v in QUALITY_OPTIONS.values()]
        initial_qual_key = get_default_quality()
        initial_qual_label = QUALITY_OPTIONS.get(initial_qual_key, {}).get("label", quality_labels[0])
        self.quality_var = ctk.StringVar(value=initial_qual_label)

        self.quality_menu = ctk.CTkOptionMenu(
            fmt_qual_frame,
            values=quality_labels,
            variable=self.quality_var,
            height=40,
            corner_radius=10,
        )
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(12, 0))

        # 5. Pasta de Destino
        dest_box = ctk.CTkFrame(self.frame, fg_color="#182330", corner_radius=10)
        dest_box.pack(fill="x", padx=24, pady=(0, 16))

        dest_header = ctk.CTkFrame(dest_box, fg_color="transparent")
        dest_header.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            dest_header,
            text="Salvar em:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
        ).pack(side="left")

        self.dest_label = ctk.CTkLabel(
            dest_header,
            text=get_default_download_dir(),
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8",
            wraplength=480,
            justify="left",
        )
        self.dest_label.pack(side="left", padx=(8, 0))

        dest_actions = ctk.CTkFrame(dest_box, fg_color="transparent")
        dest_actions.pack(fill="x", padx=14, pady=(0, 10))

        self.change_folder_btn = ctk.CTkButton(
            dest_actions,
            text="Alterar Pasta",
            height=30,
            width=120,
            command=self._choose_folder,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.change_folder_btn.pack(side="left", padx=(0, 8))

        self.open_folder_btn = ctk.CTkButton(
            dest_actions,
            text="Abrir Pasta",
            height=30,
            width=110,
            command=self._open_current_folder,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11),
        )
        self.open_folder_btn.pack(side="left")

        # 6. Card de Último Download Realizado
        self.last_download_card = ctk.CTkFrame(self.frame, fg_color="#14212e", corner_radius=10)
        self.last_download_card.pack(fill="x", padx=24, pady=(0, 16))
        self.last_download_card.pack_forget()

        self.last_file_label = ctk.CTkLabel(
            self.last_download_card,
            text="Concluído: video.mp4",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#22c55e",
            anchor="w",
            wraplength=400,
            justify="left",
        )
        self.last_file_label.pack(side="left", padx=14, pady=10)

        self.open_last_file_btn = ctk.CTkButton(
            self.last_download_card,
            text="Abrir Arquivo",
            height=30,
            width=120,
            command=self._open_last_download,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.open_last_file_btn.pack(side="right", padx=(0, 14), pady=10)

        # 7. Botão Principal de Download
        self.download_btn = ctk.CTkButton(
            self.frame,
            text="Baixar Conteúdo",
            height=50,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._handle_download,
        )
        self.download_btn.pack(fill="x", padx=24, pady=(4, 8))

        # 8. Status Label
        self.status_label = ctk.CTkLabel(
            self.frame,
            text="Pronto para baixar.",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=24, pady=(0, 8))

        self._on_format_selected(self.format_var.get())

    def _paste_clipboard(self):
        try:
            clipboard_text = self.parent.clipboard_get().strip()
            if clipboard_text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_text)
                self.status_label.configure(text="Link colado da área de transferência.")
        except Exception:
            pass

    def _on_format_selected(self, choice_label: str):
        fmt_key = self._get_format_key_from_label(choice_label)
        if is_audio_format(fmt_key):
            self.quality_menu.configure(state="disabled")
            self.quality_var.set("Apenas áudio (Original)")
        else:
            self.quality_menu.configure(state="normal")
            saved_qual = get_default_quality()
            qual_label = QUALITY_OPTIONS.get(saved_qual, {}).get("label", "Melhor qualidade disponível")
            self.quality_var.set(qual_label)

    def _get_format_key_from_label(self, label: str) -> str:
        for k, v in FORMAT_OPTIONS.items():
            if v["label"] == label:
                return k
        return "mp4"

    def _get_quality_key_from_label(self, label: str) -> str:
        for k, v in QUALITY_OPTIONS.items():
            if v["label"] == label:
                return k
        return "best"

    def _open_settings(self):
        SettingsWindow(self.parent)

    def _open_about(self):
        AboutDialog(self.parent)

    def _open_history(self):
        HistoryWindow(self.parent)

    def _choose_folder(self):
        chosen = filedialog.askdirectory(
            title="Escolha a pasta para salvar os downloads",
            initialdir=get_default_download_dir(),
        )
        if chosen:
            set_default_download_dir(chosen)
            self.dest_label.configure(text=chosen)
            self.status_label.configure(text="Pasta de destino atualizada com sucesso.")

    def _open_current_folder(self):
        folder = get_default_download_dir()
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            subprocess.Popen(["explorer", os.path.normpath(folder)])
        except Exception:
            pass

    def _open_last_download(self):
        if self.last_download_path and os.path.exists(self.last_download_path):
            try:
                os.startfile(self.last_download_path)
            except Exception:
                pass

    def _handle_download(self):
        url = self.url_entry.get().strip()
        if not url:
            ErrorDialog(self.parent, "Link Obrigatório", "Por favor, cole um link do YouTube antes de iniciar.")
            return

        if not validate_url(url):
            ErrorDialog(
                self.parent,
                "Link Inválido",
                "O link inserido não parece ser uma URL válida do YouTube.",
            )
            return

        if not is_yt_dlp_installed():
            InstallRequiredDialog(
                self.parent,
                on_confirm=lambda: launch_admin_install("yt-dlp.yt-dlp"),
                on_cancel=lambda: None,
                package_name="yt-dlp",
            )
            return

        if is_playlist_url(url):
            self.status_label.configure(
                text="O download de playlist baixará o primeiro item ou utilize um link de vídeo individual."
            )

        current_dest = get_default_download_dir()
        self._proceed_with_download(url, current_dest)

    def _proceed_with_download(self, url: str, destination: str):
        if get_use_custom_names():
            CustomNameDialog(
                self.parent,
                on_confirm=lambda name: self._start_download_task(url, destination, name),
                on_cancel=lambda: self.status_label.configure(text="Download cancelado."),
            )
        else:
            self._start_download_task(url, destination, None)

    def _set_ui_downloading_state(self, downloading: bool):
        self.is_downloading = downloading
        state = "disabled" if downloading else "normal"
        self.download_btn.configure(
            state=state,
            text="Baixando..." if downloading else "Baixar Conteúdo",
        )
        self.url_entry.configure(state=state)
        self.format_menu.configure(state=state)
        if not is_audio_format(self._get_format_key_from_label(self.format_var.get())):
            self.quality_menu.configure(state=state)
        self.change_folder_btn.configure(state=state)

    def _start_download_task(self, url: str, destination: str, custom_name: str | None = None):
        if self.is_downloading:
            return

        fmt_key = self._get_format_key_from_label(self.format_var.get())
        qual_key = self._get_quality_key_from_label(self.quality_var.get())

        dialog = ProgressDialog(self.parent)
        self.current_dialog = dialog
        self.current_session = DownloadSession()

        dialog.set_callbacks(
            on_pause=self._on_pause_download,
            on_cancel=self._on_cancel_download,
        )

        self._set_ui_downloading_state(True)
        self.status_label.configure(text=f"Iniciando download...")

        def worker():
            try:
                output_file = download_media(
                    url=url,
                    output_format=fmt_key,
                    quality=qual_key,
                    custom_name=custom_name,
                    on_progress=lambda info: self.parent.after(0, lambda: dialog.update_progress(info)),
                    save_dir=destination,
                    session=self.current_session,
                )

                file_stem = Path(output_file).stem
                add_to_history(
                    url=url,
                    title=file_stem,
                    output_format=fmt_key,
                    quality=qual_key,
                    output_path=output_file,
                )

                self.parent.after(0, lambda: self._on_download_success(dialog, output_file))

            except DownloadError as exc:
                if self.current_session and (self.current_session.cancel_requested or self.current_session.pause_requested):
                    action = "pausado" if self.current_session.pause_requested else "cancelado"
                    self.parent.after(0, lambda: self._on_download_stopped(dialog, action))
                else:
                    self.parent.after(0, lambda: self._on_download_error(dialog, str(exc)))

            except Exception as exc:
                self.parent.after(0, lambda: self._on_download_error(dialog, f"Erro inesperado: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_pause_download(self, is_paused: bool):
        if self.current_session:
            if is_paused:
                self.current_session.pause()
            else:
                self.current_session.resume()

    def _on_cancel_download(self):
        if self.current_session:
            self.current_session.cancel()

    def _on_download_stopped(self, dialog: ProgressDialog, action: str):
        dialog.close()
        self._set_ui_downloading_state(False)
        self.status_label.configure(text=f"Download {action} pelo usuário.")

    def _on_download_success(self, dialog: ProgressDialog, output_file: str):
        dialog.close()
        self._set_ui_downloading_state(False)

        self.last_download_path = output_file
        file_name = Path(output_file).name

        self.last_file_label.configure(text=f"Concluído: {file_name}")
        self.last_download_card.pack(fill="x", padx=24, pady=(0, 16))

        self.status_label.configure(text=f"Download finalizado com sucesso!")
        self.url_entry.delete(0, "end")

        if get_auto_open_folder():
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(output_file)])
            except Exception:
                pass

    def _on_download_error(self, dialog: ProgressDialog, error_msg: str):
        dialog.close()
        self._set_ui_downloading_state(False)
        ErrorDialog(self.parent, "Erro no Download", error_msg)
        self.status_label.configure(text="Falha no download. Verifique a URL e a conexão.")
