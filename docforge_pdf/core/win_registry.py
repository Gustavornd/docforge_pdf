"""
Módulo de integração com o Registro do Windows (HKCU).
Permite registrar e remover ações de menu de contexto no Windows Explorer
sem exigir permissões de Administrador.
"""

import os
import subprocess
import sys
from typing import Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None


# Chaves do Registro em HKCU
PDF_SHELL_KEY = r"Software\Classes\SystemFileAssociations\.pdf\shell\DocForge"
DIR_SHELL_KEY = r"Software\Classes\Directory\shell\DocForge"
DIR_BG_SHELL_KEY = r"Software\Classes\Directory\Background\shell\DocForge"


def is_windows() -> bool:
    """Verifica se o ambiente de execução é Windows com winreg disponível."""
    return sys.platform == "win32" and winreg is not None


def get_default_command_prefix() -> str:
    """
    Retorna o comando base para execução do DocForge PDF.
    Se o app estiver empacotado via PyInstaller, usa o executável (.exe).
    Caso contrário, usa o interpretador Python (preferindo pythonw.exe para suprimir console)
    apontando para main.py.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    python_exe = sys.executable
    if sys.platform == "win32":
        py_dir = os.path.dirname(python_exe)
        pythonw_candidate = os.path.join(py_dir, "pythonw.exe")
        if os.path.isfile(pythonw_candidate):
            python_exe = pythonw_candidate

    # Determinar caminho absoluto para o main.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_candidate = os.path.normpath(os.path.join(current_dir, "..", "main.py"))
    if not os.path.isfile(main_candidate):
        root_candidate = os.path.normpath(os.path.join(current_dir, "..", "..", "main.py"))
        if os.path.isfile(root_candidate):
            main_candidate = root_candidate

    return f'"{python_exe}" "{main_candidate}"'


def is_context_menu_registered() -> bool:
    """Verifica se o menu de contexto do DocForge está atualmente registrado no HKCU."""
    if not is_windows():
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY, 0, winreg.KEY_READ):
            return True
    except OSError:
        return False


def _set_reg_value(root_key, subkey_path: str, value_name: Optional[str], value_data: str) -> None:
    """Cria a chave (se não existir) e define um valor string."""
    with winreg.CreateKey(root_key, subkey_path) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value_data)


def _delete_key_recursive(root_key, subkey_path: str) -> None:
    """Deleta recursivamente uma chave e todas as suas subchaves."""
    try:
        with winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    _delete_key_recursive(root_key, f"{subkey_path}\\{sub}")
                except OSError:
                    break
        winreg.DeleteKey(root_key, subkey_path)
    except OSError:
        pass


def register_context_menu(app_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Registra as opções do DocForge no Menu de Contexto do Windows:
    1. Para arquivos .pdf (menu cascata ordenado com 3 ações).
    2. Para pastas e plano de fundo de pastas (ação de unir todos os PDFs da pasta).
    """
    if not is_windows():
        return False, "A integração com o Registro está disponível apenas no ambiente Windows."

    try:
        cmd_prefix = app_path if app_path else get_default_command_prefix()
        clean_app = app_path.strip('"') if app_path else ""
        if clean_app and clean_app.lower().endswith(".exe"):
            exe_icon = clean_app
        else:
            exe_icon = sys.executable

        # 1. Configurar entrada para arquivos .pdf (Menu Cascata)
        _set_reg_value(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY, None, "DocForge PDF")
        _set_reg_value(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY, "MUIVerb", "DocForge PDF")
        _set_reg_value(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY, "SubCommands", "")
        _set_reg_value(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY, "Icon", exe_icon)

        # Subcomando 1: Juntar PDFs no DocForge
        sub1 = f"{PDF_SHELL_KEY}\\shell\\01_merge"
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub1, None, "Juntar PDFs no DocForge")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub1, "MUIVerb", "Juntar PDFs no DocForge")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub1, "Icon", exe_icon)
        _set_reg_value(winreg.HKEY_CURRENT_USER, f"{sub1}\\command", None, f'{cmd_prefix} --action merge "%1"')

        # Subcomando 2: Merge Rápido (Auto-Ordem)
        sub2 = f"{PDF_SHELL_KEY}\\shell\\02_fast_merge"
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub2, None, "Merge Rápido (Auto-Ordem)")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub2, "MUIVerb", "Merge Rápido (Auto-Ordem)")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub2, "Icon", exe_icon)
        _set_reg_value(winreg.HKEY_CURRENT_USER, f"{sub2}\\command", None, f'{cmd_prefix} --action fast-merge "%1"')

        # Subcomando 3: Separar / Extrair Páginas
        sub3 = f"{PDF_SHELL_KEY}\\shell\\03_split"
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub3, None, "Separar / Extrair Páginas")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub3, "MUIVerb", "Separar / Extrair Páginas")
        _set_reg_value(winreg.HKEY_CURRENT_USER, sub3, "Icon", exe_icon)
        _set_reg_value(winreg.HKEY_CURRENT_USER, f"{sub3}\\command", None, f'{cmd_prefix} --action split "%1"')

        # 2. Configurar entrada para Pastas (Directory)
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_SHELL_KEY, None, "DocForge: Juntar todos os PDFs desta pasta")
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_SHELL_KEY, "MUIVerb", "DocForge: Juntar todos os PDFs desta pasta")
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_SHELL_KEY, "Icon", exe_icon)
        _set_reg_value(winreg.HKEY_CURRENT_USER, f"{DIR_SHELL_KEY}\\command", None, f'{cmd_prefix} --action merge-folder "%1"')

        # 3. Configurar entrada para Plano de Fundo de Pastas (Directory Background)
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_BG_SHELL_KEY, None, "DocForge: Juntar todos os PDFs desta pasta")
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_BG_SHELL_KEY, "MUIVerb", "DocForge: Juntar todos os PDFs desta pasta")
        _set_reg_value(winreg.HKEY_CURRENT_USER, DIR_BG_SHELL_KEY, "Icon", exe_icon)
        _set_reg_value(winreg.HKEY_CURRENT_USER, f"{DIR_BG_SHELL_KEY}\\command", None, f'{cmd_prefix} --action merge-folder "%V"')

        return True, "Menu de contexto do Windows registrado com sucesso!"
    except Exception as e:
        return False, f"Falha ao registrar menu de contexto: {e}"


