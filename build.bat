@echo off
echo ========================================================
echo        DYTB Downloader - Build Automatizado
echo ========================================================
echo.

echo [1/4] Instalando dependencias Python...
python -m pip install -r requirements.txt

echo.
echo [2/4] Compilando executavel portatil com PyInstaller...
pyinstaller --noconfirm DYTB.spec

echo.
echo [3/4] Copiando executavel para a raiz do projeto...
copy /Y "dist\DYTB.exe" "DYTB.exe"

echo.
echo [4/4] Gerando instalador DYTB_Setup.exe com Inno Setup...
set "ISCC_PATH=C:\Users\RickHard\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%ISCC_PATH%" (
    "%ISCC_PATH%" "installer.iss"
    copy /Y "dist\DYTB_Setup.exe" "DYTB_Setup.exe"
    echo.
    echo ========================================================
    echo  Build concluido com SUCESSO!
    echo  1. Executavel Portatil: DYTB.exe
    echo  2. Instalador Windows:   DYTB_Setup.exe
    echo ========================================================
) else (
    echo.
    echo [AVISO] Inno Setup (ISCC.exe) nao foi encontrado.
    echo Apenas a versao portatil DYTB.exe foi gerada.
)

echo.
pause
