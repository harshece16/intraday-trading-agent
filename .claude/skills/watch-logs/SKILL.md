---
name: watch-logs
description: Watch Trader Sahab's live activity log for real bugs and explain why trades are or aren't happening. Use for "keep watching live logs", "why no open positions", "why aren't we trading".
---

Each check:
1. Pull `GET /api/activity?limit=200`, `/api/state`, `/api/journal/blocker-stats`, `/api/journal/blocked-signals` (key from `backend/.dashboard_key.json`), or query `backend/data/sahab_journal.db` (`activity`, `signals`, `checklist_evals`, `trades`).
2. Separate **functional bugs** (errors, stale data, symbols dropped, orders not reaching the broker/journal, UI not reflecting state) from **strategy blocks** (checklist items failing, risk limits, market hours).
3. For "no trades": rank the top blockers by count and name the exact checklist item.
4. Report only new findings since the last check; for a real bug, show the evidence, then fix with a regression test (via /ship) or offer an issue.
5. If asked to keep watching, use `/loop` with this skill rather than sleeping in the foreground.

$ARGUMENTS
