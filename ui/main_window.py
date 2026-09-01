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
from ui.dialogs import CustomNameDialog, ErrorDialog, InstallRequiredDialog
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow


class MainWindow:
    def __init__(self, parent: ctk.CTk):
        self.parent = parent
        self.last_download_path: str | None = None
        self.is_downloading = False
        self.current_session: DownloadSession | None = None

        # Container Principal com Borda Neon Ciano/Esmeralda
        self.frame = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#0e1622",
            border_color="#06b6d4",
            border_width=1.5,
        )
        self.frame.pack(fill="both", expand=True, padx=16, pady=16)

        self._build_ui()

    def _build_ui(self):
        # 1. Header / Barra Superior
        header_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(20, 14))

        # Logo e Título à Esquerda
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        logo_badge = ctk.CTkLabel(
            title_box,
            text="⬇",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#06b6d4",
            fg_color="#102538",
            corner_radius=8,
            width=36,
            height=36,
        )
        logo_badge.pack(side="left", padx=(0, 10))

        title_lbl = ctk.CTkLabel(
            title_box,
            text="DYTB Downloader",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#10b981",
        )
        title_lbl.pack(side="left")

        # Versão à Direita
        version_lbl = ctk.CTkLabel(
            header_frame,
            text="DYTB Downloader - v1.0.0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748b",
        )
        version_lbl.pack(side="right", pady=4)

        # 2. Seção de URL
        url_section_label = ctk.CTkLabel(
            self.frame,
            text="Cole o Link do Vídeo ou Playlist do YouTube",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            anchor="w",
        )
        url_section_label.pack(fill="x", padx=24, pady=(0, 6))

        url_input_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=24, pady=(0, 14))

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=44,
            corner_radius=10,
            fg_color="#09101a",
            border_color="#06b6d4",
            border_width=1.5,
            text_color="#f8fafc",
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = ctk.CTkButton(
            url_input_frame,
            text="📋 Colar",
            width=90,
            height=44,
            corner_radius=10,
            fg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#021d2b",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_clipboard,
        )
        paste_btn.pack(side="right")

        # 3. Card de Configurações de Download
        settings_card = ctk.CTkFrame(
            self.frame,
            fg_color="#131e2e",
            corner_radius=12,
            border_color="#1f2f45",
            border_width=1,
        )
        settings_card.pack(fill="x", padx=24, pady=(0, 14))

        # Título da Seção no Card
        card_title = ctk.CTkLabel(
            settings_card,
            text="CONFIGURAÇÕES DE DOWNLOAD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
            anchor="w",
        )
        card_title.pack(fill="x", padx=16, pady=(12, 10))

        # Linha de Formato e Qualidade
        fmt_qual_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        fmt_qual_row.pack(fill="x", padx=16, pady=(0, 12))
        fmt_qual_row.grid_columnconfigure((0, 1), weight=1)

        # Formato
        fmt_box = ctk.CTkFrame(fmt_qual_row, fg_color="transparent")
        fmt_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        fmt_label = ctk.CTkLabel(
            fmt_box,
            text="📁 Formato",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0",
            anchor="w",
        )
        fmt_label.pack(fill="x", pady=(0, 4))

        format_labels = [v["label"] for v in FORMAT_OPTIONS.values()]
        initial_fmt_key = get_default_format()
        initial_fmt_label = FORMAT_OPTIONS.get(initial_fmt_key, {}).get("label", format_labels[0])
        self.format_var = ctk.StringVar(value=initial_fmt_label)

        self.format_menu = ctk.CTkOptionMenu(
            fmt_box,
            values=format_labels,
            variable=self.format_var,
            height=38,
            corner_radius=8,
            fg_color="#09101a",
            button_color="#0284c7",
            button_hover_color="#0369a1",
            dropdown_fg_color="#131e2e",
            command=self._on_format_selected,
        )
        self.format_menu.pack(fill="x")

        # Qualidade
        qual_box = ctk.CTkFrame(fmt_qual_row, fg_color="transparent")
        qual_box.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        qual_label = ctk.CTkLabel(
            qual_box,
            text="⚙️ Qualidade",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0",
            anchor="w",
        )
        qual_label.pack(fill="x", pady=(0, 4))

        quality_labels = [v["label"] for v in QUALITY_OPTIONS.values()]
        initial_qual_key = get_default_quality()
        initial_qual_label = QUALITY_OPTIONS.get(initial_qual_key, {}).get("label", quality_labels[0])
        self.quality_var = ctk.StringVar(value=initial_qual_label)

        self.quality_menu = ctk.CTkOptionMenu(
            qual_box,
            values=quality_labels,
            variable=self.quality_var,
            height=38,
            corner_radius=8,
            fg_color="#09101a",
            button_color="#0284c7",
            button_hover_color="#0369a1",
            dropdown_fg_color="#131e2e",
        )
        self.quality_menu.pack(fill="x")

        # Linha de Destino (Salvar em)
        dest_row = ctk.CTkFrame(settings_card, fg_color="#09101a", corner_radius=8)
        dest_row.pack(fill="x", padx=16, pady=(0, 14))

        dest_text_box = ctk.CTkFrame(dest_row, fg_color="transparent")
        dest_text_box.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        dest_prefix = ctk.CTkLabel(
            dest_text_box,
            text="Salvar em: ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
        )
        dest_prefix.pack(side="left")

        self.dest_label = ctk.CTkLabel(
            dest_text_box,
            text=get_default_download_dir(),
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8",
            wraplength=400,
            justify="left",
            anchor="w",
        )
        self.dest_label.pack(side="left", fill="x", expand=True)

        self.change_folder_btn = ctk.CTkButton(
            dest_row,
            text="📁 Alterar...",
            height=30,
            width=100,
            command=self._choose_folder,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
        )
        self.change_folder_btn.pack(side="right", padx=10, pady=6)

        # 4. Botão Principal de Download (Destaque Neon)
        self.download_btn = ctk.CTkButton(
            self.frame,
            text="Baixar Conteúdo ⤓",
            height=48,
            corner_radius=10,
            fg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#021d2b",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._handle_download,
        )
        self.download_btn.pack(fill="x", padx=24, pady=(2, 14))

        # 5. Card Integrado: DOWNLOADS ATIVOS / PROGRESSO
        self.active_card = ctk.CTkFrame(
            self.frame,
            fg_color="#131e2e",
            corner_radius=12,
            border_color="#1f2f45",
            border_width=1,
        )
        self.active_card.pack(fill="x", padx=24, pady=(0, 14))

        active_header = ctk.CTkFrame(self.active_card, fg_color="transparent")
        active_header.pack(fill="x", padx=16, pady=(12, 6))

        active_title = ctk.CTkLabel(
            active_header,
            text="DOWNLOADS ATIVOS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
        )
        active_title.pack(side="left")

        self.open_last_file_btn = ctk.CTkButton(
            active_header,
            text="Abrir Arquivo",
            height=26,
            width=100,
            command=self._open_last_download,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
        )
        self.open_last_file_btn.pack(side="right")
        self.open_last_file_btn.pack_forget()

        # Linha com Título do Arquivo
        self.active_file_label = ctk.CTkLabel(
            self.active_card,
            text="Nenhum download em andamento.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0",
            anchor="w",
        )
        self.active_file_label.pack(fill="x", padx=16, pady=(0, 8))

        # Barra de Progresso Ciano Neon
        self.progress_bar = ctk.CTkProgressBar(
            self.active_card,
            mode="determinate",
            height=12,
            corner_radius=6,
            progress_color="#06b6d4",
            fg_color="#09101a",
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.progress_bar.set(0.0)

        # Métricas de Progresso (Status, Velocidade, ETA)
        metrics_row = ctk.CTkFrame(self.active_card, fg_color="transparent")
        metrics_row.pack(fill="x", padx=16, pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            metrics_row,
            text="Pronto para baixar.",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            anchor="w",
        )
        self.status_label.pack(side="left")

        self.metrics_label = ctk.CTkLabel(
            metrics_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            anchor="e",
        )
        self.metrics_label.pack(side="right")

        # 6. Barra Inferior de Navegação por Abas
        nav_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        nav_frame.pack(side="bottom", fill="x", padx=24, pady=(0, 16))

        nav_inner = ctk.CTkFrame(nav_frame, fg_color="transparent")
        nav_inner.pack(anchor="center")

        # Aba Downloads (Ativa)
        tab_dl = ctk.CTkButton(
            nav_inner,
            text="Downloads",
            width=100,
            height=32,
            fg_color="transparent",
            text_color="#10b981",
            font=ctk.CTkFont(size=13, weight="bold"),
            hover=False,
        )
        tab_dl.pack(side="left", padx=8)

        # Aba Histórico
        tab_hist = ctk.CTkButton(
            nav_inner,
            text="Histórico",
            width=100,
            height=32,
            fg_color="transparent",
            hover_color="#131e2e",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=13),
            command=self._open_history,
        )
        tab_hist.pack(side="left", padx=8)

        # Aba Configurações
        tab_settings = ctk.CTkButton(
            nav_inner,
            text="Configurações",
            width=110,
            height=32,
            fg_color="transparent",
            hover_color="#131e2e",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=13),
            command=self._open_settings,
        )
        tab_settings.pack(side="left", padx=8)

        # Aba Sobre
        tab_about = ctk.CTkButton(
            nav_inner,
            text="Sobre",
            width=90,
            height=32,
            fg_color="transparent",
            hover_color="#131e2e",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=13),
            command=self._open_about,
        )
        tab_about.pack(side="left", padx=8)

        self._on_format_selected(self.format_var.get())

    def _paste_clipboard(self):
        try:
            clipboard_text = self.parent.clipboard_get().strip()
            if clipboard_text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_text)
                self.status_label.configure(text="Link colado com sucesso.")
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
            self.status_label.configure(text="Pasta de destino atualizada.")

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
            text="Baixando..." if downloading else "Baixar Conteúdo ⤓",
        )
        self.url_entry.configure(state=state)
        self.format_menu.configure(state=state)
        if not is_audio_format(self._get_format_key_from_label(self.format_var.get())):
            self.quality_menu.configure(state=state)
        self.change_folder_btn.configure(state=state)

    def _update_in_app_progress(self, info: ProgressInfo):
        norm_val = max(0.0, min(1.0, info.percent / 100.0))
        self.progress_bar.set(norm_val)

        if info.status_text:
            self.status_label.configure(text=info.status_text)
        else:
            self.status_label.configure(text=f"Baixando: {info.percent:.1f}%")

        details = []
        if info.speed:
            details.append(f"Velocidade: {info.speed}")
        if info.eta:
            details.append(f"Tempo Restante: {info.eta}")
        self.metrics_label.configure(text=" | ".join(details) if details else "")

    def _start_download_task(self, url: str, destination: str, custom_name: str | None = None):
        if self.is_downloading:
            return

        fmt_key = self._get_format_key_from_label(self.format_var.get())
        qual_key = self._get_quality_key_from_label(self.quality_var.get())

        self.current_session = DownloadSession()
        self._set_ui_downloading_state(True)
        self.open_last_file_btn.pack_forget()

        display_name = custom_name if custom_name else "Obtendo dados do vídeo..."
        self.active_file_label.configure(text=f"🎬 {display_name}", text_color="#38bdf8")
        self.status_label.configure(text="Iniciando conexão com o YouTube...")
        self.metrics_label.configure(text="")
        self.progress_bar.set(0.05)

        def worker():
            try:
                output_file = download_media(
                    url=url,
                    output_format=fmt_key,
                    quality=qual_key,
                    custom_name=custom_name,
                    on_progress=lambda info: self.parent.after(0, lambda: self._update_in_app_progress(info)),
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

                self.parent.after(0, lambda: self._on_download_success(output_file))

            except DownloadError as exc:
                if self.current_session and (self.current_session.cancel_requested or self.current_session.pause_requested):
                    action = "pausado" if self.current_session.pause_requested else "cancelado"
                    self.parent.after(0, lambda: self._on_download_stopped(action))
                else:
                    self.parent.after(0, lambda: self._on_download_error(str(exc)))

            except Exception as exc:
                self.parent.after(0, lambda: self._on_download_error(f"Erro inesperado: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_stopped(self, action: str):
        self._set_ui_downloading_state(False)
        self.status_label.configure(text=f"Download {action} pelo usuário.")
        self.active_file_label.configure(text="Download cancelado.", text_color="#ef4444")

    def _on_download_success(self, output_file: str):
        self._set_ui_downloading_state(False)
        self.last_download_path = output_file
        file_name = Path(output_file).name

        self.active_file_label.configure(text=f"✓ Concluído: {file_name}", text_color="#10b981")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Download e conversão finalizados com sucesso!")
        self.metrics_label.configure(text="100.0%")
        self.open_last_file_btn.pack(side="right")

        self.url_entry.delete(0, "end")

        if get_auto_open_folder():
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(output_file)])
            except Exception:
                pass

    def _on_download_error(self, error_msg: str):
        self._set_ui_downloading_state(False)
        self.active_file_label.configure(text="Falha no download.", text_color="#ef4444")
        self.progress_bar.set(0.0)
        ErrorDialog(self.parent, "Erro no Download", error_msg)
        self.status_label.configure(text="Falha no download. Verifique a URL e a conexão.")

