"""Mini navigateur pour récupérer un sélecteur CSS et tester le scraping."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict, Protocol
import importlib

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction, QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import os
import asyncio
import shutil
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from websockets.server import serve


class Scraper(Protocol):
    """Callable implementing a scraping function."""

    def __call__(self, url: str, selector: str) -> list[str]:
        ...


class ScrapingThread(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, scraper: Scraper, url: str, selector: str) -> None:
        super().__init__()
        self.scraper = scraper
        self.url = url
        self.selector = selector

    def run(self) -> None:  # pragma: no cover - threads hard to test
        try:
            links = self.scraper(self.url, self.selector)
            self.finished.emit(links)
        except Exception as exc:  # pragma: no cover - show error
            self.error.emit(str(exc))


def load_scrapers() -> Dict[str, Scraper]:
    """Load available scraping callables from ENV.

    Environment variable ``INSPECTEUR_SCRAPERS`` accepts a comma separated
    list of ``name=module:function`` entries. If not provided, the default
    ``scraper_liens.scrape_links`` is used.
    """
    env = os.getenv("INSPECTEUR_SCRAPERS")
    specs = [s.strip() for s in env.split(",") if s.strip()] if env else []
    if not specs:
        default_mod = "..scraper_liens" if __package__ else "scraper_liens"
        specs = [f"Liens={default_mod}:scrape_links"]
    scrapers: Dict[str, Scraper] = {}
    for spec in specs:
        if "=" in spec:
            name, target = spec.split("=", 1)
        else:
            target = spec
            name = spec.split(":")[-1]
        try:
            mod_name, func_name = target.split(":")
            if mod_name.startswith(".") and __package__:
                mod = importlib.import_module(mod_name, __package__)
            else:
                mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            scrapers[name] = func  # type: ignore[assignment]
        except Exception:
            continue
    return scrapers


class SelectorServer(QThread):
    """WebSocket server receiving CSS selectors from the browser."""

    selector_received = Signal(str)

    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        super().__init__()
        self.host = host
        self.port = port

    async def _handler(self, websocket) -> None:  # pragma: no cover - IPC
        async for message in websocket:
            self.selector_received.emit(message)

    def run(self) -> None:  # pragma: no cover - IPC
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        server = serve(self._handler, self.host, self.port)
        loop.run_until_complete(server)
        loop.run_forever()


def find_chrome() -> str | None:
    """Return path to Chrome/Chromium executable if found."""
    candidates = []
    if sys.platform.startswith("win"):
        candidates.extend(
            [
                os.path.join(
                    os.getenv("PROGRAMFILES", ""),
                    "Google",
                    "Chrome",
                    "Application",
                    "chrome.exe",
                ),
                os.path.join(
                    os.getenv("PROGRAMFILES(X86)", ""),
                    "Google",
                    "Chrome",
                    "Application",
                    "chrome.exe",
                ),
                os.path.join(
                    os.getenv("LOCALAPPDATA", ""),
                    "Google",
                    "Chrome",
                    "Application",
                    "chrome.exe",
                ),
            ]
        )
    elif sys.platform == "darwin":
        candidates.append(
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
    else:
        candidates.extend([
            shutil.which("google-chrome"),
            shutil.which("chromium-browser"),
            shutil.which("chromium"),
        ])
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return None


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "load": "Load",
        "use_selector": "Use this selector",
        "use_xpath": "Use XPath",
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
        "use_xpath": "Utiliser cet XPath",
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
    def __init__(self, scrapers: Dict[str, Scraper]) -> None:
        super().__init__()
        self.language = "fr"
        self.setWindowTitle("Inspecteur de Sélecteur")
        self.scrapers = scrapers
        self.current_scraper = next(iter(scrapers.values()))

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

        scraper_layout = QHBoxLayout()
        scraper_layout.addWidget(QLabel("Scraper:"))
        self.scraper_combo = QComboBox()
        for name in scrapers:
            self.scraper_combo.addItem(name)
        self.scraper_combo.currentTextChanged.connect(self.on_scraper_changed)
        scraper_layout.addWidget(self.scraper_combo)
        vlayout.addLayout(scraper_layout)

        self.driver: webdriver.Chrome | None = None
        self.ws_thread = SelectorServer()
        self.ws_thread.selector_received.connect(self.set_selector)
        self.ws_thread.start()

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

    def on_scraper_changed(self, name: str) -> None:
        self.current_scraper = self.scrapers.get(name, self.current_scraper)

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
        if self.driver is None:
            chrome_path = find_chrome()
            if not chrome_path:
                chrome_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select Chrome",
                    "",
                    "Executable (*)",
                )
                if not chrome_path:
                    return
            options = webdriver.ChromeOptions()
            options.add_argument("--remote-debugging-port=9222")
            options.binary_location = chrome_path
            self.driver = webdriver.Chrome(
                ChromeDriverManager().install(), options=options
            )
        self.driver.get(url)
        self.inject_script()

    def inject_script(self) -> None:
        if not self.driver:
            return
        script = """
            if(!window.__selector_ws){
                window.__selector_ws = new WebSocket('ws://localhost:8765');
                function cssPath(el){
                    var path=[];
                    while(el && el.nodeType===1){
                        var selector=el.nodeName.toLowerCase();
                        if(el.id){
                            selector+='#'+el.id;
                            path.unshift(selector);
                            break;
                        }else{
                            var sib=el,nth=1;
                            while(sib=sib.previousElementSibling){
                                if(sib.nodeName.toLowerCase()==selector) nth++;
                            }
                            if(nth!=1) selector+=':nth-of-type('+nth+')';
                        }
                        path.unshift(selector);
                        el=el.parentNode;
                    }
                    return path.join(' > ');
                }
                document.addEventListener('contextmenu',function(e){
                    const sel=cssPath(e.target);
                    window.__selector_ws.send(sel);
                },true);
            }
        """
        try:
            self.driver.execute_script(script)
        except Exception:
            pass

    def set_selector(self, selector: str) -> None:
        if not selector:
            return
        self.selector_edit.setText(selector)
        QApplication.clipboard().setText(selector, QClipboard.Clipboard)

    def handle_scrape(self) -> None:
        url = self.driver.current_url if self.driver else ""
        selector = self.selector_edit.text().strip()
        if not url or not selector:
            return
        self.scrape_button.setEnabled(False)
        self.result_edit.clear()
        self.thread = ScrapingThread(self.current_scraper, url, selector)
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
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            "liens.txt",
            "Fichier texte (*.txt)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.links))

    def export_csv(self) -> None:
        if not self.links:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            "liens.csv",
            "Fichier CSV (*.csv)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for link in self.links:
                    f.write(f"{link}\n")

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    win = BrowserInspector(load_scrapers())
    win.resize(1000, 700)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
