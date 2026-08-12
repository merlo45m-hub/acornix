# acornix — Goal

## Mission
Make acornix the fastest way to build apps on your phone. Zero laptop needed.

## Current State (2026-08-11)
- 16 plugins (app creator, agent mode, aistudio, system health, etc.)
- **Local AI wired in** — ask_ai() supports 4 providers:
  - `openai` / `anthropic` (cloud, need API keys)
  - `ollama` — local Ollama server at :11434 (FAST, 25s for plugin code)
  - `local` — HuggingFace model loaded directly (offline, ~5min startup)
- Default provider: `ollama` with `qwen2.5-coder:1.5b` (code-specialized, ~1GB)
- Verified: generates working plugin code (quote plugin, 2295 chars, 25s)

## What We Tried (and learned)
1. ❌ LoRA fine-tuning on 16 plugin examples → repetitive garbage (needs 100x data)
2. ✅ Qwen2.5-Coder-0.5B-Instruct (HF local) → real plugin structure
3. ✅ qwen2.5-coder:1.5b (Ollama) → BEST: fast + code-specialized + no API key

## Next Steps
1. **Test real app generation** — run acornix, ask it to build an app, verify output
2. **Wire coder model into app_creator.py** — the app generator plugin
3. **Collect more training data** — only if we want a custom fine-tune later
4. **Plugin marketplace** — share/reuse community plugins

## Success Criteria
- acornix generates a working plugin/app from a natural-language prompt
- Response time < 60s on phone
- No API keys required (fully local)
