"""
Interface gráfica moderna para o DocForge PDF desenvolvida com CustomTkinter.
Fornece três abas principais:
1. Juntar (Merge)
2. Separar / Extrair (Split) com visualizador de miniaturas folheável
3. Configurações / Sistema (Registro do Windows e preferências)
"""

import logging
import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from PIL import Image

from docforge_pdf.core import pdf_engine, sorter, win_registry
from docforge_pdf.core.win_registry import reveal_in_explorer

logger = logging.getLogger(__name__)

# Configurações globais de aparência inicial do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DocForgeApp(ctk.CTk):
    """
    Janela principal do DocForge PDF.
    """

    def __init__(
        self,
        initial_files: Optional[List[str]] = None,
        initial_action: str = "merge",
        auto_open_folder: bool = True,
    ):
        super().__init__()

        self.title("DocForge PDF - Ferramenta de União e Extração de Documentos")
        self.geometry("1100x740")
        self.minsize(960, 640)

        # Preferências gerais
        self.auto_open_folder_var = ctk.BooleanVar(value=auto_open_folder)
        self.current_theme_var = ctk.StringVar(value="Dark")

        # -----------------------------
        # Estado da Aba de Merge
        # -----------------------------
        self.merge_files: List[Dict[str, Any]] = []
        self.merge_output_name_var = ctk.StringVar(value="Documentos_Unificados.pdf")
        self.merge_output_dir_var = ctk.StringVar(value="")
        self.merge_status_var = ctk.StringVar(value="Pronto. Adicione PDFs para começar.")
        self.is_merging = False
        self._merge_thumb_img: Optional[ctk.CTkImage] = None

        # -----------------------------
        # Estado da Aba de Split
        # -----------------------------
        self.split_source_path: Optional[str] = None
        self.split_total_pages = 0
        self.split_current_page = 0
        self.split_source_label_var = ctk.StringVar(value="Nenhum arquivo PDF carregado")
        self.split_page_indicator_var = ctk.StringVar(value="Página 0 de 0")
        self.split_jump_var = ctk.StringVar(value="")
        self.split_mode_var = ctk.StringVar(value="extract_ranges")  # "extract_ranges" ou "split_all"
        self.split_query_var = ctk.StringVar(value="")
        self.split_merge_extracted_var = ctk.BooleanVar(value=True)
        self.split_output_name_var = ctk.StringVar(value="")
        self.split_prefix_var = ctk.StringVar(value="")
        self.split_output_dir_var = ctk.StringVar(value="")
        self.split_status_var = ctk.StringVar(value="Selecione um arquivo PDF para visualizar e dividir.")
        self.is_splitting = False
        self._split_thumb_img: Optional[ctk.CTkImage] = None

        # Configurar Estilos do ttk.Treeview
        self._setup_treeview_styles()

        # Construção dos Componentes Visuais
        self._build_header()
        self._build_tabs()

        # Carregar arquivos/ações iniciais se recebidos via CLI ou Explorer
        self._load_initial_data(initial_files=initial_files, initial_action=initial_action)

    def _set_label_image_or_text(
        self,
        label: ctk.CTkLabel,
        ctk_image: Optional[ctk.CTkImage],
        text: str = "",
    ) -> None:
        """
        Define imagem ou texto em um CTkLabel de forma segura, contornando o bug do CustomTkinter
        onde label.configure(image=None) não desassocia a imagem interna do tkinter.Label.
        """
        try:
            if ctk_image is None:
                if hasattr(label, "_label") and label._label is not None:
                    try:
                        label._label.configure(image="")
                    except Exception:
                        pass
                label.configure(image=None, text=text)
            else:
                label.configure(image=ctk_image, text=text)
        except Exception as e:
            logger.debug(f"Erro ao atualizar imagem no rótulo: {e}")

    def _safe_dispatch(self, callback) -> None:
        """
        Dispara um callback com segurança na thread principal da interface.
        Verifica se a janela ainda existe e suprime exceções caso o app tenha sido encerrado.
        """
        try:
            if not self.winfo_exists():
                return
            self.after(0, callback)
        except Exception:
            pass

    # =========================================================================
    # Configuração de Estilo e Tema
    # =========================================================================

    def _setup_treeview_styles(self) -> None:
        """Configura o estilo do ttk.Treeview para se adequar ao modo Dark/Light do CustomTkinter."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        mode = ctk.get_appearance_mode().lower()
        if mode == "light":
            bg = "#ffffff"
            fg = "#1a1a1a"
            heading_bg = "#e5e5e5"
            heading_fg = "#1a1a1a"
            selected_bg = "#3b8ed0"
        else:
            bg = "#2b2b2b"
            fg = "#f0f0f0"
            heading_bg = "#1f1f1f"
            heading_fg = "#ffffff"
            selected_bg = "#1f6aa5"

        font_name = "Segoe UI" if sys.platform == "win32" else "Helvetica"
        style.configure(
            "DocForge.Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
            rowheight=28,
            font=(font_name, 10),
        )
        style.configure(
            "DocForge.Treeview.Heading",
            background=heading_bg,
            foreground=heading_fg,
            relief="flat",
            font=(font_name, 10, "bold"),
            padding=4,
        )
        style.map(
            "DocForge.Treeview",
            background=[("selected", selected_bg)],
            foreground=[("selected", "#ffffff")],
        )

    def _on_theme_changed(self, new_theme: str) -> None:
        """Atualiza o tema geral da aplicação e re-estiliza tabelas."""
        self.current_theme_var.set(new_theme)
        ctk.set_appearance_mode(new_theme)
        self.after(50, self._setup_treeview_styles)

    # =========================================================================
    # Cabeçalho Principal
    # =========================================================================

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, height=60, fg_color=("gray85", "#1f1f1f"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_lbl = ctk.CTkLabel(
            header,
            text="DocForge PDF",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("gray10", "white"),
        )
        title_lbl.pack(side="left", padx=(20, 10), pady=12)

        subtitle_lbl = ctk.CTkLabel(
            header,
            text="•   União Inteligente & Extração de Documentos (100% Offline)",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
        )
        subtitle_lbl.pack(side="left", padx=0, pady=15)

        badge_lbl = ctk.CTkLabel(
            header,
            text="v1.0.0",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray75", "#333333"),
            corner_radius=6,
            padx=8,
            pady=3,
        )
        badge_lbl.pack(side="right", padx=20, pady=16)

    # =========================================================================
    # Abas Principais
    # =========================================================================

    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        self.tab_merge = self.tabview.add("Juntar (Merge)")
        self.tab_split = self.tabview.add("Separar / Extrair (Split)")
        self.tab_settings = self.tabview.add("Configurações / Sistema")

        self._build_merge_tab()
        self._build_split_tab()
        self._build_settings_tab()

    # =========================================================================
    # ABA 1: JUNTAR (MERGE)
    # =========================================================================

    def _build_merge_tab(self) -> None:
        container = ctk.CTkFrame(self.tab_merge, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # Divisão em duas colunas: Esquerda (Tabela e Ações) e Direita (Painel de Preview)
        left_frame = ctk.CTkFrame(container, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_frame = ctk.CTkFrame(container, width=280, corner_radius=8)
        right_frame.pack(side="right", fill="y", padx=0, pady=0)
        right_frame.pack_propagate(False)

        # 1. Barra de Ferramentas Superior
        toolbar = ctk.CTkFrame(left_frame, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))

        btn_add = ctk.CTkButton(
            toolbar,
            text="➕ Adicionar PDFs",
            command=self._browse_and_add_files,
            width=130,
            font=ctk.CTkFont(weight="bold"),
        )
        btn_add.pack(side="left", padx=(0, 6))

        btn_up = ctk.CTkButton(
            toolbar,
            text="Subir ▲",
            command=self._move_selection_up,
            width=80,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        btn_up.pack(side="left", padx=(0, 6))

        btn_down = ctk.CTkButton(
            toolbar,
            text="Descer ▼",
            command=self._move_selection_down,
            width=80,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        btn_down.pack(side="left", padx=(0, 6))

        btn_sort = ctk.CTkButton(
            toolbar,
            text="Ordenar A-Z (Natural)",
            command=self._sort_files_natural,
            width=150,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        btn_sort.pack(side="left", padx=(0, 6))

        btn_remove = ctk.CTkButton(
            toolbar,
            text="Remover",
            command=self._remove_selected_file,
            width=85,
            fg_color="#a83232",
            hover_color="#c43b3b",
        )
        btn_remove.pack(side="left", padx=(0, 6))

        btn_clear = ctk.CTkButton(
            toolbar,
            text="Limpar Lista",
            command=self._clear_merge_list,
            width=90,
            fg_color=("gray70", "#444444"),
            hover_color=("gray60", "#555555"),
        )
        btn_clear.pack(side="right")

        # 2. Tabela de Arquivos Selecionados
        table_frame = ctk.CTkFrame(left_frame)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("ordem", "nome", "paginas", "tamanho", "caminho")
        self.merge_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="DocForge.Treeview",
            selectmode="browse",
        )

        self.merge_tree.heading("ordem", text="#", anchor="center")
        self.merge_tree.heading("nome", text="Nome do Arquivo", anchor="w")
        self.merge_tree.heading("paginas", text="Páginas", anchor="center")
        self.merge_tree.heading("tamanho", text="Tamanho", anchor="center")
        self.merge_tree.heading("caminho", text="Caminho Completo", anchor="w")

        self.merge_tree.column("ordem", width=45, minwidth=35, anchor="center")
        self.merge_tree.column("nome", width=220, minwidth=140, anchor="w")
        self.merge_tree.column("paginas", width=75, minwidth=60, anchor="center")
        self.merge_tree.column("tamanho", width=85, minwidth=70, anchor="center")
        self.merge_tree.column("caminho", width=300, minwidth=150, anchor="w")

        tree_scrollbar = ctk.CTkScrollbar(table_frame, command=self.merge_tree.yview)
        self.merge_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.merge_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        self.merge_tree.bind("<<TreeviewSelect>>", self._on_merge_tree_select)

        # 3. Painel Inferior de Configurações de Saída e Ação
        bottom_box = ctk.CTkFrame(left_frame, corner_radius=8)
        bottom_box.pack(fill="x", pady=0)

        # Linha 1: Nome do arquivo final
        row1 = ctk.CTkFrame(bottom_box, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 6))

        lbl_out_name = ctk.CTkLabel(row1, text="Nome do Arquivo Final:", width=155, anchor="w")
        lbl_out_name.pack(side="left")

        self.entry_merge_name = ctk.CTkEntry(
            row1,
            textvariable=self.merge_output_name_var,
            placeholder_text="ex: Documentos_Unificados.pdf",
        )
        self.entry_merge_name.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_sug_name = ctk.CTkButton(
            row1,
            text="Sugerir Nome",
            command=self._apply_suggested_filename,
            width=110,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        btn_sug_name.pack(side="right")

        # Linha 2: Pasta de destino
        row2 = ctk.CTkFrame(bottom_box, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 10))

        lbl_out_dir = ctk.CTkLabel(row2, text="Pasta de Destino:", width=155, anchor="w")
        lbl_out_dir.pack(side="left")

        self.entry_merge_dir = ctk.CTkEntry(
            row2,
            textvariable=self.merge_output_dir_var,
            placeholder_text="Selecione a pasta onde o PDF será salvo",
        )
        self.entry_merge_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse_dir = ctk.CTkButton(
            row2,
            text="Selecionar Pasta...",
            command=self._browse_merge_output_dir,
            width=135,
        )
        btn_browse_dir.pack(side="right")

        # Linha 3: Botão de Ação em Destaque
        row3 = ctk.CTkFrame(bottom_box, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=(0, 10))

        self.btn_do_merge = ctk.CTkButton(
            row3,
            text="⚡ Juntar PDFs Agora",
            command=self._start_merge_thread,
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_do_merge.pack(fill="x")

        # Barra de Status da Aba Merge
        self.lbl_merge_status = ctk.CTkLabel(
            left_frame,
            textvariable=self.merge_status_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.lbl_merge_status.pack(fill="x", pady=(6, 0))

        # 4. Painel Lateral Direito: Pré-visualização da Capa
        lbl_prev_title = ctk.CTkLabel(
            right_frame,
            text="Pré-visualização da Capa",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_prev_title.pack(padx=10, pady=(12, 6))

        self.frame_merge_preview = ctk.CTkFrame(
            right_frame,
            fg_color=("gray90", "#242424"),
            corner_radius=6,
            width=240,
            height=300,
        )
        self.frame_merge_preview.pack(padx=15, pady=6)
        self.frame_merge_preview.pack_propagate(False)

        self.lbl_merge_thumb = ctk.CTkLabel(
            self.frame_merge_preview,
            text="Nenhum arquivo\nselecionado",
            text_color="gray50",
        )
        self.lbl_merge_thumb.pack(expand=True, fill="both")

        # Detalhes do arquivo selecionado
        self.lbl_merge_info_name = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=240,
        )
        self.lbl_merge_info_name.pack(padx=10, pady=(6, 2))

        self.lbl_merge_info_pages = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self.lbl_merge_info_pages.pack(padx=10, pady=1)

        self.lbl_merge_info_size = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self.lbl_merge_info_size.pack(padx=10, pady=1)

    # =========================================================================
    # Lógica da Aba de Merge
    # =========================================================================

    def _browse_and_add_files(self) -> None:
        """Abre diálogo para seleção de múltiplos PDFs."""
        files = filedialog.askopenfilenames(
            title="Selecionar Arquivos PDF para União",
            filetypes=[("Arquivos PDF (*.pdf)", "*.pdf"), ("Todos os Arquivos", "*.*")],
        )
        if files:
            self._add_files(list(files))

    def _add_files(self, file_paths: List[str]) -> None:
        """Processa e adiciona caminhos de arquivos PDF à lista de trabalho."""
        existing_paths = {item["path"] for item in self.merge_files}
        new_items_added = 0

        for raw_path in file_paths:
            path = os.path.abspath(raw_path)
            if not os.path.isfile(path) or not path.lower().endswith(".pdf"):
                continue
            if path in existing_paths:
                continue

            try:
                info = pdf_engine.get_pdf_info(path, page_number=0, render_thumb=False)
                item = {
                    "path": path,
                    "filename": os.path.basename(path),
                    "page_count": info["page_count"],
                    "file_size_formatted": info["file_size_formatted"],
                    "is_encrypted": info.get("is_encrypted", False),
                    "thumbnail": None,
                }
                self.merge_files.append(item)
                existing_paths.add(path)
                new_items_added += 1
            except Exception as e:
                logger.warning(f"Não foi possível ler metadados de '{path}': {e}")

        if new_items_added > 0:
            self._refresh_merge_tree()

            # Sugerir pasta de destino caso ainda não definida
            if not self.merge_output_dir_var.get() and self.merge_files:
                first_dir = os.path.dirname(self.merge_files[0]["path"])
                self.merge_output_dir_var.set(first_dir)

            # Sugerir nome de arquivo caso o atual seja o padrão
            if self.merge_output_name_var.get() in ("", "Documentos_Unificados.pdf"):
                self._apply_suggested_filename()

            self._update_merge_summary_status()

    def _refresh_merge_tree(self, target_index: Optional[int] = None) -> None:
        """Re-renderiza os itens no Treeview da aba de Merge e preserva a seleção sincronizada."""
        if target_index is not None and 0 <= target_index < len(self.merge_files):
            selected_index: Optional[int] = target_index
        else:
            selected_iid = self.merge_tree.selection()
            selected_index = int(selected_iid[0]) if selected_iid else None

        for row in self.merge_tree.get_children():
            self.merge_tree.delete(row)

        for idx, item in enumerate(self.merge_files):
            pages_str = "Protegido 🔒" if item["is_encrypted"] else f"{item['page_count']} pág"
            values = (
                str(idx + 1),
                item["filename"],
                pages_str,
                item["file_size_formatted"],
                item["path"],
            )
            self.merge_tree.insert("", "end", iid=str(idx), values=values)

        if selected_index is not None and 0 <= selected_index < len(self.merge_files):
            self.merge_tree.selection_set(str(selected_index))
            self.merge_tree.see(str(selected_index))
            self._update_merge_preview_panel(self.merge_files[selected_index])
        elif self.merge_files:
            # Seleciona o primeiro elemento por padrão
            self.merge_tree.selection_set("0")
            self.merge_tree.see("0")
            self._update_merge_preview_panel(self.merge_files[0])
        else:
            self._clear_merge_preview_panel()

    def _on_merge_tree_select(self, event: Any = None) -> None:
        """Disparado quando o usuário seleciona um item na lista de PDFs."""
        selected = self.merge_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.merge_files):
            self._update_merge_preview_panel(self.merge_files[idx])

    def _update_merge_preview_panel(self, item: Dict[str, Any]) -> None:
        """Atualiza a miniatura e as informações do painel lateral da aba de Merge."""
        self.lbl_merge_info_name.configure(text=item["filename"])
        pages_txt = f"Total: {item['page_count']} página(s)" if not item["is_encrypted"] else "Documento com Senha"
        self.lbl_merge_info_pages.configure(text=pages_txt)
        self.lbl_merge_info_size.configure(text=f"Tamanho: {item['file_size_formatted']}")

        pil_img = item.get("thumbnail")
        if pil_img is None and not item["is_encrypted"]:
            # Renderizar sob demanda
            pil_img = pdf_engine.render_page_thumbnail(item["path"], page_number=0, max_size=(220, 280))
            item["thumbnail"] = pil_img

        if pil_img:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
            self._merge_thumb_img = ctk_img
            self._set_label_image_or_text(self.lbl_merge_thumb, ctk_img, text="")
        else:
            self._merge_thumb_img = None
            msg = "Arquivo Protegido 🔒" if item["is_encrypted"] else "Miniatura indisponível"
            self._set_label_image_or_text(self.lbl_merge_thumb, None, text=msg)

    def _clear_merge_preview_panel(self) -> None:
        """Limpa as informações do painel de visualização da capa."""
        self._merge_thumb_img = None
        self._set_label_image_or_text(self.lbl_merge_thumb, None, text="Nenhum arquivo\nselecionado")
        self.lbl_merge_info_name.configure(text="")
        self.lbl_merge_info_pages.configure(text="")
        self.lbl_merge_info_size.configure(text="")

    def _move_selection_up(self) -> None:
        """Move o arquivo selecionado uma posição para cima."""
        selected = self.merge_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx > 0:
            self.merge_files[idx], self.merge_files[idx - 1] = (
                self.merge_files[idx - 1],
                self.merge_files[idx],
            )
            self._refresh_merge_tree(target_index=idx - 1)

    def _move_selection_down(self) -> None:
        """Move o arquivo selecionado uma posição para baixo."""
        selected = self.merge_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if idx < len(self.merge_files) - 1:
            self.merge_files[idx], self.merge_files[idx + 1] = (
                self.merge_files[idx + 1],
                self.merge_files[idx],
            )
            self._refresh_merge_tree(target_index=idx + 1)

    def _sort_files_natural(self) -> None:
        """Ordena a lista de arquivos atual usando Natural Sorting."""
        if len(self.merge_files) < 2:
            return
        self.merge_files.sort(key=lambda x: sorter.natural_sort_key(x["path"]))
        self._refresh_merge_tree(target_index=0)
        # Atualiza a sugestão de nome apenas se o campo estiver vazio ou com o padrão
        if self.merge_output_name_var.get() in ("", "Documentos_Unificados.pdf"):
            self._apply_suggested_filename()
        self.merge_status_var.set("Lista ordenada alfanumericamente com sucesso.")

    def _remove_selected_file(self) -> None:
        """Remove o item selecionado da lista de união."""
        selected = self.merge_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.merge_files):
            del self.merge_files[idx]
            new_target = min(idx, len(self.merge_files) - 1) if self.merge_files else None
            self._refresh_merge_tree(target_index=new_target)
            self._update_merge_summary_status()

    def _clear_merge_list(self) -> None:
        """Limpa todos os arquivos da lista de união."""
        self.merge_files.clear()
        self._refresh_merge_tree()
        self._clear_merge_preview_panel()
        self.merge_status_var.set("Lista limpa. Adicione PDFs para começar.")

    def _apply_suggested_filename(self) -> None:
        """Calcula e preenche o nome de arquivo sugerido para união."""
        paths = [item["path"] for item in self.merge_files]
        sug = sorter.suggest_output_filename(paths)
        self.merge_output_name_var.set(sug)

    def _browse_merge_output_dir(self) -> None:
        """Abre o seletor de diretório para salvar o PDF unificado."""
        initial = self.merge_output_dir_var.get() or os.path.expanduser("~")
        dest = filedialog.askdirectory(title="Selecionar Pasta de Destino", initialdir=initial)
        if dest:
            self.merge_output_dir_var.set(os.path.abspath(dest))

    def _update_merge_summary_status(self) -> None:
        """Atualiza a mensagem descritiva de total de arquivos e páginas."""
        total_files = len(self.merge_files)
        total_pages = sum(item["page_count"] for item in self.merge_files)
        if total_files == 0:
            self.merge_status_var.set("Pronto. Adicione PDFs para começar.")
        else:
            self.merge_status_var.set(
                f"Pronto: {total_files} arquivo(s) na lista • Total de {total_pages} página(s)."
            )

    def _start_merge_thread(self) -> None:
        """Inicia a operação de união em uma thread em segundo plano."""
        if self.is_merging:
            return

        if not self.merge_files:
            messagebox.showwarning("Aviso", "Adicione pelo menos um arquivo PDF para realizar a união.")
            return

        # Verificar se algum arquivo está protegido por senha
        for item in self.merge_files:
            if item.get("is_encrypted"):
                messagebox.showerror(
                    "Arquivo Protegido",
                    f"O arquivo '{item['filename']}' possui proteção por senha.\n"
                    f"Remova a senha antes de unir os documentos.",
                )
                return

        out_dir = self.merge_output_dir_var.get().strip()
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("Pasta Inválida", "Por favor, selecione uma pasta de destino válida.")
            return

        filename = self.merge_output_name_var.get().strip()
        if not filename:
            filename = "Documentos_Unificados.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        dest_path = os.path.join(out_dir, filename)

        self.is_merging = True
        self.btn_do_merge.configure(state="disabled", text="Unindo PDFs... Aguarde")
        self.merge_status_var.set(f"Processando união de {len(self.merge_files)} arquivo(s)...")

        file_paths = [item["path"] for item in self.merge_files]

        def _worker():
            try:
                pdf_engine.merge_pdfs(file_paths, dest_path)
                self._safe_dispatch(lambda: self._on_merge_completed(dest_path, None))
            except Exception as e:
                self._safe_dispatch(lambda: self._on_merge_completed(dest_path, e))

        self._current_worker = threading.Thread(target=_worker, daemon=True)
        self._current_worker.start()

    def _on_merge_completed(self, output_path: str, error: Optional[Exception]) -> None:
        """Callback executado na thread principal após término da união."""
        self.is_merging = False
        self.btn_do_merge.configure(state="normal", text="⚡ Juntar PDFs Agora")

        if error:
            logger.error(f"Falha ao unir PDFs: {error}")
            self.merge_status_var.set(f"Erro ao unir: {error}")
            messagebox.showerror("Erro na União", f"Ocorreu uma falha ao gerar o arquivo unificado:\n\n{error}")
        else:
            self.merge_status_var.set(f"Sucesso! Arquivo salvo em: {os.path.basename(output_path)}")
            if self.auto_open_folder_var.get():
                reveal_in_explorer(output_path)
            messagebox.showinfo(
                "União Concluída",
                f"PDFs unidos com sucesso!\n\nArquivo gerado:\n{output_path}",
            )

    # =========================================================================
    # ABA 2: SEPARAR / EXTRAIR (SPLIT)
    # =========================================================================

    def _build_split_tab(self) -> None:
        container = ctk.CTkFrame(self.tab_split, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # 1. Seletor Superior de Arquivo PDF de Origem
        top_card = ctk.CTkFrame(container, corner_radius=8)
        top_card.pack(fill="x", pady=(0, 10))

        row_src = ctk.CTkFrame(top_card, fg_color="transparent")
        row_src.pack(fill="x", padx=12, pady=(10, 6))

        lbl_src = ctk.CTkLabel(row_src, text="Arquivo PDF de Origem:", font=ctk.CTkFont(weight="bold"))
        lbl_src.pack(side="left")

        btn_browse_src = ctk.CTkButton(
            row_src,
            text="📂 Selecionar PDF...",
            command=self._browse_split_source,
            width=150,
            font=ctk.CTkFont(weight="bold"),
        )
        btn_browse_src.pack(side="right")

        # Rótulo de informações do documento carregado
        self.lbl_split_doc_info = ctk.CTkLabel(
            top_card,
            textvariable=self.split_source_label_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
            anchor="w",
        )
        self.lbl_split_doc_info.pack(fill="x", padx=12, pady=(0, 10))

        # 2. Corpo Dividido: Esquerda (Visualizador) e Direita (Opções de Extração)
        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Coluna Esquerda: Visualizador de Páginas Folheável
        viewer_frame = ctk.CTkFrame(body, width=340, corner_radius=8)
        viewer_frame.pack(side="left", fill="y", padx=(0, 10))
        viewer_frame.pack_propagate(False)

        lbl_vtitle = ctk.CTkLabel(
            viewer_frame,
            text="Visualizador de Páginas",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_vtitle.pack(padx=10, pady=(10, 4))

        # Contêiner da Miniatura da Página
        self.frame_split_thumb = ctk.CTkFrame(
            viewer_frame,
            fg_color=("gray90", "#242424"),
            corner_radius=6,
            width=250,
            height=320,
        )
        self.frame_split_thumb.pack(padx=15, pady=4)
        self.frame_split_thumb.pack_propagate(False)

        self.lbl_split_thumb = ctk.CTkLabel(
            self.frame_split_thumb,
            text="Nenhum arquivo\ncarregado",
            text_color="gray50",
        )
        self.lbl_split_thumb.pack(expand=True, fill="both")

        # Barra de Navegação: Anterior / Página X de Y / Próxima
        nav_frame = ctk.CTkFrame(viewer_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=6)

        self.btn_split_prev = ctk.CTkButton(
            nav_frame,
            text="◀ Anterior",
            command=self._prev_split_page,
            width=80,
            state="disabled",
        )
        self.btn_split_prev.pack(side="left")

        self.lbl_split_page_ind = ctk.CTkLabel(
            nav_frame,
            textvariable=self.split_page_indicator_var,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_split_page_ind.pack(side="left", expand=True)

        self.btn_split_next = ctk.CTkButton(
            nav_frame,
            text="Próxima ▶",
            command=self._next_split_page,
            width=80,
            state="disabled",
        )
        self.btn_split_next.pack(side="right")

        # Salto rápido de página
        jump_frame = ctk.CTkFrame(viewer_frame, fg_color="transparent")
        jump_frame.pack(fill="x", padx=15, pady=(2, 6))

        lbl_jump = ctk.CTkLabel(jump_frame, text="Ir para página:", font=ctk.CTkFont(size=11))
        lbl_jump.pack(side="left")

        self.entry_split_jump = ctk.CTkEntry(jump_frame, textvariable=self.split_jump_var, width=50)
        self.entry_split_jump.pack(side="left", padx=6)
        self.entry_split_jump.bind("<Return>", lambda e: self._jump_to_split_page())

        btn_jump_go = ctk.CTkButton(
            jump_frame,
            text="Ir",
            command=self._jump_to_split_page,
            width=40,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        btn_jump_go.pack(side="left")

        # Botão de auxílio ergonômico: insere a página atual no campo de extração
        self.btn_insert_page = ctk.CTkButton(
            viewer_frame,
            text="➕ Inserir Página no Intervalo",
            command=self._insert_current_page_to_query,
            height=32,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
            state="disabled",
        )
        self.btn_insert_page.pack(fill="x", padx=15, pady=(4, 10))

        # Coluna Direita: Modos e Opções de Extração
        options_frame = ctk.CTkFrame(body, corner_radius=8)
        options_frame.pack(side="right", fill="both", expand=True)

        lbl_opt_title = ctk.CTkLabel(
            options_frame,
            text="Modos de Divisão e Extração",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_opt_title.pack(padx=15, pady=(12, 8), anchor="w")

        # Modo 1: Extrair páginas específicas
        self.radio_mode_ranges = ctk.CTkRadioButton(
            options_frame,
            text="Modo 1: Extrair páginas específicas em um novo PDF",
            variable=self.split_mode_var,
            value="extract_ranges",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_split_mode_changed,
        )
        self.radio_mode_ranges.pack(padx=15, pady=(4, 6), anchor="w")

        self.frame_mode1_content = ctk.CTkFrame(options_frame, fg_color=("gray92", "#292929"), corner_radius=6)
        self.frame_mode1_content.pack(fill="x", padx=25, pady=(0, 10))

        # Query de páginas
        row_q = ctk.CTkFrame(self.frame_mode1_content, fg_color="transparent")
        row_q.pack(fill="x", padx=10, pady=(8, 4))

        lbl_q = ctk.CTkLabel(row_q, text="Intervalo de Páginas:", width=140, anchor="w")
        lbl_q.pack(side="left")

        self.entry_split_query = ctk.CTkEntry(
            row_q,
            textvariable=self.split_query_var,
            placeholder_text="Ex: 1-3, 5, 8-10",
        )
        self.entry_split_query.pack(side="left", fill="x", expand=True)

        lbl_q_hint = ctk.CTkLabel(
            self.frame_mode1_content,
            text="Dica: Use vírgulas para separar páginas e hífens para intervalos (Ex: 1-3, 5, 8-10).",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            anchor="w",
        )
        lbl_q_hint.pack(fill="x", padx=10, pady=(0, 6))

        # Checkbox unificar ou separar páginas extraídas
        self.chk_merge_extracted = ctk.CTkCheckBox(
            self.frame_mode1_content,
            text="Unir páginas extraídas em um único arquivo PDF",
            variable=self.split_merge_extracted_var,
            font=ctk.CTkFont(size=12),
        )
        self.chk_merge_extracted.pack(padx=10, pady=(0, 6), anchor="w")

        # Nome do arquivo final extraído
        row_m1_name = ctk.CTkFrame(self.frame_mode1_content, fg_color="transparent")
        row_m1_name.pack(fill="x", padx=10, pady=(0, 8))

        lbl_m1_name = ctk.CTkLabel(row_m1_name, text="Nome do PDF Gerado:", width=140, anchor="w")
        lbl_m1_name.pack(side="left")

        self.entry_split_name = ctk.CTkEntry(
            row_m1_name,
            textvariable=self.split_output_name_var,
            placeholder_text="ex: Contrato_extraido.pdf",
        )
        self.entry_split_name.pack(side="left", fill="x", expand=True)

        # Modo 2: Separar todas as páginas (Explodir)
        self.radio_mode_all = ctk.CTkRadioButton(
            options_frame,
            text="Modo 2: Separar todas as páginas em arquivos individuais (Explodir PDF)",
            variable=self.split_mode_var,
            value="split_all",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_split_mode_changed,
        )
        self.radio_mode_all.pack(padx=15, pady=(6, 6), anchor="w")

        self.frame_mode2_content = ctk.CTkFrame(options_frame, fg_color=("gray92", "#292929"), corner_radius=6)
        self.frame_mode2_content.pack(fill="x", padx=25, pady=(0, 10))

        row_pfx = ctk.CTkFrame(self.frame_mode2_content, fg_color="transparent")
        row_pfx.pack(fill="x", padx=10, pady=(8, 4))

        lbl_pfx = ctk.CTkLabel(row_pfx, text="Prefixo dos Arquivos:", width=140, anchor="w")
        lbl_pfx.pack(side="left")

        self.entry_split_prefix = ctk.CTkEntry(
            row_pfx,
            textvariable=self.split_prefix_var,
            placeholder_text="ex: Pagina (gera Pagina_001.pdf, Pagina_002.pdf...)",
        )
        self.entry_split_prefix.pack(side="left", fill="x", expand=True)

        lbl_pfx_hint = ctk.CTkLabel(
            self.frame_mode2_content,
            text="Gera um arquivo PDF separado para cada folha: <Prefixo>_001.pdf, <Prefixo>_002.pdf...",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            anchor="w",
        )
        lbl_pfx_hint.pack(fill="x", padx=10, pady=(0, 8))

        # Pasta de Destino da Extração
        row_split_dir = ctk.CTkFrame(options_frame, fg_color="transparent")
        row_split_dir.pack(fill="x", padx=15, pady=(10, 8))

        lbl_sdir = ctk.CTkLabel(row_split_dir, text="Pasta de Destino:", width=140, anchor="w")
        lbl_sdir.pack(side="left")

        self.entry_split_dir = ctk.CTkEntry(
            row_split_dir,
            textvariable=self.split_output_dir_var,
            placeholder_text="Selecione a pasta onde os arquivos serão salvos",
        )
        self.entry_split_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse_sdir = ctk.CTkButton(
            row_split_dir,
            text="Selecionar Pasta...",
            command=self._browse_split_output_dir,
            width=135,
        )
        btn_browse_sdir.pack(side="right")

        # Botão Principal de Processamento
        self.btn_do_split = ctk.CTkButton(
            options_frame,
            text="✂ Processar Extração",
            command=self._start_split_thread,
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_do_split.pack(fill="x", padx=15, pady=(8, 8))

        # Status da Aba Split
        self.lbl_split_status = ctk.CTkLabel(
            options_frame,
            textvariable=self.split_status_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.lbl_split_status.pack(fill="x", padx=15, pady=(0, 10))

    # =========================================================================
    # Lógica da Aba de Split
    # =========================================================================

    def _browse_split_source(self) -> None:
        """Abre diálogo para seleção do arquivo PDF de origem."""
        chosen = filedialog.askopenfilename(
            title="Selecionar PDF para Divisão / Extração",
            filetypes=[("Arquivos PDF (*.pdf)", "*.pdf"), ("Todos os Arquivos", "*.*")],
        )
        if chosen:
            self._load_split_source(chosen)

    def _load_split_source(self, file_path: str) -> None:
        """Carrega o PDF no visualizador e prepara as opções de extração."""
        path = os.path.abspath(file_path)
        if not os.path.isfile(path) or not path.lower().endswith(".pdf"):
            messagebox.showerror("Arquivo Inválido", f"O arquivo '{file_path}' não é um PDF válido.")
            return

        try:
            info = pdf_engine.get_pdf_info(path, page_number=0)
            if info.get("is_encrypted"):
                messagebox.showerror(
                    "Arquivo Protegido",
                    f"O arquivo '{os.path.basename(path)}' possui proteção por senha.\n"
                    f"Remova a proteção antes de extrair páginas.",
                )
                return

            self.split_source_path = path
            self.split_total_pages = info["page_count"]
            self.split_current_page = 0

            stem = Path(path).stem
            self.split_source_label_var.set(
                f"Documento: {info['filename']}  •  {info['page_count']} páginas  •  {info['file_size_formatted']}"
            )
            self.split_output_dir_var.set(os.path.dirname(path))
            self.split_output_name_var.set(f"{stem}_extraido.pdf")
            self.split_prefix_var.set(stem)
            if self.split_total_pages <= 1:
                self.split_query_var.set("1")
            else:
                self.split_query_var.set(f"1-{min(3, self.split_total_pages)}")

            # Habilitar botões do visualizador
            self.btn_insert_page.configure(state="normal")
            self._update_split_page_display()
            self._on_split_mode_changed()
            self.split_status_var.set(
                f"Documento carregado. Total de {self.split_total_pages} página(s). Selecione as páginas desejadas."
            )
        except Exception as e:
            logger.error(f"Erro ao carregar PDF para split: {e}")
            messagebox.showerror("Erro ao Abrir PDF", f"Falha ao carregar arquivo PDF:\n\n{e}")

    def _update_split_page_display(self) -> None:
        """Renderiza a miniatura da página atual e atualiza controles de navegação."""
        if not self.split_source_path or self.split_total_pages == 0:
            return

        # Ajustar botões de anterior / próximo
        self.btn_split_prev.configure(state="normal" if self.split_current_page > 0 else "disabled")
        self.btn_split_next.configure(
            state="normal" if self.split_current_page < self.split_total_pages - 1 else "disabled"
        )
        self.split_page_indicator_var.set(
            f"Página {self.split_current_page + 1} de {self.split_total_pages}"
        )

        # Renderizar miniatura da página
        try:
            pil_img = pdf_engine.render_page_thumbnail(
                self.split_source_path,
                page_number=self.split_current_page,
                max_size=(230, 300),
            )
            if pil_img:
                ctk_img = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height)
                )
                self._split_thumb_img = ctk_img
                self._set_label_image_or_text(self.lbl_split_thumb, ctk_img, text="")
            else:
                self._split_thumb_img = None
                self._set_label_image_or_text(self.lbl_split_thumb, None, text="Falha ao renderizar miniatura")
        except Exception as e:
            logger.warning(f"Erro ao renderizar página {self.split_current_page}: {e}")
            self._split_thumb_img = None
            self._set_label_image_or_text(self.lbl_split_thumb, None, text="Erro de renderização")

    def _prev_split_page(self) -> None:
        """Navega para a página anterior."""
        if self.split_current_page > 0:
            self.split_current_page -= 1
            self._update_split_page_display()

    def _next_split_page(self) -> None:
        """Navega para a próxima página."""
        if self.split_current_page < self.split_total_pages - 1:
            self.split_current_page += 1
            self._update_split_page_display()

    def _jump_to_split_page(self) -> None:
        """Pula diretamente para a página digitada pelo usuário."""
        raw = self.split_jump_var.get().strip()
        if not raw.isdigit():
            return
        target = int(raw)
        if 1 <= target <= self.split_total_pages:
            self.split_current_page = target - 1
            self._update_split_page_display()
        else:
            messagebox.showwarning(
                "Página Fora dos Limites",
                f"Por favor informe um número de página entre 1 e {self.split_total_pages}.",
            )

    def _insert_current_page_to_query(self) -> None:
        """Insere o número da página atual na caixa de texto do intervalo."""
        curr_page_num = str(self.split_current_page + 1)
        existing = self.split_query_var.get().strip()
        if not existing:
            self.split_query_var.set(curr_page_num)
        else:
            self.split_query_var.set(f"{existing}, {curr_page_num}")
        self.entry_split_query.focus_set()

    def _on_split_mode_changed(self) -> None:
        """Reage à mudança do modo de divisão selecionado alternando o estado dos campos."""
        mode = self.split_mode_var.get()
        if mode == "extract_ranges":
            self.entry_split_query.configure(state="normal")
            self.chk_merge_extracted.configure(state="normal")
            self.entry_split_name.configure(state="normal")
            self.entry_split_prefix.configure(state="disabled")
        else:
            self.entry_split_query.configure(state="disabled")
            self.chk_merge_extracted.configure(state="disabled")
            self.entry_split_name.configure(state="disabled")
            self.entry_split_prefix.configure(state="normal")

    def _browse_split_output_dir(self) -> None:
        """Seleciona a pasta de destino para a extração."""
        initial = self.split_output_dir_var.get() or os.path.expanduser("~")
        dest = filedialog.askdirectory(title="Selecionar Pasta de Destino", initialdir=initial)
        if dest:
            self.split_output_dir_var.set(os.path.abspath(dest))

    def _start_split_thread(self) -> None:
        """Valida e inicia a extração em segundo plano."""
        if self.is_splitting:
            return

        if not self.split_source_path or not os.path.isfile(self.split_source_path):
            messagebox.showwarning("Aviso", "Selecione primeiro um arquivo PDF de origem.")
            return

        out_dir = self.split_output_dir_var.get().strip()
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("Pasta Inválida", "Por favor, selecione uma pasta de destino válida.")
            return

        mode = self.split_mode_var.get()

        if mode == "extract_ranges":
            query = self.split_query_var.get().strip()
            if not query:
                messagebox.showerror("Intervalo Inválido", "Informe as páginas que deseja extrair (ex: 1-3, 5).")
                return

            try:
                pdf_engine.parse_page_query(query, self.split_total_pages)
            except ValueError as ve:
                messagebox.showerror("Intervalo Inválido", str(ve))
                return

            merge_extracted = self.split_merge_extracted_var.get()
            out_name = self.split_output_name_var.get().strip()
            if not out_name:
                out_name = f"{Path(self.split_source_path).stem}_extraido.pdf"
            if not out_name.lower().endswith(".pdf"):
                out_name += ".pdf"

            dest_target = os.path.join(out_dir, out_name)

            self.is_splitting = True
            self.btn_do_split.configure(state="disabled", text="Extraindo páginas... Aguarde")
            self.split_status_var.set("Processando extração de páginas...")

            def _worker():
                try:
                    generated = pdf_engine.extract_pages(
                        file_path=self.split_source_path,
                        page_query=query,
                        output_path=dest_target,
                        merge_extracted=merge_extracted,
                    )
                    self._safe_dispatch(lambda: self._on_split_completed(generated, None))
                except Exception as e:
                    self._safe_dispatch(lambda: self._on_split_completed([], e))

            self._current_worker = threading.Thread(target=_worker, daemon=True)
            self._current_worker.start()

        else:
            # Modo 2: Separar todas as páginas
            prefix = self.split_prefix_var.get().strip() or Path(self.split_source_path).stem

            self.is_splitting = True
            self.btn_do_split.configure(state="disabled", text="Dividindo todas as páginas... Aguarde")
            self.split_status_var.set(f"Dividindo {self.split_total_pages} página(s) em arquivos individuais...")

            def _worker():
                try:
                    generated = pdf_engine.split_all_pages(
                        file_path=self.split_source_path,
                        output_dir=out_dir,
                        prefix=prefix,
                    )
                    self._safe_dispatch(lambda: self._on_split_completed(generated, None))
                except Exception as e:
                    self._safe_dispatch(lambda: self._on_split_completed([], e))

            self._current_worker = threading.Thread(target=_worker, daemon=True)
            self._current_worker.start()

    def _on_split_completed(self, generated_files: List[str], error: Optional[Exception]) -> None:
        """Callback executado ao término da divisão/extração."""
        self.is_splitting = False
        self.btn_do_split.configure(state="normal", text="✂ Processar Extração")

        if error:
            logger.error(f"Erro na extração de páginas: {error}")
            self.split_status_var.set(f"Erro na extração: {error}")
            messagebox.showerror("Falha na Extração", f"Ocorreu um erro ao processar o PDF:\n\n{error}")
        else:
            count = len(generated_files)
            self.split_status_var.set(f"Sucesso! {count} arquivo(s) gerado(s).")
            if generated_files and self.auto_open_folder_var.get():
                reveal_in_explorer(generated_files[0])
            messagebox.showinfo(
                "Extração Concluída",
                f"Operação concluída com sucesso!\n\nForam gerados {count} arquivo(s) na pasta:\n{self.split_output_dir_var.get()}",
            )

    # =========================================================================
    # ABA 3: CONFIGURAÇÕES / SISTEMA
    # =========================================================================

    def _build_settings_tab(self) -> None:
        container = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # 1. Integração com o Menu de Contexto do Windows Explorer
        card_reg = ctk.CTkFrame(container, corner_radius=8)
        card_reg.pack(fill="x", pady=(0, 15))

        lbl_reg_head = ctk.CTkLabel(
            card_reg,
            text="Integração com o Menu de Contexto (Windows Explorer)",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl_reg_head.pack(padx=15, pady=(15, 6), anchor="w")

        lbl_reg_desc = ctk.CTkLabel(
            card_reg,
            text=(
                "Adiciona comandos ao botão direito para arquivos PDF e pastas no Windows Explorer:\n"
                " • Juntar PDFs no DocForge\n"
                " • Merge Rápido (Auto-Ordem para Scans)\n"
                " • Separar / Extrair Páginas\n"
                " • Juntar todos os PDFs desta pasta\n"
                "Instalação 100% segura no perfil de usuário (HKCU), sem exigir privilégios de Administrador."
            ),
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
            justify="left",
            anchor="w",
        )
        lbl_reg_desc.pack(padx=15, pady=(0, 10), fill="x")

        # Indicador de Status do Menu
        row_reg_status = ctk.CTkFrame(card_reg, fg_color="transparent")
        row_reg_status.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_reg_status_badge = ctk.CTkLabel(
            row_reg_status,
            text="Verificando status...",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_reg_status_badge.pack(side="left")

        # Botões de Instalação / Remoção / Alternância
        row_reg_btns = ctk.CTkFrame(card_reg, fg_color="transparent")
        row_reg_btns.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_reg_toggle = ctk.CTkButton(
            row_reg_btns,
            text="Ativar/Desativar Menu do Botão Direito no Windows",
            command=self._toggle_context_menu,
            width=320,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_reg_toggle.pack(side="left", padx=(0, 10))

        self.btn_reg_install = ctk.CTkButton(
            row_reg_btns,
            text="Instalar",
            command=self._install_context_menu,
            width=100,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        self.btn_reg_install.pack(side="left", padx=(0, 6))

        self.btn_reg_remove = ctk.CTkButton(
            row_reg_btns,
            text="Remover",
            command=self._uninstall_context_menu,
            width=100,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
        )
        self.btn_reg_remove.pack(side="left")

        # 2. Preferências Gerais
        card_pref = ctk.CTkFrame(container, corner_radius=8)
        card_pref.pack(fill="x", pady=(0, 15))

        lbl_pref_head = ctk.CTkLabel(
            card_pref,
            text="Preferências Gerais",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl_pref_head.pack(padx=15, pady=(15, 10), anchor="w")

        # Switch de abrir pasta automaticamente
        self.switch_auto_open = ctk.CTkSwitch(
            card_pref,
            text="Abrir pasta de destino automaticamente após concluir operações",
            variable=self.auto_open_folder_var,
            font=ctk.CTkFont(size=12),
        )
        self.switch_auto_open.pack(padx=15, pady=(0, 12), anchor="w")

        # Seletor de Tema
        row_theme = ctk.CTkFrame(card_pref, fg_color="transparent")
        row_theme.pack(fill="x", padx=15, pady=(0, 15))

        lbl_theme = ctk.CTkLabel(row_theme, text="Tema Visual da Interface:", width=180, anchor="w")
        lbl_theme.pack(side="left")

        self.opt_theme = ctk.CTkOptionMenu(
            row_theme,
            values=["Dark", "Light", "System"],
            variable=self.current_theme_var,
            command=self._on_theme_changed,
            width=120,
        )
        self.opt_theme.pack(side="left")

        # 3. Informações Sobre o Aplicativo
        card_about = ctk.CTkFrame(container, corner_radius=8)
        card_about.pack(fill="x", pady=(0, 10))

        lbl_about_head = ctk.CTkLabel(
            card_about,
            text="Sobre o DocForge PDF",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl_about_head.pack(padx=15, pady=(15, 6), anchor="w")

        lbl_about_body = ctk.CTkLabel(
            card_about,
            text=(
                "DocForge PDF - Ferramenta Especializada em União e Extração de Documentos\n"
                "Versão: 1.0.0 (Produção)\n"
                "Motor PDF: PyMuPDF (fitz) de Alta Performance\n"
                "Interface: CustomTkinter\n\n"
                "🔒 Privacidade Garantida: Toda a manipulação de documentos é realizada localmente na sua máquina.\n"
                "Nenhum arquivo ou dado é enviado para servidores externos."
            ),
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
            justify="left",
            anchor="w",
        )
        lbl_about_body.pack(padx=15, pady=(0, 15), fill="x")

        # Atualizar exibição inicial do status do registro
        self._refresh_context_menu_status()

    # =========================================================================
    # Lógica da Aba de Configurações
    # =========================================================================

    def _refresh_context_menu_status(self) -> None:
        """Atualiza a badge e botões de acordo com o registro do menu no Windows HKCU."""
        if not win_registry.is_windows():
            self.lbl_reg_status_badge.configure(
                text=f"• Indisponível no sistema operacional atual ({sys.platform}). Disponível nativamente no Windows.",
                text_color="gray50",
            )
            self.btn_reg_toggle.configure(state="disabled")
            self.btn_reg_install.configure(state="disabled")
            self.btn_reg_remove.configure(state="disabled")
            return

        is_registered = win_registry.is_context_menu_registered()
        if is_registered:
            self.lbl_reg_status_badge.configure(
                text="✔ Status: Menu de Contexto ATIVO no Windows Explorer",
                text_color="#2fa572",
            )
            self.btn_reg_toggle.configure(state="normal", text="Desativar Menu do Botão Direito")
            self.btn_reg_install.configure(state="disabled", text="Menu Já Ativado")
            self.btn_reg_remove.configure(state="normal")
        else:
            self.lbl_reg_status_badge.configure(
                text="✖ Status: Menu de Contexto INATIVO",
                text_color="#e26d5c",
            )
            self.btn_reg_toggle.configure(state="normal", text="Ativar Menu do Botão Direito no Windows")
            self.btn_reg_install.configure(state="normal", text="Instalar")
            self.btn_reg_remove.configure(state="disabled")

    def _toggle_context_menu(self) -> None:
        """Alterna o registro do menu de contexto no Windows Explorer."""
        if not win_registry.is_windows():
            messagebox.showinfo("Aviso", "A integração com o Registro está disponível apenas no ambiente Windows.")
            return
        if win_registry.is_context_menu_registered():
            self._uninstall_context_menu()
        else:
            self._install_context_menu()

    def _install_context_menu(self) -> None:
        """Registra as chaves de menu de contexto no Registro do Windows."""
        ok, msg = win_registry.register_context_menu()
        self._refresh_context_menu_status()
        if ok:
            messagebox.showinfo("Sucesso", msg)
        else:
            messagebox.showerror("Falha no Registro", msg)

    def _uninstall_context_menu(self) -> None:
        """Remove as chaves de menu de contexto do Registro do Windows."""
        ok, msg = win_registry.unregister_context_menu()
        self._refresh_context_menu_status()
        if ok:
            messagebox.showinfo("Sucesso", msg)
        else:
            messagebox.showerror("Falha ao Remover", msg)

    # =========================================================================
    # Inicialização com Dados Externos (CLI / IPC / Explorer)
    # =========================================================================

    def _load_initial_data(
        self,
        initial_files: Optional[List[str]] = None,
        initial_action: str = "merge",
    ) -> None:
        """Carrega arquivos e seleciona a aba correta com base nos parâmetros recebidos."""
        files = initial_files or []

        if initial_action == "split":
            self.tabview.set("Separar / Extrair (Split)")
            if files:
                self._load_split_source(files[0])
        else:
            self.tabview.set("Juntar (Merge)")
            if files:
                self._add_files(files)
