import os
import http.server
import socketserver
import threading
import shutil
import html

# Plugin Configuration
config = {
    "label": "AI Studio (No API needed)",
    "icon": "🤖"
}

PORT = 8081
current_file_path = ""
current_file_content = ""

# ── CAMBIO CLAVE: BaseHTTPRequestHandler en lugar de SimpleHTTPRequestHandler
# SimpleHTTPRequestHandler sirve archivos estáticos y puede interferir con POST.
class StudioHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            html_template = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acornix AI Studio</title>
  <style>
    body { margin:0; font-family: -apple-system, sans-serif; display: flex; flex-direction: column; height: 100vh; background: #1e1e1e; color: #fff; }
    .toolbar { padding: 12px; background: #2d2d2d; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; border-bottom: 3px solid #007aff; }
    button { padding: 12px 16px; border-radius: 8px; border: none; color: white; font-size: 15px; cursor: pointer; font-weight: bold; transition: transform 0.1s; display: flex; align-items: center; gap: 6px; }
    button:active { transform: scale(0.95); }
    .btn-copy   { background: #34c759; }
    .btn-select { background: #636366; }
    .btn-delete { background: #ff453a; }
    .btn-save   { background: #007aff; }
    #editor { flex: 1; width: 100%; box-sizing: border-box; background: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 14px; border: none; padding: 15px; resize: none; outline: none; }
    .info-text { font-size: 12px; color: #aaa; margin-top: 5px; text-align: center; padding: 0 10px; }
    #status { font-size: 13px; padding: 4px 10px; border-radius: 6px; display: none; }
    #status.ok  { background: #1a3a1a; color: #34c759; display: inline-block; }
    #status.err { background: #3a1a1a; color: #ff453a; display: inline-block; }
  </style>
</head>
<body>
  <div class="toolbar">
    <div style="font-weight: bold; font-size: 18px; margin-right: 5px;">🤖 AI Studio</div>
    <button class="btn-copy"   onclick="copyCode()">📋 Copy for AI</button>
    <button class="btn-select" onclick="selectAll()">☑️ Select All</button>
    <button class="btn-delete" onclick="deleteAll()">🗑️ Delete All</button>
    <span id="status"></span>
    <div style="flex:1"></div>
    <button class="btn-save" onclick="saveCode()">💾 Save & Apply</button>
  </div>
  <div class="info-text">1. Copy code → 2. Paste in ChatGPT → 3. Paste answer here → 4. Save</div>
  <textarea id="editor" spellcheck="false" autocapitalize="none" autocorrect="off">CONTENT_PLACEHOLDER</textarea>
  
  <script>
    function selectAll() {
      const ed = document.getElementById('editor');
      ed.focus();
      ed.select();
    }

    function deleteAll() {
      if (confirm('¿Borrar todo el contenido del editor?')) {
        document.getElementById('editor').value = '';
      }
    }

    function copyCode() {
      const ed = document.getElementById('editor');
      ed.select();
      document.execCommand('copy');
      alert("✅ Copied!\\n\\nPaste into ChatGPT, Gemini or Claude, describe what you want, then paste the result back here.");
    }
    
    async function saveCode() {
      const status = document.getElementById('status');
      const code = document.getElementById('editor').value;

      status.className = '';
      status.textContent = '⏳ Guardando...';
      status.style.display = 'inline-block';

      try {
        const res = await fetch('/save', {
          method: 'POST',
          headers: { 'Content-Type': 'text/plain; charset=utf-8' },
          body: code
        });

        if (res.ok) {
          status.className = 'ok';
          status.textContent = '✅ Guardado';
          setTimeout(() => { status.style.display = 'none'; }, 3000);
        } else {
          const msg = await res.text();
          status.className = 'err';
          status.textContent = '❌ Error: ' + msg;
        }
      } catch(e) {
        status.className = 'err';
        status.textContent = '❌ Sin conexión';
      }
    }
  </script>
</body>
</html>"""
            body = html_template.replace("CONTENT_PLACEHOLDER", html.escape(current_file_content))
            body = body.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        global current_file_path
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            new_code = self.rfile.read(length).decode('utf-8')
            try:
                with open(current_file_path, "w", encoding="utf-8") as f:
                    f.write(new_code)
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', '2')
                self.end_headers()
                self.wfile.write(b"OK")
            except Exception as e:
                msg = str(e).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
        else:
            self.send_error(404)


def run():
    global current_file_path, current_file_content
    
    while True:
        os.system('clear')
        print("=== 🤖 AI STUDIO (NO API NEEDED) ===")
        print("Create and edit apps easily using your external AI (ChatGPT, etc.)\n")
        print("1) 🌐 WebApp (HTML/JS/CSS)")
        print("2) 🧩 OS Plugin (Python)")
        print("0) 🔙 Back")
        
        choice = input("\nSelect type: ").strip()
        if choice == "0": return
        if choice not in ("1", "2"): continue

        name = input("\n📝 Enter project name (e.g. calculator): ").strip()
        if not name: continue

        clean_name = "".join(e for e in name if e.isalnum() or e == " ").strip().replace(" ", "_").lower()
        if not clean_name: clean_name = "untitled"

        if choice == "1":
            target_dir = os.path.join("my_apps", clean_name)
            os.makedirs(target_dir, exist_ok=True)
            current_file_path = os.path.join(target_dir, "index.html")
            
            prompt = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{name}</title>
  <style>
    body {{ font-family: sans-serif; text-align: center; padding: 20px; background: #121212; color: white; }}
    .container {{ background: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); margin-top: 20px; }}
    button {{ padding: 12px 24px; font-size: 16px; border-radius: 8px; border: none; background: #007aff; color: white; cursor: pointer; font-weight: bold; margin-top: 15px; }}
    button:active {{ transform: scale(0.95); }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{name}</h1>
    <p>This is my new application running on Acornix.</p>
    <button onclick="alert('Hello World! Your app works.')">Test Button</button>
  </div>
  <script>
    // Your Javascript logic goes here
  </script>
</body>
</html>"""

        elif choice == "2":
            target_dir = os.path.join("plugins", clean_name)
            os.makedirs(target_dir, exist_ok=True)
            current_file_path = os.path.join(target_dir, "main.py")
            
            prompt = f"""# 🤖 AI PROMPT: 
# I am building a Python plugin for the Acornix CLI terminal.
# It MUST strictly contain a 'config' dictionary (label and icon) and a 'def run():' entry point.
# Do not use infinite blocking loops without an exit option (like '0' to go back).
# Use clear text, emojis, and standard Python. Do not use external GUI libraries, just terminal output.
# TASK: Add a feature that [ WRITE YOUR IDEA HERE ]

import os
import time

# Plugin Configuration
config = {{
    "label": "{name}", 
    "icon": "⚡"
}}

def run():
    while True:
        os.system('clear')
        print("=== ⚡ {name.upper()} ===")
        print("This is my new plugin functionality.\\n")
        
        print("1) Say Hello")
        print("0) 🔙 Back to Menu")
        
        opt = input("\\nSelect option: ").strip()
        
        if opt == "0":
            break
        elif opt == "1":
            print("\\n👋 Hello, world! Your plugin works.")
            time.sleep(1.5)

if __name__ == "__main__":
    run()"""

        if os.path.exists(current_file_path):
            with open(current_file_path, "r", encoding="utf-8") as f:
                current_file_content = f.read()
                if not current_file_content.strip():
                    current_file_content = prompt
        else:
            current_file_content = prompt
            with open(current_file_path, "w", encoding="utf-8") as f:
                f.write(current_file_content)

        print(f"\n✅ Template generated at: {current_file_path}")
        print("🌐 Starting visual editor on port 8081...")

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        httpd = socketserver.ThreadingTCPServer(("", PORT), StudioHandler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        url = f"http://localhost:{PORT}/"
        termux = shutil.which("termux-open-url")
        if termux:
            os.system(f'{termux} "{url}"')
        else:
            print(f"\n👉 Please open this URL in your browser: {url}")

        input("\n⏸️  Press [ENTER] when you are done saving to close the editor and return...")
        
        print("Shutting down editor...")
        httpd.shutdown()
        break

if __name__ == "__main__":
    run()