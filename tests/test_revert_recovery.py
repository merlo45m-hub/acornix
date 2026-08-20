"""Tests for the user-facing revert half of failure recovery.

The edit path guarantees a .bak of the last working version; restore_bak is
how the user gets back to it without digging through the filesystem.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.app_creator import restore_bak, keep_bak

GOOD = "<!DOCTYPE html><html><body><h1>Working app v1</h1></body></html>"
NEWER = "<!DOCTYPE html><html><body><h1>Working app v2 regression</h1></body></html>"


def _tmp(content, suffix=""):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "index.html")
    if content is not None:
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return p


def test_restore_puts_back_previous_version():
    p = _tmp(GOOD)
    assert keep_bak(p) is True
    with open(p, "w", encoding="utf-8") as f:
        f.write(NEWER)
    assert restore_bak(p) is True
    with open(p, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_restore_is_reversible_one_step():
    p = _tmp(GOOD)
    keep_bak(p)
    with open(p, "w", encoding="utf-8") as f:
        f.write(NEWER)
    assert restore_bak(p) is True
    # the version we replaced became the new .bak, so revert can be undone
    assert restore_bak(p) is True
    with open(p, encoding="utf-8") as f:
        assert f.read() == NEWER


def test_restore_without_bak_is_a_noop():
    p = _tmp(GOOD)
    assert restore_bak(p) is False
    with open(p, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_restore_refuses_unusable_bak():
    p = _tmp(GOOD)
    with open(p + ".bak", "w", encoding="utf-8") as f:
        f.write("Sure! Here is your app:")
    assert restore_bak(p) is False
    with open(p, encoding="utf-8") as f:
        assert f.read() == GOOD


def test_restore_recreates_a_missing_file_from_bak():
    p = _tmp(GOOD)
    keep_bak(p)
    os.remove(p)
    assert restore_bak(p) is True
    with open(p, encoding="utf-8") as f:
        assert f.read() == GOOD
