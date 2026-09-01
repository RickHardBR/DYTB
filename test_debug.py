#!/usr/bin/env python
"""
Teste de debug - mostra exatamente o que esta acontecendo
"""
import customtkinter as ctk
import sys

print("[DEBUG 1] Inicio do script")
sys.stdout.flush()

try:
    print("[DEBUG 2] Importando customtkinter...")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    print("[DEBUG 3] Configuracoes de tema OK")
    sys.stdout.flush()
    
    print("[DEBUG 4] Criando janela...")
    root = ctk.CTk()
    print("[DEBUG 5] Janela criada")
    sys.stdout.flush()
    
    print("[DEBUG 6] Configurando geometria...")
    root.geometry("800x400+100+100")  # x+y posicionamento explícito
    root.title("DYTB Debug")
    print("[DEBUG 7] Geometria configurada: 800x400+100+100")
    sys.stdout.flush()
    
    print("[DEBUG 8] Criando widgets...")
    label = ctk.CTkLabel(root, text="DYTB DOWNLOADER", font=ctk.CTkFont(size=24, weight="bold"))
    label.pack(padx=20, pady=40)
    
    label2 = ctk.CTkLabel(root, text="Se voce ve este texto, FUNCIONOU!", font=ctk.CTkFont(size=16))
    label2.pack(padx=20, pady=20)
    
    button = ctk.CTkButton(root, text="Fechar", command=root.quit, height=40)
    button.pack(padx=20, pady=20)
    print("[DEBUG 9] Widgets criados")
    sys.stdout.flush()
    
    print("[DEBUG 10] Chamando deiconify...")
    root.deiconify()
    print("[DEBUG 11] Deiconify OK")
    sys.stdout.flush()
    
    print("[DEBUG 12] Chamando focus_force...")
    root.focus_force()
    print("[DEBUG 13] Focus OK")
    sys.stdout.flush()
    
    print("[DEBUG 14] Iniciando mainloop...")
    sys.stdout.flush()
    root.mainloop()
    print("[DEBUG 15] Mainloop finalizado")
    
except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
