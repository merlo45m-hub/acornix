"""Failure recovery: the Mode 2 (edit) write path must be atomic.

Mode 1 (create) already wrote atomically. Mode 2 wrote the model's HTML
straight over the app the user was editing, so a crash, a battery death, or a
full /storage mid-write truncated a working app with no way back.

These tests exercise core.atomic.atomic_write_text directly (the helper both
paths now share) and assert the app_creator edit path calls it.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.atomic import atomic_write_text


class TestAtomicWriteText(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "index.html")
        self.working = "<html><body>working app</body></html>"
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(self.working)

    def test_successful_write_replaces_content(self):
        new = "<html><body>v2</body></html>"
        self.assertTrue(atomic_write_text(self.path, new))
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), new)

    def test_no_tmp_file_left_behind_on_success(self):
        atomic_write_text(self.path, "<html>ok</html>")
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_crash_mid_write_leaves_working_app_intact(self):
        """Disk full / process killed while streaming the new version."""
        real_open = open

        def exploding_open(path, *a, **kw):
            fh = real_open(path, *a, **kw)
            if str(path).endswith(".tmp"):
                fh.write = mock.Mock(
                    side_effect=OSError(28, "No space left on device")
                )
            return fh

        with mock.patch("builtins.open", exploding_open):
            ok = atomic_write_text(self.path, "<html>never lands</html>")

        self.assertFalse(ok)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.working, "working app was destroyed")
        self.assertFalse(
            os.path.exists(self.path + ".tmp"), "temp file left behind"
        )

    def test_failed_swap_leaves_working_app_intact(self):
        with mock.patch("os.replace", side_effect=OSError("swap failed")):
            ok = atomic_write_text(self.path, "<html>v2</html>")
        self.assertFalse(ok)
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.working)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_write_to_new_path_creates_file(self):
        fresh = os.path.join(self.dir, "new.html")
        self.assertTrue(atomic_write_text(fresh, "<html>new</html>"))
        self.assertTrue(os.path.exists(fresh))


class TestEditPathUsesAtomicWrite(unittest.TestCase):
    def test_app_creator_edit_path_has_no_raw_overwrite(self):
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "plugins",
            "app_creator.py",
        )
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("atomic_write_text(target_file", src)
        self.assertNotIn('open(target_file, "w"', src)


if __name__ == "__main__":
    unittest.main()
