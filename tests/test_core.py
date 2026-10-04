import unittest

from boosts.core import Boosts


def reference_active_at(ledger, now_ms):
    """参考实现：半开区间 + 同类取优 + 按 kind 升序，暴力全扫。"""
    best = {}
    for activity_id, (start, end, kind, rate, priority) in ledger.items():
        if start <= now_ms < end:
            key = (-priority, activity_id)
            if kind not in best or key < best[kind][0]:
                best[kind] = (key, rate)
    return [(kind, best[kind][1]) for kind in sorted(best)]


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

    def test_start_boundary_is_active(self):
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        self.assertEqual(book.active_at(1000), [("xp", 1.5)])

    def test_end_boundary_is_inactive(self):
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        self.assertEqual(book.active_at(2000), [])

    def test_same_kind_highest_priority_wins(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5, priority=1)
        book.add("a2", 0, 100, "xp", 2.0, priority=5)
        self.assertEqual(book.active_at(50), [("xp", 2.0)])

    def test_same_priority_tie_breaks_by_activity_id(self):
        book = Boosts()
        book.add("b2", 0, 100, "xp", 9.0, priority=3)
        book.add("b1", 0, 100, "xp", 1.5, priority=3)
        self.assertEqual(book.active_at(50), [("xp", 1.5)])

    def test_different_kinds_kept_and_sorted(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        book.add("a2", 0, 100, "coin", 2.0)
        self.assertEqual(book.active_at(50), [("coin", 2.0), ("xp", 1.5)])

    def test_duplicate_activity_id_rejected(self):
        book = Boosts()
        self.assertTrue(book.add("a1", 0, 100, "xp", 1.5))
        self.assertFalse(book.add("a1", 0, 100, "xp", 9.0))
        self.assertEqual(book.active_at(50), [("xp", 1.5)])

    def test_invalid_window_rejected(self):
        book = Boosts()
        self.assertFalse(book.add("a1", 100, 100, "xp", 1.5))
        self.assertFalse(book.add("a2", 200, 100, "xp", 1.5))
        self.assertEqual(book.active_at(100), [])
        self.assertNotIn("a1", book.windows)
        self.assertNotIn("a2", book.windows)
        self.assertTrue(book.add("a1", 100, 200, "xp", 1.5))

    def test_scanned_not_proportional_to_windows_times_queries(self):
        book = Boosts()
        for index in range(3000):
            book.add("a-%d" % index, 0, 1000000, "kind-%d" % index, 1.0)
        for _ in range(3000):
            book.active_at(0)
        self.assertLessEqual(book.scanned_count(), 3000)

    def test_replaying_same_operations_gives_same_results(self):
        results = []
        for _ in range(2):
            book = Boosts()
            accepted = [
                book.add("a1", 0, 100, "xp", 1.5, priority=1),
                book.add("a1", 0, 100, "xp", 9.0, priority=9),
                book.add("a2", 50, 150, "xp", 2.0, priority=5),
                book.add("a3", 0, 200, "coin", 3.0),
            ]
            results.append((accepted, book.active_at(75), book.active_at(150)))
        self.assertEqual(results[0], results[1])

    def test_randomized_against_reference(self):
        import random

        rng = random.Random(20261004)
        kinds = ["xp", "coin", "drop"]
        for _ in range(200):
            book = Boosts()
            ledger = {}
            for _ in range(rng.randint(1, 12)):
                activity_id = "a%d" % rng.randint(0, 8)
                start = rng.randint(0, 50)
                end = start + rng.randint(-2, 20)
                kind = rng.choice(kinds)
                rate = round(rng.uniform(0.5, 3.0), 2)
                priority = rng.randint(0, 5)
                accepted = book.add(activity_id, start, end, kind, rate, priority)
                expected = end > start and activity_id not in ledger
                self.assertEqual(accepted, expected)
                if expected:
                    ledger[activity_id] = (start, end, kind, rate, priority)
            for _ in range(rng.randint(1, 10)):
                now = rng.randint(0, 80)
                self.assertEqual(
                    book.active_at(now), reference_active_at(ledger, now)
                )


if __name__ == "__main__":
    unittest.main()
