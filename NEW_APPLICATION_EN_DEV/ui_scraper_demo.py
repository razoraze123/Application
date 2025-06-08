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
from PySide6.QtCore import QUrl, QObject, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from pathlib import Path

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


BROWSER_SCRIPT = """
new QWebChannel(qt.webChannelTransport, function (channel) {
  const pyReceiver = channel.objects.qt;

  function getCssSelector(el) {
    const path = [];
    while (el.nodeType === Node.ELEMENT_NODE) {
      let selector = el.nodeName.toLowerCase();
      if (el.id) {
        selector += `#${el.id}`;
        path.unshift(selector);
        break;
      }
      if (el.className) {
        const classes = el.className.trim().split(/\s+/);
        if (classes.length) selector += '.' + classes.join('.');
      }
      const parent = el.parentNode;
      if (parent) {
        const siblings = Array.from(parent.children).filter(e => e.tagName === el.tagName);
        if (siblings.length > 1) {
          const index = siblings.indexOf(el) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      path.unshift(selector);
      el = el.parentNode;
    }
    return path.join(' > ');
  }

  document.body.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    const el = e.target;
    const selector = getCssSelector(el);
    const text = el.innerText.trim();
    el.style.outline = '2px solid red';
    setTimeout(() => (el.style.outline = ''), 800);
    pyReceiver.receiveElementInfo(selector, text);
  }, { capture: true });
});
"""


class ElementReceiver(QObject):
    """Exposed object receiving element information from JS."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @Slot(str, str)
    def receiveElementInfo(self, selector: str, text: str) -> None:
        if self.parent():
            self.parent().update_preview(selector, text)


class ScraperDemo(QWidget):
    """Minimal GUI to test the universal scraper with an interactive browser."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraper demo")

        self.url_edit = QLineEdit()
        self.load_btn = QPushButton("Charger")
        self.mapping_edit = QTextEdit()
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setLineWrapMode(QTextEdit.NoWrap)

        self.selector_edit = QLineEdit()
        self.selector_edit.setReadOnly(True)
        self.text_edit = QLineEdit()
        self.text_edit.setReadOnly(True)
        self.field_edit = QLineEdit()
        self.add_btn = QPushButton("Ajouter au mapping")

        self.web_view = QWebEngineView()

        self.scrap_btn = QPushButton("Scraper")
        self.example_btn = QPushButton("Exemple")

        self.scrap_btn.clicked.connect(self.run_scrape)
        self.example_btn.clicked.connect(self.fill_example)
        self.load_btn.clicked.connect(self.load_page)
        self.add_btn.clicked.connect(self.add_mapping)

        self.channel = QWebChannel()
        self.receiver = ElementReceiver(self)
        self.channel.registerObject("qt", self.receiver)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self.inject_script)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        url_row.addWidget(self.url_edit)
        url_row.addWidget(self.load_btn)

        btns = QHBoxLayout()
        btns.addWidget(self.example_btn)
        btns.addStretch()
        btns.addWidget(self.scrap_btn)

        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Nom du champ:"))
        add_row.addWidget(self.field_edit)
        add_row.addWidget(self.add_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(url_row)
        layout.addWidget(QLabel("Mapping JSON:"))
        layout.addWidget(self.mapping_edit)
        layout.addLayout(btns)
        layout.addWidget(QLabel("Sélecteur:"))
        layout.addWidget(self.selector_edit)
        layout.addWidget(QLabel("Texte:"))
        layout.addWidget(self.text_edit)
        layout.addLayout(add_row)
        layout.addWidget(QLabel("Résultat:"))
        layout.addWidget(self.result_edit)
        layout.addWidget(self.web_view)

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

    # ------------------------------------------------------------------
    def load_page(self) -> None:
        """Load the URL in the integrated browser."""
        url = self.url_edit.text().strip()
        if url:
            self.web_view.load(QUrl(url))

    # ------------------------------------------------------------------
    def inject_script(self) -> None:
        """Inject the click capture script into the loaded page."""
        qwc_js = ""
        try:
            path = Path(__file__).resolve().parents[1] / "qwebchannel.js"
            with open(path, "r", encoding="utf-8") as f:
                qwc_js = f.read()
        except Exception:
            pass
        self.web_view.page().runJavaScript(
            qwc_js, lambda _: self.web_view.page().runJavaScript(BROWSER_SCRIPT)
        )

    # ------------------------------------------------------------------
    def update_preview(self, selector: str, text: str) -> None:
        """Display selected element information."""
        self.selector_edit.setText(selector)
        self.text_edit.setText(text)

    # ------------------------------------------------------------------
    def add_mapping(self) -> None:
        """Add the selected selector to the mapping JSON."""
        key = self.field_edit.text().strip()
        selector = self.selector_edit.text()
        if not key or not selector:
            return
        try:
            mapping = json.loads(self.mapping_edit.toPlainText() or "{}")
        except Exception:
            mapping = {}
        mapping[key] = selector
        self.mapping_edit.setPlainText(
            json.dumps(mapping, indent=2, ensure_ascii=False)
        )
        self.field_edit.clear()


if __name__ == "__main__":  # pragma: no cover - manual launch
    app = QApplication([])
    win = ScraperDemo()
    win.show()
    app.exec()
