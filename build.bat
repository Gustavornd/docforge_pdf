@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo               DocForge PDF - Compilacao com PyInstaller
echo ======================================================================

REM 1. Ativar ambiente virtual se disponivel
if exist "test_venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual 'test_venv'...
    call test_venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual 'venv'...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual '.venv'...
    call .venv\Scripts\activate.bat
) else (
    echo [*] Nenhum ambiente virtual encontrado em test_venv/venv/.venv. Utilizando Python do sistema.
)

REM 2. Verificar presenca do Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao foi encontrado no PATH do sistema.
    pause
    exit /b 1
)

REM 3. Instalar/Atualizar dependencias necessarias
echo [*] Instalando/atualizando dependencias de requirements.txt e pyinstaller...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM 4. Limpeza de builds anteriores
if exist "dist\DocForge PDF" (
    echo [*] Removendo build anterior em dist\DocForge PDF...
    rmdir /s /q "dist\DocForge PDF"
)
if exist "build" (
    echo [*] Limpando pasta build temporaria...
    rmdir /s /q "build"
)

REM 5. Executar compilacao com PyInstaller (--onedir --noconsole)
echo [*] Iniciando compilacao PyInstaller (--onedir --noconsole)...
pyinstaller --noconfirm ^
    --onedir ^
    --noconsole ^
    --name "DocForge PDF" ^
    --collect-all customtkinter ^
    --collect-all pymupdf ^
    --add-data "docforge_pdf;docforge_pdf" ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo   [SUCESSO] Compilacao concluida com sucesso!
    echo   Pasta de distribuicao gerada em:
    echo   dist\DocForge PDF\
    echo.
    echo   Executavel: dist\DocForge PDF\DocForge PDF.exe
    echo ======================================================================
) else (
    echo.
    echo [ERRO] Falha durante a geracao do executavel com PyInstaller.
)

pause
