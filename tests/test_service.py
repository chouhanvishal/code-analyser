"""Unit tests for the autonomous code-change service components."""
import tempfile
import unittest
from pathlib import Path

from service.gate import DeliveryGate, static_check
from service.sandbox import copy_repo, get_git_diff


class StaticCheckTests(unittest.TestCase):
    def test_empty_diff_rejected(self):
        self.assertEqual(static_check(""), "empty diff")

    def test_oversized_diff_rejected(self):
        oversized = "diff --git a/file b/file\n" + "x" * 200_001
        self.assertIn("limit is 200000", static_check(oversized))

    def test_crlf_rejected(self):
        diff = "diff --git a/a.py b/a.py\r\n--- a/a.py\r\n+++ b/a.py\r\n"
        self.assertEqual(static_check(diff), "CRLF line endings")

    def test_non_git_diff_rejected(self):
        diff = "--- a/a.py\n+++ b/a.py\n"
        self.assertIn("must start with 'diff --git '", static_check(diff))

    def test_binary_patch_rejected(self):
        diff = "diff --git a/bin b/bin\nGIT binary patch\nliteral 0\n"
        self.assertEqual(static_check(diff), "binary patch content")

    def test_forbidden_prefix_git_rejected(self):
        diff = "diff --git a/.git/config b/.git/config\n--- a/.git/config\n"
        self.assertIn("restricted", static_check(diff))

    def test_forbidden_prefix_acceptance_rejected(self):
        diff = "diff --git a/acceptance/test.py b/acceptance/test.py\n"
        self.assertIn("restricted", static_check(diff))

    def test_path_traversal_rejected(self):
        diff = "diff --git a/../secret b/../secret\n"
        self.assertIn("escapes", static_check(diff))

    def test_valid_diff_accepted(self):
        diff = (
            "diff --git a/src/main.py b/src/main.py\n"
            "index 1234567..89abcdef 100644\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-def foo(): return 1\n"
            "+def foo(): return 2\n"
        )
        self.assertIsNone(static_check(diff))


if __name__ == "__main__":
    unittest.main()
