# Trader Sahab — frontend

React + Vite, migrated from a single-file vanilla-JS dashboard (kept at
`legacy/index.html` for reference — it still works standalone if ever needed).

```bash
npm install
npm run dev      # http://localhost:5500
npm run build    # outputs to dist/
```

The dev server (and the built app) talk to the FastAPI backend at
`http://localhost:8000` — see `../backend/README` section of the root
`README.md` for running that side and getting a dashboard API key.

See the root `README.md` for what this app actually does; this file is just
the frontend build instructions.
