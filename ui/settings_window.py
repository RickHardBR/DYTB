from __future__ import annotations

import customtkinter as ctk

from core.formats import FORMAT_OPTIONS, QUALITY_OPTIONS
from core.settings import (
    get_auto_open_folder,
    get_browser_cookies,
    get_default_format,
    get_default_quality,
    get_use_custom_names,
    set_auto_open_folder,
    set_browser_cookies,
    set_default_format,
    set_default_quality,
    set_use_custom_names,
)

BROWSER_OPTIONS = {
    "none": "Nenhuma (Download Anônimo)",
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Mozilla Firefox",
    "brave": "Brave Browser",
    "opera": "Opera",
}


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configurações")
        self.geometry("540x560")
        self.minsize(540, 560)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color="#0b1118")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        # Título
        title = ctk.CTkLabel(
            self,
            text="Configurações DYTB",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        title.pack(fill="x", padx=24, pady=(20, 12))

        # Frame scrollável
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        scroll_frame.grid_columnconfigure(0, weight=1)

        # 1. Formato padrão
        format_label = ctk.CTkLabel(
            scroll_frame,
            text="Formato Padrão",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        )
        format_label.pack(fill="x", pady=(0, 6))

        format_labels = [v["label"] for v in FORMAT_OPTIONS.values()]
        saved_fmt_key = get_default_format()
        initial_fmt_label = FORMAT_OPTIONS.get(saved_fmt_key, {}).get("label", format_labels[0])
        self.format_var = ctk.StringVar(value=initial_fmt_label)

        format_menu = ctk.CTkOptionMenu(
            scroll_frame,
            values=format_labels,
            variable=self.format_var,
            command=self._on_format_change,
            height=36,
            corner_radius=8,
        )
        format_menu.pack(fill="x", pady=(0, 14))

        # 2. Qualidade padrão
        quality_label = ctk.CTkLabel(
            scroll_frame,
            text="Qualidade Padrão",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        )
        quality_label.pack(fill="x", pady=(0, 6))

        quality_labels = [v["label"] for v in QUALITY_OPTIONS.values()]
        saved_qual_key = get_default_quality()
        initial_qual_label = QUALITY_OPTIONS.get(saved_qual_key, {}).get("label", quality_labels[0])
        self.quality_var = ctk.StringVar(value=initial_qual_label)

        quality_menu = ctk.CTkOptionMenu(
            scroll_frame,
            values=quality_labels,
            variable=self.quality_var,
            command=self._on_quality_change,
            height=36,
            corner_radius=8,
        )
        quality_menu.pack(fill="x", pady=(0, 14))

        # 3. Autenticação e Sessão de Navegador (Vídeos Privados / Cursos / Instagram)
        browser_label = ctk.CTkLabel(
            scroll_frame,
            text="Autenticação por Navegador (Vídeos Privados / Cursos / Instagram)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
            anchor="w",
        )
        browser_label.pack(fill="x", pady=(0, 4))

        browser_labels = list(BROWSER_OPTIONS.values())
        saved_browser_key = get_browser_cookies()
        initial_browser_label = BROWSER_OPTIONS.get(saved_browser_key, BROWSER_OPTIONS["none"])
        self.browser_var = ctk.StringVar(value=initial_browser_label)

        browser_menu = ctk.CTkOptionMenu(
            scroll_frame,
            values=browser_labels,
            variable=self.browser_var,
            command=self._on_browser_change,
            height=36,
            corner_radius=8,
            fg_color="#131e2e",
            button_color="#0284c7",
            button_hover_color="#0369a1",
        )
        browser_menu.pack(fill="x", pady=(0, 4))

        browser_info = ctk.CTkLabel(
            scroll_frame,
            text="Usa a sessão ativa do seu navegador para baixar Reels de contas privadas que você segue no Instagram, vídeos com restrição de idade no YouTube e aulas de cursos (Hotmart, DIO).",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            anchor="w",
            justify="left",
            wraplength=460,
        )
        browser_info.pack(fill="x", pady=(0, 16))

        # 4. Nomes customizados
        custom_names_label = ctk.CTkLabel(
            scroll_frame,
            text="Nome Personalizado para Arquivos",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        )
        custom_names_label.pack(fill="x", pady=(0, 6))

        self.custom_names_var = ctk.BooleanVar(value=get_use_custom_names())
        custom_names_switch = ctk.CTkSwitch(
            scroll_frame,
            text="Solicitar nome antes de cada download individual",
            variable=self.custom_names_var,
            command=self._on_custom_names_change,
        )
        custom_names_switch.pack(fill="x", pady=(0, 4))

        custom_names_info = ctk.CTkLabel(
            scroll_frame,
            text="Se desativado, o título original do vídeo/stream será usado automaticamente.",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            anchor="w",
            justify="left",
            wraplength=460,
        )
        custom_names_info.pack(fill="x", pady=(0, 14))

        # 5. Auto-abrir pasta
        auto_open_label = ctk.CTkLabel(
            scroll_frame,
            text="Abertura Automática",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1f5f9",
            anchor="w",
        )
        auto_open_label.pack(fill="x", pady=(0, 6))

        self.auto_open_var = ctk.BooleanVar(value=get_auto_open_folder())
        auto_open_switch = ctk.CTkSwitch(
            scroll_frame,
            text="Destacar o arquivo baixado na pasta automaticamente",
            variable=self.auto_open_var,
            command=self._on_auto_open_change,
        )
        auto_open_switch.pack(fill="x", pady=(0, 4))

        auto_open_info = ctk.CTkLabel(
            scroll_frame,
            text="Ao concluir o download, o Windows Explorer abrirá com o arquivo selecionado.",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            anchor="w",
            justify="left",
            wraplength=460,
        )
        auto_open_info.pack(fill="x", pady=(0, 16))

        # Botão fechar
        close_btn = ctk.CTkButton(
            self,
            text="Salvar e Fechar",
            command=self.destroy,
            height=42,
            corner_radius=10,
            fg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#021d2b",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        close_btn.pack(fill="x", padx=24, pady=(0, 18))

    def _on_format_change(self, choice_label: str):
        for k, v in FORMAT_OPTIONS.items():
            if v["label"] == choice_label:
                set_default_format(k)
                break

    def _on_quality_change(self, choice_label: str):
        for k, v in QUALITY_OPTIONS.items():
            if v["label"] == choice_label:
                set_default_quality(k)
                break

    def _on_browser_change(self, choice_label: str):
        for k, v in BROWSER_OPTIONS.items():
            if v == choice_label:
                set_browser_cookies(k)
                break

    def _on_custom_names_change(self):
        set_use_custom_names(self.custom_names_var.get())

    def _on_auto_open_change(self):
        set_auto_open_folder(self.auto_open_var.get())
