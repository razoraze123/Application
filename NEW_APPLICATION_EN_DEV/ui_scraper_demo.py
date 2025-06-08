from __future__ import annotations

import json
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
)

import sys
import os

# Make sure the scraper module is importable when launched from this folder or
# its parent directory.
sys.path.append(os.path.dirname(__file__))
try:  # Try local import first
    from scraper_universel import extract_fields
except ModuleNotFoundError:  # Fallback when launched from parent directory
    sys.path.append(os.path.join(os.path.dirname(__file__), "NEW_APPLICATION_EN_DEV"))
    from scraper_universel import extract_fields


class ScraperDemo(QWidget):
    """Minimal GUI to test the universal scraper."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraper demo")

        self.url_edit = QLineEdit()
        self.mapping_edit = QTextEdit()
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setLineWrapMode(QTextEdit.NoWrap)

        self.scrap_btn = QPushButton("Scraper")
        self.example_btn = QPushButton("Exemple")

        self.scrap_btn.clicked.connect(self.run_scrape)
        self.example_btn.clicked.connect(self.fill_example)

        btns = QHBoxLayout()
        btns.addWidget(self.example_btn)
        btns.addStretch()
        btns.addWidget(self.scrap_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_edit)
        layout.addWidget(QLabel("Mapping JSON:"))
        layout.addWidget(self.mapping_edit)
        layout.addLayout(btns)
        layout.addWidget(QLabel("Résultat:"))
        layout.addWidget(self.result_edit)

    # ------------------------------------------------------------------
    def fill_example(self) -> None:
        """Fill in demo values for Books to Scrape."""
        demo_url = (
            "https://books.toscrape.com/catalogue/"
            "a-light-in-the-attic_1000/index.html"
        )
        demo_mapping = {
            "titre": "h1",
            "prix": ".price_color",
            "disponibilite": "//p[contains(@class,'instock')]",
        }
        self.url_edit.setText(demo_url)
        self.mapping_edit.setPlainText(
            json.dumps(demo_mapping, indent=2, ensure_ascii=False)
        )

    # ------------------------------------------------------------------
    def run_scrape(self) -> None:
        """Run the scraper using the provided URL and mapping."""
        url = self.url_edit.text().strip()
        mapping_text = self.mapping_edit.toPlainText()
        if not url:
            self.result_edit.setPlainText("URL manquante")
            return
        try:
            mapping = json.loads(mapping_text)
        except Exception as exc:
            self.result_edit.setPlainText(f"Mapping invalide: {exc}")
            return

        try:
            data = extract_fields(url, mapping)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            self.result_edit.setPlainText(formatted)
        except Exception as exc:  # pragma: no cover - network or parser issue
            self.result_edit.setPlainText(f"Erreur: {exc}")


if __name__ == "__main__":  # pragma: no cover - manual launch
    app = QApplication([])
    win = ScraperDemo()
    win.show()
    app.exec()
