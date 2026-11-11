import pytest
from docforge_pdf.core.sorter import (
    natural_sort,
    natural_sort_key,
    is_scanner_sequence,
    detect_scanner_sequence,
    suggest_output_filename,
)


def test_natural_sort_numeric():
    files = [
        "Arquivo_10.pdf",
        "Arquivo_1.pdf",
        "Arquivo_2.pdf",
        "Arquivo_20.pdf",
        "Arquivo_3.pdf"
    ]
    sorted_files = natural_sort(files)
    assert sorted_files == [
        "Arquivo_1.pdf",
        "Arquivo_2.pdf",
        "Arquivo_3.pdf",
        "Arquivo_10.pdf",
        "Arquivo_20.pdf"
    ]


def test_natural_sort_mixed_case_and_paths():
    files = [
        "/docs/Scan_b.pdf",
        "/docs/scan_a.pdf",
        "/docs/Scan_10.pdf",
        "/docs/scan_2.pdf"
    ]
    sorted_files = natural_sort(files)
    assert sorted_files == [
        "/docs/scan_2.pdf",
        "/docs/Scan_10.pdf",
        "/docs/scan_a.pdf",
        "/docs/Scan_b.pdf"
    ]


def test_natural_sort_empty_and_none():
    assert natural_sort([]) == []
    assert natural_sort_key("") == []


def test_detect_scanner_sequence_standard():
    files = ["Doc_001.pdf", "Doc_002.pdf", "Doc_003.pdf"]
    is_seq, prefix = detect_scanner_sequence(files)
    assert is_seq is True
    assert prefix == "Doc"
    assert is_scanner_sequence(files) is True


def test_detect_scanner_sequence_hyphen():
    files = ["Contrato-1.pdf", "Contrato-2.pdf"]
    is_seq, prefix = detect_scanner_sequence(files)
    assert is_seq is True
    assert prefix == "Contrato"


def test_detect_scanner_sequence_spaces():
    files = ["Página 01.pdf", "Página 02.pdf"]
    is_seq, prefix = detect_scanner_sequence(files)
    assert is_seq is True
    assert prefix == "Página"


def test_detect_scanner_sequence_pure_numbers():
    files = ["001.pdf", "002.pdf", "003.pdf"]
    is_seq, prefix = detect_scanner_sequence(files)
    assert is_seq is True
    assert prefix == ""


def test_detect_scanner_sequence_different_prefixes():
    files = ["RG_01.pdf", "CPF_02.pdf"]
    is_seq, prefix = detect_scanner_sequence(files)
    assert is_seq is False
    assert prefix == ""
    assert is_scanner_sequence(files) is False


def test_detect_scanner_sequence_without_numbers():
    files = ["RG.pdf", "CPF.pdf", "Comprovante.pdf"]
    assert is_scanner_sequence(files) is False


def test_detect_scanner_sequence_single_file():
    assert is_scanner_sequence(["Doc_001.pdf"]) is False


def test_detect_scanner_sequence_duplicates():
    files = ["Doc_001.pdf", "Doc_001.pdf"]
    assert is_scanner_sequence(files) is False


def test_detect_scanner_sequence_cross_folder():
    files = ["/dirA/Doc_001.pdf", "/dirB/Doc_002.pdf"]
    assert is_scanner_sequence(files) is False


def test_suggest_output_filename():
    # Sequence with prefix
    assert suggest_output_filename(["Doc_001.pdf", "Doc_002.pdf"]) == "Doc_Completo.pdf"

    # Sequence with pure numbers
    assert suggest_output_filename(["001.pdf", "002.pdf"]) == "Documentos_Completo.pdf"

    # Common prefix but not scanner sequence
    assert suggest_output_filename(["Contrato_ClienteA.pdf", "Contrato_ClienteB.pdf"]) == "Contrato_Cliente_Completo.pdf"
    assert suggest_output_filename(["Contrato_A.pdf", "Contrato_B.pdf"]) == "Contrato_Completo.pdf"

    # Disparate names
    assert suggest_output_filename(["RG.pdf", "CPF.pdf"]) == "Documentos_Unificados.pdf"

    # Empty list
    assert suggest_output_filename([]) == "Documentos_Unificados.pdf"
