
import unittest
from calculator import subtract

class TestSubtractFunction(unittest.TestCase):
    def test_subtract(self):
        self.assertEqual(subtract(3, 2), 1)
        self.assertEqual(subtract(-1, 1), -2)
        self.assertEqual(subtract(0, 0), 0)

if __name__ == '__main__':
    unittest.main()
