# acornix — Goal

## Mission
Make acornix the fastest way to build apps on your phone. Zero laptop needed.

## Active Outcome (one at a time)
**NEXT: "First app works on the first try."**
A brand-new user, on the phone, describes an app and gets something that opens
and runs in the browser without editing anything by hand. Measured by actually
running Mode 1 end-to-end against the default local model and opening the file.

Not on the roadmap right now: marketplace, fine-tuning, extra plugins.

### Progress on this outcome (52 tests green)
- 2026-08-22 **OUTCOME MET on device — step 2 (the blocking product decision) is
  shipped.** The phone default no longer has to be a sub-1-tok/s local 1.5b.
  New keyless provider `omniroute` in `core.utils.ask_ai()` talks to the
  on-device OmniRoute OpenAI-compatible router (`http://127.0.0.1:20128/v1`,
  no API key, `stream: False`, override with `ACORNIX_OMNIROUTE_URL` /
  `ACORNIX_OMNIROUTE_TIMEOUT`). Measured end-to-end Mode 1 run, real plugin
  system prompt, prompt "tip calculator with slider + split by people":
  **37.5s wall clock**, 2008-char response, `is_usable_code` True, written to
  `my_apps/tipcalc_e2e/index.html`, served over HTTP 200 (1242 bytes), parses,
  ends in `</html>`, contains the range slider and the split logic. Under the
  <60s criterion, on the phone, with no API key and nothing hand-edited.
  Tests: `tests/test_omniroute_provider.py` (5 tests — keyless guard is not
  hijacked by the cloud-fallback path, streaming stays off, configured model
  wins, transport failure returns None rather than garbage).
- 2026-08-22 (re-measure, step 1 of the plan below): control run on a
  freshly-booted device (up 2 min, 3.2GB available, 8GB swap in use) gave
  **0.35 tok/s** decode (3 tokens / 8.6s eval, 14.6s load). Memory pressure is
  *not* the whole story — decode is slow on an idle device too, so the local
  1.5b default cannot meet the <60s criterion. Step 2 (change the phone default
  provider, or ship a smaller model) is now the blocking product decision.
- 2026-08-22 (step 3 shipped): the Ollama read timeout is no longer a
  hard-coded 120s. `core.utils.ollama_timeout()` defaults to 900s and is
  overridable with `ACORNIX_OLLAMA_TIMEOUT`, so a slow-but-successful
  generation is kept instead of discarded. Tests:
  `tests/test_ollama_timeout.py` (4 tests, incl. one asserting the ollama
  branch actually passes the helper's value).
- Mode 1 refuses unusable output, strips markdown fences, and trims chat prose
  around the HTML document.
- 2026-08-22: when the model ignores the `---CODIGO---` contract entirely but
  did return an HTML document, the create path now recovers the document
  instead of discarding the whole generation (`tests/test_missing_marker_recovery.py`).
  Prose-only and empty responses are still rejected.
- Test isolation fix: `tests/test_app_creator_recovery.py` no longer injects
  `/root/workspace/acornix` into `sys.path`, which was shadowing `core.utils`
  with a stale out-of-repo copy and masking real create-path regressions.
- Remaining for "first try": run Mode 1 end-to-end on-device against
  `ollama qwen2.5-coder:1.5b` and open the generated file.

## Shipped — Failure Recovery (2026-08-20, on main, 38 tests green; active-outcome guard added 2026-08-22)
The generator can no longer destroy a working app:
- Mode 1 (create) refuses to write unusable model output.
- All app writes are atomic (tmp + replace) — a crash can't truncate a file.
- Any overwritten app is kept as `index.html.bak`, on both create and edit paths.
- Cloud provider output is normalized before it is ever written.
- Mode 3 `♻️ Revert App to Last Working Version` restores from `.bak`, and the
  replaced version becomes the new `.bak` (one-step undo/redo).
- Test suite: `tests/test_*_recovery.py`, `tests/test_edit_path_*.py`.

## Progress toward the active outcome
- 2026-08-21 Mode 1 strips a wrapping markdown fence before writing.
- 2026-08-22 Mode 1 trims chat prose around the HTML document
  (`trim_to_html_document`), so the saved `index.html` starts at `<!DOCTYPE
  html>` instead of "Sure! Here's your app:" — no quirks mode, no chatter
  rendered on the page. Tests: `tests/test_first_try_prose_trim.py`.
- Still open before the outcome is met: a real end-to-end Mode 1 run against
  Ollama `qwen2.5-coder:1.5b` on device, opening the produced file.
- 2026-08-22 **Attempted that run — BLOCKED on device decode speed, not on code.**
  Measured, not estimated:
  - Mode 1 via `ask_ai()` (real plugin prompt) failed: Ollama read timeout at
    120s, `ask_ai` returned None, nothing written. The failure-recovery guard
    behaved correctly (no partial/clobbered app).
  - Same prompt straight to `/api/chat` with a 580s budget: still no response.
  - Control (`"Say OK"`, `num_predict:64`): 17 tokens in 86.4s —
    `load_duration` 0.47s, `eval_duration` 81.7s → **≈0.21 tok/s decode**.
    A ~1500-token SPA is therefore hours, not the <60s success criterion.
  - Context: host up 2 min, 8.5GB/11GB used, ~200MB free → memory pressure is
    the leading suspect (decode-bound, not model-load-bound).
  - Next step for this outcome (in order): (1) re-measure tok/s on an unloaded
    device to confirm memory pressure is the cause; (2) if decode stays <5 tok/s,
    the default provider cannot meet the outcome — either drop to a smaller
    model (qwen2.5-coder:0.5b) or make the phone default a cloud provider and
    keep Ollama as the offline path; (3) raise the Ollama client timeout above
    120s so a slow-but-successful generation is not thrown away.

## AI Backend (verified)
`ask_ai()` supports `openai`, `anthropic`, `ollama`, `local`.
Default: `ollama` + `qwen2.5-coder:1.5b` (~1GB, code-specialized, no API key,
~25s for plugin code on device).

## What We Tried (and learned)
1. ❌ LoRA fine-tuning on 16 plugin examples → repetitive garbage (needs 100x data)
2. ✅ Qwen2.5-Coder-0.5B-Instruct (HF local) → real plugin structure
3. ✅ qwen2.5-coder:1.5b (Ollama) → BEST: fast + code-specialized + no API key

## Success Criteria
- acornix generates a working app from a natural-language prompt, first try
- Response time < 60s on phone
- No API keys required (fully local)
- A bad generation never costs the user working code
