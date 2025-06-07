"""Prototype GUI script (deprecated).

This file is kept for reference and is not part of the official
application. The stable interface is ``application_definitif.py``.
"""

import os
import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QCheckBox,
    QTextEdit,
    QTabWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QTextCursor

from core.utils import (
    extraire_ids_depuis_input,
    charger_liens_avec_id_fichier,
)
from core.scraper import (
    scrap_produits_par_ids,
    scrap_fiches_concurrents,
    export_fiches_concurrents_json,
)


class EmittingStream(QObject):
    text_written = Signal(str)

    def write(self, text):
        if text:
            self.text_written.emit(str(text))

    def flush(self):
        pass


class ScrapingWorker(QThread):
    log = Signal(str)
    finished = Signal()

    def __init__(self, links_file: str, ids_range: str, actions: dict):
        super().__init__()
        self.links_file = links_file
        self.ids_range = ids_range
        self.actions = actions

    def run(self):
        emitter = EmittingStream()
        emitter.text_written.connect(self.log.emit)
        old_stdout = sys.stdout
        sys.stdout = emitter
        try:
            id_url_map = charger_liens_avec_id_fichier(self.links_file)
            ids = extraire_ids_depuis_input(self.ids_range)
            base_dir = os.path.dirname(self.links_file)

            if not ids:
                print("Aucun ID valide fourni. Abandon...")
            else:
                if self.actions.get("variantes"):
                    scrap_produits_par_ids(id_url_map, ids, base_dir)
                if self.actions.get("fiches"):
                    scrap_fiches_concurrents(id_url_map, ids, base_dir)
                if self.actions.get("export"):
                    export_fiches_concurrents_json(base_dir)
        finally:
            sys.stdout = old_stdout
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scraper GUI")
        self.resize(700, 500)

        self.worker = None

        tabs = QTabWidget()
        tabs.addTab(self._build_scraping_tab(), "Scraping Texte")
        self.setCentralWidget(tabs)

    def _build_scraping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # File picker
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        browse_btn = QPushButton("Parcourir")
        browse_btn.clicked.connect(self.select_file)
        file_layout.addWidget(QLabel("Fichier liens:"))
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # ID range
        id_layout = QHBoxLayout()
        self.id_edit = QLineEdit()
        id_layout.addWidget(QLabel("Plage d'IDs:"))
        id_layout.addWidget(self.id_edit)
        layout.addLayout(id_layout)

        # Options
        self.cb_variantes = QCheckBox("Scraper les variantes")
        self.cb_fiches = QCheckBox("Scraper les fiches concurrents")
        self.cb_export = QCheckBox("Exporter les fiches en JSON")
        layout.addWidget(self.cb_variantes)
        layout.addWidget(self.cb_fiches)
        layout.addWidget(self.cb_export)

        # Launch button
        self.launch_btn = QPushButton("Lancer")
        self.launch_btn.clicked.connect(self.start_scraping)
        layout.addWidget(self.launch_btn)

        # Logs
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit, 1)

        log_btn_layout = QHBoxLayout()
        save_btn = QPushButton("Sauvegarder les logs")
        save_btn.clicked.connect(self.save_logs)
        clear_btn = QPushButton("Vider")
        clear_btn.clicked.connect(self.log_edit.clear)
        log_btn_layout.addWidget(save_btn)
        log_btn_layout.addWidget(clear_btn)
        layout.addLayout(log_btn_layout)

        return widget

    # Slots
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner le fichier de liens", "", "Text files (*.txt);;All files (*)"
        )
        if path:
            self.file_edit.setText(path)

    def start_scraping(self):
        links_file = self.file_edit.text().strip()
        ids_range = self.id_edit.text().strip()
        if not links_file or not os.path.exists(links_file):
            QMessageBox.warning(self, "Erreur", "Fichier de liens invalide")
            return

        actions = {
            "variantes": self.cb_variantes.isChecked(),
            "fiches": self.cb_fiches.isChecked(),
            "export": self.cb_export.isChecked(),
        }
        if not any(actions.values()):
            QMessageBox.information(self, "Info", "Aucune action sélectionnée")
            return

        self.launch_btn.setEnabled(False)
        self.log_edit.clear()
        self.worker = ScrapingWorker(links_file, ids_range, actions)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text: str):
        self.log_edit.moveCursor(QTextCursor.End)
        self.log_edit.insertPlainText(text)
        self.log_edit.moveCursor(QTextCursor.End)

    def on_finished(self):
        self.launch_btn.setEnabled(True)
        QMessageBox.information(self, "Terminé", "Opérations terminées")

    def save_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer les logs", "logs.txt", "Text files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_edit.toPlainText())


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

