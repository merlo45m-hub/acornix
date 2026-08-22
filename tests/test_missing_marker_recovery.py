"""First-try recovery: the model omits the ---CODIGO--- contract marker.

Small local models (qwen2.5-coder:1.5b and friends) often answer a Mode 1
"create an app" prompt with the app itself and no ---CODIGO--- marker. The
create path used to reject that outright, so the user's first try produced
nothing at all even though a valid HTML document had been generated.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils import process_and_execute  # noqa: E402

APP = (
    "<!DOCTYPE html>\n<html><head><title>Timer</title></head>\n"
    "<body><h1>Timer</h1><script>let t=0;</script></body></html>"
)


def _app_file(tmp_path, name="markerless"):
    return tmp_path / "my_apps" / name / "index.html"


def _run(tmp_path, text, name="markerless"):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        process_and_execute(text, filename=f"{name}.html")
    finally:
        os.chdir(cwd)
    return _app_file(tmp_path, name)


def test_markerless_html_is_recovered_and_written(tmp_path):
    out = _run(tmp_path, APP)
    assert out.exists(), "markerless but valid HTML must still produce an app"
    written = out.read_text(encoding="utf-8")
    assert written.startswith("<!DOCTYPE html>")
    assert "---CODIGO---" not in written


def test_markerless_html_with_chat_prose_is_trimmed(tmp_path):
    text = f"Sure! Here's your timer app:\n\n{APP}\n\nHope this helps!"
    out = _run(tmp_path, text, name="prosey")
    written = out.read_text(encoding="utf-8")
    assert written.startswith("<!DOCTYPE html>")
    assert written.rstrip().endswith("</html>")
    assert "Hope this helps" not in written


def test_markerless_prose_only_is_still_rejected(tmp_path):
    out = _run(tmp_path, "I can't build that app, sorry.", name="proseonly")
    assert not out.exists()
    assert not (tmp_path / "my_apps" / "proseonly").exists()


def test_empty_response_is_still_rejected(tmp_path):
    assert not _run(tmp_path, "   ", name="empty").exists()


def test_marker_path_is_unchanged(tmp_path):
    out = _run(tmp_path, f"---CODIGO---\n{APP}\n---SUGERENCIA---\nadd laps", name="withmarker")
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
