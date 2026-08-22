"""OmniRoute provider: the keyless, fast-enough path for the first-try outcome.

The on-device 1.5b default decodes at <1 tok/s, which cannot meet the
"first app works on the first try" latency criterion. OmniRoute runs on the
same phone, speaks the OpenAI API, and needs no API key -- so selecting it
must not trip the "missing API key" guard, and it must not stream.
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.utils as utils


def _write_config(tmp_path, provider="omniroute", model=None):
    cfg = {
        "active_provider": provider,
        "api_keys": {"openai": "", "omniroute": ""},
        "models": {"omniroute": model} if model is not None else {},
    }
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    os.chdir(tmp_path)


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_base_url_default_and_override(monkeypatch):
    monkeypatch.delenv("ACORNIX_OMNIROUTE_URL", raising=False)
    assert utils.omniroute_base_url() == "http://127.0.0.1:20128/v1"
    monkeypatch.setenv("ACORNIX_OMNIROUTE_URL", "http://example.test:9/v1/")
    assert utils.omniroute_base_url() == "http://example.test:9/v1"


def test_timeout_default_and_bad_values(monkeypatch):
    monkeypatch.delenv("ACORNIX_OMNIROUTE_TIMEOUT", raising=False)
    assert utils.omniroute_timeout() == utils.OMNIROUTE_DEFAULT_TIMEOUT
    monkeypatch.setenv("ACORNIX_OMNIROUTE_TIMEOUT", "nope")
    assert utils.omniroute_timeout() == utils.OMNIROUTE_DEFAULT_TIMEOUT
    monkeypatch.setenv("ACORNIX_OMNIROUTE_TIMEOUT", "-5")
    assert utils.omniroute_timeout() == utils.OMNIROUTE_DEFAULT_TIMEOUT
    monkeypatch.setenv("ACORNIX_OMNIROUTE_TIMEOUT", "12")
    assert utils.omniroute_timeout() == 12


def test_no_api_key_needed_and_request_shape(tmp_path, monkeypatch):
    _write_config(tmp_path)
    monkeypatch.delenv("ACORNIX_OMNIROUTE_URL", raising=False)
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, body=json, timeout=timeout)
        return _Resp({"choices": [{"message": {"content": "<!DOCTYPE html><html></html>"}}]})

    monkeypatch.setattr(utils.requests, "post", fake_post)
    out = utils.ask_ai("build a thing", "sys")

    # No key configured, yet the cloud-fallback guard must NOT redirect to ollama.
    assert seen["url"] == "http://127.0.0.1:20128/v1/chat/completions"
    # Streaming responses are not parseable by ask_ai, so it must be disabled.
    assert seen["body"]["stream"] is False
    assert seen["body"]["model"] == utils.OMNIROUTE_DEFAULT_MODEL
    assert seen["timeout"] == utils.OMNIROUTE_DEFAULT_TIMEOUT
    assert "---CODIGO---" in out


def test_configured_model_wins(tmp_path, monkeypatch):
    _write_config(tmp_path, model="auto/fast")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json)
        return _Resp({"choices": [{"message": {"content": "x" * 60}}]})

    monkeypatch.setattr(utils.requests, "post", fake_post)
    utils.ask_ai("p", "s")
    assert captured["model"] == "auto/fast"


def test_transport_failure_returns_none_not_garbage(tmp_path, monkeypatch):
    _write_config(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(utils.requests, "post", boom)
    assert utils.ask_ai("p", "s") is None