def unregister_context_menu() -> Tuple[bool, str]:
    """Remove todas as entradas do DocForge do Menu de Contexto do Windows no HKCU."""
    if not is_windows():
        return False, "A integração com o Registro está disponível apenas no ambiente Windows."

    try:
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, PDF_SHELL_KEY)
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, DIR_SHELL_KEY)
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, DIR_BG_SHELL_KEY)
        return True, "Menu de contexto removido com sucesso!"
    except Exception as e:
        return False, f"Falha ao remover menu de contexto: {e}"


def reveal_in_explorer(target_path: str) -> bool:
    """
    Abre o explorador de arquivos destacando o arquivo gerado ou abrindo a pasta de destino.
    Suporta Windows (explorer /select), Linux (xdg-open) e macOS (open -R).
    """
    if not target_path or not os.path.exists(target_path):
        return False

    abs_path = os.path.abspath(target_path)
    try:
        if sys.platform == "win32":
            norm_path = os.path.normpath(abs_path)
            if os.path.isfile(norm_path):
                subprocess.Popen(f'explorer /select,"{norm_path}"')
            else:
                os.startfile(norm_path)
            return True
        elif sys.platform == "darwin":
            if os.path.isfile(abs_path):
                subprocess.Popen(["open", "-R", abs_path])
            else:
                subprocess.Popen(["open", abs_path])
            return True
        else:
            folder = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
            subprocess.Popen(["xdg-open", folder])
            return True
    except Exception:
        return False

