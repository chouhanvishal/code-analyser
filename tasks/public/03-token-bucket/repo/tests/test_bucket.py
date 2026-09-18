import unittest

from limiter.bucket import TokenBucket


class BucketTests(unittest.TestCase):
    def test_starts_full(self):
        b = TokenBucket(capacity=2, refill_per_second=1.0)
        self.assertTrue(b.allow(now=0.0))
        self.assertTrue(b.allow(now=0.0))
        self.assertFalse(b.allow(now=0.0))
