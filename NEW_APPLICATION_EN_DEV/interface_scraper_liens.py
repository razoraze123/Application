"""Simple PySide6 GUI to test the scraper_liens module."""
import sys
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)

from .scraper_liens import scrape_links


class ScrapingThread(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, urls: List[str], selector: str) -> None:
        super().__init__()
        self.urls = urls
        self.selector = selector

    def run(self) -> None:  # pragma: no cover - threads hard to test
        results: list[str] = []
        for url in self.urls:
            try:
                links = scrape_links(url, self.selector)
                results.extend(links)
            except Exception as exc:
                self.error.emit(f"{url}: {exc}")
        self.finished.emit(results)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraper de Liens Produits")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("URLs de collection (une par ligne):"))
        self.urls_edit = QPlainTextEdit()
        self.urls_edit.setPlaceholderText("https://exemple.com/collection...")
        layout.addWidget(self.urls_edit)

        layout.addWidget(QLabel("Sélecteur CSS:"))
        self.selector_edit = QLineEdit("h3.product-card_title > a.bold")
        layout.addWidget(self.selector_edit)

        btn_layout = QHBoxLayout()
        self.scrape_button = QPushButton("Lancer le scraping")
        self.export_txt_button = QPushButton("Exporter TXT")
        self.export_csv_button = QPushButton("Exporter CSV")
        btn_layout.addWidget(self.scrape_button)
        btn_layout.addWidget(self.export_txt_button)
        btn_layout.addWidget(self.export_csv_button)
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("Liens extraits:"))
        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        layout.addWidget(self.result_edit)

        self.links: List[str] = []
        self.thread: ScrapingThread | None = None

        self.export_txt_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)

        self.scrape_button.clicked.connect(self.handle_scrape)
        self.export_txt_button.clicked.connect(self.export_txt)
        self.export_csv_button.clicked.connect(self.export_csv)

        self._setup_menu()

    def _setup_menu(self) -> None:
        theme_menu = self.menuBar().addMenu("Thème")
        self.dark_action = QAction("Sombre", self, checkable=True)
        self.light_action = QAction("Clair", self, checkable=True)
        theme_menu.addAction(self.dark_action)
        theme_menu.addAction(self.light_action)

        self.dark_action.triggered.connect(lambda: self.load_style("dark.qss"))
        self.light_action.triggered.connect(lambda: self.load_style("light.qss"))
        self.light_action.setChecked(True)
        self.load_style("light.qss")

    def load_style(self, fname: str) -> None:
        path = Path(__file__).resolve().parent / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        if "dark" in fname:
            self.dark_action.setChecked(True)
            self.light_action.setChecked(False)
        else:
            self.dark_action.setChecked(False)
            self.light_action.setChecked(True)

    # --- actions ---
    def handle_scrape(self) -> None:
        raw = self.urls_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Attention", "Veuillez saisir au moins une URL")
            return
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        selector = self.selector_edit.text().strip() or "h3.product-card_title > a.bold"

        self.scrape_button.setEnabled(False)
        self.result_edit.clear()
        self.thread = ScrapingThread(urls, selector)
        self.thread.finished.connect(self.show_results)
        self.thread.error.connect(self.show_error)
        self.thread.start()

    def show_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Erreur", msg)

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


def main() -> None:  # pragma: no cover - ui entry
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
