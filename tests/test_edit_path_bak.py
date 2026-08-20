"""Failure recovery: the edit path (Mode 2) must leave a .bak of the last
working index.html, even when the optional ZIP backup is disabled or fails.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.app_creator import keep_bak


GOOD = "<!doctype html><html><body><h1>working app</h1></body></html>"


def test_keep_bak_copies_current_contents(tmp_path):
    target = tmp_path / "index.html"
    target.write_text(GOOD, encoding="utf-8")

    assert keep_bak(str(target)) is True
    bak = tmp_path / "index.html.bak"
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == GOOD
    # original untouched
    assert target.read_text(encoding="utf-8") == GOOD


def test_keep_bak_noop_when_file_missing(tmp_path):
    target = tmp_path / "index.html"
    assert keep_bak(str(target)) is False
    assert not (tmp_path / "index.html.bak").exists()


def test_keep_bak_survives_unwritable_backup(tmp_path, monkeypatch):
    target = tmp_path / "index.html"
    target.write_text(GOOD, encoding="utf-8")

    real_open = open

    def fake_open(path, mode="r", *a, **kw):
        if str(path).endswith(".bak") and "w" in mode:
            raise OSError("No space left on device")
        return real_open(path, mode, *a, **kw)

    monkeypatch.setattr("builtins.open", fake_open)
    # must report failure, not raise, and must not damage the original
    assert keep_bak(str(target)) is False
    monkeypatch.undo()
    assert target.read_text(encoding="utf-8") == GOOD


def test_bak_lets_user_recover_after_bad_overwrite(tmp_path):
    """End-to-end shape: back up, overwrite with worse content, restore."""
    target = tmp_path / "index.html"
    target.write_text(GOOD, encoding="utf-8")
    keep_bak(str(target))

    target.write_text("<html><body>worse regeneration</body></html>", encoding="utf-8")
    restored = (tmp_path / "index.html.bak").read_text(encoding="utf-8")
    target.write_text(restored, encoding="utf-8")

    assert target.read_text(encoding="utf-8") == GOOD
