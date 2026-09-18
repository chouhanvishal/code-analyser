import unittest

from appconf.loader import load


class Acceptance(unittest.TestCase):
    def test_file_overrides_defaults(self):
        self.assertEqual(load({"port": 80}, {"port": 8080}, {}), {"port": 8080})

    def test_env_overrides_file(self):
        self.assertEqual(load({"port": 80}, {"port": 8080}, {"APP_PORT": "9090"}), {"port": 9090})

    def test_env_prefix_required(self):
        self.assertEqual(load({"port": 80}, {}, {"PORT": "9090", "HOME": "/x"}), {"port": 80})

    def test_bool_and_int_conversion(self):
        out = load({}, {}, {"APP_DEBUG": "TRUE", "APP_WORKERS": "4", "APP_NAME": "svc"})
        self.assertEqual(out, {"debug": True, "workers": 4, "name": "svc"})

    def test_false_conversion(self):
        self.assertEqual(load({}, {}, {"APP_DEBUG": "false"}), {"debug": False})

    def test_keys_from_all_sources(self):
        out = load({"a": 1}, {"b": 2}, {"APP_C": "3"})
        self.assertEqual(out, {"a": 1, "b": 2, "c": 3})

    def test_inputs_not_mutated(self):
        d, f, e = {"a": 1}, {"a": 2}, {"APP_A": "3"}
        load(d, f, e)
        self.assertEqual((d, f, e), ({"a": 1}, {"a": 2}, {"APP_A": "3"}))
