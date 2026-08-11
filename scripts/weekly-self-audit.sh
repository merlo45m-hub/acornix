#!/usr/bin/env bash
# Weekly Self-Audit — checks ecosystem health, skills, memory, cron status
# Runs as no_agent script (zero tokens). Output delivered to user.

set -uo pipefail

ISSUES=0
WARNINGS=0
OUTPUT=""

section() { OUTPUT+=$'\n'"=== $1 ==="$'\n'; }
ok()      { OUTPUT+="  [OK] $*"$'\n'; }
warn()    { OUTPUT+="  [WARN] $*"$'\n'; ((WARNINGS++)); }
fail()    { OUTPUT+="  [FAIL] $*"$'\n'; ((ISSUES++)); }

# --- Services ---
section "Services"
for svc in "8787:WebUI:/health" "20128:OmniRoute:/dashboard" "11434:Ollama:/api/version"; do
  port="${svc%%:*}"
  rest="${svc#*:}"
  name="${rest%%:*}"
  endpoint="${rest#*:}"
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:${port}${endpoint}" 2>/dev/null || echo "000")
  if [ "$http_code" -ge 200 ] 2>/dev/null && [ "$http_code" -lt 400 ]; then
    ok "$name (HTTP $http_code)"
  else
    fail "$name DOWN (HTTP $http_code)"
  fi
done

# --- Processes ---
section "Processes"
for proc in "server.py:WebUI" "omniroute:OmniRoute" "ollama serve:Ollama"; do
  name="${proc#*:}"
  pattern="${proc%%:*}"
  pid=$(pgrep -f "$pattern" 2>/dev/null | head -1)
  if [ -n "$pid" ]; then
    ok "$name (PID $pid)"
  else
    warn "$name not running"
  fi
done

# --- Disk ---
section "Disk"
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
  fail "Disk ${DISK_PCT}% used — critical"
elif [ "$DISK_PCT" -gt 75 ]; then
  warn "Disk ${DISK_PCT}% used"
else
  ok "Disk ${DISK_PCT}% used"
fi

# --- Memory ---
section "Memory"
MEM_AVAIL=$(free -m | awk '/Mem:/{print $7}')
if [ "$MEM_AVAIL" -lt 500 ]; then
  fail "Only ${MEM_AVAIL}MB free RAM"
elif [ "$MEM_AVAIL" -lt 1500 ]; then
  warn "${MEM_AVAIL}MB free RAM (tight)"
else
  ok "${MEM_AVAIL}MB free RAM"
fi

# --- Skills ---
section "Skills"
SKILLS_DIR="$HOME/.hermes/profiles/cto/skills"
SKILL_COUNT=$(find "$SKILLS_DIR" -name "*.md" -not -path "*/.curator_backups/*" 2>/dev/null | wc -l)
PRUNED_COUNT=$(grep -rl "SKILL_PRUNED" "$SKILLS_DIR" --include="*.md" 2>/dev/null | grep -v ".curator_backups" | wc -l)
ok "$SKILL_COUNT skill files"
if [ "$PRUNED_COUNT" -gt 0 ]; then
  warn "$PRUNED_COUNT pruned skills found"
fi

# --- Memory ---
section "Memory"
MEM_DIR="$HOME/.hermes/memories"
if [ -d "$MEM_DIR" ]; then
  MEM_SIZE=$(du -sb "$MEM_DIR" 2>/dev/null | awk '{print $1}')
  MEM_KB=$((MEM_SIZE / 1024))
  if [ "$MEM_KB" -gt 50 ]; then
    warn "Memory files ${MEM_KB}KB (may be bloated)"
  else
    ok "Memory files ${MEM_KB}KB"
  fi
else
  warn "Memory directory not found"
fi

# --- Cron Jobs ---
section "Cron Jobs"
CRON_FILE="$HOME/.hermes/profiles/cto/cron/jobs.json"
if [ -f "$CRON_FILE" ]; then
  TOTAL=$(python3 -c "import json; print(len(json.load(open('$CRON_FILE'))['jobs']))" 2>/dev/null || echo "?")
  ENABLED=$(python3 -c "import json; print(len([j for j in json.load(open('$CRON_FILE'))['jobs'] if j.get('enabled')]))" 2>/dev/null || echo "?")
  PAUSED=$(python3 -c "import json; print(len([j for j in json.load(open('$CRON_FILE'))['jobs'] if not j.get('enabled')]))" 2>/dev/null || echo "?")
  ERRORS=$(python3 -c "import json; print(len([j for j in json.load(open('$CRON_FILE'))['jobs'] if j.get('enabled') and j.get('last_status')=='error']))" 2>/dev/null || echo "?")
  ok "$TOTAL total / $ENABLED enabled / $PAUSED paused"
  if [ "$ERRORS" != "0" ] && [ "$ERRORS" != "?" ]; then
    warn "$ERRORS jobs with errors"
  fi
else
  warn "Cron jobs.json not found"
fi

# --- Watchdog Log ---
section "Watchdog Log"
WATCHDOG_LOG="$HOME/.hermes/profiles/cto/cron/output/watchdog-$(date +%Y%m%d).log"
if [ -f "$WATCHDOG_LOG" ]; then
  LAST=$(tail -1 "$WATCHDOG_LOG" 2>/dev/null)
  ok "Last check: $LAST"
  WARN_COUNT=$(grep -c "WARN:" "$WATCHDOG_LOG" 2>/dev/null || echo "0")
  if [ "$WARN_COUNT" -gt 0 ]; then
    warn "$WARN_COUNT warnings in today's log"
  fi
else
  warn "No watchdog log for today"
fi

# --- Hermes Version ---
section "Hermes Agent"
HERMES_VER=$(/usr/local/lib/hermes-agent/node_modules/.bin/hermes --version 2>/dev/null || echo "unknown")
ok "Version: $HERMES_VER"

# --- GitHub ---
section "GitHub"
GH_AUTH=$(gh auth status 2>&1 | grep -o "Logged.*account.*" | head -1 || echo "not authenticated")
ok "$GH_AUTH"
PUSH_TEST=$(cd "$HOME/workspace/acornix" 2>/dev/null && git push --dry-run origin main 2>&1 | tail -1)
if echo "$PUSH_TEST" | grep -q "403\|denied"; then
  warn "GitHub push not available (fine-grained PAT)"
else
  ok "GitHub push OK"
fi

# --- Summary ---
section "SUMMARY"
OUTPUT+="Issues: $ISSUES | Warnings: $WARNINGS"$'\n'
if [ "$ISSUES" -gt 0 ]; then
  OUTPUT+="ACTION NEEDED: $ISSUES critical issues require attention"$'\n'
elif [ "$WARNINGS" -gt 0 ]; then
  OUTPUT+="Healthy with $WARNINGS minor warnings"$'\n'
else
  OUTPUT+="All systems green"$'\n'
fi

echo "$OUTPUT"
