@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo               DocForge PDF - Compilacao com PyInstaller
echo ======================================================================

REM Navegar para o diretorio do script
cd /d "%~dp0"

REM 1. Verificar presenca do Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao foi encontrado no PATH do sistema.
    pause
    exit /b 1
)

REM 2. Instalar dependencias
python -m pip install -r ..\requirements.txt 2>nul || python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM 3. Executar compilacao com PyInstaller (--onedir --noconsole)
echo [*] Iniciando compilacao PyInstaller (--onedir --noconsole)...
pyinstaller --noconfirm ^
    --onedir ^
    --noconsole ^
    --name "DocForge PDF" ^
    --collect-all customtkinter ^
    --collect-all pymupdf ^
    --add-data ".;docforge_pdf" ^
    main.py

pause
