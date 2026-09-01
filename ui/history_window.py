from __future__ import annotations

import os
import subprocess
from pathlib import Path

import customtkinter as ctk

from core.history import clear_history, load_history, remove_from_history


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Histórico de Downloads")
        self.geometry("700x520")
        self.minsize(600, 420)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color="#0b1118")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="Histórico de Downloads",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            header_frame,
            text="Limpar Histórico",
            width=130,
            height=32,
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._clear_all,
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        # Área de Rolagem
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#101923", corner_radius=12)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Rodapé
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))

        close_btn = ctk.CTkButton(
            footer_frame,
            text="Fechar",
            width=120,
            height=36,
            command=self.destroy,
            font=ctk.CTkFont(weight="bold"),
        )
        close_btn.pack(side="right")

        self._render_items()
        self._center_on_parent()

    def _center_on_parent(self):
        self.update_idletasks()
        try:
            parent_x = self.master.winfo_rootx()
            parent_y = self.master.winfo_rooty()
            parent_w = self.master.winfo_width()
            parent_h = self.master.winfo_height()
            x = parent_x + (parent_w // 2) - (self.winfo_reqwidth() // 2)
            y = parent_y + (parent_h // 2) - (self.winfo_reqheight() // 2)
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _render_items(self):
        # Limpar widgets existentes
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        history = load_history()
        if not history:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="Nenhum download registrado ainda.",
                font=ctk.CTkFont(size=14),
                text_color="#64748b",
            )
            empty_lbl.pack(pady=40)
            return

        for index, item in enumerate(history):
            self._create_item_card(index, item)

    def _create_item_card(self, index: int, item: dict):
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#182330", corner_radius=10)
        card.pack(fill="x", pady=6, padx=4)
        card.grid_columnconfigure(0, weight=1)

        title = item.get("title", "Sem título")
        fmt = item.get("format", "").upper()
        quality = item.get("quality", "")
        path = item.get("path", "")
        timestamp = item.get("timestamp", "")
        size_mb = item.get("size_mb")

        # Linha 1: Título e Badges
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        top_row.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            top_row,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff",
            anchor="w",
            wraplength=420,
            justify="left",
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        badge_text = f"{fmt} ({quality})" if quality else fmt
        badge = ctk.CTkLabel(
            top_row,
            text=badge_text,
            fg_color="#0284c7",
            text_color="#ffffff",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=8,
            pady=2,
        )
        badge.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Linha 2: Detalhes (Data, Tamanho e Caminho)
        meta_parts = []
        if timestamp:
            meta_parts.append(f"Data: {timestamp}")
        if size_mb:
            meta_parts.append(f"Tamanho: {size_mb} MB")

        meta_lbl = ctk.CTkLabel(
            card,
            text=" • ".join(meta_parts),
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            anchor="w",
        )
        meta_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        # Linha 3: Botões de Ação
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

        file_exists = os.path.exists(path) if path else False

        open_file_btn = ctk.CTkButton(
            btn_row,
            text="Abrir Arquivo",
            height=28,
            width=100,
            font=ctk.CTkFont(size=11, weight="bold"),
            state="normal" if file_exists else "disabled",
            command=lambda p=path: self._open_file(p),
            fg_color="#0284c7" if file_exists else "#334155",
            hover_color="#0369a1",
        )
        open_file_btn.pack(side="left", padx=(0, 8))

        open_folder_btn = ctk.CTkButton(
            btn_row,
            text="Abrir Pasta",
            height=28,
            width=100,
            font=ctk.CTkFont(size=11),
            command=lambda p=path: self._open_folder(p),
            fg_color="#1e293b",
            hover_color="#334155",
        )
        open_folder_btn.pack(side="left", padx=(0, 8))

        del_btn = ctk.CTkButton(
            btn_row,
            text="Excluir",
            height=28,
            width=70,
            font=ctk.CTkFont(size=11),
            fg_color="#450a0a",
            hover_color="#7f1d1d",
            command=lambda idx=index: self._remove_item(idx),
        )
        del_btn.pack(side="right")

    def _open_file(self, path: str):
        if path and os.path.exists(path):
            try:
                os.startfile(path)
            except Exception:
                pass

    def _open_folder(self, path: str):
        if not path:
            return
        folder = os.path.dirname(path) if os.path.isfile(path) else path
        if os.path.exists(path) and os.path.isfile(path):
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            except Exception:
                if os.path.exists(folder):
                    subprocess.Popen(["explorer", os.path.normpath(folder)])
        elif os.path.exists(folder):
            subprocess.Popen(["explorer", os.path.normpath(folder)])

    def _remove_item(self, index: int):
        remove_from_history(index)
        self._render_items()

    def _clear_all(self):
        clear_history()
        self._render_items()
