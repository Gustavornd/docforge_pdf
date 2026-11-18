# 📄 DocForge PDF

<p align="center">
  <strong>Ferramenta Especializada em União (Merge) e Divisão (Split) de Documentos PDF no Windows</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Platform Windows" />
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet" alt="GUI Framework" />
  <img src="https://img.shields.io/badge/Engine-PyMuPDF%20(Fitz)-green" alt="PDF Engine" />
  <img src="https://img.shields.io/badge/Tests-52%20passed-success" alt="Tests status" />
  <img src="https://img.shields.io/badge/Installer-Inno%20Setup-informational" alt="Inno Setup" />
</p>

---

## 📌 Visão Geral

O **DocForge PDF** é uma aplicação desktop rápida, moderna e leve para manipulação de arquivos PDF no ambiente Windows. O projeto foi desenhado especificamente para resolver fluxos de trabalho comuns em escritórios e rotinas de digitalização (scanners):

* **Juntar múltiplos PDFs** com ordenação humana natural (evitando a clássica desordem `Doc 1, Doc 10, Doc 2`).
* **Separar e extrair páginas** individuais ou intervalos personalizados com alta velocidade.
* **Integração nativa ao Windows Explorer (Menu de Contexto):** ações disponíveis no clique com o botão direito diretamente sobre arquivos PDF e pastas, sem exigir privilégios de Administrador.
* **Coordenação Inteligente de Múltiplas Instâncias (IPC):** ao selecionar 20 arquivos e clicar no botão direito, o Windows abre 20 processos. O DocForge intercepta e consolida todas as instâncias em uma única janela via socket local (TCP Loopback) com debounce.

---

## ✨ Principais Funcionalidades

1. **União de PDFs (Merge):**
   * Arrastar e soltar (*Drag & Drop*) ou seleção múltipla via explorador.
   * Reorganização de páginas e documentos (subir, descer, ordenar).
   * Modo **Fast-Merge:** detecta sequências padronizadas de scanner (`Scan_001.pdf`, `Scan_002.pdf`) e mescla automaticamente salvando como `Scan_Completo.pdf`.

2. **Divisão e Extração (Split):**
   * Visualização da quantidade de páginas e tamanho do arquivo.
   * Extração de todas as páginas em arquivos individuais (`pagina_01.pdf`, `pagina_02.pdf`, ...).
   * Extração por intervalos customizados (ex: `1-3, 5, 8-10`).

3. **Integração com o Menu do Botão Direito (Context Menu):**
   * **Arquivos PDF:** Menu cascata (*drawer*) com as opções:
     * *Juntar PDFs no DocForge*
     * *Merge Rápido (Auto-Ordem)*
     * *Separar / Extrair Páginas*
   * **Pastas:** Opção de juntar todos os PDFs da pasta com um clique:
     * *DocForge: Juntar todos os PDFs desta pasta*
   * Utiliza chaves de usuário (`HKCU`) através da especificação oficial `ExtendedSubCommandsKey` do Windows.

---

## 🚀 Guia de Instalação

### Opção 1: Via Instalador Windows (.exe) — Recomendado para Usuários
*Não requer ter Python instalado no computador.*

1. Acesse a pasta `dist_installer/` (ou baixe da aba de **Releases** do GitHub).
2. Execute o instalador:
   ```text
   DocForge_PDF_Setup_v1.0.0.exe
   ```
3. O assistente de instalação permitirá:
   * Escolher se deseja instalar apenas para o usuário atual (sem necessidade de privilégios de Administrador) ou para todos os usuários da máquina.
   * Criar atalho na Área de Trabalho e no Menu Iniciar.
   * Ativar a integração automática com o menu do botão direito do Windows.
4. Para desinstalar futuramente, utilize o desinstalador padrão do Windows em **Configurações > Aplicativos > Aplicativos Instalados**.

---

### Opção 2: Execução para Desenvolvedores (Ambiente Python)

#### Pré-requisitos
* **Sistema Operacional:** Windows 10 ou 11 (64-bit)
* **Python:** 3.10 ou superior
* **Git**

