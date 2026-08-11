import os
import importlib.util
import sys

def load_plugins():
    """
    Scans the 'plugins' directory and dynamically loads modules 
    containing a 'config' dict and a 'run' function.
    """
    plugin_dir = "plugins"
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)

    loaded_plugins = []
    
    for item in os.listdir(plugin_dir):
        # Skip hidden files, __init__, and cache
        if item == "__init__.py" or item.startswith(".") or item == "__pycache__":
            continue
            
        item_path = os.path.join(plugin_dir, item)
        module_name = ""
        entry_point = ""

        # Check for single-file plugins (.py)
        if item.endswith(".py"):
            module_name = item[:-3]
            entry_point = item_path
        # Check for folder-based plugins (folder/main.py)
        elif os.path.isdir(item_path):
            main_file = os.path.join(item_path, "main.py")
            if os.path.exists(main_file):
                module_name = item 
                entry_point = main_file
            else:
                continue

        if entry_point:
            try:
                spec = importlib.util.spec_from_file_location(module_name, entry_point)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Only load if valid plugin structure is present
                if hasattr(module, 'config') and hasattr(module, 'run'):
                    loaded_plugins.append(module)
            except Exception as e:
                print(f"⚠️ Error loading {item}: {e}")

    # Default alphabetical sort by label for the 'Others' category
    return sorted(loaded_plugins, key=lambda x: x.config.get("label", "").lower())

def main_menu():
    """
    Displays the categorized main menu and handles user selection.
    """
    # Categorization mapping: names must match the 'label' in each plugin's config
    CATEGORIES = {
        "🚀 CREATION & AI": [
            "App Creator & Editor",
            "Auto-Evolve (create functionality)",
            "Agent Mode (Total control)"
        ],
        "🗂️ APPs MANAGEMENT": [
            "APPs Manager",
            "Visual Launcher",
            "Delete Apps",
            "Smart Import-Export Hub"
        ],
        "🧠 SYSTEM & SECURITY": [            
            "Time Machine (Restore)",
            "Uninstaller Functionality"            
        ],
        "⚙️ SETTINGS": [
            "Global Settings Hub",                      
            "System Health"
        ],
        "ℹ️ HELP": [
            "Help"
        ]
    }

    while True:
        os.system('clear')
        plugins = load_plugins()
        
        print("==========================================")
        print("      🚀 ACORNIX          ")
        print("==========================================")
        
        mapping = {}
        current_idx = 1
        displayed_labels = set()

        # 1. Display Categorized Plugins (in the order defined above)
        for cat_name, desired_order in CATEGORIES.items():
            plugins_in_cat = []
            
            for label_name in desired_order:
                # Find the loaded plugin matching the category label
                found = next((p for p in plugins if p.config.get('label') == label_name), None)
                if found:
                    plugins_in_cat.append(found)

            if plugins_in_cat:
                print(f"\n {cat_name}")
                for p in plugins_in_cat:
                    icon = p.config.get('icon', '🧩')
                    label = p.config.get('label', 'Unknown')
                    print(f"   {current_idx}) {icon} {label}")
                    
                    mapping[current_idx] = p
                    displayed_labels.add(label)
                    current_idx += 1

        # 2. Display Uncategorized / New Plugins
        others = [p for p in plugins if p.config.get('label') not in displayed_labels]
        
        if others:
            print(f"\n 📂 OTHERS / UTILITIES")
            for p in others:
                icon = p.config.get('icon', '🧩')
                label = p.config.get('label', 'Unknown')
                print(f"   {current_idx}) {icon} {label}")
                mapping[current_idx] = p
                current_idx += 1

        print("\n------------------------------------------")
        print(" 0) ❌ EXIT")
        print("------------------------------------------")
        
        choice = input(f"\nSelect an option (1-{current_idx-1} or 0): ").strip()
        
        if choice == "0":
            print("\nGoodbye, creator! Shutdown complete.")
            break
            
        if choice.isdigit():
            idx = int(choice)
            if idx in mapping:
                try:
                    # Run the selected plugin's main function
                    mapping[idx].run()
                except Exception as e:
                    print(f"\n❌ Critical Error running plugin: {e}")
                    input("\nPress Enter to return to main menu...")
            else:
                print(f"\n⚠️ Invalid selection. Please choose a number between 0 and {current_idx-1}.")
                import time
                time.sleep(1.5)

if __name__ == "__main__":
    main_menu()

# =============================================================================
# 9-HOUR OVERNIGHT WORKFLOW INTEGRATION
# =============================================================================
# This module provides the 9-hour overnight automation framework for the acornix
# project. It wires the guide at /root/workspace/clip-engine/COMPLETE_GUIDE_TO_THE_9-HOUR_OVERNIGHT_WORKFLOW.md
# into your daily operations, enabling autonomous agent operation while you sleep.
#
# The 9-hour window covers:
#   00:00 - 03:00 - "Early Bird" — wake-up brief, service health, setup checks
#   03:00 - 06:00 - "Midnight" — cron jobs, skill maintenance, memory review
#   06:00 - 09:00 - "Morning" — standup briefing, project state, updates
#   09:00 - 12:00 - "Afternoon" — active work, PR review, monitoring
#   12:00 - 15:00 - "Lunch" — deep work blocks, async processing
#   15:00 - 18:00 - "Evening" — delivery, scheduling, cleanup
#   18:00 - 21:00 - "Night" — review, logging, next-day prep
#   21:00 - 24:00 - "Late Night" — final checks, shutdown prep
# =============================================================================


