"""Active outcome: "First app works on the first try."

Small local models (the default no-API-key path) frequently answer with chat
prose around the code and no markdown fence at all:

    Sure! Here's your app:
    <!DOCTYPE html> ... </html>
    Hope this helps!

normalize_ai_output wraps that whole thing in the ---CODIGO--- contract, and the
Mode 1 create path wrote it verbatim. The saved index.html then STARTS with
prose, so the browser ignores <!DOCTYPE> (quirks mode) and renders the model's
chatter at the top of the page — the app does not work on the first try.

These tests pin the trim, and pin that non-HTML generations stay untouched.

Run: python3 -m pytest tests -q
"""
import importlib.util
import os
import sys
import tempfile

ACORNIX = "/root/workspace/acornix"
sys.path.insert(0, ACORNIX)

spec = importlib.util.spec_from_file_location(
    "ac_utils_first_try", os.path.join(ACORNIX, "core/utils.py")
)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

DOC = (
    "<!DOCTYPE html>\n<html><head><title>Timer</title></head>"
    "<body><h1>Timer</h1><script>let t=0;</script></body></html>"
)


def test_leading_prose_is_trimmed():
    assert u.trim_to_html_document("Sure! Here's your app:\n\n" + DOC) == DOC


def test_trailing_prose_is_trimmed():
    assert u.trim_to_html_document(DOC + "\n\nHope this helps! Let me know.") == DOC


def test_both_sides_trimmed():
    noisy = "Of course. Below is the code:\n" + DOC + "\nOpen it in a browser."
    assert u.trim_to_html_document(noisy) == DOC


def test_clean_html_is_idempotent():
    assert u.trim_to_html_document(DOC) == DOC
    assert u.trim_to_html_document(u.trim_to_html_document(DOC)) == DOC


def test_fragment_without_html_tag_is_untouched():
    frag = "<body><h1>hi</h1></body>"
    assert u.trim_to_html_document(frag) == frag


def test_python_generation_is_untouched():
    py = "import os\n\ndef main():\n    print('hi')\n"
    assert u.trim_to_html_document(py) == py


def test_empty_and_none_are_safe():
    assert u.trim_to_html_document(None) is None
    assert u.trim_to_html_document("   ") == "   "


def test_create_path_writes_clean_html():
    """End-to-end on the real Mode 1 write path: prose in, clean file out."""
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            noisy = "Sure! Here's your app:\n" + DOC + "\nHope this helps!"
            u.process_and_execute(u.normalize_ai_output(noisy), "timer")
            with open(os.path.join(tmp, "my_apps", "timer", "index.html")) as f:
                saved = f.read()
        finally:
            os.chdir(cwd)
    assert saved.startswith("<!DOCTYPE html>")
    assert saved.rstrip().endswith("</html>")
    assert "Hope this helps" not in saved
    assert "Sure!" not in saved
