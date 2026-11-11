import os
import shutil
import tempfile
import time
from unittest.mock import MagicMock, patch
import pymupdf as fitz
import pytest

from docforge_pdf.ui.app_window import DocForgeApp


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _create_sample_pdf(filepath: str, pages: int = 1):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Sample Page {i + 1}")
    doc.save(filepath)
    doc.close()


@pytest.fixture
def sample_pdfs(temp_dir):
    p1 = os.path.join(temp_dir, "Doc_002.pdf")
    p2 = os.path.join(temp_dir, "Doc_001.pdf")
    p3 = os.path.join(temp_dir, "Doc_010.pdf")
    _create_sample_pdf(p1, pages=2)
    _create_sample_pdf(p2, pages=3)
    _create_sample_pdf(p3, pages=1)
    return [p1, p2, p3]


def test_app_window_init():
    app = DocForgeApp()
    app.withdraw()
    try:
        assert "DocForge" in app.title()
        assert app.tabview.get() == "Juntar (Merge)"
        assert len(app.merge_files) == 0
    finally:
        app.destroy()


def test_merge_add_files_and_selection(sample_pdfs):
    app = DocForgeApp()
    app.withdraw()
    try:
        app._add_files(sample_pdfs)
        assert len(app.merge_files) == 3
        assert len(app.merge_tree.get_children()) == 3

        # Suggested filename should be detected
        sug = app.merge_output_name_var.get()
        assert sug == "Doc_Completo.pdf"

        # Preview label should have filename
        assert "Doc_002.pdf" in app.lbl_merge_info_name.cget("text")

        # Select second item (Doc_001.pdf)
        app.merge_tree.selection_set("1")
        app._on_merge_tree_select()
        assert "Doc_001.pdf" in app.lbl_merge_info_name.cget("text")
    finally:
        app.destroy()


def test_merge_reorder_up_and_down(sample_pdfs):
    app = DocForgeApp(initial_files=sample_pdfs)
    app.withdraw()
    try:
        # Initial order: Doc_002, Doc_001, Doc_010
        assert app.merge_files[0]["filename"] == "Doc_002.pdf"
        assert app.merge_files[1]["filename"] == "Doc_001.pdf"

        # Select index 1 and move UP
        app.merge_tree.selection_set("1")
        app._move_selection_up()

        # Now Doc_001 should be at index 0 and highlighted in Treeview
        assert app.merge_files[0]["filename"] == "Doc_001.pdf"
        assert app.merge_files[1]["filename"] == "Doc_002.pdf"
        assert app.merge_tree.selection() == ("0",)
        assert "Doc_001.pdf" in app.lbl_merge_info_name.cget("text")

        # Now move index 0 DOWN
        app.merge_tree.selection_set("0")
        app._move_selection_down()
        assert app.merge_files[0]["filename"] == "Doc_002.pdf"
        assert app.merge_files[1]["filename"] == "Doc_001.pdf"
        assert app.merge_tree.selection() == ("1",)
        assert "Doc_001.pdf" in app.lbl_merge_info_name.cget("text")
    finally:
        app.destroy()


def test_merge_natural_sort(sample_pdfs):
    app = DocForgeApp(initial_files=sample_pdfs)
    app.withdraw()
    try:
        # Definir nome de arquivo personalizado pelo usuário
        app.merge_output_name_var.set("Meu_Contrato_Especial.pdf")

        # Initial order: Doc_002, Doc_001, Doc_010
        app._sort_files_natural()
        filenames = [item["filename"] for item in app.merge_files]
        assert filenames == ["Doc_001.pdf", "Doc_002.pdf", "Doc_010.pdf"]

        # O nome personalizado digitado pelo usuário NÃO deve ser apagado
        assert app.merge_output_name_var.get() == "Meu_Contrato_Especial.pdf"
    finally:
        app.destroy()


def test_merge_remove_and_clear(sample_pdfs):
    app = DocForgeApp(initial_files=sample_pdfs)
    app.withdraw()
    try:
        assert len(app.merge_files) == 3

        # Select index 1 and remove
        app.merge_tree.selection_set("1")
        app._remove_selected_file()
        assert len(app.merge_files) == 2

        # Clear list
        app._clear_merge_list()
        assert len(app.merge_files) == 0
        assert len(app.merge_tree.get_children()) == 0
        assert app.lbl_merge_info_name.cget("text") == ""
    finally:
        app.destroy()


def test_merge_execution_worker(temp_dir, sample_pdfs):
    app = DocForgeApp(initial_files=sample_pdfs)
    app.withdraw()
    try:
        out_file = "Merged_Test.pdf"
        app.merge_output_dir_var.set(temp_dir)
        app.merge_output_name_var.set(out_file)
        app.auto_open_folder_var.set(False)

        with patch("docforge_pdf.ui.app_window.messagebox.showinfo"):
            # Trigger merge
            app._start_merge_thread()

            # Wait for worker thread to complete
            for _ in range(50):
                if not app.is_merging:
                    break
                time.sleep(0.05)
                app.update()

            if hasattr(app, "_current_worker") and app._current_worker.is_alive():
                app._current_worker.join(timeout=2.0)

            dest_path = os.path.join(temp_dir, out_file)
            assert os.path.isfile(dest_path)
            doc = fitz.open(dest_path)
            # Pages: Doc_002 (2) + Doc_001 (3) + Doc_010 (1) = 6 pages
            assert doc.page_count == 6
            doc.close()
    finally:
        app.destroy()


