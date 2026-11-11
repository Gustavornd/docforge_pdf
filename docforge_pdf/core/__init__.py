"""
Módulos centrais do DocForge PDF.
"""

from .sorter import (
    natural_sort,
    natural_sort_key,
    is_scanner_sequence,
    detect_scanner_sequence,
    suggest_output_filename,
)
from .pdf_engine import (
    format_file_size,
    parse_page_query,
    render_page_thumbnail,
    get_pdf_info,
    merge_pdfs,
    split_all_pages,
    extract_pages,
)
from .ipc_collector import collect_files_via_ipc
from .win_registry import (
    is_windows,
    is_context_menu_registered,
    register_context_menu,
    unregister_context_menu,
    get_default_command_prefix,
)
