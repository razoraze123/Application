import os
import re
import sys
import time
import math

from PySide6.QtCore import (
    Signal,
    QObject,
    QThread,
    Qt,
    QSettings,
    QUrl,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QGroupBox,
)
from PySide6.QtGui import (
    QTextCursor,
    QColor,
    QTextCharFormat,
    QDesktopServices,
)
import importlib.util
import subprocess
import qtawesome as qta

from core.scraper import (
    export_fiches_concurrents_json,
    scrap_fiches_concurrents,
    scrap_produits_par_ids,
)
from core.utils import charger_liens_avec_id_fichier
from ui.widgets import AnimatedProgressBar
from qt_material import apply_stylesheet
import logging


logger = logging.getLogger(__name__)

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
QPushButton, QToolButton {
    background-color: #444;
    color: #eee;
    border: 1px solid #666;
    border-radius: 10px;
    padding: 4px 8px;
}
QPushButton:hover, QToolButton:hover { background-color: #555; }
QPushButton:checked, QToolButton:checked {
    background-color: #0078d7;
}
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
            sys.__stdout__.write(str(text))

    def flush(self) -> None:  # pragma: no cover - no logic
        sys.__stdout__.flush()


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
        headless: bool = False,
    ) -> None:
        """Run scraping operations in a background thread.

        Parameters
        ----------
        headless : bool, optional
            Launch Selenium in headless mode when ``True``.
        """
        super().__init__()
        self.links_file = links_file
        self.ids = ids
        self.actions = actions
        self.batch_size = batch_size
        self.session_paths = session_paths
        self.headless = headless

        self.emitter = EmittingStream()
        self.emitter.text_written.connect(self.handle_output)

        self.totals: dict[str, int] = {}
        if actions.get("variantes"):
            self.totals["variantes"] = len(self.ids)
        if actions.get("fiches"):
            self.totals["fiches"] = len(self.ids)
        if actions.get("export"):
            self.totals["export"] = math.ceil(len(self.ids) / (self.batch_size or 1))

        self.total = sum(self.totals.values()) or 1
        self.completed_totals = {k: 0 for k in self.totals}
        self.current_action: str | None = None
        self.overall_completed = 0
        self._buffer = ""

    def handle_output(self, text: str) -> None:
        """Accumulate output until newline and parse completed lines."""
        self._buffer += text
        if "\n" in self._buffer:
            lines = self._buffer.split("\n")
            self._buffer = lines[-1]
            for line in lines[:-1]:
                self.parse_line(line)

    def parse_line(self, line: str) -> None:
        """Interpret stdout lines to update progress."""
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
        clean = line.lstrip()
        if clean.startswith("✅") or clean.startswith("❌") or clean.startswith("⚠️") or "Erreur" in line:
            current = self.completed_totals.get(self.current_action, 0)
            self.update_action(current + 1)
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
        old_stdout = sys.stdout
        sys.stdout = self.emitter
        for h in logging.getLogger().handlers:
            if isinstance(h, logging.StreamHandler):
                h.stream = sys.stdout
        self.start = time.time()
        try:
            id_url_map = charger_liens_avec_id_fichier(self.links_file)
            if not self.ids:
                logger.warning("Aucun ID valide fourni. Abandon...")
                return
            if self.actions.get("variantes"):
                self.current_action = "variantes"
                var_dir = self.session_paths["variantes"]
                os.makedirs(var_dir, exist_ok=True)
                scrap_produits_par_ids(
                    id_url_map,
                    self.ids,
                    var_dir,
                    headless=self.headless,
                )
            if self.actions.get("fiches"):
                self.current_action = "fiches"
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                scrap_fiches_concurrents(
                    id_url_map,
                    self.ids,
                    fc_dir,
                    headless=self.headless,
                )
            if self.actions.get("export"):
                self.current_action = "export"
                fc_dir = self.session_paths["fiches"]
                os.makedirs(fc_dir, exist_ok=True)
                export_fiches_concurrents_json(fc_dir, self.batch_size)
        finally:
            self.current_action = None
            self.increment_progress()
            sys.stdout = old_stdout
            for h in logging.getLogger().handlers:
                if isinstance(h, logging.StreamHandler):
                    h.stream = sys.stdout
            if self.overall_completed < self.total:
                logger.warning(
                    "Progress incomplet: %d/%d", self.overall_completed, self.total
                )
            elapsed = time.time() - self.start
            self.progress.emit(100, elapsed, 0.0)
            self.finished.emit()


