"""Guard: a slow-but-successful local generation must not be thrown away.

Measured on-device decode for qwen2.5-coder:1.5b was 0.21-0.35 tok/s, so the
old hard-coded 120s read timeout aborted runs that would have finished.
"""
import os

from core.utils import OLLAMA_DEFAULT_TIMEOUT, ollama_timeout


def _clear(monkeypatch):
    monkeypatch.delenv("ACORNIX_OLLAMA_TIMEOUT", raising=False)


def test_default_is_generous(monkeypatch):
    _clear(monkeypatch)
    assert ollama_timeout() == OLLAMA_DEFAULT_TIMEOUT
    assert OLLAMA_DEFAULT_TIMEOUT >= 600


def test_env_override_is_used(monkeypatch):
    monkeypatch.setenv("ACORNIX_OLLAMA_TIMEOUT", "45")
    assert ollama_timeout() == 45


def test_garbage_and_nonpositive_fall_back_to_default(monkeypatch):
    for bad in ("", "abc", "0", "-10"):
        monkeypatch.setenv("ACORNIX_OLLAMA_TIMEOUT", bad)
        assert ollama_timeout() == OLLAMA_DEFAULT_TIMEOUT


def test_ollama_call_uses_the_helper(monkeypatch, tmp_path):
    """The ollama branch must pass ollama_timeout(), not a literal 120."""
    import json
    import core.utils as utils

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "ai_provider": "ollama",
        "models": {"ollama": "qwen2.5-coder:1.5b"},
    }))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ACORNIX_OLLAMA_TIMEOUT", "321")

    seen = {}

    class FakeResp:
        def json(self):
            return {"choices": [{"message": {"content": "hi"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(utils.requests, "post", fake_post)
    utils.ask_ai("make an app", "you are a builder")
    assert seen["timeout"] == 321
