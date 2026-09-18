import unittest

from textkit.slug import slugify


class Acceptance(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_accents(self):
        self.assertEqual(slugify("Crème Brûlée"), "creme-brulee")

    def test_runs_collapse(self):
        self.assertEqual(slugify("a  --  b___c"), "a-b-c")

    def test_strip_edges(self):
        self.assertEqual(slugify("--hello--"), "hello")

    def test_digits_kept(self):
        self.assertEqual(slugify("Version 2.0.1"), "version-2-0-1")

    def test_empty(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify("   "), "")
        self.assertEqual(slugify("!!!"), "")

    def test_max_length(self):
        self.assertEqual(slugify("hello wonderful world", max_length=10), "hello-wond")
        self.assertEqual(slugify("hello wonderful world", max_length=6), "hello")
        self.assertEqual(slugify("hello wonderful world", max_length=15), "hello-wonderful")
        self.assertEqual(slugify("hello", max_length=100), "hello")

    def test_non_latin_dropped(self):
        self.assertEqual(slugify("日本語 test"), "test")