class PipInstaller(QThread):
    """Install Python packages in a separate thread."""

    finished = Signal(str, bool, str)

    def __init__(self, args: list[str]) -> None:
        super().__init__()
        self.args = args

    def run(self) -> None:
        cmd = [sys.executable, "-m", "pip", "install"] + self.args
        proc = subprocess.run(cmd, capture_output=True, text=True)
        pkg = " ".join(self.args)
        out = proc.stdout + proc.stderr
        self.finished.emit(pkg, proc.returncode == 0, out)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scraping Produit")
        self.resize(850, 600)
        self.statusBar()

        self.settings = QSettings("scraping_app", "ui")
        style_dir = os.path.join(os.path.dirname(__file__), "ui")
        default_theme = os.path.join(style_dir, "style.qss")
        theme_path = self.settings.value("theme", default_theme)
        self._apply_stylesheet(theme_path)
        self.theme_path = theme_path

        # Parameters reserved for future customisation like font or density
        self.extra_params: dict[str, str] = {}

        self.links_path = ""
        self.id_url_map: dict[str, str] = {}
        self.all_ids: list[str] = []
        self.selected_ids: list[str] = []
        self.internal_logs: list[str] = []

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.addTab(self._build_scraping_tab(), "Scraping")
        tabs.addTab(self._build_settings_tab(), "Paramètres")
        tabs.addTab(self._build_update_tab(), "Mise à jour")
        tabs.addTab(self._build_guide_tab(), "Guide")
        self.setCentralWidget(tabs)

        self.repo_dir = os.path.dirname(os.path.abspath(__file__))

        self.worker = None

    # ---------- UI builders ----------
    def _build_scraping_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        self.total_links_label = QLabel("Nombre de liens total : 0")
        f = self.total_links_label.font()
        f.setPointSize(f.pointSize() + 2)
        self.total_links_label.setFont(f)
        self.total_links_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.total_links_label)

        range_layout = QHBoxLayout()
        self.min_id_edit = QLineEdit()
        self.min_id_edit.setPlaceholderText("ID min")
        self.max_id_edit = QLineEdit()
        self.max_id_edit.setPlaceholderText("ID max")
        self.min_id_edit.textChanged.connect(self.update_range)
        self.max_id_edit.textChanged.connect(self.update_range)
        select_all = QPushButton(
            qta.icon("fa5s.check-double"),
            "Tout sélectionner",
        )
        select_all.clicked.connect(self.select_all_ids)
        clear_sel = QPushButton(
            qta.icon("fa5s.eraser"),
            "Effacer sélection",
        )
        clear_sel.clicked.connect(self.clear_selection)
        range_layout.addWidget(self.min_id_edit)
        range_layout.addWidget(self.max_id_edit)
        range_layout.addWidget(select_all)
        range_layout.addWidget(clear_sel)
        layout.addLayout(range_layout)

        self.count_label = QLabel("IDs sélectionnés : 0/0")
        self.count_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.count_label)

        action_layout = QHBoxLayout()
        self.btn_variantes = QToolButton()
        self.btn_variantes.setCheckable(True)
        self.btn_variantes.setIcon(qta.icon("fa5s.cubes"))
        self.btn_variantes.setText("Variantes")
        self.btn_variantes.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.status_var = QLabel()

        self.btn_fiches = QToolButton()
        self.btn_fiches.setCheckable(True)
        self.btn_fiches.setIcon(qta.icon("fa5s.file-alt"))
        self.btn_fiches.setText("Fiches")
        self.btn_fiches.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.status_fiche = QLabel()

        self.btn_export = QToolButton()
        self.btn_export.setCheckable(True)
        self.btn_export.setIcon(qta.icon("fa5s.download"))
        self.btn_export.setText("Export JSON")
        self.btn_export.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.status_export = QLabel()

        chip_style = (
            "background:#333;color:#fff;font-weight:bold;"
            "border:1px solid #555;border-radius:8px;padding:2px 6px;"
        )
        for b in (self.btn_variantes, self.btn_fiches, self.btn_export):
            b.setStyleSheet(
                "QToolButton {padding:2px 6px;}"
                "QToolButton:checked{background-color:#0078d7;}"
            )
            b.setFixedHeight(28)
        for lab in (self.status_var, self.status_fiche, self.status_export):
            lab.setStyleSheet(chip_style)
        action_layout.addWidget(self.btn_variantes)
        action_layout.addWidget(self.status_var)
        action_layout.addWidget(self.btn_fiches)
        action_layout.addWidget(self.status_fiche)
        action_layout.addWidget(self.btn_export)
        action_layout.addWidget(self.status_export)
        layout.addLayout(action_layout)

        self.launch_btn = QPushButton(qta.icon("fa5s.play"), "Lancer")
        self.launch_btn.clicked.connect(self.start_actions)
        layout.addWidget(self.launch_btn)

        self.progress = AnimatedProgressBar()
        progress_line = QHBoxLayout()
        progress_line.addWidget(self.progress, 1)
        progress_line.addStretch(1)
        layout.addLayout(progress_line)

        self.time_label = QLabel("Temps écoulé: 0s | Temps restant estimé: ?")
        layout.addWidget(self.time_label)

        self.results_table = QTableWidget(0, 2)
        self.results_table.setObjectName("results_table")
        self.results_table.setHorizontalHeaderLabels(["Action", "Progression"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.results_table)

        self.toggle_log_btn = QToolButton()
        self.toggle_log_btn.setIcon(qta.icon("fa5s.book"))
        self.toggle_log_btn.setText("Afficher le journal")
        self.toggle_log_btn.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )
        self.toggle_log_btn.setCheckable(True)
        self.toggle_log_btn.clicked.connect(self.toggle_log)

        self.copy_log_btn = QPushButton(qta.icon("fa5s.copy"), "Copier le journal")
        self.copy_log_btn.setToolTip("Copier le journal")
        self.copy_log_btn.clicked.connect(self.copy_log)

        self.clear_log_btn = QPushButton(qta.icon("fa5s.trash"), "Vider le journal")
        self.clear_log_btn.setToolTip("Effacer le journal")
        self.clear_log_btn.clicked.connect(self.clear_log)

        log_btn_layout = QHBoxLayout()
        log_btn_layout.setContentsMargins(0, 0, 0, 0)
        log_btn_layout.setSpacing(2)
        log_btn_layout.addWidget(self.toggle_log_btn)
        log_btn_layout.addWidget(self.copy_log_btn)
        log_btn_layout.addWidget(self.clear_log_btn)
        layout.addLayout(log_btn_layout)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        self.log_area.setLineWrapMode(QTextEdit.NoWrap)
        self.log_area.setVisible(False)
        layout.addWidget(self.log_area)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        dir_layout = QHBoxLayout()
        default_dir = r"C:\\Users\\Lamine\\Desktop\\Application 1"
        self.dir_edit = QLineEdit(default_dir)
        dir_btn = QPushButton(qta.icon("fa5s.folder"), "Parcourir")
        dir_btn.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("Dossier de sortie:"))
        dir_layout.addWidget(self.dir_edit, 1)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)

        sub_layout = QHBoxLayout()
        self.subdir_edit = QLineEdit()
        sub_layout.addWidget(QLabel("Nom du dossier principal:"))
        sub_layout.addWidget(self.subdir_edit, 1)
        layout.addLayout(sub_layout)

        file_layout = QHBoxLayout()
        default_links = (
            r"C:\\Users\\Lamine\\Desktop\\Application 1\\liens_avec_id.txt"
        )
        self.links_edit = QLineEdit(default_links)
        self.links_path = default_links
        self.links_edit.setReadOnly(True)
        links_btn = QPushButton(qta.icon("fa5s.folder-open"), "Fichier liens")
        links_btn.clicked.connect(self.browse_links_settings)
        file_layout.addWidget(self.links_edit, 1)
        file_layout.addWidget(links_btn)
        layout.addLayout(file_layout)
        if os.path.exists(default_links):
            self.load_ids(default_links)

        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch JSON:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10)
        self.batch_spin.setValue(5)

        self.batch_slider = QSlider(Qt.Horizontal)
        self.batch_slider.setRange(
            self.batch_spin.minimum(), self.batch_spin.maximum()
        )
        self.batch_slider.setValue(self.batch_spin.value())

        self.batch_spin.valueChanged.connect(self.batch_slider.setValue)
        self.batch_slider.valueChanged.connect(self.batch_spin.setValue)
        self.batch_slider.valueChanged.connect(self.update_export_estimate)
        self.batch_spin.valueChanged.connect(self.update_export_estimate)

        batch_layout.addWidget(self.batch_slider, 1)
        batch_layout.addWidget(self.batch_spin)
        layout.addLayout(batch_layout)

        self.cb_headless = QCheckBox("Scraping silencieux (headless)")

        self.theme_toggle = QToolButton()
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setChecked(
            os.path.basename(self.theme_path) == "style.qss"
        )
        self._update_theme_icon()
        self.theme_toggle.clicked.connect(self.on_theme_changed)

        layout.addWidget(self.cb_headless)
        layout.addWidget(self.theme_toggle)

        save_btn = QPushButton(qta.icon("fa5s.save"), "Sauvegarder")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        deps_group = QGroupBox("Dépendances Python")
        deps_layout = QVBoxLayout(deps_group)
        self.deps_table = QTableWidget(0, 3)
        self.deps_table.setHorizontalHeaderLabels(
            ["Nom du module", "Statut", "Action"]
        )
        self.deps_table.verticalHeader().setVisible(False)
        self.deps_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.deps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.deps_table.setSelectionMode(QAbstractItemView.NoSelection)
        deps_layout.addWidget(self.deps_table)

        btn_line = QHBoxLayout()
        self.install_all_btn = QPushButton("Installer les dépendances")
        self.install_all_btn.clicked.connect(self.install_all_deps)
        self.refresh_deps_btn = QPushButton("Actualiser la liste")
        self.refresh_deps_btn.clicked.connect(self.refresh_deps_status)
        self.doc_btn = QToolButton()
        self.doc_btn.setIcon(qta.icon("fa5s.question-circle"))
        self.doc_btn.setToolTip("Ouvrir la documentation pip install")
        self.doc_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://pip.pypa.io/en/stable/cli/pip_install/")
            )
        )
        btn_line.addWidget(self.install_all_btn)
        btn_line.addWidget(self.refresh_deps_btn)
        btn_line.addWidget(self.doc_btn)
        deps_layout.addLayout(btn_line)

        layout.addWidget(deps_group)
        self.required_packages = self._load_requirements()
        self.refresh_deps_status()
        layout.addStretch(1)
        return widget

    def _build_update_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        warn = QLabel(
            "Attention : la mise à jour écrase vos modifications locales non synchronisées !"
        )
        warn.setWordWrap(True)
        layout.addWidget(warn)

        self.update_log = QTextEdit()
        self.update_log.setReadOnly(True)
        layout.addWidget(self.update_log, 1)

        btn_line = QHBoxLayout()
        self.update_btn = QPushButton("Mettre à jour depuis Git")
        self.update_btn.clicked.connect(self.update_from_git)
        self.restart_btn = QPushButton("Redémarrer l'application")
        self.restart_btn.clicked.connect(self.restart_app)
        btn_line.addWidget(self.update_btn)
        btn_line.addWidget(self.restart_btn)
        layout.addLayout(btn_line)

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
   - Gérez les dépendances Python et installez-les au besoin.

