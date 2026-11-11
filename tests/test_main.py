import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch
import pymupdf as fitz
import pytest

from docforge_pdf import main as docforge_main


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _create_sample_pdf(filepath: str, pages: int = 1):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    doc.save(filepath)
    doc.close()


def test_expand_and_normalize_inputs_empty():
    res = docforge_main.expand_and_normalize_inputs([])
    assert res == []
    res2 = docforge_main.expand_and_normalize_inputs(["", "   "])
    assert res2 == []


def test_expand_and_normalize_inputs_files(temp_dir):
    f1 = os.path.join(temp_dir, "Doc_001.pdf")
    f2 = os.path.join(temp_dir, "Doc_002.pdf")
    txt = os.path.join(temp_dir, "notes.txt")
    _create_sample_pdf(f1)
    _create_sample_pdf(f2)
    with open(txt, "w") as fp:
        fp.write("hello")

    inputs = [f1, f2, txt, os.path.join(temp_dir, "non_existent.pdf"), f1]
    expanded = docforge_main.expand_and_normalize_inputs(inputs)

    assert len(expanded) == 2
    assert expanded[0] == os.path.abspath(f1)
    assert expanded[1] == os.path.abspath(f2)


def test_expand_and_normalize_inputs_directory(temp_dir):
    f1 = os.path.join(temp_dir, "Scan_10.pdf")
    f2 = os.path.join(temp_dir, "Scan_2.pdf")
    f3 = os.path.join(temp_dir, "Scan_1.pdf")
    _create_sample_pdf(f1)
    _create_sample_pdf(f2)
    _create_sample_pdf(f3)

    expanded = docforge_main.expand_and_normalize_inputs([temp_dir])
    assert len(expanded) == 3
    # Verify natural order inside directory: Scan_1, Scan_2, Scan_10
    names = [os.path.basename(p) for p in expanded]
    assert names == ["Scan_1.pdf", "Scan_2.pdf", "Scan_10.pdf"]


def test_execute_fast_merge_success(temp_dir):
    f1 = os.path.join(temp_dir, "Contrato_001.pdf")
    f2 = os.path.join(temp_dir, "Contrato_002.pdf")
    _create_sample_pdf(f1, pages=2)
    _create_sample_pdf(f2, pages=3)

    with patch.object(docforge_main, "reveal_in_explorer") as mock_reveal:
        ok = docforge_main.execute_fast_merge([f2, f1])
        assert ok is True
        mock_reveal.assert_called_once()

    expected_out = os.path.join(temp_dir, "Contrato_Completo.pdf")
    assert os.path.isfile(expected_out)

    doc = fitz.open(expected_out)
    assert doc.page_count == 5
    doc.close()


def test_execute_fast_merge_empty():
    assert docforge_main.execute_fast_merge([]) is False


def test_main_cli_fast_merge_scanner_sequence(temp_dir):
    f1 = os.path.join(temp_dir, "Scan_001.pdf")
    f2 = os.path.join(temp_dir, "Scan_002.pdf")
    _create_sample_pdf(f1)
    _create_sample_pdf(f2)

    with patch.object(docforge_main, "reveal_in_explorer"):
        ret = docforge_main.main(["--action", "fast-merge", f1, f2, "--debounce", "0.01"])
        assert ret == 0

    expected_out = os.path.join(temp_dir, "Scan_Completo.pdf")
    assert os.path.isfile(expected_out)


def test_main_cli_fast_merge_non_scanner_sequence_launches_gui(temp_dir):
    f1 = os.path.join(temp_dir, "RG.pdf")
    f2 = os.path.join(temp_dir, "CPF.pdf")
    _create_sample_pdf(f1)
    _create_sample_pdf(f2)

    mock_app = MagicMock()
    with patch("docforge_pdf.main.DocForgeApp", return_value=mock_app) as mock_app_cls:
        ret = docforge_main.main(["--action", "fast-merge", f1, f2, "--debounce", "0.01"])
        assert ret == 0
        mock_app_cls.assert_called_once()
        args, kwargs = mock_app_cls.call_args
        assert kwargs["initial_action"] == "merge"
        assert len(kwargs["initial_files"]) == 2
        mock_app.mainloop.assert_called_once()


def test_main_cli_split_launches_gui(temp_dir):
    f1 = os.path.join(temp_dir, "Documento.pdf")
    _create_sample_pdf(f1, pages=4)

    mock_app = MagicMock()
    with patch("docforge_pdf.main.DocForgeApp", return_value=mock_app) as mock_app_cls:
        ret = docforge_main.main(["--action", "split", f1, "--debounce", "0.01"])
        assert ret == 0
        mock_app_cls.assert_called_once()
        args, kwargs = mock_app_cls.call_args
        assert kwargs["initial_action"] == "split"
        assert len(kwargs["initial_files"]) == 1
        mock_app.mainloop.assert_called_once()


def test_main_cli_merge_folder_expands(temp_dir):
    f1 = os.path.join(temp_dir, "Doc_1.pdf")
    f2 = os.path.join(temp_dir, "Doc_2.pdf")
    _create_sample_pdf(f1)
    _create_sample_pdf(f2)

    mock_app = MagicMock()
    with patch("docforge_pdf.main.DocForgeApp", return_value=mock_app) as mock_app_cls:
        ret = docforge_main.main(["--action", "merge-folder", temp_dir, "--debounce", "0.01"])
        assert ret == 0
        mock_app_cls.assert_called_once()
        args, kwargs = mock_app_cls.call_args
        assert kwargs["initial_action"] == "merge"
        assert len(kwargs["initial_files"]) == 2
