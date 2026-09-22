# Trader Sahab — NSE intraday trading agent

FastAPI backend (`backend/`) + React/Vite dashboard (`frontend/`). Paper mode by default; live trading via Zerodha Kite Connect. Repo: `harshece16/intraday-trading-agent` (private). Board: https://github.com/users/harshece16/projects/1

## Run

```bash
cd backend && source .venv/bin/activate && uvicorn app:app --port 8000   # API
cd frontend && npm run dev                                               # http://localhost:5500
ngrok http 8000        # only for the in-app "Connect Kite" login (callback: /kite/callback)
```

- The user usually already has the backend on **8000** and the dashboard on **5500** — check with `lsof -i :8000 -i :5500` and don't kill them. Test your own copy on another port.
- **A different port does NOT isolate the database.** Importing `app` starts a second engine that scans and writes activity into whatever journal `database.DB_PATH` points at. Copy the db and set `SAHAB_DB_PATH=/path/to/copy.db` (issue #70), then point the dashboard at it with `?api=http://127.0.0.1:<port>`. A second engine on the same journal now refuses to start.
- Every API route except `/kite/callback` needs the dashboard key (`X-Api-Key` header or `?key=`), stored in `backend/.dashboard_key.json`.
- Local Python is **3.9** (no `X | Y` type hints, no `match`); CI runs 3.11.

## Test

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
cd frontend && npm run lint && npm run build
```

## Live log

"Watch the live log" = the engine's activity stream: `GET /api/activity?limit=200` (in-memory `state.activity`) and the `activity`, `signals`, `checklist_evals`, `trades` tables in `backend/data/sahab_journal.db` (sqlite). Blocked-entry reasons: `/api/journal/blocked-signals`, `/api/journal/blocker-stats`.

## Key modules

`scanner.py` (what to trade) · `trader_brain.py` (when — Varsity checklist) · `trading_engine.py` (execution) · `risk_manager.py` · `costs.py` (slippage/charges) · `backtester.py` / `swing_backtester.py` · `chaywanaprash.py` (internal self-review LLM) · `app.py` (routes) · `kite_broker.py` / `paper_broker.py`.

## Workflow (see WORKFLOW.md)

- Never commit straight to `main`: branch `type/short-desc` → Conventional Commit (`feat:`/`fix:`/`docs:`…) with a prose body explaining why → PR using `.github/PULL_REQUEST_TEMPLATE.md` (include real verification evidence and `Closes #N`) → CI green → squash merge.
- Update `README.md` with a new numbered section for user-visible changes.
- Every confirmed bug: file a GitHub issue (label `bug`, with evidence) right away, even if it isn't fixed now, and add a row to `BUG_LOG.md`. When the fix merges, move the row to "Fixed" and note the deploy.

## Rules

- Judge strategy changes by net-of-cost backtests on both halves of the sample; call out curve-fitting; never imply profit is guaranteed.
- Verify UI changes in the browser before reporting them.
- Never commit anything in `research/` except notes — book PDFs are copyrighted.
- Never commit `.kite_session.json`, `.dashboard_key.json`, or `data/*.db`; never print Kite access tokens.
