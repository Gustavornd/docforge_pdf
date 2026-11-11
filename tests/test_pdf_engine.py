import os
import tempfile
import pytest
import pymupdf as fitz
from PIL import Image
from docforge_pdf.core.pdf_engine import (
    format_file_size,
    parse_page_query,
    render_page_thumbnail,
    get_pdf_info,
    merge_pdfs,
    split_all_pages,
    extract_pages,
)


def _create_sample_pdf(path: str, page_count: int = 3, password: str = None) -> None:
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), f"Página de Teste {i + 1}", fontsize=20)
    
    if password:
        # Encrypt with owner and user password
        perm = int(
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password, permissions=perm)
    else:
        doc.save(path)
    doc.close()


def test_format_file_size():
    assert format_file_size(500) == "500 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(1024 * 1024 * 3) == "3.00 MB"


def test_parse_page_query_valid():
    query = "1-3, 5, 8-10"
    indices = parse_page_query(query, max_pages=10)
    assert indices == [0, 1, 2, 4, 7, 8, 9]

    # Spaces and single numbers
    query_spaces = " 1 - 2 ,  4 "
    assert parse_page_query(query_spaces, max_pages=5) == [0, 1, 3]


def test_parse_page_query_invalid():
    # Empty query
    with pytest.raises(ValueError, match="Nenhuma página"):
        parse_page_query("", max_pages=5)

    # Out of range (page 6 when max is 5)
    with pytest.raises(ValueError, match="fora dos limites"):
        parse_page_query("6", max_pages=5)

    # Out of range range end
    with pytest.raises(ValueError, match="ultrapassa o total"):
        parse_page_query("1-8", max_pages=5)

    # Inverted range
    with pytest.raises(ValueError, match="maior que o fim"):
        parse_page_query("4-2", max_pages=5)

    # Non-numeric
    with pytest.raises(ValueError, match="inválido"):
        parse_page_query("abc", max_pages=5)


def test_merge_pdfs(tmp_path):
    f1 = str(tmp_path / "doc1.pdf")
    f2 = str(tmp_path / "doc2.pdf")
    out = str(tmp_path / "merged.pdf")

    _create_sample_pdf(f1, page_count=2)
    _create_sample_pdf(f2, page_count=3)

    merge_pdfs([f1, f2], out)

    assert os.path.exists(out)
    merged_doc = fitz.open(out)
    assert merged_doc.page_count == 5
    merged_doc.close()


def test_merge_pdfs_empty():
    with pytest.raises(ValueError, match="vazia"):
        merge_pdfs([], "/dummy/out.pdf")


def test_merge_pdfs_missing_file():
    with pytest.raises(FileNotFoundError):
        merge_pdfs(["/nao/existe/doc.pdf"], "/dummy/out.pdf")


def test_split_all_pages(tmp_path):
    src = str(tmp_path / "multi.pdf")
    _create_sample_pdf(src, page_count=4)

    out_dir = str(tmp_path / "split_output")
    files = split_all_pages(src, out_dir, prefix="Parte")

    assert len(files) == 4
    for idx, f in enumerate(files, start=1):
        assert os.path.exists(f)
        assert f.endswith(f"Parte_{idx:03d}.pdf")
        doc = fitz.open(f)
        assert doc.page_count == 1
        doc.close()


def test_extract_pages_merged(tmp_path):
    src = str(tmp_path / "original.pdf")
    _create_sample_pdf(src, page_count=5)

    out = str(tmp_path / "extracted.pdf")
    res = extract_pages(src, "1, 3-4", out, merge_extracted=True)

    assert len(res) == 1
    assert os.path.exists(out)
    doc = fitz.open(out)
    assert doc.page_count == 3
    doc.close()


def test_extract_pages_separate(tmp_path):
    src = str(tmp_path / "original.pdf")
    _create_sample_pdf(src, page_count=5)

    out_base = str(tmp_path / "custom.pdf")
    res = extract_pages(src, "2, 4", out_base, merge_extracted=False)

    assert len(res) == 2
    for f in res:
        assert os.path.exists(f)
        doc = fitz.open(f)
        assert doc.page_count == 1
        doc.close()


def test_extract_pages_intervals_separate(tmp_path):
    src = str(tmp_path / "multichapter.pdf")
    _create_sample_pdf(src, page_count=10)

    out_base = str(tmp_path / "Chapter.pdf")
    res = extract_pages(src, "1-3, 5, 8-10", out_base, merge_extracted=False)

    # Devem ser gerados exatamente 3 arquivos (um para cada página ou intervalo)
    assert len(res) == 3
    expected_names = ["Chapter_p1-3.pdf", "Chapter_p5.pdf", "Chapter_p8-10.pdf"]
    actual_names = [os.path.basename(f) for f in res]
    assert actual_names == expected_names

    doc1 = fitz.open(res[0])
    assert doc1.page_count == 3
    doc1.close()

    doc2 = fitz.open(res[1])
    assert doc2.page_count == 1
    doc2.close()

    doc3 = fitz.open(res[2])
    assert doc3.page_count == 3
    doc3.close()


def test_parse_page_query_with_semicolon():
    # Suporte a ponto e vírgula na consulta de páginas
    indices = parse_page_query("1-2; 4; 5-6", max_pages=10)
    assert indices == [0, 1, 3, 4, 5]


def test_get_pdf_info_and_thumbnail(tmp_path):
    src = str(tmp_path / "info_test.pdf")
    _create_sample_pdf(src, page_count=3)

    info = get_pdf_info(src, page_number=0)
    assert info["page_count"] == 3
    assert info["is_encrypted"] is False
    assert isinstance(info["thumbnail"], Image.Image)
    assert info["thumbnail"].width > 0
    assert info["thumbnail"].height > 0
    assert "KB" in info["file_size_formatted"] or "B" in info["file_size_formatted"]

    # Teste sem renderização de miniatura (modo ultra-rápido)
    info_fast = get_pdf_info(src, render_thumb=False)
    assert info_fast["thumbnail"] is None
    assert info_fast["page_count"] == 3


def test_encrypted_pdf(tmp_path):
    src = str(tmp_path / "secret.pdf")
    _create_sample_pdf(src, page_count=2, password="mypassword123")

    # get_pdf_info should mark it encrypted
    info = get_pdf_info(src)
    assert info["is_encrypted"] is True

    # merge should raise PermissionError
    out = str(tmp_path / "merged_secret.pdf")
    with pytest.raises(PermissionError, match="protegido por senha"):
        merge_pdfs([src], out)
