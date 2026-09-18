import unittest

from pricing.cart import Item, subtotal, total


class SubtotalTests(unittest.TestCase):
    def test_subtotal(self):
        self.assertEqual(subtotal([Item("a", 2.0, 3), Item("b", 1.5)]), 7.5)


class TotalTests(unittest.TestCase):
    def test_total_applies_tax(self):
        self.assertEqual(total([Item("a", 10.0)], 0.2), 12.0)