#### Passo a Passo

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/Gustavornd/docforge_pdf.git
   cd docforge_pdf
   ```

2. **Criar e ativar o ambiente virtual:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   *(No CMD clássico, use `venv\Scripts\activate.bat`)*

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Executar a aplicação:**
   ```bash
   python main.py
   ```

5. **Executar os testes automatizados:**
   ```bash
   python -m pytest tests
   ```

---

## 🛠️ Uso via Linha de Comando (CLI)

O DocForge PDF pode ser acionado diretamente pelo terminal ou scripts automatizados:

```powershell
# Abrir a interface gráfica normalmente
python main.py

# Unir arquivos específicos
python main.py --action merge "doc1.pdf" "doc2.pdf"

# Executar Fast-Merge silencioso para documentos de scanner
python main.py --action fast-merge "Scan_001.pdf" "Scan_002.pdf"

# Abrir no modo de divisão para um arquivo
python main.py --action split "documento.pdf"

# Juntar todos os PDFs dentro de uma pasta
python main.py --action merge-folder "C:\Caminho\Da\Pasta"

# Registrar o menu de contexto no Windows via linha de comando
python main.py --register-menu

# Remover o menu de contexto do Windows
python main.py --unregister-menu
```

> **Dica no Windows 11:** O menu de contexto simplificado padrão do Windows 11 agrupa comandos estáticos do Registro sob a opção **"Mostrar mais opções"** (atalho `Shift + F10`). Ao clicar com o botão direito em um PDF e pressionar `Shift + F10`, o menu em cascata com as opções do DocForge será exibido.

---

## 📦 Como Compilar o Executável e o Instalador

O projeto conta com scripts batch automatizados na raiz:

### 1. Gerar a pasta standalone do Executável (`dist\DocForge PDF\`)
Compila com PyInstaller incluindo todas as dependências e o interpretador embutido:
```cmd
.\build.bat
```

### 2. Gerar o Instalador Único Setup (`dist_installer\DocForge_PDF_Setup_v1.0.0.exe`)
Compila o executável via PyInstaller e em seguida empacota no instalador oficial do Windows via **Inno Setup**:
```cmd
.\build_setup.bat
```
*(Requer o [Inno Setup 6](https://jrsoftware.org/isinfo.php) instalado no sistema, instalável via `winget install JRSoftware.InnoSetup`)*.

---

## 🏗️ Estrutura do Projeto

```text
docforge_pdf/
├── docforge_pdf/
│   ├── core/
│   │   ├── ipc_collector.py   # Coordenação inter-processos (socket TCP local)
│   │   ├── pdf_engine.py      # Motor PyMuPDF (merge, split, thumbnails, metadados)
│   │   ├── sorter.py          # Ordenação alfanumérica natural e detecção de scanner
│   │   └── win_registry.py    # Integração com o Registro do Windows (HKCU)
│   ├── ui/
│   │   └── app_window.py      # Interface gráfica moderna em CustomTkinter
│   └── main.py                # Ponto de entrada interno do pacote
├── installer/
│   └── setup.iss              # Script de compilação do Inno Setup
├── tests/                     # Suíte de 52 testes automatizados com Pytest
├── build.bat                  # Script de build rápido com PyInstaller
├── build_setup.bat            # Script de compilação completa do instalador Setup
├── main.py                    # Ponto de entrada raiz
├── requirements.txt           # Dependências do projeto
└── README.md                  # Documentação do projeto
```

---

## 🧪 Qualidade e Testes

O projeto conta com cobertura extensiva de testes automatizados unitários e de integração:

* `test_pdf_engine.py`: manipulação de PDFs, quebras de páginas, senhas e extrações.
* `test_sorter.py`: ordenação natural alfanumérica e heurísticas de sequenciamento de scanner.
* `test_ipc_collector.py`: debounce TCP loopback e transferência de arquivos entre instâncias.
* `test_win_registry.py`: testes de escrita e remoção de chaves no Registro do Windows.
* `test_app_window.py`: validação de fluxos de interface gráfica e eventos.

Para executar toda a suíte:
```bash
pytest tests
```

---

## ⚖️ Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais informações.
