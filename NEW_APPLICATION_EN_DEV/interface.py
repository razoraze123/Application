"""Prototype GUI script (deprecated).

This file is kept for reference and is not part of the official
application. The stable interface is ``application_definitif.py``.
"""

import os
import re
import sys
import time
from PySide6.QtWidgets import QCheckBox


from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

import qtawesome as qta

from core.scraper import export_fiches_concurrents_json, scrap_fiches_concurrents, scrap_produits_par_ids
from core.utils import charger_liens_avec_id_fichier


DARK_STYLE = """
QMainWindow { background-color: #2b2b2b; color: #eee; }
QWidget { background-color: #2b2b2b; color: #eee; }
QLineEdit, QListWidget, QTextEdit {
    background-color: #3c3c3c;
    color: #eee;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
}
QPushButton, QToolButton {
    background-color: #444;
    color: #eee;
    border: 1px solid #666;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover, QToolButton:hover { background-color: #555; }
QProgressBar {
    background-color: #3c3c3c;
    border: 1px solid #555;
    border-radius: 6px;
    text-align: center;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #0078d7;
    border-radius: 6px;
}
QTabWidget::pane { border: 1px solid #444; }
QTabBar::tab {
    background: #444;
    color: #eee;
    padding: 8px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #0078d7; }
"""


class EmittingStream(QObject):
    text_written = Signal(str)

    def write(self, text: str) -> None:
        if text:
            self.text_written.emit(str(text))

    def flush(self) -> None:  # pragma: no cover - no logic
        pass


class ScrapingWorker(QThread):
    progress = Signal(int, float, float)
    finished = Signal()

    def __init__(
        self,
        links_file: str,
        ids: list[str],
        actions: dict,
        batch_size: int,
        session_paths: dict,
    ) -> None:
        super().__init__()
        self.links_file = links_file
        self.ids = ids
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

    def handle_output(self, text: str) -> None:
        self._buffer += text
        if "\n" in self._buffer:
            lines = self._buffer.split("\n")
            self._buffer = lines[-1]
            for line in lines[:-1]:
                self.parse_line(line)

    def parse_line(self, line: str) -> None:
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

    def update_progress(self, value: int) -> None:
        if value <= self.completed:
            return
        self.completed = value
        elapsed = time.time() - self.start
        avg = elapsed / self.completed if self.completed else 0
        remaining = max(self.total - self.completed, 0) * avg
        percent = int((self.completed / self.total) * 100)
        self.progress.emit(percent, elapsed, remaining)

    def run(self) -> None:
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
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraping Produit")
        self.resize(850, 600)
        self.setStyleSheet(DARK_STYLE)

        self.links_path = ""
        self.id_url_map = {}

        tabs = QTabWidget()
        tabs.addTab(self._build_scraping_tab(), "Scraping")
        tabs.addTab(self._build_settings_tab(), "Paramètres")
        tabs.addTab(self._build_guide_tab(), "Guide")
        self.setCentralWidget(tabs)

        self.worker = None

    # ---------- UI builders ----------
    def _build_scraping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        # Utilisation de l'icône FontAwesome 5 solid
        file_btn = QPushButton(qta.icon("fa5s.folder-open"), "Choisir le fichier")
        file_btn.clicked.connect(self.browse_links)
        self.file_info = QLabel()
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(file_btn)
        layout.addLayout(file_layout)
        layout.addWidget(self.file_info)

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher un ID...")
        self.search_edit.textChanged.connect(self.filter_ids)
        self.count_label = QLabel("0 sélectionné")
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.count_label)
        layout.addLayout(search_layout)

        self.ids_list = QListWidget()
        self.ids_list.itemChanged.connect(self.update_count)
        layout.addWidget(self.ids_list, 1)

        action_layout = QHBoxLayout()
        self.action_btn = QToolButton()
        self.action_btn.setText("Actions")
        self.action_btn.setPopupMode(QToolButton.InstantPopup)
        self.action_menu = QMenu(self)
        # "cubes" n'existe qu'en style solid dans FA5
        self.act_variantes = QAction(qta.icon("fa5s.cubes"), "Scraper les variantes", self.action_btn, checkable=True)
        # "file-text" devient "file-alt" en FontAwesome 5 (style solid)
        self.act_fiches = QAction(qta.icon("fa5s.file-alt"), "Scraper les fiches", self.action_btn, checkable=True)
        # Icône de téléchargement en style solid
        self.act_export = QAction(qta.icon("fa5s.download"), "Exporter en JSON", self.action_btn, checkable=True)
        self.action_menu.addAction(self.act_variantes)
        self.action_menu.addAction(self.act_fiches)
        self.action_menu.addAction(self.act_export)
        self.action_btn.setMenu(self.action_menu)
        action_layout.addWidget(self.action_btn)
        action_layout.addStretch(1)
        layout.addLayout(action_layout)

        batch_layout = QHBoxLayout()
        self.batch_slider = QSlider(Qt.Horizontal)
        self.batch_slider.setRange(1, 10)
        self.batch_slider.setValue(5)
        self.batch_slider.valueChanged.connect(self.update_batch_label)
        self.batch_label = QLabel("Batch JSON : 5")
        batch_layout.addWidget(self.batch_label)
        batch_layout.addWidget(self.batch_slider)
        layout.addLayout(batch_layout)

        # Bouton lecture en style solid
        self.launch_btn = QPushButton(qta.icon("fa5s.play"), "Lancer")
        self.launch_btn.clicked.connect(self.start_actions)
        layout.addWidget(self.launch_btn)

        self.progress = ProgressBar()
        layout.addWidget(self.progress)

        self.time_label = QLabel("Temps écoulé: 0s | Temps restant estimé: ?")
        layout.addWidget(self.time_label)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        dir_layout = QHBoxLayout()
        default_dir = "C:/Users/Lamine/Desktop/TEST APPLI"
        self.dir_edit = QLineEdit(default_dir)
        # Icône dossier en style solid
        dir_btn = QPushButton(qta.icon("fa5s.folder"), "Parcourir")
        dir_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("Dossier de sortie:"))
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)

        file_layout = QHBoxLayout()
        self.links_edit = QLineEdit()
        self.links_edit.setReadOnly(True)
        # Dossier ouvert (solid)
        links_btn = QPushButton(qta.icon("fa5s.folder-open"), "Fichier liens")
        links_btn.clicked.connect(self.browse_links_settings)
        file_layout.addWidget(self.links_edit, 1)
        file_layout.addWidget(links_btn)
        layout.addLayout(file_layout)

        batch_layout = QHBoxLayout()
        self.batch_setting_slider = QSlider(Qt.Horizontal)
        self.batch_setting_slider.setRange(1, 10)
        self.batch_setting_slider.setValue(5)
        self.batch_setting_slider.valueChanged.connect(self.update_batch_setting_label)
        self.batch_setting_label = QLabel("Batch JSON : 5")
        batch_layout.addWidget(self.batch_setting_label)
        batch_layout.addWidget(self.batch_setting_slider)
        layout.addLayout(batch_layout)

        self.cb_headless = QCheckBox("Scraping silencieux (headless)")
        self.cb_dark = QCheckBox("Mode sombre")
        self.cb_dark.setChecked(True)
        layout.addWidget(self.cb_headless)
        layout.addWidget(self.cb_dark)

        # Icône disquette en FA5 (solid)
        save_btn = QPushButton(qta.icon("fa5s.save"), "Sauvegarder")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
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
   - Choisissez le dossier de sortie pour les données.
   - Sélectionnez le fichier contenant les liens produits.
   - Ajustez la taille des lots JSON et les options.

