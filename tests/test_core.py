import unittest

from boosts.core import Boosts


class BoostsTest(unittest.TestCase):
    def test_empty_has_no_boost(self):
        self.assertEqual(Boosts().active_at(0), [])

    def test_inside_window_is_active(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        self.assertEqual(book.active_at(50), [("xp", 1.5)])

    def test_outside_window_is_inactive(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        self.assertEqual(book.active_at(500), [])

    def test_scanned_starts_at_zero(self):
        self.assertEqual(Boosts().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()