def test_split_load_and_navigation(temp_dir):
    pdf_path = os.path.join(temp_dir, "MultiPage.pdf")
    _create_sample_pdf(pdf_path, pages=5)

    app = DocForgeApp(initial_files=[pdf_path], initial_action="split")
    app.withdraw()
    try:
        assert app.tabview.get() == "Separar / Extrair (Split)"
        assert app.split_total_pages == 5
        assert app.split_current_page == 0
        assert "MultiPage.pdf" in app.split_source_label_var.get()
        assert app.split_page_indicator_var.get() == "Página 1 de 5"

        # Navigate next
        app._next_split_page()
        assert app.split_current_page == 1
        assert app.split_page_indicator_var.get() == "Página 2 de 5"

        # Navigate prev
        app._prev_split_page()
        assert app.split_current_page == 0

        # Jump to page
        app.split_jump_var.set("4")
        app._jump_to_split_page()
        assert app.split_current_page == 3
        assert app.split_page_indicator_var.get() == "Página 4 de 5"

        # Insert page into query
        app.split_query_var.set("")
        app._insert_current_page_to_query()
        assert app.split_query_var.get() == "4"

        app._insert_current_page_to_query()
        assert app.split_query_var.get() == "4, 4"
    finally:
        app.destroy()


def test_split_extract_ranges_execution(temp_dir):
    pdf_path = os.path.join(temp_dir, "SourceDoc.pdf")
    _create_sample_pdf(pdf_path, pages=6)

    app = DocForgeApp(initial_files=[pdf_path], initial_action="split")
    app.withdraw()
    try:
        app.auto_open_folder_var.set(False)
        app.split_mode_var.set("extract_ranges")
        app.split_query_var.set("1-2, 5")
        app.split_merge_extracted_var.set(True)
        app.split_output_dir_var.set(temp_dir)
        app.split_output_name_var.set("Extracted.pdf")

        with patch("docforge_pdf.ui.app_window.messagebox.showinfo"):
            app._start_split_thread()

            for _ in range(50):
                if not app.is_splitting:
                    break
                time.sleep(0.05)
                app.update()

            if hasattr(app, "_current_worker") and app._current_worker.is_alive():
                app._current_worker.join(timeout=2.0)

            out_path = os.path.join(temp_dir, "Extracted.pdf")
            assert os.path.isfile(out_path)
            doc = fitz.open(out_path)
            assert doc.page_count == 3
            doc.close()
    finally:
        app.destroy()


def test_split_extract_ranges_separate_execution(temp_dir):
    pdf_path = os.path.join(temp_dir, "Chapters.pdf")
    _create_sample_pdf(pdf_path, pages=6)

    app = DocForgeApp(initial_files=[pdf_path], initial_action="split")
    app.withdraw()
    try:
        app.auto_open_folder_var.set(False)
        app.split_mode_var.set("extract_ranges")
        app.split_query_var.set("1-2, 5")
        app.split_merge_extracted_var.set(False)
        app.split_output_dir_var.set(temp_dir)
        app.split_output_name_var.set("Chapter.pdf")

        with patch("docforge_pdf.ui.app_window.messagebox.showinfo"):
            app._start_split_thread()

            for _ in range(50):
                if not app.is_splitting:
                    break
                time.sleep(0.05)
                app.update()

            if hasattr(app, "_current_worker") and app._current_worker.is_alive():
                app._current_worker.join(timeout=2.0)

            # Devem ser gerados Chapter_p1-2.pdf (2 páginas) e Chapter_p5.pdf (1 página)
            p1 = os.path.join(temp_dir, "Chapter_p1-2.pdf")
            p2 = os.path.join(temp_dir, "Chapter_p5.pdf")
            assert os.path.isfile(p1)
            assert os.path.isfile(p2)

            d1 = fitz.open(p1)
            assert d1.page_count == 2
            d1.close()

            d2 = fitz.open(p2)
            assert d2.page_count == 1
            d2.close()
    finally:
        app.destroy()


def test_split_all_pages_execution(temp_dir):
    pdf_path = os.path.join(temp_dir, "ExplodeDoc.pdf")
    _create_sample_pdf(pdf_path, pages=3)

    app = DocForgeApp(initial_files=[pdf_path], initial_action="split")
    app.withdraw()
    try:
        app.auto_open_folder_var.set(False)
        app.split_mode_var.set("split_all")
        app.split_prefix_var.set("Page")
        app.split_output_dir_var.set(temp_dir)

        with patch("docforge_pdf.ui.app_window.messagebox.showinfo"):
            app._start_split_thread()

            for _ in range(50):
                if not app.is_splitting:
                    break
                time.sleep(0.05)
                app.update()

            if hasattr(app, "_current_worker") and app._current_worker.is_alive():
                app._current_worker.join(timeout=2.0)

            assert os.path.isfile(os.path.join(temp_dir, "Page_001.pdf"))
            assert os.path.isfile(os.path.join(temp_dir, "Page_002.pdf"))
            assert os.path.isfile(os.path.join(temp_dir, "Page_003.pdf"))
    finally:
        app.destroy()


def test_theme_and_settings_toggle():
    app = DocForgeApp()
    app.withdraw()
    try:
        app._on_theme_changed("Light")
        assert app.current_theme_var.get() == "Light"

        app._on_theme_changed("Dark")
        assert app.current_theme_var.get() == "Dark"

        app._refresh_context_menu_status()

        # Test toggle button on non-windows platform
        with patch("docforge_pdf.ui.app_window.messagebox.showinfo"):
            app._toggle_context_menu()
    finally:
        app.destroy()
