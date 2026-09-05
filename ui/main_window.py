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
    get_download_dir,
)
from core.formats import (
    FORMAT_OPTIONS,
    QUALITY_OPTIONS,
    extract_urls,
    get_format_extension,
    is_audio_format,
    is_playlist_url,
    validate_url,
)
from core.installer import is_yt_dlp_installed, launch_admin_install
from core.queue_manager import DownloadItem, DownloadQueueManager
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

import sys
from PIL import Image


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent.parent / relative_path


try:
    from app import log
except Exception:
    def log(msg: str) -> None:
        pass


class MainWindow:
    def __init__(self, parent: ctk.CTk):
        self.parent = parent
        self.last_download_path: str | None = None
        self.item_widgets: dict[str, dict] = {}

        # Gerenciador da Fila de Downloads
        self.queue_manager = DownloadQueueManager(
            on_item_updated=self._thread_safe_item_update,
            on_queue_finished=self._thread_safe_queue_finished,
        )

        log("MainWindow.__init__: Criando frame principal...")
        # Container Principal com Borda Neon Ciano
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
        log("MainWindow: 1. Reservando barra de navegacao inferior...")
        # 1. Barra Inferior de Navegação por Abas
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

        log("MainWindow: 2. Construindo Header...")
        # 2. Header / Barra Superior
        header_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(18, 10))

        # Logo e Título à Esquerda
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        logo_path = get_resource_path("codeline.png")
        if logo_path.exists():
            try:
                pil_logo = Image.open(logo_path)
                ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(30, 30))
                self.logo_lbl = ctk.CTkLabel(title_box, image=ctk_logo, text="")
                self.logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

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

        log("MainWindow: 3. Construindo Seção de URL...")
        # 3. Seção de URL
        url_section_label = ctk.CTkLabel(
            self.frame,
            text="Cole um ou múltiplos links do YouTube (separados por espaço ou quebra de linha)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            anchor="w",
        )
        url_section_label.pack(fill="x", padx=24, pady=(0, 6))

        url_input_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=24, pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="https://www.youtube.com/watch?v=... (Cole um ou mais links)",
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
            text="Colar Link(s)",
            width=110,
            height=44,
            corner_radius=10,
            fg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#021d2b",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._paste_clipboard,
        )
        paste_btn.pack(side="right")

        log("MainWindow: 4. Construindo Card de Configurações...")
        # 4. Card de Configurações de Download
        settings_card = ctk.CTkFrame(
            self.frame,
            fg_color="#131e2e",
            corner_radius=12,
            border_color="#1f2f45",
            border_width=1,
        )
        settings_card.pack(fill="x", padx=24, pady=(0, 10))

        # Título da Seção no Card
        card_title = ctk.CTkLabel(
            settings_card,
            text="CONFIGURACOES DE DOWNLOAD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
            anchor="w",
        )
        card_title.pack(fill="x", padx=16, pady=(10, 8))

        # Linha de Formato e Qualidade
        fmt_qual_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        fmt_qual_row.pack(fill="x", padx=16, pady=(0, 10))
        fmt_qual_row.grid_columnconfigure((0, 1), weight=1)

        # Formato
        fmt_box = ctk.CTkFrame(fmt_qual_row, fg_color="transparent")
        fmt_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        fmt_label = ctk.CTkLabel(
            fmt_box,
            text="Formato de Saida",
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
            height=36,
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
            text="Qualidade / Resolucao",
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
            height=36,
            corner_radius=8,
            fg_color="#09101a",
            button_color="#0284c7",
            button_hover_color="#0369a1",
            dropdown_fg_color="#131e2e",
        )
        self.quality_menu.pack(fill="x")

        # Linha de Destino (Salvar em)
        dest_row = ctk.CTkFrame(settings_card, fg_color="#09101a", corner_radius=8)
        dest_row.pack(fill="x", padx=16, pady=(0, 10))

        dest_text_box = ctk.CTkFrame(dest_row, fg_color="transparent")
        dest_text_box.pack(side="left", fill="x", expand=True, padx=12, pady=6)

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
            text="Alterar Pasta...",
            height=28,
            width=115,
            command=self._choose_folder,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
        )
        self.change_folder_btn.pack(side="right", padx=10, pady=4)

        log("MainWindow: 5. Construindo Botão de Download...")
        # 5. Botão Principal de Download / Adicionar à Fila
        self.download_btn = ctk.CTkButton(
            self.frame,
            text="Baixar Conteúdo ⤓",
            height=46,
            corner_radius=10,
            fg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#021d2b",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._handle_download,
        )
        self.download_btn.pack(fill="x", padx=24, pady=(0, 10))

        log("MainWindow: 6. Construindo Card de Fila e Downloads Ativos...")
        # 6. Card Integrado: DOWNLOADS ATIVOS E FILA
        self.active_card = ctk.CTkFrame(
            self.frame,
            fg_color="#131e2e",
            corner_radius=12,
            border_color="#1f2f45",
            border_width=1,
        )
        self.active_card.pack(fill="both", expand=True, padx=24, pady=(0, 10))

        # Cabeçalho do Card de Downloads
        active_header = ctk.CTkFrame(self.active_card, fg_color="transparent")
        active_header.pack(fill="x", padx=16, pady=(10, 6))

        self.active_title = ctk.CTkLabel(
            active_header,
            text="DOWNLOADS ATIVOS / FILA",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
        )
        self.active_title.pack(side="left")

        # Botões de Ação Global da Fila (Limpar / Cancelar Todos)
        header_actions = ctk.CTkFrame(active_header, fg_color="transparent")
        header_actions.pack(side="right")

        self.clear_completed_btn = ctk.CTkButton(
            header_actions,
            text="Limpar Finalizados",
            height=24,
            width=110,
            command=self._clear_completed_items,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=4,
        )
        self.clear_completed_btn.pack(side="right", padx=(6, 0))
        self.clear_completed_btn.pack_forget()

        self.cancel_all_btn = ctk.CTkButton(
            header_actions,
            text="Cancelar Todos",
            height=24,
            width=95,
            command=self._cancel_all_downloads,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            text_color="#fca5a5",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=4,
        )
        self.cancel_all_btn.pack(side="right")
        self.cancel_all_btn.pack_forget()

        # Frame de Rolagem com a Lista de Downloads
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.active_card,
            fg_color="#09101a",
            corner_radius=8,
            border_color="#1e293b",
            border_width=1,
            height=140,
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        # Mensagem quando a fila estiver vazia
        self.empty_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Nenhum download em andamento.\nCole um ou mais links acima para iniciar.",
            font=ctk.CTkFont(size=12),
            text_color="#64748b",
            justify="center",
        )
        self.empty_label.pack(expand=True, pady=30)

        log("MainWindow: 7. Aplicando selecao inicial de formato...")
        self._on_format_selected(self.format_var.get())
        log("MainWindow: _build_ui concluido com sucesso!")

    def _paste_clipboard(self):
        try:
            clipboard_text = self.parent.clipboard_get().strip()
            if clipboard_text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_text)
                detected = extract_urls(clipboard_text)
                if len(detected) > 1:
                    self._update_queue_header_counts()
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

    def _handle_download(self):
        raw_text = self.url_entry.get().strip()
        if not raw_text:
            ErrorDialog(self.parent, "Link Obrigatório", "Por favor, cole ao menos um link do YouTube antes de iniciar.")
            return

        urls = extract_urls(raw_text)
        if not urls:
            # Tenta validar se a URL é válida diretamente
            if validate_url(raw_text):
                urls = [raw_text]
            else:
                ErrorDialog(
                    self.parent,
                    "Link Inválido",
                    "Nenhum link válido do YouTube foi encontrado no texto inserido.",
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

        current_dest = get_default_download_dir()
        fmt_key = self._get_format_key_from_label(self.format_var.get())
        qual_key = self._get_quality_key_from_label(self.quality_var.get())

        if len(urls) == 1 and get_use_custom_names():
            CustomNameDialog(
                self.parent,
                on_confirm=lambda name: self._enqueue_single_download(urls[0], fmt_key, qual_key, current_dest, name),
                on_cancel=lambda: None,
            )
        else:
            self._enqueue_multiple_downloads(urls, fmt_key, qual_key, current_dest)

        self.url_entry.delete(0, "end")

    def _enqueue_single_download(self, url: str, fmt: str, qual: str, dest: str, custom_name: str | None = None):
        if self.empty_label.winfo_ismapped():
            self.empty_label.pack_forget()

        self.queue_manager.add_item(
            url=url,
            output_format=fmt,
            quality=qual,
            save_dir=dest,
            custom_name=custom_name,
        )
        self.queue_manager.start()
        self._update_queue_header_counts()

    def _enqueue_multiple_downloads(self, urls: list[str], fmt: str, qual: str, dest: str):
        if self.empty_label.winfo_ismapped():
            self.empty_label.pack_forget()

        self.queue_manager.add_items(
            urls=urls,
            output_format=fmt,
            quality=qual,
            save_dir=dest,
        )
        self.queue_manager.start()
        self._update_queue_header_counts()

    def _cancel_all_downloads(self):
        self.queue_manager.cancel_all()
        self._update_queue_header_counts()

    def _clear_completed_items(self):
        self.queue_manager.clear_completed()
        # Remove widgets que não estão mais na lista
        existing_ids = {it.id for it in self.queue_manager.items}
        for item_id in list(self.item_widgets.keys()):
            if item_id not in existing_ids:
                widgets = self.item_widgets.pop(item_id)
                try:
                    widgets["card"].destroy()
                except Exception:
                    pass

        if not self.queue_manager.items:
            self.empty_label.pack(expand=True, pady=30)

        self._update_queue_header_counts()

    def _thread_safe_item_update(self, item: DownloadItem):
        self.parent.after(0, lambda: self._render_item(item))

    def _thread_safe_queue_finished(self):
        self.parent.after(0, self._on_queue_finished)

    def _on_queue_finished(self):
        self._update_queue_header_counts()
        counts = self.queue_manager.get_counts()
        if counts["completed"] > 0 and get_auto_open_folder():
            # Abre a pasta do último download concluído
            for it in reversed(self.queue_manager.items):
                if it.status == "completed" and it.output_path and os.path.exists(it.output_path):
                    try:
                        subprocess.Popen(["explorer", "/select,", os.path.normpath(it.output_path)])
                    except Exception:
                        pass
                    break

    def _update_queue_header_counts(self):
        counts = self.queue_manager.get_counts()
        total = counts["total"]

        if total > 0:
            active_str = f"DOWNLOADS ({counts['completed']}/{total} CONCLUÍDOS)"
            if counts["downloading"] > 0:
                active_str += f" - {counts['downloading']} BAIXANDO"
            self.active_title.configure(text=active_str)

            if counts["downloading"] > 0 or counts["pending"] > 0:
                self.cancel_all_btn.pack(side="right", padx=(6, 0))
            else:
                self.cancel_all_btn.pack_forget()

            if counts["completed"] > 0 or counts["cancelled"] > 0 or counts["error"] > 0:
                self.clear_completed_btn.pack(side="right")
            else:
                self.clear_completed_btn.pack_forget()
        else:
            self.active_title.configure(text="DOWNLOADS ATIVOS / FILA")
            self.cancel_all_btn.pack_forget()
            self.clear_completed_btn.pack_forget()

    def _render_item(self, item: DownloadItem):
        if self.empty_label.winfo_ismapped():
            self.empty_label.pack_forget()

        if item.id not in self.item_widgets:
            # Cria novo card de item na lista
            item_card = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="#131e2e",
                corner_radius=8,
                border_color="#1e293b",
                border_width=1,
            )
            item_card.pack(fill="x", pady=4, padx=4)

            # Linha superior: Título e Botão de Ação
            top_row = ctk.CTkFrame(item_card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(6, 4))

            title_lbl = ctk.CTkLabel(
                top_row,
                text=item.display_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#e2e8f0",
                anchor="w",
            )
            title_lbl.pack(side="left", fill="x", expand=True)

            action_btn = ctk.CTkButton(
                top_row,
                text="✕",
                width=28,
                height=22,
                corner_radius=4,
                fg_color="#334155",
                hover_color="#ef4444",
                text_color="#f8fafc",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda i_id=item.id: self.queue_manager.cancel_item(i_id),
            )
            action_btn.pack(side="right", padx=(6, 0))

            # Barra de progresso
            p_bar = ctk.CTkProgressBar(
                item_card,
                mode="determinate",
                height=8,
                corner_radius=4,
                progress_color="#06b6d4",
                fg_color="#09101a",
            )
            p_bar.pack(fill="x", padx=10, pady=(2, 4))
            p_bar.set(0.0)

            # Linha inferior: Status e Métricas
            bottom_row = ctk.CTkFrame(item_card, fg_color="transparent")
            bottom_row.pack(fill="x", padx=10, pady=(0, 6))

            status_lbl = ctk.CTkLabel(
                bottom_row,
                text="Aguardando...",
                font=ctk.CTkFont(size=10),
                text_color="#94a3b8",
                anchor="w",
            )
            status_lbl.pack(side="left")

            metrics_lbl = ctk.CTkLabel(
                bottom_row,
                text="",
                font=ctk.CTkFont(size=10),
                text_color="#64748b",
                anchor="e",
            )
            metrics_lbl.pack(side="right")

            self.item_widgets[item.id] = {
                "card": item_card,
                "title_lbl": title_lbl,
                "action_btn": action_btn,
                "p_bar": p_bar,
                "status_lbl": status_lbl,
                "metrics_lbl": metrics_lbl,
            }

        # Atualiza o card existente
        w = self.item_widgets[item.id]
        w["title_lbl"].configure(text=item.display_name)

        if item.status == "downloading":
            pct = max(0.0, min(1.0, item.progress.percent / 100.0)) if item.progress.percent else 0.05
            w["p_bar"].set(pct)
            w["p_bar"].configure(progress_color="#06b6d4")
            w["status_lbl"].configure(
                text=item.progress.status_text or f"Baixando: {item.progress.percent:.1f}%",
                text_color="#38bdf8",
            )
            details = []
            if item.progress.speed:
                details.append(item.progress.speed)
            if item.progress.eta:
                details.append(f"ETA {item.progress.eta}")
            w["metrics_lbl"].configure(text=" | ".join(details) if details else "")

            w["action_btn"].configure(
                text="✕ Cancelar",
                width=80,
                fg_color="#7f1d1d",
                hover_color="#b91c1c",
                command=lambda i_id=item.id: self.queue_manager.cancel_item(i_id),
            )

        elif item.status == "completed":
            w["p_bar"].set(1.0)
            w["p_bar"].configure(progress_color="#10b981")
            w["status_lbl"].configure(text="✓ Concluído com sucesso", text_color="#10b981")
            w["metrics_lbl"].configure(text="100.0%")
            w["action_btn"].configure(
                text="Abrir",
                width=65,
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda out=item.output_path: self._open_file(out),
            )

        elif item.status == "cancelled":
            w["p_bar"].configure(progress_color="#64748b")
            w["status_lbl"].configure(text="Download cancelado", text_color="#ef4444")
            w["metrics_lbl"].configure(text="")
            w["action_btn"].configure(
                text="Remover",
                width=75,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda i_id=item.id: self._remove_single_widget(i_id),
            )

        elif item.status == "error":
            w["p_bar"].configure(progress_color="#ef4444")
            err_short = item.error_message or "Erro no download"
            if len(err_short) > 50:
                err_short = err_short[:47] + "..."
            w["status_lbl"].configure(text=f"✕ {err_short}", text_color="#ef4444")
            w["metrics_lbl"].configure(text="")
            w["action_btn"].configure(
                text="Remover",
                width=75,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda i_id=item.id: self._remove_single_widget(i_id),
            )

        elif item.status == "pending":
            w["p_bar"].set(0.0)
            w["status_lbl"].configure(text="Na fila de espera...", text_color="#94a3b8")
            w["metrics_lbl"].configure(text="")
            w["action_btn"].configure(
                text="✕",
                width=28,
                fg_color="#334155",
                hover_color="#ef4444",
                command=lambda i_id=item.id: self.queue_manager.cancel_item(i_id),
            )

        self._update_queue_header_counts()

    def _remove_single_widget(self, item_id: str):
        if item_id in self.item_widgets:
            widgets = self.item_widgets.pop(item_id)
            try:
                widgets["card"].destroy()
            except Exception:
                pass

        self.queue_manager.items = [it for it in self.queue_manager.items if it.id != item_id]

        if not self.queue_manager.items:
            self.empty_label.pack(expand=True, pady=30)

        self._update_queue_header_counts()

    def _open_file(self, file_path: str | None):
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except Exception:
                pass
