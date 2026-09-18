import unittest

from limiter.bucket import TokenBucket


class Acceptance(unittest.TestCase):
    def test_starts_full_and_drains(self):
        b = TokenBucket(3, 1.0)
        self.assertEqual([b.allow(0.0) for _ in range(4)], [True, True, True, False])

    def test_refills_over_time(self):
        b = TokenBucket(2, 1.0)
        b.allow(0.0); b.allow(0.0)
        self.assertFalse(b.allow(0.5))
        self.assertTrue(b.allow(1.0))

    def test_refill_capped_at_capacity(self):
        b = TokenBucket(2, 10.0)
        self.assertTrue(b.allow(100.0))
        self.assertTrue(b.allow(100.0))
        self.assertFalse(b.allow(100.0))

    def test_cost(self):
        b = TokenBucket(5, 1.0)
        self.assertTrue(b.allow(0.0, cost=3))
        self.assertFalse(b.allow(0.0, cost=3))
        self.assertTrue(b.allow(0.0, cost=2))

    def test_failed_allow_consumes_nothing(self):
        b = TokenBucket(2, 1.0)
        self.assertFalse(b.allow(0.0, cost=3))
        self.assertTrue(b.allow(0.0, cost=2))

    def test_time_going_backwards(self):
        b = TokenBucket(1, 1.0)
        self.assertTrue(b.allow(10.0))
        self.assertFalse(b.allow(5.0))
        self.assertFalse(b.allow(10.5))
        self.assertTrue(b.allow(11.0))

    def test_validation(self):
        with self.assertRaises(ValueError):
            TokenBucket(0, 1.0)
        with self.assertRaises(ValueError):
            TokenBucket(1, 0)
        with self.assertRaises(ValueError):
            TokenBucket(1, 1.0).allow(0.0, cost=0)