2. Onglet Scraping :
   - Chargez le même fichier de liens si ce n'est déjà fait.
   - Sélectionnez les IDs à traiter dans la liste.
   - Ouvrez le menu Actions pour activer les fonctions souhaitées.
   - Appuyez sur Lancer pour démarrer.

La barre de progression et le minuteur indiquent l'avancement."""
        )
        layout.addWidget(guide)
        return widget

    # ---------- Slots ----------
    def browse_links(self) -> None:
        file_filter = "Text files (*.txt);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Fichier de liens", "", file_filter)
        if path:
            self.links_path = path
            self.file_edit.setText(path)
            self.links_edit.setText(path)
            self.load_ids(path)

    def browse_links_settings(self) -> None:
        self.browse_links()

    def load_ids(self, path: str) -> None:
        self.id_url_map = charger_liens_avec_id_fichier(path)
        self.ids_list.clear()
        for ident in self.id_url_map.keys():
            item = QListWidgetItem(ident)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ids_list.addItem(item)
        self.file_info.setText(f"{os.path.basename(path)} - {len(self.id_url_map)} liens")
        self.update_count()

    def filter_ids(self, text: str) -> None:
        for i in range(self.ids_list.count()):
            item = self.ids_list.item(i)
            item.setHidden(text.upper() not in item.text().upper())

    def update_count(self) -> None:
        count = sum(1 for i in range(self.ids_list.count()) if self.ids_list.item(i).checkState() == Qt.Checked)
        self.count_label.setText(f"{count} sélectionné(s)")

    def update_batch_label(self, value: int) -> None:
        self.batch_label.setText(f"Batch JSON : {value}")

    def update_batch_setting_label(self, value: int) -> None:
        self.batch_setting_label.setText(f"Batch JSON : {value}")

    def browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de sortie", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def save_settings(self) -> None:
        self.batch_slider.setValue(self.batch_setting_slider.value())
        self.cb_dark.setChecked(True)
        QMessageBox.information(self, "Sauvegardé", "Paramètres enregistrés")

    def start_actions(self) -> None:
        if not self.links_path or not os.path.exists(self.links_path):
            QMessageBox.warning(self, "Erreur", "Fichier de liens invalide")
            return
        ids = [self.ids_list.item(i).text() for i in range(self.ids_list.count()) if self.ids_list.item(i).checkState() == Qt.Checked]
        if not ids:
            QMessageBox.warning(self, "Erreur", "Aucun ID sélectionné")
            return
        actions = {
            "variantes": self.act_variantes.isChecked(),
            "fiches": self.act_fiches.isChecked(),
            "export": self.act_export.isChecked(),
        }
        if not any(actions.values()):
            QMessageBox.information(self, "Info", "Aucune action sélectionnée")
            return
        output_dir = self.dir_edit.text().strip() or os.getcwd()
        batch_size = self.batch_slider.value()
        self.paths = {
            "variantes": os.path.join(output_dir, "variantes"),
            "fiches": os.path.join(output_dir, "fiches_concurrents"),
        }
        self.launch_btn.setEnabled(False)
        self.worker = ScrapingWorker(self.links_path, ids, actions, batch_size, self.paths)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, percent: int, elapsed: float, remaining: float) -> None:
        self.progress.setValue(percent)
        txt = f"Temps écoulé: {int(elapsed)}s | Temps restant estimé: {int(remaining)}s"
        self.time_label.setText(txt)

    def on_finished(self) -> None:
        self.launch_btn.setEnabled(True)
        QMessageBox.information(self, "Terminé", "Opérations terminées")


class ProgressBar(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self.setRange(0, 100)
        self.setValue(0)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
