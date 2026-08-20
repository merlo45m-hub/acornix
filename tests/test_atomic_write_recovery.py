"""Failure-recovery tests: the app write itself must be crash-safe.

Remaining gap in the active outcome (local app generation must never lose a
working app): process_and_execute() opened the target app file in "w" mode and
wrote the new code directly into it. Truncation happens at open() time, so a
failure part-way through the write (full disk / killed process — routine on a
phone) left a half-written index.html where a working app used to be, with no
restore path even though a .bak had just been taken.

Fix: write to <file>.tmp and os.replace() it into place, and if the write fails
after the original was already gone, restore it from the .bak.

Run: python3 -m pytest tests -q
"""
import importlib.util
import os
import sys
import tempfile

ACORNIX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ACORNIX)

spec = importlib.util.spec_from_file_location(
    "ac_utils3", os.path.join(ACORNIX, "core/utils.py")
)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

GOOD = "<!DOCTYPE html><html><body><h1>Notes v1</h1><script>let n=[];</script></body></html>"
NEW = "<!DOCTYPE html><html><body><h1>Notes v2</h1><script>let n=[1];</script></body></html>"


def _payload(code):
    return f"---CODIGO---\n{code}\n---SUGERENCIA---\nok"


def _app_path(tmp, name="notes"):
    return os.path.join(tmp, "my_apps", name, "index.html")


def _seed(tmp, name="notes", content=GOOD):
    p = _app_path(tmp, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


def test_successful_write_leaves_no_tmp_file():
    """Happy path still works and does not litter a .tmp beside the app."""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            u.process_and_execute(_payload(NEW), filename="notes.html")
        finally:
            os.chdir(cwd)
        p = _app_path(tmp)
        assert os.path.exists(p)
        with open(p, encoding="utf-8") as f:
            assert f.read() == NEW
        assert not os.path.exists(p + ".tmp"), "temp file was left behind"


def test_write_failure_does_not_truncate_working_app():
    """A failing write must leave the existing app intact, not truncated."""
    with tempfile.TemporaryDirectory() as tmp:
        _seed(tmp)
        real_replace = os.replace

        def boom(src, dst):
            raise OSError(28, "No space left on device")

        cwd = os.getcwd()
        os.chdir(tmp)
        os.replace = boom
        try:
            u.process_and_execute(_payload(NEW), filename="notes.html")
        finally:
            os.replace = real_replace
            os.chdir(cwd)

        p = _app_path(tmp)
        with open(p, encoding="utf-8") as f:
            survived = f.read()
        # Pre-fix this file was empty (opened "w" then the write blew up).
        assert survived == GOOD, f"working app was damaged: {survived!r}"
        assert not os.path.exists(p + ".tmp"), "temp file was left behind"


def test_restore_from_bak_when_target_vanishes():
    """If the target is gone after a failed write, restore it from the .bak."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _seed(tmp)
        real_replace = os.replace

        def eat_target(src, dst):
            # Simulate a swap that destroys the destination then fails.
            os.remove(dst)
            raise OSError(5, "I/O error")

        cwd = os.getcwd()
        os.chdir(tmp)
        os.replace = eat_target
        try:
            u.process_and_execute(_payload(NEW), filename="notes.html")
        finally:
            os.replace = real_replace
            os.chdir(cwd)

        assert os.path.exists(p), "app file was not restored from backup"
        with open(p, encoding="utf-8") as f:
            assert f.read() == GOOD


def test_unusable_response_still_writes_nothing():
    """Regression guard: the guard clause runs before any temp file is made."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _seed(tmp)
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            u.process_and_execute(_payload("Sure! Here you go:"), filename="notes.html")
        finally:
            os.chdir(cwd)
        with open(p, encoding="utf-8") as f:
            assert f.read() == GOOD
        assert not os.path.exists(p + ".tmp")
