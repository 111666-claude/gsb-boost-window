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


class HalfOpenBoundaryTest(unittest.TestCase):
    def test_end_moment_is_inactive(self):
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        self.assertEqual(book.active_at(2000), [])

    def test_start_moment_is_active(self):
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        self.assertEqual(book.active_at(1000), [("xp", 1.5)])

    def test_just_before_end_is_active(self):
        book = Boosts()
        book.add("a1", 1000, 2000, "xp", 1.5)
        self.assertEqual(book.active_at(1999), [("xp", 1.5)])


class InvalidWindowTest(unittest.TestCase):
    def test_zero_length_window_rejected(self):
        book = Boosts()
        self.assertFalse(book.add("a1", 100, 100, "xp", 1.5))
        self.assertEqual(book.windows, {})
        self.assertEqual(book.active_at(100), [])

    def test_inverted_window_rejected(self):
        book = Boosts()
        self.assertFalse(book.add("a1", 200, 100, "xp", 1.5))
        self.assertEqual(book.windows, {})
        self.assertEqual(book.active_at(150), [])


class KindPriorityTest(unittest.TestCase):
    def test_same_kind_keeps_highest_priority(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5, priority=1)
        book.add("a2", 0, 100, "xp", 2.0, priority=5)
        self.assertEqual(book.active_at(50), [("xp", 2.0)])

    def test_same_priority_picks_smallest_activity_id(self):
        book = Boosts()
        book.add("b2", 0, 100, "xp", 9.0, priority=3)
        book.add("a1", 0, 100, "xp", 2.0, priority=3)
        self.assertEqual(book.active_at(50), [("xp", 2.0)])

    def test_different_kinds_all_kept_sorted_by_kind(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        book.add("a2", 0, 100, "coin", 2.0)
        book.add("a3", 0, 100, "ap", 3.0)
        self.assertEqual(book.active_at(50),
                         [("ap", 3.0), ("coin", 2.0), ("xp", 1.5)])


class IdempotentAddTest(unittest.TestCase):
    def test_duplicate_activity_id_returns_false(self):
        book = Boosts()
        self.assertTrue(book.add("a1", 0, 100, "xp", 1.5))
        self.assertFalse(book.add("a1", 0, 100, "xp", 9.0))

    def test_duplicate_does_not_overwrite(self):
        book = Boosts()
        book.add("a1", 0, 100, "xp", 1.5)
        book.add("a1", 0, 100, "xp", 9.0, priority=99)
        self.assertEqual(book.active_at(50), [("xp", 1.5)])

    def test_replaying_same_operations_gives_same_result(self):
        def run():
            book = Boosts()
            book.add("a1", 0, 100, "xp", 1.5, priority=1)
            book.add("a2", 0, 100, "xp", 2.0, priority=5)
            book.add("a2", 0, 100, "xp", 9.0, priority=9)
            book.add("bad", 50, 50, "xp", 7.0)
            return [book.active_at(t) for t in (0, 50, 99, 100)]

        self.assertEqual(run(), run())


class ScannedCountTest(unittest.TestCase):
    def test_repeated_queries_do_not_rescan(self):
        book = Boosts()
        for index in range(3000):
            book.add("a-%d" % index, 0, 1000000, "kind-%d" % index, 1.0)
        for _ in range(3000):
            book.active_at(0)
        self.assertLessEqual(book.scanned_count(), 3000)


class ReferenceComparisonTest(unittest.TestCase):
    def test_matches_naive_reference_on_random_cases(self):
        import random

        def reference(windows, now):
            best = {}
            for activity_id, (start, end, kind, rate, priority) in windows.items():
                if start <= now < end:
                    key = (-priority, activity_id)
                    if kind not in best or key < best[kind][0]:
                        best[kind] = (key, rate)
            return [(kind, best[kind][1]) for kind in sorted(best)]

        rng = random.Random(20261004)
        kinds = ["ap", "coin", "xp"]
        for case in range(200):
            book = Boosts()
            kept = {}
            for index in range(rng.randint(1, 30)):
                activity_id = "act-%d" % rng.randint(0, 12)
                start = rng.randint(0, 500)
                end = start + rng.randint(-2, 200)
                kind = rng.choice(kinds)
                rate = round(rng.uniform(1.0, 5.0), 1)
                priority = rng.randint(0, 4)
                if book.add(activity_id, start, end, kind, rate, priority):
                    kept[activity_id] = (start, end, kind, rate, priority)
            for _ in range(rng.randint(1, 20)):
                now = rng.randint(0, 700)
                self.assertEqual(book.active_at(now), reference(kept, now),
                                 "case %d now=%d" % (case, now))
