"""
Motor de manipulação de PDFs baseado em PyMuPDF (fitz).
Oferece operações de união (merge), divisão (split), extração e geração de miniaturas.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple, Union
import pymupdf as fitz
from PIL import Image


def format_file_size(size_bytes: int) -> str:
    """Formata o tamanho do arquivo em bytes para formato legível (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def parse_page_query_items(page_query: str, max_pages: int) -> List[Tuple[str, List[int]]]:
    """
    Interpreta uma consulta de páginas no formato '1-3, 5, 8-10'.
    Preserva a estrutura de cada item (intervalo ou página avulsa).
    Retorna uma lista de tuplas: (rotulo_do_item, [indices_base_0]).
    Ex: '1-3, 5, 8-10' -> [('1-3', [0, 1, 2]), ('5', [4]), ('8-10', [7, 8, 9])]
    """
    if not page_query or not page_query.strip():
        raise ValueError("Nenhuma página informada para extração.")

    # Normalizar delimitadores comuns como ';' para ','
    normalized_query = page_query.replace(";", ",")
    chunks = [c.strip() for c in normalized_query.split(",") if c.strip()]
    if not chunks:
        raise ValueError("Formato de páginas inválido.")

    items: List[Tuple[str, List[int]]] = []

    for chunk in chunks:
        if "-" in chunk:
            parts = [p.strip() for p in chunk.split("-")]
            if len(parts) != 2:
                raise ValueError(f"Intervalo de páginas inválido: '{chunk}'")
            try:
                start = int(parts[0])
                end = int(parts[1])
            except ValueError:
                raise ValueError(f"Números inválidos no intervalo: '{chunk}'")

            if start < 1 or end < 1:
                raise ValueError(f"O número da página deve ser maior ou igual a 1: '{chunk}'")
            if start > end:
                raise ValueError(f"Início do intervalo maior que o fim: {start} > {end}")
            if end > max_pages:
                raise ValueError(f"Página final {end} ultrapassa o total de páginas ({max_pages}).")

            indices = [p - 1 for p in range(start, end + 1)]
            label = f"{start}-{end}" if start != end else f"{start}"
            items.append((label, indices))
        else:
            try:
                page_num = int(chunk)
            except ValueError:
                raise ValueError(f"Número de página inválido: '{chunk}'")

            if page_num < 1 or page_num > max_pages:
                raise ValueError(f"Página {page_num} fora dos limites do documento (1 a {max_pages}).")

            items.append((str(page_num), [page_num - 1]))

    return items


def parse_page_query(page_query: str, max_pages: int) -> List[int]:
    """
    Interpreta uma consulta de páginas no formato '1-3, 5, 8-10'.
    Valida limites (1 até max_pages) e retorna lista de índices base-0.
    
    Lança ValueError em caso de sintaxe inválida ou página fora dos limites.
    """
    items = parse_page_query_items(page_query, max_pages)
    flattened: List[int] = []
    for _, indices in items:
        flattened.extend(indices)
    return flattened


def render_page_thumbnail(
    source: Union[str, fitz.Document],
    page_number: int = 0,
    max_size: Tuple[int, int] = (200, 260)
) -> Optional[Image.Image]:
    """
    Renderiza uma miniatura da página especificada como um objeto PIL.Image.
    Redimensiona proporcionalmente para caber em max_size (largura, altura).
    """
    doc_opened = False
    doc = None
    try:
        if isinstance(source, str):
            if not os.path.isfile(source):
                return None
            doc = fitz.open(source)
            doc_opened = True
        else:
            doc = source

        if page_number < 0 or page_number >= doc.page_count:
            return None

        page = doc.load_page(page_number)
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            return None

        # Calcular fator de escala para preencher max_size mantendo proporção
        scale_w = max_size[0] / rect.width
        scale_h = max_size[1] / rect.height
        scale = min(scale_w, scale_h)

        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Converter PyMuPDF Pixmap para PIL.Image
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return img
    except Exception:
        return None
    finally:
        if doc_opened and doc is not None:
            doc.close()


def get_pdf_info(file_path: str, page_number: int = 0, render_thumb: bool = True) -> dict:
    """
    Coleta informações detalhadas sobre um arquivo PDF, incluindo miniatura da página indicada.
    Permite desativar render_thumb para leituras ultra-rápidas em listas de arquivos.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: '{file_path}'")

    file_size = os.path.getsize(file_path)
    file_size_fmt = format_file_size(file_size)

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Falha ao abrir PDF '{file_path}': {e}")

    try:
        # Verifica se o documento realmente requer senha que não foi fornecida
        is_password_required = False
        if doc.is_encrypted:
            # Tentar autenticar com senha vazia (comum para PDFs com apenas restrições de permissão)
            auth_res = doc.authenticate("")
            if not auth_res and getattr(doc, "needs_pass", True):
                is_password_required = True

        if is_password_required:
            return {
                "file_path": file_path,
                "filename": os.path.basename(file_path),
                "page_count": 0,
                "file_size": file_size,
                "file_size_formatted": file_size_fmt,
                "thumbnail": None,
                "is_encrypted": True,
                "metadata": {}
            }

        page_count = doc.page_count
        thumb = None
        if render_thumb and page_count > 0:
            thumb = render_page_thumbnail(doc, page_number=min(page_number, max(0, page_count - 1)))
        metadata = dict(doc.metadata) if doc.metadata else {}

        return {
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "page_count": page_count,
            "file_size": file_size,
            "file_size_formatted": file_size_fmt,
            "thumbnail": thumb,
            "is_encrypted": False,
            "metadata": metadata
        }
    finally:
        doc.close()


def merge_pdfs(file_paths: List[str], output_path: str) -> None:
    """
    Une todos os PDFs fornecidos em file_paths na ordem exata da lista.
    Gera o arquivo unificado em output_path de forma atômica e segura.
    """
    if not file_paths:
        raise ValueError("A lista de arquivos para união está vazia.")

    merged_doc = fitz.open()
    try:
        for path in file_paths:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Arquivo inexistente: '{path}'")

            try:
                doc = fitz.open(path)
            except Exception as e:
                raise ValueError(f"Erro ao abrir arquivo PDF corrompido ou inválido '{path}': {e}")

            try:
                if doc.is_encrypted and not doc.authenticate(""):
                    raise PermissionError(f"O arquivo '{os.path.basename(path)}' está protegido por senha.")
                merged_doc.insert_pdf(doc)
            finally:
                doc.close()

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        tmp_output = output_path + ".tmp"
        try:
            merged_doc.save(tmp_output, garbage=3, deflate=True)
            if os.path.exists(output_path):
                os.replace(tmp_output, output_path)
            else:
                os.rename(tmp_output, output_path)
        except Exception:
            if os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except OSError:
                    pass
            # Fallback direto se rename/replace falhar por restrição de sistema
            merged_doc.save(output_path, garbage=3, deflate=True)
    finally:
        merged_doc.close()


def split_all_pages(file_path: str, output_dir: str, prefix: Optional[str] = None) -> List[str]:
    """
    Separa cada página do documento PDF em um arquivo individual.
    Salva como <prefix>_001.pdf, <prefix>_002.pdf, etc.
    Retorna a lista de caminhos gerados.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: '{file_path}'")

    os.makedirs(output_dir, exist_ok=True)
    base_prefix = prefix.strip() if prefix and prefix.strip() else Path(file_path).stem

    src_doc = fitz.open(file_path)
    try:
        if src_doc.is_encrypted and not src_doc.authenticate(""):
            raise PermissionError(f"O arquivo '{os.path.basename(file_path)}' está protegido por senha.")

        total_pages = src_doc.page_count
        if total_pages == 0:
            raise ValueError(f"O documento '{file_path}' não possui páginas.")

        pad_width = max(3, len(str(total_pages)))
        generated_files: List[str] = []

        for i in range(total_pages):
            page_num = i + 1
            filename = f"{base_prefix}_{page_num:0{pad_width}d}.pdf"
            dest_path = os.path.join(output_dir, filename)

            single_page_doc = fitz.open()
            try:
                single_page_doc.insert_pdf(src_doc, from_page=i, to_page=i)
                single_page_doc.save(dest_path, garbage=3, deflate=True)
                generated_files.append(dest_path)
            finally:
                single_page_doc.close()

        return generated_files
    finally:
        src_doc.close()


def extract_pages(
    file_path: str,
    page_query: str,
    output_path: str,
    merge_extracted: bool = True
) -> List[str]:
    """
    Extrai páginas especificadas por page_query (ex: '1-3, 5, 8-10').
    - Se merge_extracted=True: gera um único arquivo PDF com as páginas selecionadas.
    - Se merge_extracted=False: gera um arquivo PDF separado para cada página ou intervalo especificado.
    
    Retorna a lista de caminhos gerados.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: '{file_path}'")

    src_doc = fitz.open(file_path)
    try:
        if src_doc.is_encrypted and not src_doc.authenticate(""):
            raise PermissionError(f"O arquivo '{os.path.basename(file_path)}' está protegido por senha.")

        query_items = parse_page_query_items(page_query, src_doc.page_count)
        if not query_items:
            raise ValueError("Nenhuma página correspondente encontrada.")

        if merge_extracted:
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            out_doc = fitz.open()
            try:
                for _, indices in query_items:
                    for idx in indices:
                        out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                out_doc.save(output_path, garbage=3, deflate=True)
                return [output_path]
            finally:
                out_doc.close()
        else:
            # Gerar arquivos separados para cada página ou intervalo especificado
            if output_path.lower().endswith(".pdf"):
                out_dir = os.path.dirname(output_path) or "."
                base_stem = Path(output_path).stem
            else:
                out_dir = output_path
                base_stem = Path(file_path).stem

            os.makedirs(out_dir, exist_ok=True)
            generated_files: List[str] = []
            used_filenames = set()

            for item_label, indices in query_items:
                candidate_name = f"{base_stem}_p{item_label}.pdf"
                # Disambiguate se o mesmo intervalo/página for repetido na consulta
                count = 1
                while candidate_name in used_filenames:
                    count += 1
                    candidate_name = f"{base_stem}_p{item_label}_{count}.pdf"
                used_filenames.add(candidate_name)

                dest_path = os.path.join(out_dir, candidate_name)
                item_doc = fitz.open()
                try:
                    for idx in indices:
                        item_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                    item_doc.save(dest_path, garbage=3, deflate=True)
                    generated_files.append(dest_path)
                finally:
                    item_doc.close()

            return generated_files
    finally:
        src_doc.close()
