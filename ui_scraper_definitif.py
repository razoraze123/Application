# -*- coding: utf-8 -*-
"""Interactive scraper interface using QWebEngineView and QWebChannel."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView


# Disable the sandbox to avoid restrictions in some environments
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")


BROWSER_SCRIPT = r"""
console.log('JS inject\u00e9');
new QWebChannel(qt.webChannelTransport, function (channel) {
  console.log('WebChannel ready', channel.objects);
  const pyReceiver = channel.objects.qt;
  if (!pyReceiver) {
    console.error('pyReceiver non d\u00e9fini');
    return;
  }

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
        const sibs = Array.from(parent.children).filter(
          e => e.tagName === el.tagName
        );
        if (sibs.length > 1) {
          const index = sibs.indexOf(el) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      path.unshift(selector);
      el = el.parentNode;
    }
    return path.join(' > ');
  }

  document.addEventListener(
    'click',
    function (e) {
      e.preventDefault();
      e.stopPropagation();
      const el = e.target;
      const selector = getCssSelector(el);
      const text = el.innerText.trim();
      el.style.outline = '2px solid red';
      setTimeout(() => (el.style.outline = ''), 800);
      console.log('Element cliqu\u00e9', selector, text);
      pyReceiver.receiveElementInfo(selector, text);
    },
    true
  );
});
"""


class ElementReceiver(QObject):
    """Receive element information from the injected JS."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    @Slot(str, str)
    def receiveElementInfo(self, selector: str, text: str) -> None:
        print(f"Received: {selector} -> {text}")
        if self.parent():
            self.parent().update_preview(selector, text)


class ScraperWindow(QWidget):
    """Main window integrating the browser and mapping helpers."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraper d\u00e9finitif")

        self.url_edit = QLineEdit()
        self.load_btn = QPushButton("Charger")
        self.inject_btn = QPushButton("Injecter script")

        self.selector_edit = QLineEdit()
        self.selector_edit.setReadOnly(True)
        self.text_edit = QLineEdit()
        self.text_edit.setReadOnly(True)

        self.mapping_edit = QTextEdit()

        self.web_view = QWebEngineView()
        self._script_added = False

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("URL:"))
        top_row.addWidget(self.url_edit)
        top_row.addWidget(self.load_btn)
        top_row.addWidget(self.inject_btn)

        info_row = QVBoxLayout()
        info_row.addWidget(QLabel("S\u00e9lecteur:"))
        info_row.addWidget(self.selector_edit)
        info_row.addWidget(QLabel("Texte:"))
        info_row.addWidget(self.text_edit)
        info_row.addWidget(QLabel("Mapping JSON:"))
        info_row.addWidget(self.mapping_edit)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addLayout(info_row)
        layout.addWidget(self.web_view)

        self.channel = QWebChannel()
        self.receiver = ElementReceiver(self)
        self.channel.registerObject("qt", self.receiver)
        self.web_view.page().setWebChannel(self.channel)

        self.load_btn.clicked.connect(self.load_page)
        self.inject_btn.clicked.connect(self.inject_script)
        self.web_view.loadFinished.connect(self.inject_script)

    # -------------------------------------------------------------
    def load_page(self) -> None:
        url = self.url_edit.text().strip()
        if url:
            self._script_added = False
            self.web_view.load(QUrl(url))

    # -------------------------------------------------------------
    def inject_script(self) -> None:
        if self._script_added:
            return
        qwc_js = ""
        try:
            path = Path(__file__).resolve().parent / "qwebchannel.js"
            qwc_js = path.read_text(encoding="utf-8")
        except OSError:
            pass
        script = QWebEngineScript()
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setRunsOnSubFrames(False)
        script.setSourceCode("\n".join([qwc_js, BROWSER_SCRIPT]))

        def do_insert() -> None:
            self.web_view.page().scripts().insert(script)
            self._script_added = True

        QTimer.singleShot(100, do_insert)

    # -------------------------------------------------------------
    def update_preview(self, selector: str, text: str) -> None:
        self.selector_edit.setText(selector)
        self.text_edit.setText(text)
        field = selector.split(" > ")[-1].split("#")[0].split(".")[0]
        try:
            mapping = json.loads(self.mapping_edit.toPlainText() or "{}")
        except Exception:
            mapping = {}
        mapping[field] = selector
        self.mapping_edit.setPlainText(
            json.dumps(mapping, indent=2, ensure_ascii=False)
        )


def main() -> None:
    app = QApplication([])
    win = ScraperWindow()
    win.resize(900, 600)
    win.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
