import os
import re
import sys
import time
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
    QProgressBar,
)
from PySide6.QtCore import Signal, QObject, QThread

from core.utils import charger_liens_avec_id_fichier
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


def parse_ids_list(text: str) -> list:
    """Parse un champ texte contenant des IDs séparés par espace ou virgule."""
    text = text.replace(',', ' ')
    return [part.strip().upper() for part in text.split() if part.strip()]


class ScrapingWorker(QThread):
    progress = Signal(int, float, float)  # pourcentage, elapsed, remaining
    finished = Signal()

    def __init__(
        self,
        links_file,
        ids_text,
        actions,
        batch_size,
        session_paths,
    ):
        super().__init__()
        self.links_file = links_file
        self.ids = parse_ids_list(ids_text)
        self.actions = actions
        self.batch_size = batch_size
        self.session_paths = session_paths

        self.total = 0
        if actions.get("variantes"):
            self.total += len(self.ids)
        if actions.get("fiches"):
            self.total += len(self.ids)
        if actions.get("export"):
            fc_dir = self.session_paths["fiches"]
            src = os.path.join(fc_dir, "fiche concurrents")
            if os.path.isdir(src):
                txt_files = [f for f in os.listdir(src) if f.endswith(".txt")]
                self.total += len(txt_files)
        if self.total == 0:
            self.total = 1

        self._buffer = ""

    def handle_output(self, text):
        self._buffer += text
        if "\n" in self._buffer:
            lines = self._buffer.split("\n")
            self._buffer = lines[-1]
            for line in lines[:-1]:
                self.parse_line(line)

    def parse_line(self, line: str):
        if "[" in line and "/" in line:
            match = re.search(r"\[(\d+)/(\d+)\]", line)
            if match:
                self.update_progress(int(match.group(1)))
                return
        if "📦" in line:
            match = re.search(r"📦\s*(\d+)\s*/", line)
            if match:
                self.update_progress(int(match.group(1)))
                return
        if line.strip().startswith("✅"):
            self.update_progress(self.completed + 1)

    def update_progress(self, value):
        if value <= self.completed:
            return
        self.completed = value
        elapsed = time.time() - self.start
        avg = elapsed / self.completed if self.completed else 0
        remaining = max(self.total - self.completed, 0) * avg
        percent = int((self.completed / self.total) * 100)
        self.progress.emit(percent, elapsed, remaining)

    def run(self):
        emitter = EmittingStream()
        emitter.text_written.connect(self.handle_output)
        old_stdout = sys.stdout
        sys.stdout = emitter
        self.start = time.time()
        self.completed = 0
        try:
            id_url_map = charger_liens_avec_id_fichier(self.links_file)
            if not self.ids:
                print("Aucun ID valide fourni. Abandon...")
                return

            if self.actions.get("variantes"):
                var_dir = self.session_paths["variantes"]
                os.makedirs(var_dir, exist_ok=True)
                scrap_produits_par_ids(id_url_map, self.ids, var_dir)

            if self.actions.get("fiches"):
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                scrap_fiches_concurrents(id_url_map, self.ids, fc_dir)

            if self.actions.get("export"):
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                export_fiches_concurrents_json(fc_dir, self.batch_size)
        finally:
            self.update_progress(self.total)
            sys.stdout = old_stdout
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scraping Produit")
        self.resize(750, 550)

        tabs = QTabWidget()
        tabs.addTab(self._build_scraping_tab(), "Scraping")
        tabs.addTab(self._build_settings_tab(), "Paramètres")
        tabs.addTab(self._build_guide_tab(), "Guide")
        self.setCentralWidget(tabs)

        self.worker = None

    def _build_scraping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        id_layout = QHBoxLayout()
        self.id_edit = QLineEdit()
        id_layout.addWidget(QLabel("IDs à scraper:"))
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

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.time_label = QLabel("Temps écoulé: 0s | Temps restant estimé: ?")
        layout.addWidget(self.time_label)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit(os.getcwd())
        dir_btn = QPushButton("Parcourir")
        dir_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("Dossier de sortie:"))
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)

        file_layout = QHBoxLayout()
        default_file = (
            "C:/Users/Lamine/Desktop/woocommerce/code/Nouveau dossier/"
            "CODE POUR BOB/liens_avec_id.txt"
        )
        self.links_edit = QLineEdit(default_file)
        file_btn = QPushButton("Parcourir")
        file_btn.clicked.connect(self.browse_links)
        file_layout.addWidget(QLabel("Fichier de liens:"))
        file_layout.addWidget(self.links_edit, 1)
        file_layout.addWidget(file_btn)
        layout.addLayout(file_layout)

        layout.addStretch(1)
        return widget

    def _build_guide_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        guide = QTextEdit()
        guide.setReadOnly(True)
        guide.setPlainText(
            """Guide d'utilisation

1. Onglet Paramètres :
   - Choisissez le dossier de sortie pour enregistrer les données.
   - Sélectionnez le fichier contenant les liens avec les identifiants.

2. Onglet Scraping :
   - Entrez les identifiants à scraper séparés par espace ou virgule.
   - Cochez les actions souhaitées (variantes, fiches, export JSON).
   - Spécifiez la taille des lots JSON si nécessaire.
   - Cliquez sur 'Lancer' pour démarrer.

Pendant l'exécution, la barre de progression et le minuteur indiquent
l'avancement et le temps estimé restant.
"""
        )
        layout.addWidget(guide)
        return widget

    def start_actions(self):
        links_file = self.links_edit.text().strip()
        ids_text = self.id_edit.text().strip()
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
        output_dir = self.dir_edit.text().strip() or os.getcwd()
        self.paths = {
            "variantes": os.path.join(output_dir, "variantes"),
            "fiches": os.path.join(output_dir, "fiches_concurrents"),
        }
        self.worker = ScrapingWorker(
            links_file,
            ids_text,
            actions,
            batch_size,
            self.paths,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def browse_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choisir le dossier de sortie", self.dir_edit.text()
        )
        if path:
            self.dir_edit.setText(path)

    def browse_links(self):
        file_filter = "Text files (*.txt);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Fichier de liens",
            os.path.dirname(self.links_edit.text()),
            file_filter,
        )
        if path:
            self.links_edit.setText(path)

    def update_progress(self, percent: int, elapsed: float, remaining: float):
        self.progress.setValue(percent)
        remaining_s = int(remaining)
        elapsed_s = int(elapsed)
        txt = (
            f"Temps écoulé: {elapsed_s}s | "
            f"Temps restant estimé: {remaining_s}s"
        )
        self.time_label.setText(txt)

    def on_finished(self):
        self.launch_btn.setEnabled(True)
        QMessageBox.information(self, "Terminé", "Opérations terminées")


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
