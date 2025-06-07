import unittest
from core.utils import extraire_ids_depuis_input


class TestUtils(unittest.TestCase):
    def test_extraire_ids_depuis_input(self):
        result = extraire_ids_depuis_input('A1-A3')
        self.assertEqual(result, ['A1', 'A2', 'A3'])


if __name__ == '__main__':
    unittest.main()
