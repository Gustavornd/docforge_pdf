@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo           DocForge PDF - Compilacao Completa do Setup / Instalador
echo ======================================================================

REM 1. Ativar ambiente virtual se disponivel
if exist "venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual 'venv'...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [*] Ativando ambiente virtual '.venv'...
    call .venv\Scripts\activate.bat
) else (
    echo [*] Utilizando interpretador Python do sistema.
)

REM 2. Verificar presenca do Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao foi encontrado no PATH do sistema.
    pause
    exit /b 1
)

REM 3. Localizar o compilador do Inno Setup (ISCC.exe)
set "ISCC_PATH="
where iscc >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "ISCC_PATH=iscc"
) else if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

if "%ISCC_PATH%"=="" (
    echo [ERRO] Compilador Inno Setup (ISCC.exe) nao foi encontrado.
    echo Instale o Inno Setup via winget: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

REM 4. Instalar/atualizar dependencias do projeto e PyInstaller
echo [*] Verificando dependencias...
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller --quiet

REM 5. Limpar pasta temporaria de build
if exist "build" rmdir /s /q "build"

REM 6. Compilar executavel com PyInstaller
echo [*] Etapa 1/2: Compilando binarios com PyInstaller...
pyinstaller --noconfirm ^
    --onedir ^
    --noconsole ^
    --name "DocForge PDF" ^
    --collect-all customtkinter ^
    --collect-all pymupdf ^
    --add-data "docforge_pdf;docforge_pdf" ^
    main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha durante a compilacao com PyInstaller.
    pause
    exit /b 1
)

REM 7. Compilar o Instalador com Inno Setup
echo.
echo [*] Etapa 2/2: Gerando instalador Setup com Inno Setup...
"%ISCC_PATH%" "installer\setup.iss"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo   [SUCESSO] Instalador gerado com sucesso!
    echo   Local do arquivo:
    echo   dist_installer\DocForge_PDF_Setup_v1.0.0.exe
    echo ======================================================================
) else (
    echo.
    echo [ERRO] Falha ao compilar instalador com o Inno Setup.
)

pause
