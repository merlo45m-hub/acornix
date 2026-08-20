import os
import shutil
import datetime
import json
from core.utils import ask_ai, process_and_execute
from core.atomic import atomic_write_text

# Plugin Configuration
config = {"label": "App Creator & Editor", "icon": "🏗️"}

# --- SAFETY AND UTILITY TOOLS ---
def perform_backup(app_folder_path):
    """Creates a security ZIP backup of the app before modification."""
    # 1. Check user preferences in config.json
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                settings = json.load(f)
                if not settings.get("preferences", {}).get("backup_before_evolve", True):
                    return 
        except: 
            pass

    # 2. Prepare backup directory
    backup_dir = "backups"
    if not os.path.exists(backup_dir): 
        os.makedirs(backup_dir)

    # 3. Create ZIP archive
    app_name = os.path.basename(app_folder_path)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_base = os.path.join(backup_dir, f"{app_name}_{timestamp}")

    try:
        shutil.make_archive(zip_base, 'zip', app_folder_path)
        print(f"🛡️  Security backup created: {zip_base}.zip")
    except Exception as e:
        print(f"⚠️  Failed to create backup: {e}")

def is_usable_html(code):
    """True when `code` looks like a real HTML document worth writing to disk.

    Guards the edit path: an empty, whitespace-only, or prose-only model
    response must never overwrite a working index.html.
    """
    if not code or not code.strip():
        return False
    low = code.lower()
    if len(code.strip()) < 40:
        return False
    return "<html" in low or "<!doctype html" in low or "<body" in low


def clean_html_code(text):
    """Cleans an AI response down to raw HTML/JS/CSS.

    Honors both contracts the active providers emit:
      - The ---CODIGO---/---SUGERENCIA--- contract produced by the local/Ollama
        providers via normalize_ai_output (the default, no-API-key path).
      - Standard ``` / ```html fenced blocks (cloud providers).
    Falls back to the raw text if neither marker is present.
    """
    if not text:
        return text
    # Local/Ollama contract (default offline, no-API-key path)
    if "---CODIGO---" in text:
        code = text.split("---CODIGO---", 1)[1]
        if "---SUGERENCIA---" in code:
            code = code.split("---SUGERENCIA---", 1)[0]
        return code.strip()
    if "```html" in text:
        text = text.split("```html")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()

# --- MAIN LOGIC ---
def run():
    """Main loop for creating and editing web applications."""
    while True:
        os.system('clear')
        print("=== 🏗️ WEB APP CREATOR & EDITOR ===")
        print("1) ✨ Create New Web App")
        print("2) 🛠️ Improve/Fix Existing App")
        print("0) 🔙 Back")

        opt = input("\nSelect an option: ").strip()

        if opt == "0":
            break

        # --- MODE 1: CREATE ---
        elif opt == "1":
            name = input("\n📝 Project Name (folder name): ").strip()
            if not name: 
                continue
            
            idea = input(f"🎨 What should I build for '{name}'?: ")
            
            # Optimized prompt for initial creation
            sys_prompt = (
                "You are an Expert Web Developer Assistant. "
                "Strictly follow this format: ---CODIGO--- and ---SUGERENCIA---. "
                "Use HTML/JS/CSS to build high-quality Single Page Applications (SPA). "
                "All UI text and comments MUST be in English."
            )
            
            print(f"\n🧠 Programming '{name}' from scratch...")
            res = ask_ai(idea, sys_prompt)

            # Failure recovery: ask_ai returns None on any config/provider error.
            # Don't hand a None into process_and_execute (it would mask the cause).
            if not res:
                print("\n⚠️ App generation failed — see error above. Nothing was saved.")
                input("\nPress Enter to continue...")
                continue

            # process_and_execute handles file generation and server checks
            process_and_execute(res, name)
            input("\nPress Enter to continue...")

        # --- MODE 2: IMPROVE/EDIT ---
        elif opt == "2":
            apps_dir = "my_apps"
            if not os.path.exists(apps_dir):
                print(f"\n🚫 Base directory '{apps_dir}' does not exist.")
                input("Press Enter...")
                continue
            
            # List available apps sorted alphabetically
            apps = sorted([d for d in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, d))])
            
            if not apps:
                print("\n🚫 You haven't created any apps yet.")
                input("Press Enter...")
                continue

            print("\n--- SELECT APP TO IMPROVE ---")
            for i, app in enumerate(apps, 1):
                print(f"{i}) {app}")
            print("0) Cancel")

            choice = input("\nSelection number: ")
            if choice == "0" or not choice.isdigit(): 
                continue

            idx = int(choice) - 1
            if 0 <= idx < len(apps):
                app_name = apps[idx]
                app_path = os.path.join(apps_dir, app_name)
                
                # Locate the main file (index.html)
                target_file = os.path.join(app_path, "index.html")
                if not os.path.exists(target_file):
                    print(f"\n⚠️ Could not find 'index.html' in {app_name}.")
                    input("Press Enter...")
                    continue

                # 1. SECURITY BACKUP
                perform_backup(app_path)

                # 2. READ CURRENT SOURCE CODE
                with open(target_file, "r", encoding="utf-8") as f:
                    old_code = f.read()

                # 3. REQUEST IMPROVEMENT
                print(f"\nEditing: {app_name}")
                req = input("🛠️ What changes or improvements do you need?: ")
                if req == "0": 
                    continue

                sys_prompt = (
                    "YOU ARE A SENIOR WEB DEVELOPER. OUTPUT ONLY RAW HTML/JS/CSS CODE. "
                    "NO MARKDOWN. NO EXPLANATIONS. ALL TEXT MUST BE IN ENGLISH."
                )
                prompt = (
                    f"Existing code:\n\n{old_code}\n\n"
                    f"TASK: {req}\n\n"
                    "Return the COMPLETE updated index.html code."
                )

                print(f"\n🧠 Applying changes to {app_name}...")
                new_code = ask_ai(prompt, sys_prompt)

                if new_code:
                    clean_code = clean_html_code(new_code)
                    # Failure recovery: never destroy a working app with an
                    # unusable model response. Small local models sometimes
                    # answer with prose only, or the response is truncated by
                    # the request timeout. Writing that out truncated
                    # index.html to garbage (or to nothing at all).
                    if not is_usable_html(clean_code):
                        print(
                            "\n⚠️ The model did not return usable HTML "
                            f"({len(clean_code or '')} chars). "
                            f"{app_name} was left unchanged."
                        )
                        input("\nPress Enter to continue...")
                        continue
                    # Atomic write: a crash or a full disk mid-write can no
                    # longer truncate the working app the user is editing.
                    if not atomic_write_text(target_file, clean_code):
                        print(f"\n⚠️ {app_name} was left unchanged.")
                        input("\nPress Enter to continue...")
                        continue
                    print(f"\n✅ App successfully updated: {target_file}")
                    input("\nPress Enter to continue...")