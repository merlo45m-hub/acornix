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
    """Check if the local server is running on port 8080."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', 8080)) == 0

def ask_ai(prompt, system_prompt):
    """
    Sends a prompt to the configured AI provider and returns the response.
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
    
    if not api_key or not model:
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

def process_and_execute(ai_text, filename="generated_app.html"):
    """
    Handles AI output, saves files in project folders, and manages server status.
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

    # 2. Parsing AI Response
    parts = ai_text.split("---SUGERENCIA---")
    code_block = parts[0].replace("---CODIGO---", "").strip()
    # Remove markdown formatting if present
    code_block = code_block.replace("```python", "").replace("```html", "").replace("```", "").strip()
    suggestion = parts[1].strip() if len(parts) > 1 else ""

    # 3. Handling Web Content (HTML)
    if "<html" in code_block.lower() or "<!doctype" in code_block.lower():
        file_path = os.path.join(project_path, "index.html")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_block)
        print(f"\n✅ Project saved in: {file_path}")

        # Server Management
        if not is_server_active():
            print(f"\n🤖 [ASSISTANT]: Local server is currently OFF.")
            if input(f"👉 Would you like to start it? (y/n): ").lower() == 'y':
                print("📡 Starting server in background (Port 8080)...")
                subprocess.Popen(["python", "-m", "http.server", "8080"], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1)
        
        # Open in Browser (Android/Termux)
        url = f"http://localhost:8080/{base_folder}/{project_name}/index.html"
        print(f"🌍 Opening: {url}")
        os.system(f'termux-open-url "{url}"')
        
    # 4. Handling Logic Content (Python)
    else:
        file_path = os.path.join(project_path, "main.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_block)
        print(f"\n🚀 Executing script at: {file_path}")
        subprocess.run([sys.executable, file_path])

    # 5. Iterative Improvement Loop
    if suggestion:
        print(f"\n🤖 [ASSISTANT SUGGESTS]: {suggestion}")
        print("💡 (Type 'y' to accept, 'n' to exit, or type your OWN IMPROVEMENT directly)")
        
        user_input = input("👉 Your choice: ").strip()
        if user_input.lower() == 'n' or not user_input:
            print("👍 Returning to menu.")
            return

        improvement = suggestion if user_input.lower() == 'y' else user_input
        print(f"\n🧠 Applying: '{improvement}'...")

        improvement_prompt = (
            f"Current code:\n\n{code_block}\n\n"
            f"Requested change: {improvement}. "
            f"Return the full updated code within ---CODIGO--- and a new ---SUGERENCIA---."
        )
        
        new_res = ask_ai(improvement_prompt, "You are an expert developer. Return ONLY ---CODIGO--- and ---SUGERENCIA---.")
        process_and_execute(new_res, filename)