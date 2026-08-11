#!/usr/bin/env python3
"""
LoRA Fine-Tuning Script — Optimized for Termux/Android ARM (CPU only)
Hardware: Samsung S26 Ultra, no CUDA, 8GB RAM
Stack: transformers + trl SFTTrainer (1.9 API) + peft LoRA + datasets
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig
from datasets import load_dataset

# =============================================================================
# CONFIG — edit these for your use case
# =============================================================================

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"   # Small enough for 8GB RAM CPU
DATA_SOURCE = "tatsu-lab/alpaca"            # HF dataset name or local path
OUTPUT_DIR = "./lora-output"
MAX_SEQ_LENGTH = 128                        # Keeps CPU memory usage low
MAX_SAMPLES = 500                           # Cap dataset size for CPU
MAX_STEPS = 100                             # Cap training steps for CPU

# =============================================================================
# 1. LOAD MODEL + TOKENIZER
# =============================================================================

print(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,       # CPU needs float32 (not float16)
    device_map=None,                  # CPU only
    trust_remote_code=True,
)

# =============================================================================
# 2. LoRA CONFIG — light adapter for CPU training
# =============================================================================

peft_config = LoraConfig(
    r=8,                              # Low rank — keeps params small
    lora_alpha=16,                    # Scaling factor
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)

# =============================================================================
# 3. DATASET — format as chat/instruction text
# =============================================================================

print(f"Loading dataset: {DATA_SOURCE}")
dataset = load_dataset(DATA_SOURCE, split="train")

def format_instruction(example):
    if example.get("input"):
        text = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Input:\n{example['input']}\n\n"
            f"### Response:\n{example['output']}"
        )
    else:
        text = (
            f"### Instruction:\n{example['instruction']}\n\n"
            f"### Response:\n{example['output']}"
        )
    return {"text": text}

dataset = dataset.map(format_instruction, remove_columns=dataset.column_names)

if len(dataset) > MAX_SAMPLES:
    dataset = dataset.select(range(MAX_SAMPLES))
    print(f"Subsampled to {MAX_SAMPLES} examples for CPU training")

# =============================================================================
# 4. TRAINING CONFIG — SFTConfig (trl 1.9 API, tuned for mobile/CPU)
# =============================================================================

config = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=1,
    per_device_train_batch_size=1,      # Small batch for 8GB RAM
    gradient_accumulation_steps=8,       # Effective batch size = 8
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=20,
    logging_steps=1,
    save_strategy="no",                  # Prevents heavy disk writes on mobile storage
    max_steps=MAX_STEPS,                 # Cap training steps for CPU
    fp16=False,                          # CPU doesn't support fp16
    bf16=False,                          # CPU doesn't support bf16 either
    dataloader_num_workers=0,            # Single process on mobile
    report_to="none",                    # No wandb/tensorboard
    optim="adamw_torch",
    lr_scheduler_type="cosine",
    dataset_text_field="text",
    packing=False,
    max_length=MAX_SEQ_LENGTH,          # Truncation length (trl 1.9 renamed max_seq_length -> max_length)
)

# =============================================================================
# 5. SFT TRAINER — trl 1.9 API (processing_class not processing)
# =============================================================================

print("Starting training...")
trainer = SFTTrainer(
    model=model,
    args=config,
    train_dataset=dataset,
    processing_class=tokenizer,
    peft_config=peft_config,
)

# =============================================================================
# 6. TRAIN + SAVE
# =============================================================================

trainer.train()
print("Training complete!")

trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")

# Quick inference test
print("\n--- Inference Test ---")
test_prompt = "### Instruction:\nWhat is the capital of France?\n\n### Response:\n"
inputs = tokenizer(test_prompt, return_tensors="pt")
with torch.no_grad():
    outputs = trainer.model.generate(**inputs, max_new_tokens=50, temperature=0.7)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))