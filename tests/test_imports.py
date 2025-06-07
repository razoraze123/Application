import importlib
import unittest


class TestImports(unittest.TestCase):
    def test_main_imports(self):
        importlib.import_module('main')

    def test_application_definitif_imports(self):
        try:
            importlib.import_module('application_definitif')
        except ImportError:
            self.skipTest('PySide6 non disponible')

    def test_image_scraper_imports(self):
        importlib.import_module('core.image_scraper')


if __name__ == '__main__':
    unittest.main()
