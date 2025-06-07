import importlib
import importlib.util
import unittest

SKIP_SELENIUM = importlib.util.find_spec("selenium") is None
SKIP_PANDAS = importlib.util.find_spec("pandas") is None


class TestImports(unittest.TestCase):
    def test_main_imports(self):
        importlib.import_module('main')

    def test_application_definitif_imports(self):
        try:
            importlib.import_module('application_definitif')
        except ImportError:
            self.skipTest('PySide6 non disponible')

    def test_image_scraper_imports(self):
        if SKIP_SELENIUM:
            self.skipTest('selenium non disponible')
        importlib.import_module('core.image_scraper')

    def test_scraper_imports(self):
        if SKIP_SELENIUM or SKIP_PANDAS:
            self.skipTest('dépendances selenium/pandas manquantes')
        importlib.import_module('core.scraper')


if __name__ == '__main__':
    unittest.main()
