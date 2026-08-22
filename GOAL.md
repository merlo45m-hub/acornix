# acornix — Goal

## Mission
Make acornix the fastest way to build apps on your phone. Zero laptop needed.

## Active Outcome (one at a time)
**NEXT: "First app works on the first try."**
A brand-new user, on the phone, describes an app and gets something that opens
and runs in the browser without editing anything by hand. Measured by actually
running Mode 1 end-to-end against the default local model and opening the file.

Not on the roadmap right now: marketplace, fine-tuning, extra plugins.

## Shipped — Failure Recovery (2026-08-20, on main, 30 tests green; active-outcome guard added 2026-08-22)
The generator can no longer destroy a working app:
- Mode 1 (create) refuses to write unusable model output.
- All app writes are atomic (tmp + replace) — a crash can't truncate a file.
- Any overwritten app is kept as `index.html.bak`, on both create and edit paths.
- Cloud provider output is normalized before it is ever written.
- Mode 3 `♻️ Revert App to Last Working Version` restores from `.bak`, and the
  replaced version becomes the new `.bak` (one-step undo/redo).
- Test suite: `tests/test_*_recovery.py`, `tests/test_edit_path_*.py`.

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
