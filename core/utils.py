import os
import sys
import json
import requests
import subprocess
import socket
import time
from dotenv import load_dotenv
from core.local_ai import ask_local

# API Configuration
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

def is_server_active():
    """Check local server running on port 8080."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', 8080)) == 0

def normalize_ai_output(text):
    """
    Converts standard markdown code blocks into the ---CODIGO--- contract
    that process_and_execute() expects. Falls back to raw text if no
    fenced code block is found.
    """
    if not text:
        return text
    if "---CODIGO---" in text:
        return text
    if "```" in text:
        parts = text.split("```")
        # parts[0] = prose before, parts[1] = code (may have language tag), parts[2] = rest
        code = parts[1]
        # Strip language tag like "python" or "html" on first line
        code_lines = code.split("\n")
        if code_lines and code_lines[0].strip() and not code_lines[0].strip().startswith(("<", "import", "def", "class", "from", "#!/")):
            code_lines = code_lines[1:]
        code = "\n".join(code_lines).strip()
        suggestion = parts[2].strip() if len(parts) > 2 else ""
        return f"---CODIGO---\n{code}\n---SUGERENCIA---\n{suggestion}"
    return f"---CODIGO---\n{text}\n---SUGERENCIA---"

def ask_ai(prompt, system_prompt):
    """
    Sends prompt to configured provider and returns response.
    """
    config_file = "config.json"
    if not os.path.exists(config_file):
        print("\n❌ Error: config.json not found.")
        return None
    
    with open(config_file, "r") as f:
        settings = json.load(f)

    provider = settings.get("active_provider", "openai")
    api_key = settings.get("api_keys", {}).get(provider)
    model = settings.get("models", {}).get(provider)

    # Local/Ollama providers don't need API keys
    no_key_needed = provider in ("local", "ollama")
    if (not model) or ((not api_key) and not no_key_needed):
        print(f"\n❌ Error: Missing configuration for {provider}")
        return None

    # --- OpenAI Provider ---
    if provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": model, 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=120).json()
            return res['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
            return None

    # --- Anthropic Provider ---
    elif provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=120).json()
            return res['content'][0]['text']
        except Exception as e:
            print(f"❌ Anthropic API Error: {e}")
            return None

    # --- Local Provider (HuggingFace, offline) ---
    elif provider == "local":
        try:
            return normalize_ai_output(ask_local(prompt, system_prompt, model))
        except Exception as e:
            print(f"❌ Local AI Error: {e}")
            return None

    # --- Ollama Provider (local server) ---
    elif provider == "ollama":
        url = "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=120).json()
            return normalize_ai_output(res["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"❌ Ollama API Error: {e}")
            return None

def process_and_execute(ai_text, filename="generated_app.html"):
    """
    Handles output, saves files to project folders, manages server status.
    """
    if not ai_text or "---CODIGO---" not in ai_text:
        print("⚠️ No valid code block found in AI response.")
        return

    # 1. Path Configuration
    base_folder = "my_apps"
    project_name = filename.replace(".html", "").strip()
    project_path = os.path.join(base_folder, project_name)

    if not os.path.exists(project_path):
        os.makedirs(project_path)

    # 2. Parsing Response
    parts = ai_text.split("---SUGERENCIA---")
    code_block = parts[0].replace("---CODIGO---", "").strip()

    # 3. Determine file type
    if ".html" in filename or "html" in code_block[:200].lower():
        file_path = os.path.join(project_path, "index.html")
    elif ".py" in filename or "python" in code_block[:200].lower():
        file_path = os.path.join(project_path, "main.py")
    else:
        file_path = os.path.join(project_path, "index.html")

    # 4. Save the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code_block)
    print(f"✅ Saved to {file_path}")

    # 5. Start server if needed
    if not is_server_active() and file_path.endswith(".html"):
        print("📡 Starting server in background (Port 8080)...")
        subprocess.Popen(
            ["python", "-m", "http.server", "8080"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        url = f"http://localhost:8080/{base_folder}/{project_name}/index.html"
        print(f"🌍 Opening: {url}")
        os.system(f'termux-open-url "{url}"')