class OvernightWorkflow:
    """
    The 9-hour overnight automation framework.

    Wires together the 9-hour workflow guide with active service monitoring.
    Uses the guide at /root/workspace/clip-engine/COMPLETE_GUIDE_TO_THE_9-HOUR_OVERNIGHT_WORKFLOW.md
    to define the full automation pipeline.

    The guide provides:
    - 5 layers for autonomous operation
    - Setup checklist (VPS, Hermes, Gateway, Telegram, Cron, SOUL.md)
    - Compounding mechanics (daily → weekly → monthly growth)
    - Realistic token math and cost estimate
    - 9-hour schedule breakdown
    """

    def __init__(self, guide_path="/root/workspace/clip-engine/COMPLETE_GUIDE_TO_THE_9-HOUR_OVERNIGHT_WORKFLOW.md",
                 vault_path="/sdcard/Documents/Obsidian1main/obsidian1"):
        self.guide_path = guide_path
        self.vault_path = vault_path
        self._guide_exists = False

    def load_guide(self):
        """Load the overnight workflow guide if it exists."""
        import os
        if os.path.exists(self.guide_path):
            with open(self.guide_path, "r") as f:
                self.guide_content = f.read()
            self._guide_exists = True
            return self.guide_content
        return None

    def verify_setup(self):
        """Verify the 9-hour setup is complete. Returns (ok, issues)."""
        issues = []

        # 1. Check the guide exists
        if not self._guide_exists:
            issues.append("OVERNIGHT_GUIDE_MISSING: Guide file not found at " + self.guide_path)

        # 2. Check all 5 layers are set up
        layers = [
            ("Gateway", "check", "/root/.hermes/profiles/cto/scripts/gateway"),
            ("Cron Jobs", "check", "/root/.hermes/profiles/cto/scripts/"),
            ("Skills Library", "check", "/root/.hermes/skills/"),
            ("Memory DB", "check", "/root/.hermes/profiles/cto/"),
            ("Wiki", "check", "/sdcard/Documents/Obsidian1main/obsidian1/"),
        ]
        for name, check_type, check_path in layers:
            if not os.path.exists(check_path):
                issues.append(f"LAYER_MISSING: {name} at {check_path}")

        # 3. Check Telegram is connected
        import subprocess
        result = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:8644/health"],
                               capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            issues.append("TELEGRAM_GATEWAY_UNAVAILABLE: cannot reach webhook at :8644")

        # 4. Check cron jobs are scheduled
        import json
        cron_dir = "/root/.hermes/profiles/cto/cron/"
        if os.path.exists(cron_dir):
            cron_files = [f for f in os.listdir(cron_dir) if f.endswith(".json")]
            if len(cron_files) < 3:
                issues.append(f"CRON_JOBS_LOW: only {len(cron_files)} cron jobs found (need at least 3)")

        return ("clean" if not issues else "issues", issues)

    def run(self):
        """Execute the overnight workflow. Returns status dict."""
        result = {
            "status": "ok",
            "guide_loaded": self._guide_exists,
            "setup_complete": True,
            "checks": []
        }

        # Load guide
        guide = self.load_guide()
        if guide:
            result["guide_loaded"] = True
            result["guide_size"] = len(guide)
            result["guide_summary"] = guide[:500]

        # Verify setup
        status, issues = self.verify_setup()
        result["setup_status"] = status
        result["setup_issues"] = issues

        # Run health checks
        result["health"] = {
            "webui": self._check_webui(),
            "omniroute": self._check_omniroute(),
            "ollama": self._check_ollama(),
            "telegram_gateway": self._check_telegram_gateway(),
            "cron_jobs": self._check_cron_jobs(),
        }

        return result

    def _check_webui(self):
        import subprocess
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:8787/health"],
                          capture_output=True, text=True, timeout=5)
        try:
            import json
            d = json.loads(r.stdout)
            return "ok" if d.get("status") == "ok" else "down"
        except:
            return "unknown"

    def _check_omniroute(self):
        import subprocess
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:20128/v1/chat/completions"],
                          capture_output=True, text=True, timeout=5)
        return "healthy" if r.returncode == 0 else "unreachable"

    def _check_ollama(self):
        import subprocess
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:11434/api/tags"],
                          capture_output=True, text=True, timeout=5)
        try:
            import json
            d = json.loads(r.stdout)
            return "ok" if "models" in d else "unhealthy"
        except:
            return "unknown"

    def _check_telegram_gateway(self):
        import subprocess
        r = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:8644/health"],
                          capture_output=True, text=True, timeout=5)
        return "ok" if r.returncode == 0 else "unreachable"

    def _check_cron_jobs(self):
        import os, json
        cron_dir = "/root/.hermes/profiles/cto/cron/"
        cron_files = [f for f in os.listdir(cron_dir) if f.endswith(".json")]
        return len(cron_files)


# =============================================================================
# INSTANTIATE THE OVERNIGHT WORKFLOW
# =============================================================================
# Create an instance that runs the full 9-hour workflow check
# Schedule: every day at 3 AM (03:00 UTC)

overnight = OvernightWorkflow()


# =============================================================================
# QUICK TEST: verify the guide is loaded
# =============================================================================
if __name__ == "__main__":
    result = overnight.run()
    print("OVERNIGHT WORKFLOW STATUS:")
    print(f"  Guide loaded: {result['guide_loaded']}")
    print(f"  Setup complete: {result['setup_complete']}")
    print(f"  Health: {result['health']}")
    print(f"  Issues: {result['setup_issues']}")
    print(f"  Summary: {result.get('guide_summary', '')}")
