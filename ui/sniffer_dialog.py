from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from core.sniffer_manager import SnifferManager


class SnifferDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        sniffer_manager: SnifferManager,
        on_download_stream: Callable[[str, str], None],
        initial_url: str = "https://hotmart.com/",
    ):
        super().__init__(parent)
        self.sniffer_manager = sniffer_manager
        self.on_download_stream = on_download_stream
        self.initial_url = initial_url

        self.title("DYTB - Navegador Sniffer EAD")
        self.geometry("780x560")
        self.minsize(680, 480)
        self.configure(fg_color="#0b1320")

        # Centraliza a janela sobre a janela principal
        self.transient(parent)
        self.after(10, self._center_window)

        self._stream_cards: list[ctk.CTkFrame] = []
        self._build_ui()

        # Registra callbacks no SnifferManager
        self.sniffer_manager.on_status_changed = self._on_status_changed_cb
        self.sniffer_manager.on_stream_captured = self._on_stream_captured_cb

        # Se o navegador não estiver aberto, inicia automaticamente com a URL fornecida
        if not self.sniffer_manager.is_running():
            self.after(200, lambda: self._start_browser(self.initial_url))
        else:
            self._update_status(True, "Navegador já em execução. Monitorando transmissões...")
            self._reload_captured_list()

    def _center_window(self):
        self.update_idletasks()
        try:
            x = self.master.winfo_x() + (self.master.winfo_width() - 780) // 2
            y = self.master.winfo_y() + (self.master.winfo_height() - 560) // 2
            self.geometry(f"+{max(20, x)}+{max(20, y)}")
        except Exception:
            pass

    def _build_ui(self):
        # 1. Header
        header = ctk.CTkFrame(self, fg_color="#131e2e", height=64, corner_radius=0)
        header.pack(fill="x")

        head_box = ctk.CTkFrame(header, fg_color="transparent")
        head_box.pack(fill="both", expand=True, padx=20, pady=12)

        title_lbl = ctk.CTkLabel(
            head_box,
            text="🌐 Navegador Sniffer EAD",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
        )
        title_lbl.pack(side="left")

        subtitle_lbl = ctk.CTkLabel(
            head_box,
            text="Hotmart Club, Panda Video, Kiwify, Eduzz, etc.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        subtitle_lbl.pack(side="left", padx=12, pady=2)

        # 2. Status Bar
        self.status_bar = ctk.CTkFrame(self, fg_color="#09101a", height=38, corner_radius=0)
        self.status_bar.pack(fill="x", padx=0, pady=0)

        self.status_dot = ctk.CTkLabel(
            self.status_bar,
            text="●",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ef4444",
        )
        self.status_dot.pack(side="left", padx=(20, 6), pady=6)

        self.status_text = ctk.CTkLabel(
            self.status_bar,
            text="Navegador não iniciado",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        self.status_text.pack(side="left", pady=6)

        # 3. Controles do Navegador
        ctrl_frame = ctk.CTkFrame(self, fg_color="#131e2e", corner_radius=10)
        ctrl_frame.pack(fill="x", padx=20, pady=(12, 10))

        url_box = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        url_box.pack(fill="x", padx=12, pady=10)

        url_lbl = ctk.CTkLabel(
            url_box,
            text="Página da Aula / Plataforma:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1",
        )
        url_lbl.pack(anchor="w", pady=(0, 4))

        input_row = ctk.CTkFrame(url_box, fg_color="transparent")
        input_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="https://hotmart.com/...",
            height=36,
            fg_color="#09101a",
            border_color="#38bdf8",
            border_width=1,
            text_color="#f8fafc",
            font=ctk.CTkFont(size=12),
        )
        self.url_entry.insert(0, self.initial_url if self.initial_url.startswith("http") else "https://hotmart.com/")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_launch = ctk.CTkButton(
            input_row,
            text="▶ Iniciar Navegador",
            width=140,
            height=36,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_launch_clicked,
        )
        self.btn_launch.pack(side="right", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            input_row,
            text="⏹ Fechar",
            width=80,
            height=36,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#ffffff",
            font=ctk.CTkFont(size=12),
            command=self._on_stop_clicked,
        )
        self.btn_stop.pack(side="right")

        # 4. Guia Rápido
        guide_box = ctk.CTkFrame(self, fg_color="#102030", corner_radius=8)
        guide_box.pack(fill="x", padx=20, pady=(0, 10))

        guide_txt = (
            "📌 Como Usar: 1. Inicie o navegador acima | 2. Faça login na sua conta no curso | "
            "3. Ao dar Play no vídeo, ele aparecerá capturado na lista abaixo automaticamente!"
        )
        guide_lbl = ctk.CTkLabel(
            guide_box,
            text=guide_txt,
            font=ctk.CTkFont(size=11),
            text_color="#7dd3fc",
            anchor="w",
        )
        guide_lbl.pack(fill="x", padx=12, pady=6)

        # 5. Lista de Streams Capturados
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(4, 6))

        list_title = ctk.CTkLabel(
            list_header,
            text="Vídeos e Streams Detectados em Tempo Real:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc",
        )
        list_title.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            list_header,
            text="Limpar Lista",
            width=90,
            height=26,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11),
            command=self._clear_list,
        )
        self.clear_btn.pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#09101a",
            corner_radius=10,
            border_color="#1f2f45",
            border_width=1,
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.empty_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="Nenhum vídeo reproduzido ainda.\nNavegue até a aula e clique em Play no player.",
            font=ctk.CTkFont(size=13),
            text_color="#64748b",
        )
        self.empty_lbl.pack(expand=True, pady=40)

    def _start_browser(self, url: str):
        target = url.strip() or "https://hotmart.com/"
        self._update_status(True, "Iniciando navegador com monitoramento CDP...")
        self.sniffer_manager.launch(target)

    def _on_launch_clicked(self):
        url = self.url_entry.get().strip() or "https://hotmart.com/"
        self._start_browser(url)

    def _on_stop_clicked(self):
        self.sniffer_manager.stop()
        self._update_status(False, "Navegador fechado.")

    def _on_status_changed_cb(self, connected: bool, msg: str):
        self.after(0, lambda: self._update_status(connected, msg))

    def _update_status(self, connected: bool, msg: str):
        try:
            if connected:
                self.status_dot.configure(text_color="#10b981")
                self.status_text.configure(text=msg, text_color="#10b981")
            else:
                self.status_dot.configure(text_color="#ef4444")
                self.status_text.configure(text=msg, text_color="#94a3b8")
        except Exception:
            pass

    def _on_stream_captured_cb(self, url: str, title: str):
        self.after(0, self._reload_captured_list)

    def _reload_captured_list(self):
        for card in self._stream_cards:
            try:
                card.destroy()
            except Exception:
                pass
        self._stream_cards.clear()

        items = self.sniffer_manager.captured_urls
        if not items:
            self.empty_lbl.pack(expand=True, pady=40)
            return

        self.empty_lbl.pack_forget()

        for idx, it in enumerate(reversed(items)):
            c_url = it.get("url", "")
            c_title = it.get("title", f"Vídeo EAD #{len(items)-idx}")
            c_time = it.get("time", "")

            card = ctk.CTkFrame(self.scroll_frame, fg_color="#131e2e", corner_radius=8, border_color="#0284c7", border_width=1)
            card.pack(fill="x", padx=6, pady=4)
            self._stream_cards.append(card)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=8)

            # Informações do vídeo
            info_col = ctk.CTkFrame(inner, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True)

            t_lbl = ctk.CTkLabel(
                info_col,
                text=f"🎬 {c_title}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#38bdf8",
                anchor="w",
            )
            t_lbl.pack(fill="x")

            url_sub = c_url[:80] + "..." if len(c_url) > 80 else c_url
            sub_lbl = ctk.CTkLabel(
                info_col,
                text=f"⏰ {c_time} | {url_sub}",
                font=ctk.CTkFont(size=10),
                text_color="#64748b",
                anchor="w",
            )
            sub_lbl.pack(fill="x", pady=(2, 0))

            # Ações
            btn_box = ctk.CTkFrame(inner, fg_color="transparent")
            btn_box.pack(side="right", padx=(8, 0))

            dl_btn = ctk.CTkButton(
                btn_box,
                text="📥 Baixar no DYTB",
                width=120,
                height=32,
                fg_color="#10b981",
                hover_color="#059669",
                text_color="#022c22",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda u=c_url, t=c_title: self._download_and_close(u, t),
            )
            dl_btn.pack(side="left", padx=(0, 6))

            copy_btn = ctk.CTkButton(
                btn_box,
                text="📋 Copiar Link",
                width=90,
                height=32,
                fg_color="#1e293b",
                hover_color="#334155",
                text_color="#cbd5e1",
                font=ctk.CTkFont(size=11),
                command=lambda u=c_url: self._copy_to_clipboard(u),
            )
            copy_btn.pack(side="left")

    def _download_and_close(self, url: str, title: str):
        self.on_download_stream(url, title)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear_list(self):
        self.sniffer_manager.captured_urls.clear()
        self.sniffer_manager._seen_urls.clear()
        self._reload_captured_list()
