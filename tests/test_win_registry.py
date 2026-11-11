from unittest.mock import MagicMock, patch
import pytest
from docforge_pdf.core import win_registry


def test_win_registry_non_windows_behavior():
    # If not on Windows (such as Linux CI/Dev)
    if not win_registry.is_windows():
        assert win_registry.is_context_menu_registered() is False
        ok, msg = win_registry.register_context_menu()
        assert ok is False
        assert "Windows" in msg

        ok, msg = win_registry.unregister_context_menu()
        assert ok is False
        assert "Windows" in msg


def test_get_default_command_prefix():
    prefix = win_registry.get_default_command_prefix()
    assert isinstance(prefix, str)
    assert len(prefix) > 0
    assert "main.py" in prefix or "python" in prefix.lower()


def test_win_registry_mocked_windows():
    mock_winreg = MagicMock()
    mock_winreg.HKEY_CURRENT_USER = "HKCU"
    mock_winreg.REG_SZ = 1

    created_keys = {}

    def mock_create_key(root, subkey):
        created_keys[f"{root}\\{subkey}"] = {}
        mock_handle = MagicMock()
        return mock_handle

    mock_winreg.CreateKey.side_effect = mock_create_key

    with patch.object(win_registry, "winreg", mock_winreg), \
         patch.object(win_registry, "sys") as mock_sys:
        mock_sys.platform = "win32"
        mock_sys.executable = "C:\\Python\\python.exe"
        mock_sys.frozen = False

        assert win_registry.is_windows() is True

        ok, msg = win_registry.register_context_menu(app_path='"C:\\DocForge\\DocForge.exe"')
        assert ok is True
        assert "sucesso" in msg.lower()

        # Check that PDF shell key and Directory shell key were touched
        assert any(win_registry.PDF_SHELL_KEY in k for k in created_keys)
        assert any(win_registry.DIR_SHELL_KEY in k for k in created_keys)
