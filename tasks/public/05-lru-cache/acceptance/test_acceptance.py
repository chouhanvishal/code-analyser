import unittest

from cache.lru import LRUCache


class Acceptance(unittest.TestCase):
    def test_put_get(self):
        c = LRUCache(2)
        c.put("a", 1)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("zzz"))

    def test_eviction_order(self):
        c = LRUCache(2)
        c.put("a", 1); c.put("b", 2); c.put("c", 3)
        self.assertFalse(c.contains("a"))
        self.assertEqual(c.keys(), ["b", "c"])

    def test_get_refreshes(self):
        c = LRUCache(2)
        c.put("a", 1); c.put("b", 2)
        c.get("a")
        c.put("c", 3)
        self.assertEqual(c.keys(), ["a", "c"])

    def test_put_existing_refreshes_and_updates(self):
        c = LRUCache(2)
        c.put("a", 1); c.put("b", 2)
        c.put("a", 10)
        c.put("c", 3)
        self.assertEqual(c.keys(), ["a", "c"])
        self.assertEqual(c.get("a"), 10)

    def test_none_value(self):
        c = LRUCache(1)
        c.put("a", None)
        self.assertTrue(c.contains("a"))
        self.assertIsNone(c.get("a"))
        self.assertFalse(c.contains("b"))

    def test_len(self):
        c = LRUCache(3)
        self.assertEqual(len(c), 0)
        c.put("a", 1); c.put("b", 2); c.put("a", 3)
        self.assertEqual(len(c), 2)

    def test_validation(self):
        for bad in (0, -1, 1.5, "2", True):
            with self.assertRaises(ValueError):
                LRUCache(bad)
