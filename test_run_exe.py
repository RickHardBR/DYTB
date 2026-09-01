import subprocess
import time
import sys

print("[TESTE] Iniciando DYTB.exe na raiz...")
proc = subprocess.Popen([r"j:\RickHardBR\DYTB\DYTB.exe"])
time.sleep(3)

poll = proc.poll()
if poll is None:
    print("[SUCESSO] DYTB.exe está rodando normalmente e a interface está ativa!")
    proc.terminate()
else:
    print(f"[ERRO] Processo encerrou com código {poll}")
    sys.exit(1)