2. Onglet Scraping :
   - Sélectionnez la plage d'IDs à traiter.
   - Activez les fonctionnalités désirées.
   - Appuyez sur Lancer pour démarrer.

3. Dépendances et installation automatique :
   - Le statut de chaque module apparaît en vert ou rouge.
   - Utilisez les boutons "Installer" pour agir dans le même environnement Python.
   - Cliquez sur "Actualiser la liste" après une installation pour forcer la détection.
   - Certains modules peuvent nécessiter un redémarrage complet pour être pris en compte.
   - Des conflits sont possibles si plusieurs versions de Python sont présentes.
   - Installer depuis l'application limite ces problèmes de venv.

La barre de progression et le minuteur indiquent l'avancement."""
        )
        layout.addWidget(guide)
        return widget

    # ---------- Slots ----------
    def browse_links_settings(self) -> None:
        file_filter = "Text files (*.txt);;All files (*)"
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Fichier de liens",
            "",
            file_filter,
        )
        if path:
            self.links_path = path
            self.links_edit.setText(path)
            self.load_ids(path)

    def load_ids(self, path: str) -> None:
        def natural_key(s: str) -> list:
            return [
                int(t) if t.isdigit() else t
                for t in re.split(r"(\d+)", s)
            ]

        self.id_url_map = charger_liens_avec_id_fichier(path)
        self.all_ids = sorted(self.id_url_map.keys(), key=natural_key)
        self.total_links_label.setText(
            f"Nombre de liens total : {len(self.all_ids)}"
        )
        self.clear_selection()

    def browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier de sortie",
            self.dir_edit.text(),
        )
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
                self.selected_ids = self.all_ids[i1:i2 + 1]
            else:
                self.selected_ids = self.all_ids[i2:i1 + 1]
        else:
            self.selected_ids = []
        self.count_label.setText(
            "IDs sélectionnés : "
            f"{len(self.selected_ids)} / {len(self.all_ids)}"
        )
        self.update_export_estimate()

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
        self.count_label.setText(
            f"IDs sélectionnés : 0 / {len(self.all_ids)}"
        )
        self.update_export_estimate()

    def update_export_estimate(self) -> None:
        if not self.selected_ids:
            self.status_export.setText("")
            return
        batch = self.batch_spin.value() or 1
        total = math.ceil(len(self.selected_ids) / batch)
        self.status_export.setText(f"Export : 0/{total}")

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
        sub = self.subdir_edit.text().strip()
        if sub:
            output_dir = os.path.join(output_dir, sub)
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
        self.log_area.clear()
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self.worker = ScrapingWorker(
            self.links_path,
            self.selected_ids,
            actions,
            batch_size,
            self.paths,
            headless=self.cb_headless.isChecked(),
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.action_progress.connect(self.update_action_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.emitter.text_written.connect(self.append_log)
        self.action_rows = {}
        self.results_table.setRowCount(len(self.worker.totals))
        for row, (action, total) in enumerate(self.worker.totals.items()):
            self.action_rows[action] = row
            self.results_table.setItem(
                row,
                0,
                QTableWidgetItem(action.capitalize()),
            )
            self.results_table.setItem(
                row,
                1,
                QTableWidgetItem(f"0/{total}"),
            )
            self.update_action_status(action, 0, total)
        self.worker.start()

    def update_progress(
        self,
        percent: int,
        elapsed: float,
        remaining: float,
    ) -> None:
        percent = max(0, min(int(percent), 100))
        self.progress.set_animated_value(percent)
        txt = (
            f"Temps écoulé: {int(elapsed)}s | "
            f"Temps restant estimé: {int(remaining)}s"
        )
        self.time_label.setText(txt)

    def update_action_status(self, action: str, done: int, total: int) -> None:
        """Display per-action progress in labels and table."""
        text = f"{action.capitalize()} : {done}/{total}"
        if action == "variantes":
            self.status_var.setText(text)
        elif action == "fiches":
            self.status_fiche.setText(text)
        elif action == "export":
            self.status_export.setText(text)
        if hasattr(self, "action_rows") and action in self.action_rows:
            row = self.action_rows[action]
            item = self.results_table.item(row, 1)
            if item:
                item.setText(f"{done}/{total}")

    def toggle_log(self, checked: bool) -> None:
        self.log_area.setVisible(checked)

    def copy_log(self) -> None:
        """Copy the current log to the clipboard."""
        clipboard = QApplication.clipboard()
        if self.log_area.isVisible():
            text = self.log_area.toPlainText()
        else:
            text = "".join(self.internal_logs)
        clipboard.setText(text)
        self.statusBar().showMessage("Journal copié !", 3000)

    def clear_log(self) -> None:
        """Erase the visible log and clear the internal buffer."""
        self.log_area.clear()
        self.internal_logs.clear()
        self.statusBar().showMessage("Journal vidé !", 3000)

    def append_log(self, text: str) -> None:
        self.internal_logs.append(text)
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.insertPlainText(text)
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.ensureCursorVisible()

    def append_update_log(self, text: str, color: str = "white") -> None:
        cursor = self.update_log.textCursor()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text, fmt)
        self.update_log.setTextCursor(cursor)
        self.update_log.ensureCursorVisible()

    # ---------- Dependency management ----------
    def _load_requirements(self) -> list[str]:
        req = os.path.join(os.path.dirname(__file__), "requirements.txt")
        packages: list[str] = []
        if os.path.exists(req):
            with open(req, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        name = re.split(r"[<>=]", line)[0]
                        packages.append(name)
        return packages

    def _pkg_installed(self, name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    def refresh_deps_status(self) -> None:
        self.deps_table.setRowCount(len(self.required_packages))
        self.install_btns: dict[str, QPushButton] = {}
        for row, pkg in enumerate(self.required_packages):
            self.deps_table.setItem(row, 0, QTableWidgetItem(pkg))
            installed = self._pkg_installed(pkg)
            item = QTableWidgetItem("OK" if installed else "Manquant")
            color = QColor("green" if installed else "red")
            item.setForeground(color)
            self.deps_table.setItem(row, 1, item)
            if installed:
                self.deps_table.setCellWidget(row, 2, QWidget())
            else:
                btn = QPushButton("Installer")
                btn.clicked.connect(
                    lambda _=False, p=pkg: self.install_single_dep(p)
                )
                self.deps_table.setCellWidget(row, 2, btn)
                self.install_btns[pkg] = btn

    def install_single_dep(self, pkg: str) -> None:
        self.append_log(f"Installation de {pkg}\n")
        self.disable_dep_buttons()
        self.pip_thread = PipInstaller([pkg])
        self.pip_thread.finished.connect(self.on_pip_finished)
        self.pip_thread.start()

    def install_all_deps(self) -> None:
        req = os.path.join(os.path.dirname(__file__), "requirements.txt")
        self.append_log("Installation des dépendances\n")
        self.disable_dep_buttons()
        self.pip_thread = PipInstaller(["-r", req])
        self.pip_thread.finished.connect(self.on_pip_finished)
        self.pip_thread.start()

    def disable_dep_buttons(self) -> None:
        self.install_all_btn.setEnabled(False)
        self.refresh_deps_btn.setEnabled(False)
        for btn in self.install_btns.values():
            btn.setEnabled(False)

    def enable_dep_buttons(self) -> None:
        self.install_all_btn.setEnabled(True)
        self.refresh_deps_btn.setEnabled(True)
        for btn in self.install_btns.values():
            btn.setEnabled(True)

    def on_pip_finished(self, pkg: str, ok: bool, output: str) -> None:
        self.enable_dep_buttons()
        self.append_log(output)
        if ok:
            QMessageBox.information(
                self,
                "Succès",
                f"{pkg} installé avec succès",
            )
            self.statusBar().showMessage(
                f"{pkg} installé avec succès",
                5000,
            )
        else:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'installation de {pkg}",
            )
            self.statusBar().showMessage(
                f"Erreur lors de l'installation de {pkg}",
                5000,
            )
        self.refresh_deps_status()
        if ok:
            if pkg.startswith("-r"):
                missing = [
                    p for p in self.required_packages if not self._pkg_installed(p)
                ]
                if missing:
                    QMessageBox.information(
                        self,
                        "Redémarrage recommandé",
                        "Un redémarrage peut être nécessaire pour finaliser l'installation.",
                    )
            else:
                target = pkg.split()[0]
                if not self._pkg_installed(target):
                    QMessageBox.information(
                        self,
                        "Redémarrage recommandé",
                        "Le module reste manquant. Redémarrez l'application.",
                    )

    def on_finished(self) -> None:
        self.launch_btn.setEnabled(True)
        QMessageBox.information(self, "Terminé", "Opérations terminées")

    def _apply_stylesheet(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except OSError:
            self.setStyleSheet(DARK_STYLE)

    def on_theme_changed(self) -> None:
        style_dir = os.path.join(os.path.dirname(__file__), "ui")
        if self.theme_toggle.isChecked():
            theme = os.path.join(style_dir, "style.qss")
        else:
            theme = os.path.join(style_dir, "light.qss")
        self._apply_stylesheet(theme)
        self.settings.setValue("theme", theme)
        self._update_theme_icon()

    def _update_theme_icon(self) -> None:
        if self.theme_toggle.isChecked():
            self.theme_toggle.setIcon(qta.icon("fa5s.moon"))
            self.theme_toggle.setText("Mode sombre")
        else:
            self.theme_toggle.setIcon(qta.icon("fa5s.sun"))
            self.theme_toggle.setText("Mode clair")
        self.theme_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

    def update_from_git(self) -> None:
        cmd = ["git", "pull", "origin", "main"]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.repo_dir
        )
        output = proc.stdout + proc.stderr
        for line in output.splitlines():
            low = line.lower()
            if "error" in low or "fatal" in low:
                color = "red"
            elif "warning" in low:
                color = "orange"
            else:
                color = "green"
            self.append_update_log(line + "\n", color)
        if proc.returncode == 0:
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_dir,
            ).stdout.strip()
            self.append_update_log(f"Version : {commit}\n", "blue")

    def restart_app(self) -> None:
        import sys, os, traceback
        from PySide6.QtWidgets import QMessageBox

        confirm = QMessageBox.question(
            self,
            "Redémarrer",
            "Voulez-vous redémarrer l'application ?",
        )
        if confirm != QMessageBox.Yes:
            return

        python = sys.executable
        script = os.path.abspath(__file__)
        script_dir = os.path.dirname(script)
        cwd = os.getcwd()
        logger.info("Redémarrage avec :")
        logger.info(f"  python : {python}")
        logger.info(f"  script : {script}")
        logger.info(f"  cwd    : {cwd}")

        # Place le cwd sur le dossier du script principal
        os.chdir(script_dir)

        try:
            if not os.path.exists(script):
                raise FileNotFoundError(f"Script introuvable : {script}")
            self.statusBar().showMessage("Redémarrage de l'application…", 3000)
            os.execv(python, [python, script])
        except Exception as e:
            logger.exception("Échec du redémarrage avec %s %s", python, script)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Redémarrage échoué !\n\n"
                f"python : {python}\nscript : {script}\ncwd : {cwd}\n\n"
                f"Erreur : {e}\n\n{traceback.format_exc()}",
            )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    app = QApplication(sys.argv)
    settings = QSettings("scraping_app", "ui")

    def load_extra_params() -> dict[str, str]:
        extras: dict[str, str] = {}
        font = settings.value("font", "")
        density = settings.value("density", "")
        if font:
            extras["font"] = font
        if density:
            extras["density"] = density
        return extras

    extras = load_extra_params()
    apply_stylesheet(app, theme="dark_purple.xml", extra=extras)
    win = MainWindow()
    win.extra_params = extras
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
