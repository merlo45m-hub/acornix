#!/bin/bash
# WebUI-OmniRoute-Watchdog
# Checks services every 15 minutes. Restarts WebUI if down.
# OmniRoute, Ollama run as Termux processes (phone-cmd for restart).
# Uses python3 for reliable JSON parsing.

LOG="/root/.hermes/profiles/cto/cron/output/watchdog-$(date +%Y%m%d).log"
mkdir -p "$(dirname "$LOG")"

log() {
  echo "[$(date -Iseconds)] $*" >> "$LOG"
}

log "Watchdog check starting"

# ---- WebUI ----
WEBUI_HEALTH=$(curl -s --max-time 3 http://127.0.0.1:8787/health 2>/dev/null || echo "FAIL")
WEBUI_OK=$(echo "$WEBUI_HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('status')=='ok' else 'no')" 2>/dev/null || echo "no")

if [ "$WEBUI_OK" = "yes" ]; then
  log "WebUI: OK"
else
  log "WebUI: DOWN - restarting"
  pkill -f "server.py" 2>/dev/null || true
  pkill -f "bootstrap.py" 2>/dev/null || true
  for i in $(seq 1 10); do
    if ss -tlnp 2>/dev/null | grep -q ':8787'; then
      break
    fi
    sleep 1
  done
  sleep 1
  cd /root/hermes-webui
  nohup ./start.sh >> "$LOG" 2>&1 &
  log "WebUI start.sh launched (PID $!)"
  WEBUI_RESTART_OK=false
  for i in $(seq 1 15); do
    sleep 1
    CHECK=$(curl -s --max-time 2 http://127.0.0.1:8787/health 2>/dev/null || echo "")
    CHECK_OK=$(echo "$CHECK" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('status')=='ok' else 'no')" 2>/dev/null || echo "no")
    if [ "$CHECK_OK" = "yes" ]; then
      WEBUI_RESTART_OK=true
      log "WebUI restart: OK (healthy after ${i}s)"
      break
    fi
  done
  if [ "$WEBUI_RESTART_OK" != "true" ]; then
    log "WebUI restart: FAILED after 15s"
  fi
fi

# ---- OmniRoute ----
OMNIROUTE_RESP=$(curl -s --max-time 3 http://127.0.0.1:20128/ 2>/dev/null || echo "FAIL")
OMNIROUTE_OK=$(echo "$OMNIROUTE_RESP" | python3 -c "
import sys
data = sys.stdin.read().lower()
print('yes' if 'dashboard' in data or 'omniroute' in data else 'no')
" 2>/dev/null || echo "no")

if [ "$OMNIROUTE_OK" = "yes" ]; then
  log "OmniRoute: OK"
else
  log "OmniRoute: DOWN - attempting restart via phone-cmd"
  if command -v phone-cmd &>/dev/null; then
    phone-cmd "pgrep 'omniroute serve' || omniroute serve --daemon" 2>/dev/null
    log "OmniRoute: restart attempted via Termux"
  else
    log "OmniRoute: DOWN but phone-cmd unavailable"
  fi
fi

# ---- Termux Bridge ----
BRIDGE_RESP=$(curl -s --max-time 3 -X POST http://127.0.0.1:9999/ -H "Content-Type: application/json" -d '{"command":"echo ok"}' 2>/dev/null || echo "FAIL")
BRIDGE_OK=$(echo "$BRIDGE_RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('yes' if d.get('status')=='success' and 'ok' in d.get('stdout','').strip() else 'no')
except:
    print('no')
" 2>/dev/null || echo "no")

if [ "$BRIDGE_OK" = "yes" ]; then
  log "Bridge: OK"
else
  log "Bridge: DOWN - attempting restart via phone-cmd"
  if command -v phone-cmd &>/dev/null; then
    phone-cmd "pgrep -f termux_bridge_server || (nohup /data/data/com.termux/files/usr/bin/python /data/data/com.termux/files/home/termux_bridge_server.py > /data/data/com.termux/files/home/.hermes/webui/bridge.log 2>&1 &)" 2>/dev/null
    log "Bridge: restart attempted via Termux"
  else
    log "Bridge: DOWN but phone-cmd unavailable"
  fi
fi

# ---- Ollama ----
OLLAMA_RESP=$(curl -s --max-time 3 http://127.0.0.1:11434/api/tags 2>/dev/null || echo "FAIL")
OLLAMA_OK=$(echo "$OLLAMA_RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('yes' if 'models' in d else 'no')
except:
    print('no')
" 2>/dev/null || echo "no")

if [ "$OLLAMA_OK" = "yes" ]; then
  log "Ollama: OK"
else
  log "Ollama: DOWN - restart not automated (runs in Termux, check manually)"
fi

# ---- Summary ----
ALL_OK=true
for svc_ok in "$WEBUI_OK" "$OMNIROUTE_OK" "$BRIDGE_OK" "$OLLAMA_OK"; do
  if [ "$svc_ok" != "yes" ]; then
    ALL_OK=false
    break
  fi
done

if [ "$ALL_OK" = "true" ]; then
  log "All services healthy"
else
  log "WARN: some services down (WebUI=$WEBUI_OK OmniRoute=$OMNIROUTE_OK Bridge=$BRIDGE_OK Ollama=$OLLAMA_OK)"
fi

log "Watchdog check complete"
