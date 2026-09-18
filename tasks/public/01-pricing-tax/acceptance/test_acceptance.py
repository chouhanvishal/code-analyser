import unittest

from pricing.cart import Item, total


class Acceptance(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(total([Item("a", 10.0)], 0.2), 12.0)

    def test_empty_cart(self):
        self.assertEqual(total([], 0.2), 0.0)

    def test_zero_tax(self):
        self.assertEqual(total([Item("a", 19.99)], 0.0), 19.99)

    def test_quantity(self):
        self.assertEqual(total([Item("a", 2.5, 4)], 0.1), 11.0)

    def test_rounding(self):
        self.assertEqual(total([Item("a", 0.1), Item("b", 0.2)], 0.0), 0.3)
        self.assertEqual(total([Item("a", 1.005)], 0.0), 1.0)

    def test_signature_unchanged(self):
        import inspect
        self.assertEqual(list(inspect.signature(total).parameters), ["items", "tax_rate"])
