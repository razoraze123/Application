import os
import sys
import datetime
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
    QDialog,
    QFormLayout,
)
from PySide6.QtCore import Signal, QObject, QThread
from PySide6.QtGui import QTextCursor

from core.utils import extraire_ids_depuis_input, charger_liens_avec_id_fichier
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


class StartDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Définir la session")
        layout = QFormLayout(self)

        self.dir_edit = QLineEdit(os.getcwd())
        browse_btn = QPushButton("Parcourir")
        browse_btn.clicked.connect(self.browse_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addRow("Dossier de travail", dir_layout)

        default_name = datetime.datetime.now().strftime(
            "Extraction_%Y%m%d_%H%M"
        )
        self.name_edit = QLineEdit(default_name)
        layout.addRow("Nom du dossier", self.name_edit)

        btn_box = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)

    def browse_dir(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier de travail",
            self.dir_edit.text(),
        )
        if path:
            self.dir_edit.setText(path)

    @property
    def selected_dir(self):
        return self.dir_edit.text().strip() or os.getcwd()

    @property
    def folder_name(self):
        name = self.name_edit.text().strip()
        if not name:
            name = datetime.datetime.now().strftime("Extraction_%Y%m%d_%H%M")
        return name


class ScrapingWorker(QThread):
    log = Signal(str)
    finished = Signal()

    def __init__(
        self,
        links_file,
        ids_range,
        actions,
        batch_size,
        session_paths,
    ):
        super().__init__()
        self.links_file = links_file
        self.ids_range = ids_range
        self.actions = actions
        self.batch_size = batch_size
        self.session_paths = session_paths

    def run(self):
        emitter = EmittingStream()
        emitter.text_written.connect(self.log.emit)
        old_stdout = sys.stdout
        sys.stdout = emitter
        try:
            id_url_map = charger_liens_avec_id_fichier(self.links_file)
            ids = extraire_ids_depuis_input(self.ids_range)
            if not ids:
                print("Aucun ID valide fourni. Abandon...")
                return

            if self.actions.get("variantes"):
                var_dir = self.session_paths["variantes"]
                os.makedirs(var_dir, exist_ok=True)
                scrap_produits_par_ids(id_url_map, ids, var_dir)

            if self.actions.get("fiches"):
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                scrap_fiches_concurrents(id_url_map, ids, fc_dir)

            if self.actions.get("export"):
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                export_fiches_concurrents_json(fc_dir, self.batch_size)
        finally:
            sys.stdout = old_stdout
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, session_root):
        super().__init__()
        self.setWindowTitle("Scraping Produit")
        self.resize(750, 550)

        self.session_root = session_root
        self.paths = {
            "variantes": os.path.join(session_root, "variantes"),
            "fiches": os.path.join(session_root, "fiches_concurrents"),
        }

        tabs = QTabWidget()
        tabs.addTab(self._build_scraping_tab(), "Scraping Texte")
        self.setCentralWidget(tabs)

        self.worker = None

    def _build_scraping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        browse_btn = QPushButton("Charger")
        browse_btn.clicked.connect(self.select_file)
        file_layout.addWidget(QLabel("Fichier liens:"))
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        id_layout = QHBoxLayout()
        self.id_edit = QLineEdit()
        id_layout.addWidget(QLabel("Plage d'IDs:"))
        id_layout.addWidget(self.id_edit)
        layout.addLayout(id_layout)

        opt_layout = QHBoxLayout()
        self.cb_variantes = QCheckBox("Scraper les variantes")
        self.cb_fiches = QCheckBox("Scraper les fiches concurrents")
        self.cb_export = QCheckBox("Exporter en JSON")
        opt_layout.addWidget(self.cb_variantes)
        opt_layout.addWidget(self.cb_fiches)
        opt_layout.addWidget(self.cb_export)
        layout.addLayout(opt_layout)

        batch_layout = QHBoxLayout()
        self.batch_edit = QLineEdit("5")
        batch_layout.addWidget(QLabel("Taille batch JSON:"))
        batch_layout.addWidget(self.batch_edit)
        layout.addLayout(batch_layout)

        self.launch_btn = QPushButton("Lancer")
        self.launch_btn.clicked.connect(self.start_actions)
        layout.addWidget(self.launch_btn)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit, 1)

        log_btns = QHBoxLayout()
        save_btn = QPushButton("Sauvegarder les logs")
        save_btn.clicked.connect(self.save_logs)
        clear_btn = QPushButton("Vider")
        clear_btn.clicked.connect(self.log_edit.clear)
        log_btns.addWidget(save_btn)
        log_btns.addWidget(clear_btn)
        layout.addLayout(log_btns)

        return widget

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Fichier liens",
            self.session_root,
            "Text files (*.txt);;All files (*)",
        )
        if path:
            self.file_edit.setText(path)

    def start_actions(self):
        links_file = self.file_edit.text().strip()
        ids_range = self.id_edit.text().strip()
        if not links_file or not os.path.exists(links_file):
            QMessageBox.warning(self, "Erreur", "Fichier de liens invalide")
            return

        try:
            batch_size = int(self.batch_edit.text().strip() or 5)
        except ValueError:
            batch_size = 5

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
        self.worker = ScrapingWorker(
            links_file,
            ids_range,
            actions,
            batch_size,
            self.paths,
        )
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
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les logs",
            os.path.join(self.session_root, "logs.txt"),
            "Text files (*.txt)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_edit.toPlainText())


def main():
    app = QApplication(sys.argv)
    start_dlg = StartDialog()
    if start_dlg.exec() != QDialog.Accepted:
        sys.exit()

    work_dir = start_dlg.selected_dir
    folder_name = start_dlg.folder_name
    session_root = os.path.join(work_dir, folder_name)
    os.makedirs(session_root, exist_ok=True)

    window = MainWindow(session_root)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
