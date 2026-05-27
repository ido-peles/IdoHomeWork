import unittest
from app import myMultiple

class TestApp(unittest.TestCase):
    def test_myMultiple(self):
        self.assertEqual(myMultiple(2, 3), 6)
        self.assertEqual(myMultiple(-1, 5), -5)
        self.assertEqual(myMultiple(0, 10), 0)

if __name__ == '__main__':
    unittest.main()
