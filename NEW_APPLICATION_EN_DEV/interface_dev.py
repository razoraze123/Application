# Only for running the prototype directly
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

import os
import re
import sys
import time

from PySide6.QtCore import Signal, QObject, QThread
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

import qtawesome as qta

from core.scraper import (
    export_fiches_concurrents_json,
    scrap_fiches_concurrents,
    scrap_produits_par_ids,
)
from core.utils import charger_liens_avec_id_fichier

DARK_STYLE = """
QMainWindow { background-color: #2b2b2b; color: #eee; }
QWidget { background-color: #2b2b2b; color: #eee; }
QLineEdit, QTextEdit {
    background-color: #3c3c3c;
    color: #eee;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
}
QPushButton {
    background-color: #444;
    color: #eee;
    border: 1px solid #666;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover { background-color: #555; }
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
    action_progress = Signal(str, int, int)
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

        self.totals: dict[str, int] = {}
        if actions.get("variantes"):
            self.totals["variantes"] = len(self.ids)
        if actions.get("fiches"):
            self.totals["fiches"] = len(self.ids)
        if actions.get("export"):
            fc_dir = self.session_paths["fiches"]
            src = os.path.join(fc_dir, "fiche concurrents")
            txt_files = [f for f in os.listdir(src) if f.endswith(".txt")] if os.path.isdir(src) else []
            self.totals["export"] = len(txt_files)

        self.total = sum(self.totals.values()) or 1
        self.completed_totals = {k: 0 for k in self.totals}
        self.current_action: str | None = None
        self.overall_completed = 0
        self._buffer = ""

    def handle_output(self, text: str) -> None:
        self._buffer += text
        if "\n" in self._buffer:
            lines = self._buffer.split("\n")
            self._buffer = lines[-1]
            for line in lines[:-1]:
                self.parse_line(line)

    def parse_line(self, line: str) -> None:
        match = re.search(r"\[(\d+)/(\d+)\]", line)
        if match:
            self.update_action(int(match.group(1)))
            self.increment_progress()
            return
        match = re.search(r"📦\s*(\d+)\s*/", line)
        if match:
            self.update_action(int(match.group(1)))
            self.increment_progress()
            return
        if line.strip().startswith("✅"):
            self.update_action(self.completed_totals.get(self.current_action, 0) + 1)
            self.increment_progress()

    def update_action(self, value: int) -> None:
        if not self.current_action:
            return
        if value <= self.completed_totals[self.current_action]:
            return
        self.completed_totals[self.current_action] = value
        total = self.totals[self.current_action]
        self.action_progress.emit(self.current_action, value, total)

    def increment_progress(self) -> None:
        self.overall_completed += 1
        elapsed = time.time() - self.start
        avg = elapsed / self.overall_completed if self.overall_completed else 0
        remaining = max(self.total - self.overall_completed, 0) * avg
        percent = int((self.overall_completed / self.total) * 100)
        self.progress.emit(percent, elapsed, remaining)

    def run(self) -> None:
        emitter = EmittingStream()
        emitter.text_written.connect(self.handle_output)
        old_stdout = sys.stdout
        sys.stdout = emitter
        self.start = time.time()
        try:
            id_url_map = charger_liens_avec_id_fichier(self.links_file)
            if not self.ids:
                print("Aucun ID valide fourni. Abandon...")
                return
            if self.actions.get("variantes"):
                self.current_action = "variantes"
                var_dir = self.session_paths["variantes"]
                os.makedirs(var_dir, exist_ok=True)
                scrap_produits_par_ids(id_url_map, self.ids, var_dir)
            if self.actions.get("fiches"):
                self.current_action = "fiches"
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                scrap_fiches_concurrents(id_url_map, self.ids, fc_dir)
            if self.actions.get("export"):
                self.current_action = "export"
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                export_fiches_concurrents_json(fc_dir, self.batch_size)
        finally:
            self.current_action = None
            self.increment_progress()
            sys.stdout = old_stdout
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraping Produit")
        self.resize(850, 600)
        self.setStyleSheet(DARK_STYLE)

        self.links_path = ""
        self.id_url_map: dict[str, str] = {}
        self.all_ids: list[str] = []
        self.selected_ids: list[str] = []

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

        self.file_info = QLabel("Aucun fichier chargé")
        layout.addWidget(self.file_info)

        range_layout = QHBoxLayout()
        self.min_id_edit = QLineEdit()
        self.min_id_edit.setPlaceholderText("ID min")
        self.max_id_edit = QLineEdit()
        self.max_id_edit.setPlaceholderText("ID max")
        self.min_id_edit.textChanged.connect(self.update_range)
        self.max_id_edit.textChanged.connect(self.update_range)
        select_all = QPushButton("Tout sélectionner")
        select_all.clicked.connect(self.select_all_ids)
        clear_sel = QPushButton("Effacer sélection")
        clear_sel.clicked.connect(self.clear_selection)
        range_layout.addWidget(self.min_id_edit)
        range_layout.addWidget(self.max_id_edit)
        range_layout.addWidget(select_all)
        range_layout.addWidget(clear_sel)
        layout.addLayout(range_layout)

        self.count_label = QLabel("0/0")
        layout.addWidget(self.count_label)

        action_layout = QHBoxLayout()
        self.btn_variantes = QPushButton(qta.icon("fa5s.cubes"), "Variantes")
        self.btn_variantes.setCheckable(True)
        self.btn_fiches = QPushButton(qta.icon("fa5s.file-alt"), "Fiches")
        self.btn_fiches.setCheckable(True)
        self.btn_export = QPushButton(qta.icon("fa5s.download"), "Export JSON")
        self.btn_export.setCheckable(True)
        for b in (self.btn_variantes, self.btn_fiches, self.btn_export):
            b.setStyleSheet("QPushButton:checked{background-color:#0078d7;}")
        action_layout.addWidget(self.btn_variantes)
        action_layout.addWidget(self.btn_fiches)
        action_layout.addWidget(self.btn_export)
        layout.addLayout(action_layout)

        self.launch_btn = QPushButton(qta.icon("fa5s.play"), "Lancer")
        self.launch_btn.clicked.connect(self.start_actions)
        layout.addWidget(self.launch_btn)

        self.progress = ProgressBar()
        layout.addWidget(self.progress)

        status_layout = QHBoxLayout()
        self.status_var = QLabel()
        self.status_fiche = QLabel()
        self.status_export = QLabel()
        for lab in (self.status_var, self.status_fiche, self.status_export):
            lab.setStyleSheet("background:#555;padding:2px 4px;border-radius:4px;")
        status_layout.addWidget(self.status_var)
        status_layout.addWidget(self.status_fiche)
        status_layout.addWidget(self.status_export)
        layout.addLayout(status_layout)

        self.time_label = QLabel("Temps écoulé: 0s | Temps restant estimé: ?")
        layout.addWidget(self.time_label)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        dir_layout = QHBoxLayout()
        default_dir = os.getcwd()
        self.dir_edit = QLineEdit(default_dir)
        dir_btn = QPushButton(qta.icon("fa5s.folder"), "Parcourir")
        dir_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("Dossier de sortie:"))
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)

        file_layout = QHBoxLayout()
        self.links_edit = QLineEdit()
        self.links_edit.setReadOnly(True)
        links_btn = QPushButton(qta.icon("fa5s.folder-open"), "Fichier liens")
        links_btn.clicked.connect(self.browse_links_settings)
        file_layout.addWidget(self.links_edit, 1)
        file_layout.addWidget(links_btn)
        layout.addLayout(file_layout)

        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch JSON:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(5)
        batch_layout.addWidget(self.batch_spin)
        layout.addLayout(batch_layout)

        self.cb_headless = QCheckBox("Scraping silencieux (headless)")
        self.cb_dark = QCheckBox("Mode sombre")
        self.cb_dark.setChecked(True)
        layout.addWidget(self.cb_headless)
        layout.addWidget(self.cb_dark)

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
   - Sélectionnez la plage d'IDs à traiter.
   - Activez les fonctionnalités désirées.
   - Appuyez sur Lancer pour démarrer.

La barre de progression et le minuteur indiquent l'avancement."""
        )
        layout.addWidget(guide)
        return widget

    # ---------- Slots ----------
    def browse_links_settings(self) -> None:
        file_filter = "Text files (*.txt);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Fichier de liens", "", file_filter)
        if path:
            self.links_path = path
            self.links_edit.setText(path)
            self.load_ids(path)

    def load_ids(self, path: str) -> None:
        self.id_url_map = charger_liens_avec_id_fichier(path)
        self.all_ids = sorted(self.id_url_map.keys())
        self.file_info.setText(f"{os.path.basename(path)} - {len(self.all_ids)} liens")
        self.clear_selection()

    def browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de sortie", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def save_settings(self) -> None:
        QMessageBox.information(self, "Sauvegardé", "Paramètres enregistrés")

    def update_range(self) -> None:
        start = self.min_id_edit.text().strip().upper()
        end = self.max_id_edit.text().strip().upper()
        if start and end and start in self.all_ids and end in self.all_ids:
            i1 = self.all_ids.index(start)
            i2 = self.all_ids.index(end)
            if i1 <= i2:
                self.selected_ids = self.all_ids[i1 : i2 + 1]
            else:
                self.selected_ids = self.all_ids[i2 : i1 + 1]
        else:
            self.selected_ids = []
        self.count_label.setText(f"{len(self.selected_ids)} / {len(self.all_ids)}")

    def select_all_ids(self) -> None:
        if not self.all_ids:
            return
        self.min_id_edit.setText(self.all_ids[0])
        self.max_id_edit.setText(self.all_ids[-1])
        self.update_range()

    def clear_selection(self) -> None:
        self.min_id_edit.clear()
        self.max_id_edit.clear()
        self.selected_ids = []
        self.count_label.setText(f"0 / {len(self.all_ids)}")

    def start_actions(self) -> None:
        if not self.links_path or not os.path.exists(self.links_path):
            QMessageBox.warning(self, "Erreur", "Fichier de liens invalide")
            return
        if not self.selected_ids:
            QMessageBox.warning(self, "Erreur", "Aucun ID sélectionné")
            return
        actions = {
            "variantes": self.btn_variantes.isChecked(),
            "fiches": self.btn_fiches.isChecked(),
            "export": self.btn_export.isChecked(),
        }
        if not any(actions.values()):
            QMessageBox.information(self, "Info", "Aucune action sélectionnée")
            return
        output_dir = self.dir_edit.text().strip() or os.getcwd()
        batch_size = self.batch_spin.value()
        self.paths = {
            "variantes": os.path.join(output_dir, "variantes"),
            "fiches": os.path.join(output_dir, "fiches_concurrents"),
        }
        self.launch_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_var.setText("")
        self.status_fiche.setText("")
        self.status_export.setText("")
        self.worker = ScrapingWorker(self.links_path, self.selected_ids, actions, batch_size, self.paths)
        self.worker.progress.connect(self.update_progress)
        self.worker.action_progress.connect(self.update_action_status)
        self.worker.finished.connect(self.on_finished)
        for action, total in self.worker.totals.items():
            self.update_action_status(action, 0, total)
        self.worker.start()

    def update_progress(self, percent: int, elapsed: float, remaining: float) -> None:
        self.progress.setValue(percent)
        txt = f"Temps écoulé: {int(elapsed)}s | Temps restant estimé: {int(remaining)}s"
        self.time_label.setText(txt)

    def update_action_status(self, action: str, done: int, total: int) -> None:
        text = f"{action.capitalize()} : {done}/{total}"
        if action == "variantes":
            self.status_var.setText(text)
        elif action == "fiches":
            self.status_fiche.setText(text)
        elif action == "export":
            self.status_export.setText(text)

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
