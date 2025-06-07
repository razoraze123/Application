import os
import time
import random
import urllib.request
import re
import unicodedata
from typing import Iterable, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class ImageScraper:
    """Generic image scraper using Selenium."""

    def __init__(
        self,
        chrome_driver_path: Optional[str] = None,
        chrome_binary_path: Optional[str] = None,
        root_folder: str = "images",
        selector: str = ".product-gallery__media img",
    ) -> None:
        self.chrome_driver_path = chrome_driver_path
        self.chrome_binary_path = chrome_binary_path
        self.root_folder = root_folder
        self.selector = selector
        self.driver: Optional[webdriver.Chrome] = None

    # ------------------------------------------------------------------
    # Utility helpers
    @staticmethod
    def slugify(text: str) -> str:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[-\s]+", "-", text).strip("-")

    # ------------------------------------------------------------------
    def load_urls(self, path: str) -> List[str]:
        """Load product URLs from a text file."""
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    # ------------------------------------------------------------------
    def setup_driver(self) -> webdriver.Chrome:
        """Initialise the Selenium driver."""
        options = Options()
        if self.chrome_binary_path:
            options.binary_location = self.chrome_binary_path
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if self.chrome_driver_path:
            service = Service(self.chrome_driver_path)
        else:  # pragma: no cover - fallback used mainly in dev env
            service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        return self.driver

    # ------------------------------------------------------------------
    def get_product_title(self) -> str:
        """Return the current product title. Overridable for custom sites."""
        raw_title = self.driver.title.strip() if self.driver else ""
        return raw_title.split("|")[0].strip()

    def get_image_elements(self) -> Iterable:
        """Return image elements found on the page. Overridable."""
        assert self.driver is not None
        return self.driver.find_elements(By.CSS_SELECTOR, self.selector)

    # ------------------------------------------------------------------
    def scrape_images(self, urls: Iterable[str]) -> int:
        """Main scraping routine."""
        exit_code = 0
        try:
            if self.driver is None:
                self.setup_driver()
            os.makedirs(self.root_folder, exist_ok=True)
            total = len(list(urls)) if not isinstance(urls, list) else len(urls)
            if not isinstance(urls, list):
                urls = list(urls)
            for index, url in enumerate(urls, start=1):
                print(f"\n🔍 Produit {index}/{total} : {url}")
                try:
                    assert self.driver is not None
                    self.driver.get(url)
                    time.sleep(random.uniform(2.5, 4.5))

                    product_title = self.get_product_title()
                    folder = os.path.join(self.root_folder, self.slugify(product_title))
                    os.makedirs(folder, exist_ok=True)

                    images = list(self.get_image_elements())
                    print(f"🖼️ {len(images)} image(s) trouvée(s)")

                    for i, img in enumerate(images):
                        src = img.get_attribute("src")
                        if not src:
                            continue
                        filename = f"img_{i}.webp"
                        filepath = os.path.join(folder, filename)
                        try:
                            urllib.request.urlretrieve(src, filepath)
                            print(f"   ✅ Image {i+1} → {filename}")
                        except Exception as err:
                            exit_code = 1
                            print(f"   ❌ Échec de téléchargement pour image {i+1}: {err}")
                except Exception as e:  # pragma: no cover - debug output
                    exit_code = 1
                    print(f"❌ Erreur sur la page {url} : {e}")
        finally:
            if self.driver:
                self.driver.quit()
        return exit_code

