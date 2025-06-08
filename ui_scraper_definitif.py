# -*- coding: utf-8 -*-
"""Simple interface to pick a description block from a local HTML file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QFileDialog,
)

from html_block_selector import BlocSelectionWindow


class ScraperWindow(QWidget):
    """GUI opening a secondary window to analyse HTML blocks."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Extraction description")

        self.load_btn = QPushButton("Charger HTML local")
        self.mapping_edit = QTextEdit()
        self.mapping_edit.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.load_btn)
        layout.addWidget(QLabel("Mapping JSON:"))
        layout.addWidget(self.mapping_edit)

        self.load_btn.clicked.connect(self.load_html)
        self._selector_window: Optional[BlocSelectionWindow] = None

    # ------------------------------------------------------------------
    def load_html(self) -> None:
        """Open a local HTML file and start block selection."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Fichier HTML", "", "HTML (*.html *.htm)"
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        self._selector_window = BlocSelectionWindow(text, self.receive_block)
        self._selector_window.resize(800, 600)
        self._selector_window.show()

    # ------------------------------------------------------------------
    def receive_block(self, selector: str, _text: str) -> None:
        """Receive selected block from the secondary window."""
        mapping = {"description": selector}
        self.mapping_edit.setPlainText(
            json.dumps(mapping, indent=2, ensure_ascii=False)
        )


def main() -> None:  # pragma: no cover - manual execution
    app = QApplication([])
    win = ScraperWindow()
    win.resize(400, 200)
    win.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
