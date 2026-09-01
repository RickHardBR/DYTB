from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path


LOG_DIR = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "DYTB"
LOG_DIR.mkdir(parents=True, exist_ok=True)
STARTUP_LOG = LOG_DIR / "startup.log"


def log(msg: str) -> None:
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(STARTUP_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path


def main() -> None:
    # Limpa log anterior
    try:
        with open(STARTUP_LOG, "w", encoding="utf-8") as f:
            f.write(f"=== DYTB Startup Log - {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    except Exception:
        pass

    log("Iniciando main()...")
    log(f"sys.executable: {sys.executable}")
    log(f"sys.argv: {sys.argv}")
    log(f"Frozen: {getattr(sys, 'frozen', False)}")

    try:
        log("Importando customtkinter e MainWindow...")
        import customtkinter as ctk
        from ui.main_window import MainWindow
        log("Imports concluídos com sucesso.")

        log("Configurando tema do CustomTkinter...")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        log("Criando instância de CTk()...")
        root = ctk.CTk()
        log("CTk() criado com sucesso.")

        root.title("DYTB Downloader")

        # Centralizar na tela
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        win_w, win_h = 860, 700
        x = max(40, (screen_w - win_w) // 2)
        y = max(40, (screen_h - win_h) // 2)
        root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        root.minsize(760, 620)
        root.configure(fg_color="#0b1118")
        log(f"Geometria configurada: {win_w}x{win_h}+{x}+{y}")

        # Ícone
        icon_path = get_resource_path("DW.ico")
        if icon_path.exists():
            try:
                root.iconbitmap(str(icon_path))
                log(f"Ícone carregado: {icon_path}")
            except Exception as e:
                log(f"Aviso ao carregar ícone: {e}")

        log("Construindo MainWindow...")
        MainWindow(root)
        log("MainWindow construída com sucesso.")

        log("Forçando atualização e visibilidade...")
        root.update_idletasks()
        root.deiconify()
        root.lift()
        root.focus_force()
        log("Visibilidade aplicada. Entrando no mainloop()...")

        root.mainloop()
        log("mainloop() finalizado normalmente.")

    except Exception as e:
        err_msg = traceback.format_exc()
        log(f"ERRO CRÍTICO NA INICIALIZAÇÃO:\n{err_msg}")

        try:
            import tkinter as tk
            import tkinter.messagebox as mb

            err_root = tk.Tk()
            err_root.withdraw()
            mb.showerror(
                "Erro ao Iniciar DYTB",
                f"Ocorreu um erro ao abrir a aplicação:\n\n{e}\n\nDetalhes gravados em:\n{STARTUP_LOG}",
            )
            err_root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
