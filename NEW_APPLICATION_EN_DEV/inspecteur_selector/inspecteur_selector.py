"""Mini navigateur pour récupérer un sélecteur CSS et tester le scraping."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict

from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QAction, QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# Import du module de scraping existant
# Lorsque le script est exécuté directement, l'import relatif ci-dessous ne
# fonctionne pas car `__package__` est vide. On ajoute alors dynamiquement le
# dossier parent au `sys.path` pour pouvoir importer ``scraper_liens``.
if __package__:
    from ..scraper_liens import scrape_links  # type: ignore
else:  # exécution directe du fichier
    CURRENT_DIR = Path(__file__).resolve().parent
    PARENT_DIR = CURRENT_DIR.parent
    sys.path.insert(0, str(PARENT_DIR))
    from scraper_liens import scrape_links


class ScrapingThread(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, url: str, selector: str) -> None:
        super().__init__()
        self.url = url
        self.selector = selector

    def run(self) -> None:  # pragma: no cover - threads hard to test
        try:
            links = scrape_links(self.url, self.selector)
            self.finished.emit(links)
        except Exception as exc:  # pragma: no cover - show error
            self.error.emit(str(exc))


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "load": "Load",
        "use_selector": "Use this selector",
        "selector": "CSS selector:",
        "scrape": "Scrape",
        "export_txt": "Export TXT",
        "export_csv": "Export CSV",
        "links": "Extracted links:",
        "theme": "Theme",
        "dark": "Dark",
        "light": "Light",
        "language": "Language",
        "english": "English",
        "french": "Français",
    },
    "fr": {
        "load": "Charger",
        "use_selector": "Utiliser ce sélecteur",
        "selector": "Sélecteur CSS :",
        "scrape": "Lancer le scraping",
        "export_txt": "Exporter TXT",
        "export_csv": "Exporter CSV",
        "links": "Liens extraits :",
        "theme": "Thème",
        "dark": "Sombre",
        "light": "Clair",
        "language": "Langue",
        "english": "English",
        "french": "Français",
    },
}


class BrowserInspector(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "fr"
        self.setWindowTitle("Inspecteur de Sélecteur")

        central = QWidget()
        self.setCentralWidget(central)
        vlayout = QVBoxLayout(central)

        url_layout = QHBoxLayout()
        self.url_edit = QLineEdit("https://")
        self.load_button = QPushButton()
        self.load_button.clicked.connect(self.load_page)
        url_layout.addWidget(self.url_edit)
        url_layout.addWidget(self.load_button)
        vlayout.addLayout(url_layout)

        self.view = QWebEngineView()
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        vlayout.addWidget(self.view)

        sel_layout = QHBoxLayout()
        self.selector_label = QLabel()
        self.selector_edit = QLineEdit()
        self.scrape_button = QPushButton()
        sel_layout.addWidget(self.selector_label)
        sel_layout.addWidget(self.selector_edit)
        sel_layout.addWidget(self.scrape_button)
        vlayout.addLayout(sel_layout)

        btn_layout = QHBoxLayout()
        self.export_txt_button = QPushButton()
        self.export_csv_button = QPushButton()
        btn_layout.addWidget(self.export_txt_button)
        btn_layout.addWidget(self.export_csv_button)
        vlayout.addLayout(btn_layout)

        self.links_label = QLabel()
        vlayout.addWidget(self.links_label)
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        vlayout.addWidget(self.result_edit)

        self.links: List[str] = []
        self.thread: ScrapingThread | None = None

        self.export_txt_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)

        self.load_button.clicked.connect(self.load_page)
        self.scrape_button.clicked.connect(self.handle_scrape)
        self.export_txt_button.clicked.connect(self.export_txt)
        self.export_csv_button.clicked.connect(self.export_csv)

        self._setup_menu()
        self.set_language("fr")

    # ----- internationalisation -----
    def set_language(self, lang: str) -> None:
        self.language = lang
        t = TRANSLATIONS[lang]
        self.load_button.setText(t["load"])
        self.scrape_button.setText(t["scrape"])
        self.selector_label.setText(t["selector"])
        self.export_txt_button.setText(t["export_txt"])
        self.export_csv_button.setText(t["export_csv"])
        self.links_label.setText(t["links"])
        self.dark_action.setText(t["dark"])
        self.light_action.setText(t["light"])
        self.theme_menu.setTitle(t["theme"])
        self.lang_menu.setTitle(t["language"])
        self.fr_action.setText(t["french"])
        self.en_action.setText(t["english"])

    # ----- menu/theme -----
    def _setup_menu(self) -> None:
        menubar = self.menuBar()
        self.theme_menu = menubar.addMenu(TRANSLATIONS[self.language]["theme"])
        self.dark_action = QAction("Sombre", self, checkable=True)
        self.light_action = QAction("Clair", self, checkable=True)
        self.theme_menu.addAction(self.dark_action)
        self.theme_menu.addAction(self.light_action)
        self.dark_action.triggered.connect(
            lambda: self.load_style("dark.qss")
        )
        self.light_action.triggered.connect(
            lambda: self.load_style("light.qss")
        )
        self.light_action.setChecked(True)
        self.load_style("light.qss")

        self.lang_menu = menubar.addMenu(
            TRANSLATIONS[self.language]["language"]
        )
        self.fr_action = QAction("Français", self, checkable=True)
        self.en_action = QAction("English", self, checkable=True)
        self.lang_menu.addAction(self.fr_action)
        self.lang_menu.addAction(self.en_action)
        self.fr_action.triggered.connect(lambda: self.change_lang("fr"))
        self.en_action.triggered.connect(lambda: self.change_lang("en"))
        self.fr_action.setChecked(True)

    def change_lang(self, lang: str) -> None:
        if lang == "fr":
            self.fr_action.setChecked(True)
            self.en_action.setChecked(False)
        else:
            self.fr_action.setChecked(False)
            self.en_action.setChecked(True)
        self.set_language(lang)

    def load_style(self, fname: str) -> None:
        path = Path(__file__).resolve().parent.parent / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        if "dark" in fname:
            self.dark_action.setChecked(True)
            self.light_action.setChecked(False)
        else:
            self.dark_action.setChecked(False)
            self.light_action.setChecked(True)

    # ----- actions -----
    def load_page(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        self.view.setUrl(QUrl(url))

    def show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        use_action = menu.addAction(
            TRANSLATIONS[self.language]["use_selector"]
        )
        action = menu.exec_(self.view.mapToGlobal(pos))
        if action == use_action:
            self.grab_selector_at(pos)

    def grab_selector_at(self, pos) -> None:
        js = """
            (function() {
                function cssPath(el) {
                    var path = [];
                    while (el.nodeType === Node.ELEMENT_NODE) {
                        var selector = el.nodeName.toLowerCase();
                        if (el.id) {
                            selector += '#' + el.id;
                            path.unshift(selector);
                            break;
                        } else {
                            var sib = el, nth = 1;
                            while (sib = sib.previousElementSibling) {
                                if (sib.nodeName.toLowerCase() == selector) nth++;
                            }
                            if (nth != 1) selector += ':nth-of-type(' + nth + ')';
                        }
                        path.unshift(selector);
                        el = el.parentNode;
                    }
                    return path.join(' > ');
                }
                var el = document.elementFromPoint(%d, %d);
                return cssPath(el);
            }())
        """ % (pos.x(), pos.y())
        self.view.page().runJavaScript(js, self.set_selector)

    def set_selector(self, selector: str) -> None:
        if not selector:
            return
        self.selector_edit.setText(selector)
        QApplication.clipboard().setText(selector, QClipboard.Clipboard)

    def handle_scrape(self) -> None:
        url = self.view.url().toString()
        selector = self.selector_edit.text().strip()
        if not url or not selector:
            return
        self.scrape_button.setEnabled(False)
        self.result_edit.clear()
        self.thread = ScrapingThread(url, selector)
        self.thread.finished.connect(self.show_results)
        self.thread.error.connect(self.show_error)
        self.thread.start()

    def show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Erreur", msg)
        self.scrape_button.setEnabled(True)

    def show_results(self, links: list[str]) -> None:
        self.links = links
        if not links:
            self.result_edit.setPlainText("Aucun lien trouvé")
        else:
            self.result_edit.setPlainText("\n".join(links))
        self.export_txt_button.setEnabled(bool(links))
        self.export_csv_button.setEnabled(bool(links))
        self.scrape_button.setEnabled(True)

    def export_txt(self) -> None:
        if not self.links:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", "liens.txt", "Fichier texte (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.links))

    def export_csv(self) -> None:
        if not self.links:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", "liens.csv", "Fichier CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for link in self.links:
                    f.write(f"{link}\n")


def main() -> None:
    app = QApplication(sys.argv)
    win = BrowserInspector()
    win.resize(1000, 700)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
