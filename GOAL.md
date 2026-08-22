# acornix — Goal

## Mission
Make acornix the fastest way to build apps on your phone. Zero laptop needed.

## Active Outcome (one at a time)
**NEXT: "First app works on the first try."**
A brand-new user, on the phone, describes an app and gets something that opens
and runs in the browser without editing anything by hand. Measured by actually
running Mode 1 end-to-end against the default local model and opening the file.

Not on the roadmap right now: marketplace, fine-tuning, extra plugins.

### Progress on this outcome (43 tests green)
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
