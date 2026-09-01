from __future__ import annotations

import customtkinter as ctk

from core.downloader import ProgressInfo


class BaseDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int = 440, height: int = 260):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.minsize(width, height)
        self.configure(fg_color="#0e1621")
        self.resizable(False, False)

        try:
            if master and master.winfo_exists() and master.winfo_viewable():
                self.transient(master)
                self.grab_set()
        except Exception:
            pass

    def center_on_parent(self):
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


class InstallRequiredDialog(BaseDialog):
    def __init__(self, master, on_confirm, on_cancel, package_name: str = "yt-dlp"):
        super().__init__(master, f"{package_name} obrigatório", 480, 240)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        title = ctk.CTkLabel(
            self,
            text=f"O {package_name} não foi encontrado.",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        )
        title.pack(pady=(20, 8), padx=24, anchor="w")

        message = ctk.CTkLabel(
            self,
            text=f"Para realizar downloads e conversões com precisão, é necessário instalar o {package_name} através do winget.",
            wraplength=430,
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color="#b7c4d4",
        )
        message.pack(padx=24, pady=(0, 20), anchor="w")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))

        confirm = ctk.CTkButton(
            actions,
            text="Instalar Agora",
            command=self._confirm,
            width=150,
            height=38,
            font=ctk.CTkFont(weight="bold"),
        )
        confirm.pack(side="right")

        cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            command=self._cancel,
            width=120,
            height=38,
            fg_color="#2d3748",
            hover_color="#374151",
        )
        cancel.pack(side="right", padx=(0, 12))

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.center_on_parent()

    def _confirm(self):
        self.destroy()
        self.on_confirm()

    def _cancel(self):
        self.destroy()
        self.on_cancel()


class ErrorDialog(BaseDialog):
    def __init__(self, master, title: str, message: str):
        super().__init__(master, title, 480, 260)

        title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f87171",
        )
        title_lbl.pack(padx=24, pady=(20, 10), anchor="w")

        label = ctk.CTkLabel(
            self,
            text=message,
            wraplength=430,
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color="#cbd5e1",
        )
        label.pack(padx=24, pady=(0, 16), anchor="w", fill="both", expand=True)

        button = ctk.CTkButton(
            self,
            text="OK",
            command=self.destroy,
            width=140,
            height=36,
            font=ctk.CTkFont(weight="bold"),
        )
        button.pack(pady=(0, 20))

        self.center_on_parent()


class DestinationDialog(BaseDialog):
    def __init__(self, master, current_path: str, on_keep, on_change):
        super().__init__(master, "Destino do download", 480, 240)
        self.on_keep = on_keep
        self.on_change = on_change

        label = ctk.CTkLabel(
            self,
            text="Deseja salvar nesta pasta?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        label.pack(padx=24, pady=(20, 6), anchor="w")

        path_frame = ctk.CTkFrame(self, fg_color="#182330", corner_radius=8)
        path_frame.pack(fill="x", padx=24, pady=(0, 16))

        path_lbl = ctk.CTkLabel(
            path_frame,
            text=current_path,
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8",
            anchor="w",
            wraplength=410,
            justify="left",
        )
        path_lbl.pack(padx=12, pady=10, fill="x")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))

        keep = ctk.CTkButton(
            actions,
            text="Manter Pasta",
            command=self._keep,
            width=140,
            height=38,
            font=ctk.CTkFont(weight="bold"),
        )
        keep.pack(side="right")

        change = ctk.CTkButton(
            actions,
            text="Escolher Outra",
            command=self._change,
            width=140,
            height=38,
            fg_color="#1f2d3d",
            hover_color="#29384f",
        )
        change.pack(side="right", padx=(0, 12))

        self.protocol("WM_DELETE_WINDOW", self._keep)
        self.center_on_parent()

    def _keep(self):
        self.destroy()
        self.on_keep()

    def _change(self):
        self.destroy()
        self.on_change()


