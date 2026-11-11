"""
Ponto de entrada na raiz do repositório para o DocForge PDF.
Permite executar `python main.py` diretamente a partir da raiz do projeto.
"""

import os
import sys

# Garantir que o diretório atual esteja no caminho de busca de módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docforge_pdf.main import main

if __name__ == "__main__":
    sys.exit(main())
