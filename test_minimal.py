#!/usr/bin/env python
"""
Teste minimalista - apenas janela pura
"""
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("DYTB Downloader - TESTE")
root.geometry("820x560")
root.configure(fg_color="#0b0f14")

label = ctk.CTkLabel(root, text="Se voce ve isto, o problema foi resolvido!", font=ctk.CTkFont(size=20))
label.pack(padx=20, pady=20)

button = ctk.CTkButton(root, text="Fechar", command=root.quit)
button.pack(padx=20, pady=10)

print("[TEST] Janela criada - iniciando mainloop...")
root.mainloop()
print("[TEST] Mainloop finalizado")