class ProgressDialog(BaseDialog):
    def __init__(self, master, title: str = "Baixando Conteúdo..."):
        super().__init__(master, title, 540, 260)
        self.is_paused = False
        self.on_pause_cb = None
        self.on_cancel_cb = None

        # Título / Etapa
        self.title_label = ctk.CTkLabel(
            self,
            text="Preparando download...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        self.title_label.pack(padx=24, pady=(20, 6), fill="x")

        # Barra de Progresso
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate", height=16, corner_radius=8)
        self.progress_bar.pack(padx=24, pady=(8, 8), fill="x")
        self.progress_bar.set(0.0)

        # Frame de Informações (Porcentagem + Detalhes)
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(padx=24, pady=(0, 12), fill="x")

        self.percent_label = ctk.CTkLabel(
            info_frame,
            text="0%",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
            anchor="w",
        )
        self.percent_label.pack(side="left")

        self.details_label = ctk.CTkLabel(
            info_frame,
            text="Iniciando conexão...",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            anchor="e",
        )
        self.details_label.pack(side="right")

        # Status inferior
        self.status_label = ctk.CTkLabel(
            self,
            text="Aguardando resposta do servidor...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
            anchor="w",
        )
        self.status_label.pack(padx=24, pady=(0, 14), fill="x")

        # Botões de Ação
        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.pack(padx=24, pady=(0, 18), fill="x")

        self.cancel_button = ctk.CTkButton(
            self.actions,
            text="Cancelar",
            width=130,
            height=36,
            fg_color="#dc2626",
            hover_color="#ef4444",
            command=self._on_cancel_click,
            font=ctk.CTkFont(weight="bold"),
        )
        self.cancel_button.pack(side="right")

        self.pause_button = ctk.CTkButton(
            self.actions,
            text="Pausar",
            width=130,
            height=36,
            fg_color="#1f2d3d",
            hover_color="#29384f",
            command=self._on_pause_click,
            font=ctk.CTkFont(weight="bold"),
        )
        self.pause_button.pack(side="right", padx=(0, 12))

        self.protocol("WM_DELETE_WINDOW", self._on_cancel_click)
        self.center_on_parent()

    def set_callbacks(self, on_pause=None, on_cancel=None):
        self.on_pause_cb = on_pause
        self.on_cancel_cb = on_cancel

    def _on_pause_click(self):
        if self.on_pause_cb is not None:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_button.configure(text="Retomar", fg_color="#16a34a", hover_color="#22c55e")
                self.status_label.configure(text="Download pausado pelo usuário.")
            else:
                self.pause_button.configure(text="Pausar", fg_color="#1f2d3d", hover_color="#29384f")
                self.status_label.configure(text="Retomando download...")
            self.on_pause_cb(self.is_paused)

    def _on_cancel_click(self):
        self.status_label.configure(text="Cancelando download...")
        if self.on_cancel_cb is not None:
            self.on_cancel_cb()

    def update_progress(self, info: ProgressInfo):
        if not self.winfo_exists():
            return
        
        norm_val = max(0.0, min(1.0, info.percent / 100.0))
        self.progress_bar.set(norm_val)
        self.percent_label.configure(text=f"{info.percent:.1f}%")
        
        details = []
        if info.speed:
            details.append(info.speed)
        if info.eta:
            details.append(f"Restante: {info.eta}")
        if info.total_size:
            details.append(f"Total: {info.total_size}")
            
        self.details_label.configure(text=" | ".join(details) if details else "")
        
        if info.status_text:
            self.status_label.configure(text=info.status_text)
            
        self.update_idletasks()

    def set_status(self, message: str):
        if self.winfo_exists():
            self.status_label.configure(text=message)
            self.update_idletasks()

    def close(self):
        if self.winfo_exists():
            self.destroy()


class CustomNameDialog(BaseDialog):
    def __init__(self, master, on_confirm, on_cancel, video_title: str = ""):
        super().__init__(master, "Nome Personalizado", 500, 230)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        label = ctk.CTkLabel(
            self,
            text="Digite o nome desejado para o arquivo (sem extensão):",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        label.pack(padx=24, pady=(20, 8), anchor="w")

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=f"Ex: {video_title or 'meu_video'}",
            height=42,
            border_width=1,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
        )
        self.entry.pack(padx=24, pady=(0, 20), fill="x")
        self.entry.focus()

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))

        confirm = ctk.CTkButton(
            actions,
            text="Confirmar",
            command=self._confirm,
            width=140,
            height=38,
            font=ctk.CTkFont(weight="bold"),
        )
        confirm.pack(side="right")

        cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            command=self._cancel,
            width=120,
            height=38,
            fg_color="#2d3748",
            hover_color="#374151",
        )
        cancel.pack(side="right", padx=(0, 12))

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.center_on_parent()
        self.bind("<Return>", lambda e: self._confirm())

    def _confirm(self):
        result = self.entry.get().strip()
        self.destroy()
        if result:
            self.on_confirm(result)
        else:
            self.on_cancel()

    def _cancel(self):
        self.destroy()
        self.on_cancel()
