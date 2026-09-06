from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from PIL import Image
import customtkinter as ctk


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent.parent / relative_path


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Sobre DYTB Downloader")
        self.geometry("480x440")
        self.minsize(480, 440)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color="#111820")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=24)
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            frame,
            text="DYTB Downloader",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#ffffff",
        )
        title.pack(pady=(0, 4))

        version = ctk.CTkLabel(
            frame,
            text="Versão 1.2.0",
            font=ctk.CTkFont(size=12),
            text_color="#999999",
        )
        version.pack(pady=(0, 16))

        desc = ctk.CTkLabel(
            frame,
            text="Uma ferramenta moderna e poderosa para baixar vídeos do YouTube em múltiplos formatos.",
            font=ctk.CTkFont(size=13),
            text_color="#b7c4d4",
            wraplength=420,
            justify="center",
        )
        desc.pack(pady=(0, 20))

        divider = ctk.CTkFrame(frame, height=1, fg_color="#2d3748")
        divider.pack(fill="x", pady=(10, 10))

        features_title = ctk.CTkLabel(
            frame,
            text="Recursos",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
        )
        features_title.pack(anchor="w", pady=(0, 8))

        features_text = """• Múltiplos formatos (MP4, WebM, MKV, MP3, WAV, M4A)
• Seleção de qualidade (até 1080p)
• Histórico de downloads
• Nome customizado para arquivos
• Suporte a playlists
• Configurações personalizáveis
• Interface moderna e intuitiva"""

        features = ctk.CTkLabel(
            frame,
            text=features_text,
            font=ctk.CTkFont(size=11),
            text_color="#94a6bb",
            wraplength=420,
            justify="left",
        )
        features.pack(anchor="w", pady=(0, 16))

        divider2 = ctk.CTkFrame(frame, height=1, fg_color="#2d3748")
        divider2.pack(fill="x", pady=(10, 10))

        credits = ctk.CTkLabel(
            frame,
            text="Desenvolvido para a comunidade.",
            font=ctk.CTkFont(size=11),
            text_color="#999999",
        )
        credits.pack(pady=(0, 6))

        # Seção Desenvolvido por RickHardDev com ícone e link
        dev_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dev_frame.pack(pady=(0, 16))

        dev_label = ctk.CTkLabel(
            dev_frame,
            text="Desenvolvido por ",
            font=ctk.CTkFont(size=12),
            text_color="#94a6bb",
        )
        dev_label.pack(side="left")

        icon_path = get_resource_path("codeline.png")
        if icon_path.exists():
            try:
                pil_img = Image.open(icon_path)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
                self.icon_lbl = ctk.CTkLabel(dev_frame, image=ctk_img, text="")
                self.icon_lbl.pack(side="left", padx=(2, 6))
            except Exception:
                pass

        def open_profile():
            webbrowser.open_new_tab("https://www.instagram.com/rick.hard.dev/")

        link_btn = ctk.CTkButton(
            dev_frame,
            text="RickHardDev",
            font=ctk.CTkFont(size=12, weight="bold", underline=True),
            text_color="#38bdf8",
            fg_color="transparent",
            hover_color="#1a2636",
            cursor="hand2",
            width=0,
            height=24,
            command=open_profile,
        )
        link_btn.pack(side="left")

        close_btn = ctk.CTkButton(
            frame,
            text="Fechar",
            command=self.destroy,
            width=120,
            height=36,
        )
        close_btn.pack(pady=(0, 0))

        self.center_on_parent()

    def center_on_parent(self):
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        x = parent_x + (parent_w // 2) - (self.winfo_reqwidth() // 2)
        y = parent_y + (parent_h // 2) - (self.winfo_reqheight() // 2)
        self.geometry(f"+{x}+{y}")
