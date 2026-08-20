"""Failure-recovery tests: cloud-provider output contract + overwrite backup.

Two gaps remained in the active outcome (local app generation must never lose
a working app):

1. The openai/anthropic branches of ask_ai() returned raw model text, while
   only the local/ollama branches ran it through normalize_ai_output(). A cloud
   response wrapped in markdown fences therefore either failed the
   ---CODIGO--- contract outright or wrote ``` fences into index.html.
2. process_and_execute() overwrote an existing app file in place. Even a
   *usable* but worse regeneration destroyed the only copy of a working app.

Run: python3 -m pytest tests -q
"""
import importlib.util
import os
import sys
import tempfile

ACORNIX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ACORNIX)

spec = importlib.util.spec_from_file_location("ac_utils2", os.path.join(ACORNIX, "core/utils.py"))
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

DOC_V1 = "<!DOCTYPE html><html><body><h1>Timer v1</h1><script>let t=0;</script></body></html>"
DOC_V2 = "<!DOCTYPE html><html><body><h1>Timer v2</h1><script>let t=1;</script></body></html>"


def test_fenced_cloud_style_response_is_normalized_to_contract():
    fenced = "Sure, here you go:\n```html\n" + DOC_V1 + "\n```\nHope that helps."
    out = u.normalize_ai_output(fenced)
    assert "---CODIGO---" in out
    assert "```" not in out
    code = out.split("---SUGERENCIA---")[0].replace("---CODIGO---", "").strip()
    assert code == DOC_V1
    assert u.is_usable_code(code) is True


def test_normalize_is_idempotent_and_none_safe():
    already = "---CODIGO---\n" + DOC_V1 + "\n---SUGERENCIA---\n"
    assert u.normalize_ai_output(already) == already
    assert u.normalize_ai_output(None) is None
    assert u.normalize_ai_output("") == ""


def _write(ai_text, name, preexisting=None):
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            path = os.path.join("my_apps", name)
            f_path = os.path.join(path, "index.html")
            if preexisting is not None:
                os.makedirs(path)
                with open(f_path, "w") as f:
                    f.write(preexisting)
            u.process_and_execute(ai_text, name)
            cur = bak = None
            if os.path.exists(f_path):
                with open(f_path) as f:
                    cur = f.read()
            if os.path.exists(f_path + ".bak"):
                with open(f_path + ".bak") as f:
                    bak = f.read()
            return cur, bak
        finally:
            os.chdir(cwd)


def test_overwrite_keeps_recoverable_backup_of_previous_version():
    cur, bak = _write(
        "---CODIGO---\n" + DOC_V2 + "\n---SUGERENCIA---\n", "timer", preexisting=DOC_V1
    )
    assert cur is not None and "Timer v2" in cur
    assert bak == DOC_V1, "previous working app must remain recoverable from .bak"


def test_first_create_writes_no_spurious_backup():
    cur, bak = _write("---CODIGO---\n" + DOC_V1 + "\n---SUGERENCIA---\n", "fresh")
    assert cur is not None and "Timer v1" in cur
    assert bak is None


def test_unusable_response_leaves_no_backup_and_keeps_original():
    cur, bak = _write("---CODIGO---\nSure! Rebuilding now.\n", "timer", preexisting=DOC_V1)
    assert cur == DOC_V1
    assert bak is None, "guarded path must not touch disk at all"
