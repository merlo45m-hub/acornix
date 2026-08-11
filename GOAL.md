# acornix — Goal

## Mission
Make acornix the fastest way to build apps on your phone. Zero laptop needed.

## Current State
- 16 plugins (app creator, agent mode, aistudio, system health, etc.)
- LoRA training pipeline ready (train_lora.py, tested, smoke test passed)
- ML stack installed (torch, transformers, trl, peft) in /root/ml-env
- Model: Qwen2.5-0.5B-Instruct (fits 8GB RAM CPU)

## Goal: Fine-tune acornix's brain
Train a LoRA adapter on acornix's own plugin codebase so the AI generates better apps, faster.

### Steps
1. **Extract training data** from existing plugins — each plugin's code + README = one training example
2. **Format as instructions** — "Build a plugin that does X" → plugin code
3. **Run LoRA training** on Qwen2.5-0.5B with the extracted data
4. **Test the fine-tuned model** — ask it to generate a new plugin, compare quality
5. **Integrate into acornix** — the fine-tuned adapter loads alongside the base model

### Success Criteria
- Fine-tuned model generates working plugin code (not just boilerplate)
- Training completes in <1 hour on CPU
- Model size stays under 2GB (fits alongside Ollama on 8GB RAM)

## Stretch Goals
- Voice input → app generation ("acornix, build me a weather app")
- One-tap deploy to Termux (no SSH, no laptop)
- Plugin marketplace (share/reuse community plugins)
