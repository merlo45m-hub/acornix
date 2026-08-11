#!/usr/bin/env python3
"""
Local AI provider for acornix — uses Ollama or HuggingFace models.
Drop-in replacement for ask_ai() that works offline.
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Global model cache (load once, reuse)
_model = None
_tokenizer = None
_model_name = None

def load_model(model_name="Qwen/Qwen2.5-Coder-0.5B-Instruct"):
    """Load model once and cache it."""
    global _model, _tokenizer, _model_name
    if _model_name == model_name and _model is not None:
        return _model, _tokenizer
    
    print(f"Loading {model_name}...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32,
        device_map=None,
        trust_remote_code=True,
    )
    _model_name = model_name
    print(f"Model loaded.")
    return _model, _tokenizer

def ask_local(prompt, system_prompt="", model_name="Qwen/Qwen2.5-Coder-0.5B-Instruct"):
    """
    Generate code using local model. Drop-in for ask_ai().
    
    Args:
        prompt: User instruction (e.g., "Build a calculator plugin")
        system_prompt: Optional system context
        model_name: HuggingFace model to use
    
    Returns:
        Generated code string
    """
    model, tokenizer = load_model(model_name)
    
    # Format as chat
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Apply chat template
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
        )
    
    # Decode only new tokens
    generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return generated

# Quick test
if __name__ == "__main__":
    result = ask_local(
        "Build a Termux plugin called 'weather' that fetches weather data from wttr.in",
        system_prompt="You are an expert Python developer for Termux. Generate clean, working code."
    )
    print(result)
