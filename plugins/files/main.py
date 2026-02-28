import os
import json
import http.server
import socketserver
import webbrowser
import shutil
from urllib.parse import urlparse, parse_qs, unquote

# Acornix Plugin Configuration
config = {"label": "FILES (edit your apps, plugins)", "icon": "📱"}
PORT = 8083

def get_safe_path(base, rel_path):
    if not rel_path: return base
    rel_path = unquote(rel_path).lstrip("/")
    target = os.path.abspath(os.path.join(base, rel_path))
    if os.path.commonpath([base, target]) == base:
        return target
    raise ValueError("Access Denied")

class AcornixEditorHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self._get_ui_html().encode("utf-8"))
            return

        if parsed.path == "/api/list":
            qs = parse_qs(parsed.query)
            rel = qs.get("path", [""])[0]
            try:
                target = get_safe_path(self.server.base_dir, rel)
                entries = []
                for entry in sorted(os.scandir(target), key=lambda e: (not e.is_dir(), e.name.lower())):
                    if entry.name.startswith(".") and entry.name != ".env": continue
                    entries.append({
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "path": os.path.relpath(entry.path, self.server.base_dir)
                    })
                self._send_json({"entries": entries, "current": rel})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        if parsed.path == "/api/read":
            qs = parse_qs(parsed.query)
            rel = qs.get("path", [""])[0]
            try:
                target = get_safe_path(self.server.base_dir, rel)
                with open(target, "r", encoding="utf-8") as f:
                    self._send_json({"content": f.read()})
            except Exception as e:
                self._send_json({"error": "File cannot be read"}, 400)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length).decode('utf-8'))
        parsed = urlparse(self.path)

        if parsed.path == "/api/save":
            try:
                target = get_safe_path(self.server.base_dir, data['path'])
                with open(target, "w", encoding="utf-8") as f:
                    f.write(data['content'])
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        if parsed.path == "/api/delete":
            try:
                target = get_safe_path(self.server.base_dir, data['path'])
                if os.path.isdir(target): shutil.rmtree(target)
                else: os.remove(target)
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        if parsed.path == "/api/rename":
            try:
                old_target = get_safe_path(self.server.base_dir, data['old_path'])
                new_target = get_safe_path(self.server.base_dir, data['new_path'])
                os.rename(old_target, new_target)
                self._send_json({"status": "ok"})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

    def _get_ui_html(self):
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>Acornix Mobile Editor</title>
            <style>
                :root { --bg: #0d1117; --panel: #161b22; --text: #c9d1d9; --accent: #238636; --danger: #da3633; --border: #30363d; --blue: #58a6ff; }
                body { margin: 0; font-family: sans-serif; background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
                header { background: var(--panel); padding: 12px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
                #sidebar { height: 35vh; overflow-y: auto; border-bottom: 1px solid var(--border); background: #0d1117; }
                #editor-container { flex: 1; display: flex; flex-direction: column; position: relative; }
                textarea { flex: 1; background: transparent; color: #e6edf3; border: none; padding: 15px; font-family: monospace; font-size: 14px; outline: none; resize: none; width: 100%; box-sizing: border-box; line-height: 1.5; }
                
                .file-item { padding: 12px 20px; border-bottom: 1px solid #21262d; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-size: 14px; -webkit-user-select: none; user-select: none; }
                .file-item:active { background: #1f6feb33; }
                .item-info { display: flex; align-items: center; gap: 10px; flex: 1; }
                .dir { color: var(--blue); font-weight: bold; }
                .del-btn-small { padding: 8px 15px; color: #8b949e; font-size: 18px; }
                
                .actions { padding: 10px; background: var(--panel); border-top: 1px solid var(--border); display: flex; gap: 10px; }
                button { flex: 1; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 13px; cursor: pointer; }
                #save-btn { background: var(--accent); }
                #cancel-btn { background: #30363d; }
                button:disabled { opacity: 0.3; pointer-events: none; }
                
                #status { font-size: 11px; color: #8b949e; text-transform: uppercase; }
                .breadcrumb { background: #161b22; padding: 8px 20px; font-size: 12px; border-bottom: 1px solid var(--border); color: var(--blue); }
            </style>
        </head>
        <body>
            <header>
                <div style="font-weight:bold">🌳 Acornix <span style="color:var(--blue)">Editor</span></div>
                <div id="status">Ready</div>
            </header>
            <div id="sidebar"></div>
            <div class="breadcrumb" id="path-display">/root</div>
            <div id="editor-container">
                <textarea id="code-editor" spellcheck="false" placeholder="Select a file or long-press to rename..."></textarea>
                <div class="actions">
                    <button id="cancel-btn" onclick="discardChanges()" disabled>CANCEL</button>
                    <button id="save-btn" onclick="saveFile()" disabled>SAVE CHANGES</button>
                </div>
            </div>

            <script>
                let currentFile = null;
                let currentPath = "";
                let pressTimer;

                async function loadDir(path = "") {
                    currentPath = path;
                    document.getElementById('path-display').innerText = "📂 " + (path || "root");
                    const res = await fetch(`/api/list?path=${encodeURIComponent(path)}`);
                    const data = await res.json();
                    const sidebar = document.getElementById('sidebar');
                    sidebar.innerHTML = path ? `<div class="file-item dir" onclick="loadDir('${path.split('/').slice(0,-1).join('/')}')"><div class="item-info">⬅️ .. (Back)</div></div>` : "";
                    
                    data.entries.forEach(e => {
                        const div = document.createElement('div');
                        div.className = `file-item ${e.is_dir ? 'dir' : ''}`;
                        
                        // Long press logic
                        div.ontouchstart = () => pressTimer = setTimeout(() => renameItem(e.path, e.name), 800);
                        div.ontouchend = () => clearTimeout(pressTimer);
                        div.onmousedown = () => pressTimer = setTimeout(() => renameItem(e.path, e.name), 800);
                        div.onmouseup = () => clearTimeout(pressTimer);

                        div.innerHTML = `
                            <div class="item-info" onclick="${e.is_dir ? `loadDir('${e.path}')` : `readFile('${e.path}')`}">
                                <span>${e.is_dir ? '📁' : '📄'} ${e.name}</span>
                            </div>
                            <div class="del-btn-small" onclick="deleteItem('${e.path}', '${e.name}')">×</div>
                        `;
                        sidebar.appendChild(div);
                    });
                }

                async function readFile(path) {
                    document.getElementById('status').innerText = "Reading...";
                    const res = await fetch(`/api/read?path=${encodeURIComponent(path)}`);
                    const data = await res.json();
                    if(data.error) return alert(data.error);
                    currentFile = path;
                    document.getElementById('code-editor').value = data.content;
                    document.getElementById('save-btn').disabled = false;
                    document.getElementById('cancel-btn').disabled = false;
                    document.getElementById('status').innerText = "File: " + path.split('/').pop();
                    document.getElementById('editor-container').scrollIntoView({ behavior: 'smooth' });
                }

                function discardChanges() {
                    if(confirm("Close file and clear editor?")) {
                        currentFile = null;
                        document.getElementById('code-editor').value = "";
                        document.getElementById('save-btn').disabled = true;
                        document.getElementById('cancel-btn').disabled = true;
                        document.getElementById('status').innerText = "Ready";
                    }
                }

                async function saveFile() {
                    if(!currentFile) return;
                    document.getElementById('status').innerText = "Saving...";
                    const content = document.getElementById('code-editor').value;
                    const res = await fetch('/api/save', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ path: currentFile, content })
                    });
                    if(res.ok) {
                        document.getElementById('status').innerText = "✅ SAVED";
                        setTimeout(() => document.getElementById('status').innerText = "Editing: " + currentFile.split('/').pop(), 2000);
                    }
                }

                async function renameItem(oldPath, oldName) {
                    const newName = prompt("Rename to:", oldName);
                    if(!newName || newName === oldName) return;
                    const newPath = (currentPath ? currentPath + "/" : "") + newName;
                    const res = await fetch('/api/rename', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ old_path: oldPath, new_path: newPath })
                    });
                    if(res.ok) loadDir(currentPath);
                    else alert("Rename failed");
                }

                async function deleteItem(path, name) {
                    if(confirm(`Delete permanently: ${name}?`)) {
                        const res = await fetch('/api/delete', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ path: path })
                        });
                        if(res.ok) {
                            if(currentFile === path) discardChanges();
                            loadDir(currentPath);
                        }
                    }
                }
                loadDir();
            </script>
        </body>
        </html>
        """

def run():
    base = os.getcwd()
    print(f"🚀 Mobile Editor V3 started in {base}")
    class ThreadedServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        base_dir = base
    with ThreadedServer(("", PORT), AcornixEditorHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"🌍 Link: {url}")
        if shutil.which("termux-open-url"): os.system(f"termux-open-url {url}")
        else: webbrowser.open(url)
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\n🛑 Stopped.")

if __name__ == "__main__":
    run()