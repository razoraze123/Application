import unittest
from core.utils import extraire_ids_depuis_input


class TestUtils(unittest.TestCase):
    def test_extraire_ids_depuis_input(self):
        result = extraire_ids_depuis_input('A1-A3')
        self.assertEqual(result, ['A1', 'A2', 'A3'])

    def test_extraire_ids_depuis_input_invalid(self):
        self.assertEqual(extraire_ids_depuis_input('invalid'), [])

    def test_extraire_ids_depuis_input_reversed(self):
        self.assertEqual(extraire_ids_depuis_input('A5-A1'), [])


if __name__ == '__main__':
    unittest.main()
