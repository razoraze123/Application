import unittest
from core.utils import extraire_ids_depuis_input
from core.image_scraper import ImageScraper


class TestUtils(unittest.TestCase):
    def test_extraire_ids_depuis_input(self):
        result = extraire_ids_depuis_input('A1-A3')
        self.assertEqual(result, ['A1', 'A2', 'A3'])

    def test_extraire_ids_depuis_input_invalid(self):
        result = extraire_ids_depuis_input('bad')
        self.assertEqual(result, [])

    def test_slugify(self):
        result = ImageScraper.slugify('Hôtel du Nord')
        self.assertEqual(result, 'hotel-du-nord')


if __name__ == '__main__':
    unittest.main()
