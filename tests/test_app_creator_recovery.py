import importlib.util, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
spec = importlib.util.spec_from_file_location(
    "ac", os.path.join(REPO, "plugins", "app_creator.py")
)
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
except SystemExit:
    pass

doc = "<!DOCTYPE html><html><body><h1>Stopwatch</h1><script>let t=0;</script></body></html>"
cases = [
    # clean_html_code: local ---CODIGO--- contract
    ("contract", m.clean_html_code("blah\n---CODIGO---\n" + doc + "\n---SUGERENCIA---\nadd laps"), doc),
    # fenced cloud contract
    ("fenced_html", m.clean_html_code("intro\n```html\n" + doc + "\n```\nbye"), doc),
    ("fenced_plain", m.clean_html_code("```\n" + doc + "\n```"), doc),
    ("raw", m.clean_html_code(doc), doc),
    ("none", m.clean_html_code(None), None),
]
fails = []
for name, got, want in cases:
    ok = (got or "") .strip() == (want or "").strip() if want else got == want
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails.append((name, repr(got)[:120]))

guard = [
    ("usable_doc", doc, True),
    ("empty", "", False),
    ("none", None, False),
    ("whitespace", "   \n ", False),
    ("prose_only", "Sure! Here is how you would update the stopwatch app for you.", False),
    ("too_short", "<html></html>", False),
    ("body_only", "<body><div id='app'>hello world stopwatch app content</div></body>", True),
]
for name, code, want in guard:
    got = m.is_usable_html(code)
    ok = got == want
    print(("PASS " if ok else "FAIL ") + "guard:" + name)
    if not ok:
        fails.append(("guard:" + name, got))

print("FAILURES:", fails if fails else "none")


def test_app_creator_recovery():
    """pytest entrypoint — assert instead of sys.exit so collection works."""
    assert not fails, fails


if __name__ == "__main__":
    sys.exit(1 if fails else 0)
