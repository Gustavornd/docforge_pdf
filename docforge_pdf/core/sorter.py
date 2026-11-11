"""
Módulo de ordenação inteligente e detecção de padrões de scanner.
Implementa Natural Sorting e heurística para identificação de sequências de digitalização.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def natural_sort_key(path_or_name: str) -> list:
    """
    Gera uma chave de ordenação natural (alfanumerica) para nomes de arquivo.
    Ex: 'Arquivo_2.pdf' virá antes de 'Arquivo_10.pdf'.
    Compara partes numéricas como inteiros e partes de texto como strings minúsculas.
    """
    if not path_or_name:
        return []
    name = os.path.basename(str(path_or_name))
    parts = re.split(r'(\d+)', name)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def natural_sort(file_list: List[str]) -> List[str]:
    """
    Ordena uma lista de caminhos ou nomes de arquivos usando Natural Sorting.
    """
    if not file_list:
        return []
    return sorted(file_list, key=natural_sort_key)


def detect_scanner_sequence(file_list: List[str]) -> Tuple[bool, str]:
    """
    Verifica se todos os arquivos selecionados compartilham o mesmo prefixo base
    e diferem apenas por um sufixo numérico (ex: Contrato_001.pdf, Contrato_002.pdf).
    
    Retorna uma tupla:
      (is_sequence: bool, clean_prefix: str)
      
    Se for uma sequência válida, clean_prefix contém o prefixo sem separadores finais.
    """
    if not file_list or len(file_list) < 2:
        return False, ""

    # Se os caminhos forem de diretórios diferentes, não é uma sequência na mesma pasta
    non_empty_dirs = {os.path.dirname(os.path.abspath(item)) for item in file_list if os.path.dirname(str(item))}
    if len(non_empty_dirs) > 1:
        return False, ""

    # Regex para capturar prefixo e número final no stem do arquivo (sem extensão)
    # Suporta formatos como: Doc_001, Scan-02, Arquivo 10, Página1, 001
    pattern = re.compile(r'^(.*?)(\d+)$')
    
    canonical_prefix = None
    original_prefix_sample = ""
    seen_numbers = set()

    for item in file_list:
        stem = Path(item).stem
        match = pattern.match(stem)
        if not match:
            # O nome não termina em dígitos
            return False, ""
        
        prefix, num_str = match.group(1), match.group(2)
        norm_prefix = prefix.strip().lower()
        num_val = int(num_str)

        if canonical_prefix is None:
            canonical_prefix = norm_prefix
            original_prefix_sample = prefix
        elif norm_prefix != canonical_prefix:
            # Prefixos diferentes (ex: RG_01 e CPF_02)
            return False, ""

        if num_val in seen_numbers:
            # Números duplicados na mesma lista de sequência
            return False, ""
        seen_numbers.add(num_val)

    # Limpar separadores finais do prefixo (como _, -, espaço)
    clean_prefix = re.sub(r'[\s_\-]+$', '', original_prefix_sample).strip()
    return True, clean_prefix


def is_scanner_sequence(file_list: List[str]) -> bool:
    """
    Retorna True se a lista de arquivos for uma sequência identificável de scanner.
    """
    is_seq, _ = detect_scanner_sequence(file_list)
    return is_seq


def suggest_output_filename(file_list: List[str]) -> str:
    """
    Gera um nome sugerido inteligente para o arquivo final unificado:
    - Se for sequência de scanner com prefixo: <Prefixo>_Completo.pdf
    - Se compartilhar um prefixo comum significativo: <PrefixoComum>_Completo.pdf
    - Caso contrário: Documentos_Unificados.pdf
    """
    if not file_list:
        return "Documentos_Unificados.pdf"

    is_seq, prefix = detect_scanner_sequence(file_list)
    if is_seq:
        if prefix:
            return f"{prefix}_Completo.pdf"
        return "Documentos_Completo.pdf"

    # Verificar se todos os arquivos compartilham um prefixo comum
    stems = [Path(f).stem for f in file_list if f]
    if len(stems) >= 2:
        common = os.path.commonprefix(stems)
        clean_common = re.sub(r'[\s_\-]+$', '', common).strip()
        if len(clean_common) >= 3:
            return f"{clean_common}_Completo.pdf"

    return "Documentos_Unificados.pdf"
