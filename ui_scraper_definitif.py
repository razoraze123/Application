# -*- coding: utf-8 -*-
"""Simple interface to extract product descriptions from a local HTML file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QLineEdit,
    QTextEdit,
    QFileDialog,
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


class ScraperWindow(QWidget):
    """GUI to pick a description block from a static HTML file."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Extraction description")

        self.load_btn = QPushButton("Charger HTML local")
        self.html_view = QTextBrowser()
        self.blocks_list = QListWidget()
        self.selector_edit = QLineEdit()
        self.selector_edit.setReadOnly(True)
        self.use_btn = QPushButton("Utiliser ce bloc")
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.mapping_edit = QTextEdit()
        self.mapping_edit.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.load_btn)
        layout.addWidget(QLabel("Contenu HTML:"))
        layout.addWidget(self.html_view, 1)
        layout.addWidget(QLabel("Blocs détectés:"))
        layout.addWidget(self.blocks_list, 1)
        layout.addWidget(QLabel("Sélecteur:"))
        layout.addWidget(self.selector_edit)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.use_btn)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel("Texte extrait:"))
        layout.addWidget(self.result_edit)
        layout.addWidget(QLabel("Mapping JSON:"))
        layout.addWidget(self.mapping_edit)

        self.load_btn.clicked.connect(self.load_html)
        self.blocks_list.currentRowChanged.connect(self.show_candidate)
        self.use_btn.clicked.connect(self.use_current_block)

        self._candidates: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def load_html(self) -> None:
        """Open a local HTML file and parse candidate blocks."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Fichier HTML", "", "HTML (*.html *.htm)"
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        self.html_view.setHtml(text)
        self._parse_candidates(text)

    # ------------------------------------------------------------------
    def _parse_candidates(self, html: str) -> None:
        soup = BeautifulSoup(html, "lxml")
        tags = ["div", "p", "section", "article", "span"]
        self.blocks_list.clear()
        self._candidates.clear()
        for tag in soup.find_all(tags):
            txt = tag.get_text(" ", strip=True)
            if len(txt) >= 100:
                selector = build_css_selector(tag)
                snippet = txt[:120] + ("..." if len(txt) > 120 else "")
                self._candidates.append({"selector": selector, "text": txt})
                self.blocks_list.addItem(QListWidgetItem(snippet))

    # ------------------------------------------------------------------
    def show_candidate(self, index: int) -> None:
        if index < 0 or index >= len(self._candidates):
            self.selector_edit.clear()
            self.result_edit.clear()
            return
        cand = self._candidates[index]
        self.selector_edit.setText(cand["selector"])
        self.result_edit.setPlainText(cand["text"])

    # ------------------------------------------------------------------
    def use_current_block(self) -> None:
        idx = self.blocks_list.currentRow()
        if idx < 0 or idx >= len(self._candidates):
            return
        selector = self._candidates[idx]["selector"]
        mapping = {"description": selector}
        self.mapping_edit.setPlainText(
            json.dumps(mapping, indent=2, ensure_ascii=False)
        )


def main() -> None:  # pragma: no cover - manual execution
    app = QApplication([])
    win = ScraperWindow()
    win.resize(800, 600)
    win.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
