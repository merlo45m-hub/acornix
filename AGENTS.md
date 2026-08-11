# acornix — Agent Overview

## Project
acornix (merlo45m-hub/acornix) — Python/Termux web-based agent orchestration system.

## Stack
- Python 3.14 / 3.12
- FastAPI (WebUI)
- OmniRoute Dashboard (Node.js)
- Ollama (local LLMs)
- Telegram Bot Gateway
- Cloudflare Tunnel
- Supabase

## Files
```
/root/workspace/acornix/
├── main.py          # Core orchestrator — runs the 9-hour overnight workflow
├── core/
│   ├── api.py       # FastAPI app, routes, webhooks
│   ├── services/    # Service management (WebUI, OmniRoute, Telegram, Ollama)
│   └── cron/        # Cron job definitions
├── plugins/
│   └── (dynamic plugin loading)
└── tests/           # Integration tests
```

## Integration: 9-Hour Overnight Workflow

The 9-hour overnight workflow is integrated via `OvernightWorkflow` class in `main.py`.

### What it does
- **03:00 UTC** — Checks all services (WebUI, OmniRoute, Ollama, Telegram, Cron jobs)
- **03:00–06:00** — Runs overnight cron jobs (security scan, daily summary, skill maintenance)
- **06:00–09:00** — Standup briefing + project state refresh
- **09:00–12:00** — Active development, PR review, monitoring
- **12:00–15:00** — Deep work blocks, async processing
- **15:00–18:00** — Delivery, scheduling, cleanup
- **18:00–21:00** — Review, logging, next-day prep
- **21:00–24:00** — Final checks, shutdown prep

### Guide
The full guide at `/root/workspace/clip-engine/COMPLETE_GUIDE_TO_THE_9-HOUR_OVERNIGHT_WORKFLOW.md` covers:
- 5-layer autonomous operation framework
- 30-day compounding growth model
- 6-step setup checklist
- Token math and cost estimates
- 9-hour schedule breakdown

### Integration Steps
1. Ensure `CLEAN_GUIDE.md` exists at `/root/workspace/clip-engine/COMPLETE_GUIDE_TO_THE_9-HOUR_OVERNIGHT_WORKFLOW.md`
2. Start the nightly cron: `cronjob action=run job_id=45f97a096613`
3. Run health check: `curl -s http://127.0.0.1:8787/health`
4. All services monitored: WebUI, OmniRoute, Ollama, Telegram gateway

### Monitoring
- WebUI: `localhost:8787/health`
- OmniRoute: `localhost:20128` (WebSocket)
- Ollama: `localhost:11434/api/tags`
- Telegram gateway: `localhost:8644`
- Cron output: `/root/.hermes/profiles/cto/cron/output/`
