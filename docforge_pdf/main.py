"""
Ponto de entrada principal do DocForge PDF.
Gerencia argumentos CLI, comunicação inter-processos (IPC) para seleção múltipla do Explorer,
execução de ações automáticas (como Fast-Merge de sequências de scanner) e lançamento da GUI.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

# Garantir que a raiz do projeto esteja no sys.path
pkg_parent = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if pkg_parent not in sys.path:
    sys.path.insert(0, pkg_parent)

from docforge_pdf.core import ipc_collector, pdf_engine, sorter
from docforge_pdf.core.win_registry import reveal_in_explorer
from docforge_pdf.ui.app_window import DocForgeApp

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("docforge_main")


def expand_and_normalize_inputs(inputs: List[str]) -> List[str]:
    """
    Expande caminhos de entrada:
    - Se for um arquivo .pdf existente: inclui o caminho absoluto.
    - Se for um diretório existente: busca todos os arquivos .pdf dentro dele.
    - Remove duplicatas preservando a ordem natural de detecção.
    """
    result: List[str] = []
    seen = set()

    for item in inputs:
        if not item:
            continue
        abs_p = os.path.abspath(item.strip('"'))
        if os.path.isdir(abs_p):
            dir_pdfs: List[str] = []
            try:
                for entry in os.listdir(abs_p):
                    if entry.lower().endswith(".pdf"):
                        full_path = os.path.join(abs_p, entry)
                        if os.path.isfile(full_path):
                            dir_pdfs.append(full_path)
            except OSError as e:
                logger.warning(f"Erro ao ler diretório '{abs_p}': {e}")

            sorted_dir = sorter.natural_sort(dir_pdfs)
            for f in sorted_dir:
                if f not in seen:
                    seen.add(f)
                    result.append(f)
        elif os.path.isfile(abs_p):
            if abs_p.lower().endswith(".pdf") and abs_p not in seen:
                seen.add(abs_p)
                result.append(abs_p)
        else:
            logger.debug(f"Caminho ignorado (inexistente ou não-PDF): {abs_p}")

    return result


def execute_fast_merge(file_list: List[str]) -> bool:
    """
    Executa o merge automático de uma sequência de scanner.
    Ordena alfanumericamente e salva como <Prefixo>_Completo.pdf na pasta de origem.
    Retorna True se concluído com sucesso, False se falhou.
    """
    if not file_list:
        return False

    try:
        sorted_files = sorter.natural_sort(file_list)
        output_name = sorter.suggest_output_filename(sorted_files)
        first_dir = os.path.dirname(sorted_files[0])
        dest_path = os.path.join(first_dir, output_name)

        logger.info(f"Executando Fast-Merge para {len(sorted_files)} arquivos -> '{dest_path}'")
        pdf_engine.merge_pdfs(sorted_files, dest_path)
        reveal_in_explorer(dest_path)
        return True
    except Exception as e:
        logger.error(f"Falha ao executar Fast-Merge automático: {e}")
        return False


def build_arg_parser() -> argparse.ArgumentParser:
    """Configura o analisador de argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="DocForge PDF - Ferramenta Especializada de União e Divisão de PDFs."
    )
    parser.add_argument(
        "--action",
        choices=["merge", "fast-merge", "split", "merge-folder"],
        default="merge",
        help="Ação a ser executada com os arquivos fornecidos.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=ipc_collector.DEFAULT_PORT,
        help="Porta TCP local para coordenação IPC entre instâncias do Explorer.",
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=ipc_collector.DEFAULT_DEBOUNCE,
        help="Tempo de espera de debounce em segundos para acumulação de instâncias.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=[],
        help="Caminhos de arquivos PDF ou pastas para processamento.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Ponto de entrada principal da aplicação.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    raw_files = list(args.files)
    effective_action = args.action

    # Caso especial: merge-folder converte diretório em lista de PDFs
    if effective_action == "merge-folder":
        effective_action = "merge"

    # Expandir caminhos (diretórios viram lista de PDFs)
    input_files = expand_and_normalize_inputs(raw_files)

    # Coordenação Inter-Processos (IPC) para múltiplas instâncias disparadas pelo Explorer
    is_master, resolved_action, collected_files = ipc_collector.collect_files_via_ipc(
        action=effective_action,
        incoming_files=input_files,
        port=args.port,
        debounce_seconds=args.debounce,
        exit_on_client=True,
    )

    if not is_master:
        # Instância secundária entregou arquivos ao Mestre e encerra
        return 0

    # Expandir quaisquer arquivos coletados que possam ter vindo como diretório via IPC
    final_files = expand_and_normalize_inputs(collected_files)

    # 1. Tratar Fast-Merge
    if resolved_action == "fast-merge":
        if sorter.is_scanner_sequence(final_files):
            success = execute_fast_merge(final_files)
            if success:
                return 0
            # Se falhou o fast-merge silencioso, cai para abrir a interface gráfica
            logger.warning("Falha no Fast-Merge automático. Abrindo interface gráfica com os arquivos.")
        # Se NÃO for sequência de scanner (ex: RG.pdf, CPF.pdf), abre a GUI para o usuário conferir a ordem
        resolved_action = "merge"

    # 2. Inicializar Interface Gráfica
    app = DocForgeApp(
        initial_files=final_files,
        initial_action=resolved_action,
    )
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
