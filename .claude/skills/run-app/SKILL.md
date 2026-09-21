---
name: run-app
description: Start Trader Sahab (backend :8000, dashboard :5500, optional ngrok for Kite login). Use when the user says "start the app", "open the web", "run it", or pastes a /kite/callback URL.
---

1. `lsof -nP -i :8000 -i :5500` — if already running, don't restart; just report the URLs.
2. Backend (background): `cd backend && .venv/bin/uvicorn app:app --port 8000`. Wait for `/api/state` to answer (with the key from `backend/.dashboard_key.json`).
3. Dashboard (background): `cd frontend && npm run dev` → http://localhost:5500
4. For Kite login: ensure `ngrok http 8000` is running (static domain if configured), then open `/kite/login`. If the user pastes a callback URL containing `request_token`, it's single-use and short-lived: open that exact URL against the running backend so it's exchanged, don't repeat the token in chat.
5. Open the dashboard in Chrome and confirm it loads. Report URLs and Kite connection status (`/api/kite/status`).
