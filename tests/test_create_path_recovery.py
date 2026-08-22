"""Failure-recovery tests for the CREATE path (app_creator Mode 1).

Mode 2 (edit) was hardened first; Mode 1 wrote whatever came back from the
model straight to disk, so a prose-only or truncated response created an empty
project folder — or clobbered an existing working app of the same name.

Run: python3 -m pytest tests -q
"""
import importlib.util
import os
import sys
import tempfile

ACORNIX = "/root/workspace/acornix"
sys.path.insert(0, ACORNIX)

spec = importlib.util.spec_from_file_location("ac_utils", os.path.join(ACORNIX, "core/utils.py"))
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

DOC = "<!DOCTYPE html><html><body><h1>Stopwatch</h1><script>let t=0;</script></body></html>"


def test_is_usable_code_classification():
    assert u.is_usable_code(DOC) is True
    assert u.is_usable_code("import os\ndef main():\n    print('hello world app')\n") is True
    assert u.is_usable_code("") is False
    assert u.is_usable_code(None) is False
    assert u.is_usable_code("   \n  ") is False
    assert u.is_usable_code("Sure! Here is how you would build that app.") is False
    assert u.is_usable_code("<html></html>") is False  # truncated


def _run_in_tmp(ai_text, name, preexisting=None):
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            path = os.path.join("my_apps", name)
            if preexisting is not None:
                os.makedirs(path)
                with open(os.path.join(path, "index.html"), "w") as f:
                    f.write(preexisting)
            u.process_and_execute(ai_text, name)
            exists = os.path.isdir(path)
            content = None
            f_path = os.path.join(path, "index.html")
            if os.path.exists(f_path):
                with open(f_path) as f:
                    content = f.read()
            return exists, content
        finally:
            os.chdir(cwd)


def test_prose_only_response_does_not_create_folder():
    exists, content = _run_in_tmp("---CODIGO---\nSure! I can build that for you.\n", "ghost")
    assert exists is False, "unusable output must not create a project folder"
    assert content is None


def test_prose_only_response_does_not_clobber_existing_app():
    exists, content = _run_in_tmp(
        "---CODIGO---\nSure! Here is the updated app.\n", "stopwatch", preexisting=DOC
    )
    assert exists is True
    assert content == DOC, "a working app must survive an unusable model response"


def test_usable_response_is_written():
    exists, content = _run_in_tmp("---CODIGO---\n" + DOC + "\n---SUGERENCIA---\nadd laps", "sw2")
    assert exists is True
    assert content is not None and "Stopwatch" in content


def test_fenced_contract_is_stripped_on_first_try():
    """Active outcome: 'First app works on the first try.'

    Small local models wrap the generated code in a ```html fence even inside
    the ---CODIGO--- contract. The Mode 1 create path (process_and_execute)
    must strip that single wrapping fence so the file the user opens is real
    HTML, not backticks. Regression guard for commit 0ff2586b.
    """
    fenced = "---CODIGO---\n```html\n" + DOC + "\n```\n---SUGERENCIA---\nadd laps"
    exists, content = _run_in_tmp(fenced, "fencewire")
    assert exists is True, "a fenced-but-usable response must still create the app"
    assert content is not None
    assert content.startswith(
        "<!DOCTYPE html>"
    ), "a stray opening fence must not reach the saved file"
    assert "```" not in content, "no markdown fence may remain in the saved app"
