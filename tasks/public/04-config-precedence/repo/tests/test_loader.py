import unittest

from appconf.loader import load


class LoaderTests(unittest.TestCase):
    def test_file_overrides_defaults(self):
        self.assertEqual(load({"port": 80}, {"port": 8080}, {}), {"port": 8080})
