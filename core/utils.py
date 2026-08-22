import os
import sys
import json
import requests
import subprocess
import socket
import time
from dotenv import load_dotenv
from core.local_ai import ask_local
from core.atomic import atomic_write_text

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

OLLAMA_DEFAULT_TIMEOUT = 900


def ollama_timeout():
    """Read timeout (seconds) for the local Ollama call.

    Measured on-device decode for qwen2.5-coder:1.5b is well under 1 tok/s on a
    memory-pressured phone, so the old hard-coded 120s threw away generations
    that would have succeeded. Default is generous; override with
    ACORNIX_OLLAMA_TIMEOUT (seconds, must be a positive number).
    """
    raw = os.getenv("ACORNIX_OLLAMA_TIMEOUT")
    if not raw:
        return OLLAMA_DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return OLLAMA_DEFAULT_TIMEOUT
    return value if value > 0 else OLLAMA_DEFAULT_TIMEOUT


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

    # --- FAILURE RECOVERY ---
    # Mission promise: build apps with NO API key. If a cloud provider was
    # selected but has no key configured, transparently fall back to the local
    # Ollama path instead of failing at the cloud call.
    if (not no_key_needed) and (not api_key):
        print(f"\n⚠️ No API key for cloud provider '{provider}'. "
              f"Falling back to local Ollama (no key needed).")
        provider = "ollama"
        no_key_needed = True
        model = model or settings.get("models", {}).get("ollama") or "qwen2.5-coder:1.5b"

    if (not model) or ((not api_key) and not no_key_needed):
        fallback = model or "qwen2.5-coder:1.5b"
        print(f"\n❌ Error: Missing model/configuration for '{provider}'.\n"
              f"   If using Ollama: ensure it's running (`ollama serve`) and pulled "
              f"(`ollama pull {fallback}`).")
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
            return normalize_ai_output(res['choices'][0]['message']['content'])
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
            return normalize_ai_output(res['content'][0]['text'])
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
            res = requests.post(url, headers=headers, json=data,
                                timeout=ollama_timeout()).json()
            return normalize_ai_output(res["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"❌ Ollama error: {e}. Is Ollama running at localhost:11434? Try: `ollama serve`")
            return None

def is_usable_code(code):
    """True when `code` looks like a real app file worth writing to disk.

    Guards the create path the same way is_usable_html guards the edit path:
    an empty, whitespace-only, truncated, or prose-only model response must
    never be written out as an app (and must never clobber an existing one).
    """
    if not code or not code.strip():
        return False
    stripped = code.strip()
    if len(stripped) < 40:
        return False
    low = stripped.lower()
    if "<html" in low or "<!doctype html" in low or "<body" in low:
        return True
    # Allow python app output too (Mode 1 can emit main.py)
    return "def " in stripped or "import " in stripped


def trim_to_html_document(code):
    """Trim chat prose from around an HTML document.

    Returns ``code`` unchanged when it does not look like an HTML document, so
    Python/other generations are never touched. When a document start marker
    (``<!doctype html`` or ``<html``) is present, everything before it is
    dropped; when a closing ``</html>`` is present, everything after it is
    dropped. Idempotent: clean HTML in, identical HTML out.
    """
    if not code or not code.strip():
        return code
    low = code.lower()
    start = -1
    for marker in ("<!doctype html", "<html"):
        pos = low.find(marker)
        if pos != -1 and (start == -1 or pos < start):
            start = pos
    if start == -1:
        return code
    end = low.rfind("</html>")
    trimmed = code[start:end + len("</html>")] if end != -1 else code[start:]
    return trimmed.strip()


def process_and_execute(ai_text, filename="generated_app.html"):
    """
    Handles output, saves files to project folders, manages server status.
    """
    if not ai_text or not ai_text.strip():
        print("⚠️ No valid code block found in AI response.")
        return

    # 0. First-try recovery: small local models frequently ignore the
    # ---CODIGO--- contract entirely and just answer with the app itself.
    # Rejecting that response meant the user got *nothing* on the first try
    # even though a perfectly good HTML document was in hand. If the marker is
    # missing but the response contains an HTML document, treat the document as
    # the code block instead of throwing the generation away.
    if "---CODIGO---" not in ai_text:
        low = ai_text.lower()
        has_document = "<!doctype html" in low or "<html" in low
        salvaged = trim_to_html_document(ai_text) if has_document else ""
        if not has_document or not is_usable_code(salvaged):
            print("⚠️ No valid code block found in AI response.")
            return
        print("ℹ️ Model skipped the ---CODIGO--- marker; recovered the HTML document.")
        ai_text = "---CODIGO---\n" + salvaged

    # 1. Path Configuration
    base_folder = "my_apps"
    project_name = filename.replace(".html", "").strip()
    project_path = os.path.join(base_folder, project_name)

    # 2. Parsing Response
    parts = ai_text.split("---SUGERENCIA---")
    code_block = parts[0].replace("---CODIGO---", "").strip()

    # 2a. First-try hygiene: small local models sometimes wrap the code in a
    # ```html fence even inside the ---CODIGO--- contract. The Mode 2 edit path
    # strips fences via clean_html_code, but this create path writes
    # code_block verbatim, which would leave stray backticks in the app the
    # user opens. Strip a single wrapping fence so the saved file is real HTML.
    if code_block.startswith("```"):
        code_block = code_block.split("\n", 1)[1] if "\n" in code_block else ""
    if code_block.endswith("```"):
        code_block = code_block[:-3].rstrip()
    code_block = code_block.strip()

    # 2a-bis. First-try hygiene: small local models often top-and-tail the code
    # with chat prose ("Sure! Here's your app:" / "Hope this helps!") and no
    # fence at all. Written verbatim that prose lands *before* <!DOCTYPE html>,
    # which forces quirks mode and renders the chatter on the page — the app
    # does not "work on the first try". Trim to the HTML document boundaries.
    code_block = trim_to_html_document(code_block)

    # 2b. Failure recovery: don't create an empty project folder, and never
    # overwrite an existing app, with an unusable response.
    if not is_usable_code(code_block):
        print(
            "⚠️ The model did not return usable code "
            f"({len(code_block or '')} chars). Nothing was saved."
        )
        return

    if not os.path.exists(project_path):
        os.makedirs(project_path)

    # 3. Determine file type
    if ".html" in filename or "html" in code_block[:200].lower():
        file_path = os.path.join(project_path, "index.html")
    elif ".py" in filename or "python" in code_block[:200].lower():
        file_path = os.path.join(project_path, "main.py")
    else:
        file_path = os.path.join(project_path, "index.html")

    # 4. Save the file. Failure recovery: keep one backup of the previous
    # version so a usable-but-worse regeneration is never the last copy of a
    # working app.
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as old:
                previous = old.read()
            with open(file_path + ".bak", "w", encoding="utf-8") as bak:
                bak.write(previous)
            print(f"🗂️  Previous version backed up to {file_path}.bak")
        except OSError as e:
            print(f"⚠️ Could not back up {file_path}: {e}")

    # Atomic write: build the new version beside the target, then swap it in.
    # A crash / full disk mid-write can no longer leave a half-written app where
    # a working one used to be. If the swap itself fails and we destroyed the
    # original, restore it from the .bak we just took.
    tmp_path = file_path + ".tmp"
    if not atomic_write_text(file_path, code_block):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        if not os.path.exists(file_path) and os.path.exists(file_path + ".bak"):
            try:
                with open(file_path + ".bak", "r", encoding="utf-8") as bak:
                    restored = bak.read()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(restored)
                print(f"♻️  Restored previous version from {file_path}.bak")
            except OSError as restore_error:
                print(f"⚠️ Restore from backup failed: {restore_error}")
        return
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
