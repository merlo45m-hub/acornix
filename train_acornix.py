#!/usr/bin/env python3
"""
acornix LoRA Fine-Tuning — trains on plugin codebase
Hardware: Samsung S26 Ultra (CPU, 8GB RAM)
Model: Qwen2.5-0.5B-Instruct
"""
import torch, time, json
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig
from datasets import Dataset

# =============================================================================
# CONFIG
# =============================================================================

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = "./lora-acornix"
MAX_SEQ_LENGTH = 512      # Longer for code generation
MAX_STEPS = 200            # Enough for 16 examples to overfit (that's fine for testing)
TRAINING_DATA = "./plugin_training_data.json"

# =============================================================================
# LOAD MODEL
# =============================================================================

print(f"Loading {MODEL_NAME}...")
t0 = time.time()
tok = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32, device_map=None)
print(f"Model loaded in {time.time()-t0:.0f}s")

# =============================================================================
# LOAD PLUGIN DATA
# =============================================================================

print(f"Loading training data from {TRAINING_DATA}...")
with open(TRAINING_DATA) as f:
    raw = json.load(f)

# Convert to alpaca format
def format_example(example):
    text = (
        f"### Instruction:\n{example['instruction']}\n\n"
        f"### Response:\n```python\n{example['output']}\n```"
    )
    return {"text": text}

rows = [format_example(d) for d in raw]
ds = Dataset.from_list(rows)
print(f"Dataset: {len(ds)} examples")

# =============================================================================
# LoRA CONFIG
# =============================================================================

peft_config = LoraConfig(
    r=16,                             # Higher rank for code generation
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)

# =============================================================================
# TRAINING CONFIG
# =============================================================================

config = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=10,
    logging_steps=5,
    save_strategy="no",
    max_steps=MAX_STEPS,
    fp16=False,
    bf16=False,
    dataloader_num_workers=0,
    report_to="none",
    optim="adamw_torch",
    lr_scheduler_type="cosine",
    dataset_text_field="text",
    packing=False,
    max_length=MAX_SEQ_LENGTH,
)

# =============================================================================
# TRAIN
# =============================================================================

print("Starting training...")
trainer = SFTTrainer(
    model=model,
    args=config,
    train_dataset=ds,
    processing_class=tok,
    peft_config=peft_config,
)

trainer.train()
print(f"Training complete in {time.time()-t0:.0f}s")

# =============================================================================
# SAVE
# =============================================================================

trainer.save_model(OUTPUT_DIR)
tok.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")

# =============================================================================
# INFERENCE TEST
# =============================================================================

print("\n--- Inference Test ---")
test_prompts = [
    "### Instruction:\nBuild a Termux plugin called 'calculator' that performs basic math operations\n\n### Response:\n```python\n",
    "### Instruction:\nBuild a Termux plugin called 'timer' that sets a countdown timer\n\n### Response:\n```python\n",
]

for prompt in test_prompts:
    inputs = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = trainer.model.generate(
            **inputs, 
            max_new_tokens=200,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
        )
    generated = tok.decode(outputs[0], skip_special_tokens=True)
    print(f"\nPrompt: {prompt.split(chr(10))[1][:60]}...")
    print(f"Generated:\n{generated[-500:]}")
    print("---")
