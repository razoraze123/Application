"""Secondary window to inspect HTML and pick a description block."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextBrowser,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
)

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
def build_css_selector(el: Any) -> str:
    """Return a CSS selector for ``el`` by walking up the DOM tree."""
    path: List[str] = []
    while el and getattr(el, "name", None) and el.name != "[document]":
        selector = el.name
        el_id = el.get("id")
        if el_id:
            selector += f"#{el_id}"
            path.insert(0, selector)
            break
        classes = el.get("class") or []
        if classes:
            selector += "." + ".".join(classes)
        parent = getattr(el, "parent", None)
        if parent:
            siblings = [sib for sib in parent.find_all(el.name, recursive=False)]
            if len(siblings) > 1:
                index = siblings.index(el) + 1
                selector += f":nth-of-type({index})"
        path.insert(0, selector)
        el = parent
    return " > ".join(path)


class BlocSelectionWindow(QWidget):
    """Window used to visualise HTML blocks and select one."""

    def __init__(
        self,
        html: str,
        on_use: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Analyse HTML - Description produit")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._on_use = on_use

        self.html_view = QTextBrowser()
        self.blocks_list = QListWidget()
        self.selector_edit = QLineEdit()
        self.selector_edit.setReadOnly(True)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.use_btn = QPushButton("Utiliser ce bloc")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Aperçu du HTML brut:"))
        layout.addWidget(self.html_view, 1)
        layout.addWidget(QLabel("Liste des blocs détectés:"))
        layout.addWidget(self.blocks_list, 1)
        layout.addWidget(QLabel("Sélecteur CSS:"))
        layout.addWidget(self.selector_edit)
        layout.addWidget(QLabel("Texte extrait:"))
        layout.addWidget(self.text_edit, 1)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.use_btn)
        layout.addLayout(btn_row)

        self.blocks_list.currentRowChanged.connect(self._show_candidate)
        self.use_btn.clicked.connect(self._use_current)

        self._candidates: List[Dict[str, str]] = []
        self._parse_html(html)

    # ------------------------------------------------------------------
    def _parse_html(self, html: str) -> None:
        self.html_view.setHtml(html)
        soup = BeautifulSoup(html, "lxml")
        tags = ["div", "p", "section", "article", "span"]
        ignored = {"footer", "nav", "header", "menu"}
        for tag in soup.find_all(tags):
            if tag.name in ignored:
                continue
            if any(parent.name in ignored for parent in tag.parents):
                continue
            text = tag.get_text(" ", strip=True)
            if len(text.split()) <= 80:
                continue
            selector = build_css_selector(tag)
            snippet = text[:200] + ("..." if len(text) > 200 else "")
            self._candidates.append({"selector": selector, "text": text})
            self.blocks_list.addItem(QListWidgetItem(snippet))

    # ------------------------------------------------------------------
    def _show_candidate(self, index: int) -> None:
        if index < 0 or index >= len(self._candidates):
            self.selector_edit.clear()
            self.text_edit.clear()
            return
        cand = self._candidates[index]
        self.selector_edit.setText(cand["selector"])
        self.text_edit.setPlainText(cand["text"])

    # ------------------------------------------------------------------
    def _use_current(self) -> None:
        idx = self.blocks_list.currentRow()
        if idx < 0 or idx >= len(self._candidates):
            return
        selector = self._candidates[idx]["selector"]
        text = self._candidates[idx]["text"]
        if self._on_use:
            self._on_use(selector, text)
        QGuiApplication.clipboard().setText(selector)

