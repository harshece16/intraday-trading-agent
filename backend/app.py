"""
FastAPI app. Serves the dashboard's REST endpoints + a WebSocket that pushes
state updates, and runs the trading engine loop in the background.

Run with:
    uvicorn app:app --reload --port 8000
Then open frontend/index.html (or serve it — see README) in a browser.
"""

import asyncio
import csv
import io
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

import config
import data_provider
import database
import day_plan
import fno_instruments
import llm_sentiment
import methods
import news_sentiment
import portfolio_diagnostic
import universe
from state import AppState
from trading_engine import TradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trading_bot")
IST_TZ = ZoneInfo("Asia/Kolkata")

initial_watchlist = list(config.SCANNER.get("pinned", [])) if config.SCANNER.get("enabled") else config.WATCHLIST
state = AppState(watchlist=initial_watchlist, paper_mode=config.PAPER_MODE_DEFAULT)
engine = TradingEngine(state)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(engine.run_forever())
    yield
    state.running = False
    task.cancel()


app = FastAPI(title="Trader Sahab", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Public only because Zerodha's own redirect must reach it, and it can't
# carry our custom header — /kite/callback only ever exchanges a one-time
# token against OUR api_secret, so reaching it without the key can't read or
# change anything by itself. Everything else — including /kite/login, since
# nothing should be able to kick off a new Kite session but us — requires
# config.DASHBOARD_API_KEY, as an X-Api-Key header or a ?key= query param
# (the latter for the WebSocket and the Connect-Kite popup, neither of which
# can set a custom header).
PUBLIC_PATHS = {"/kite/callback"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        key = request.headers.get("x-api-key") or request.query_params.get("key")
        if key != config.DASHBOARD_API_KEY:
            return JSONResponse({"detail": "Missing or invalid API key."}, status_code=401)
        return await call_next(request)


app.add_middleware(ApiKeyMiddleware)
if config.DASHBOARD_API_KEY_IS_NEW:
    logger.warning(f"Dashboard API key generated — enter this into the dashboard once: {config.DASHBOARD_API_KEY}")
else:
    # Printed in full only on the one run that generates it; every later restart shows a
    # masked reference instead, since this key gates real trading control and repeatedly
    # writing it in full into stdout/journald/log-aggregator output on every restart was a
    # real, avoidable exposure the multi-expert review flagged. Full value stays retrievable
    # from backend/.dashboard_key.json (already gitignored) if it's ever needed again.
    k = config.DASHBOARD_API_KEY
    logger.warning(f"Dashboard API key: {k[:6]}...{k[-4:]} (unchanged — see backend/.dashboard_key.json for the full value)")


@app.get("/api/state")
def get_state():
    return state.snapshot()


@app.get("/api/candles/{symbol}")
def get_candles(symbol: str):
    with state.lock:
        candles = list(state.candles.get(symbol) or [])
    if not candles and engine.scanner:
        candles = engine.scanner.intraday.get(symbol, [])
    return {"symbol": symbol, "candles": candles}


@app.get("/api/scanner")
def get_scanner():
    return state.scanner or {"rows": [], "active": [], "market": None}


@app.post("/api/scan")
def trigger_scan():
    if not engine.scanner:
        raise HTTPException(status_code=400, detail="Scanner is disabled (config.SCANNER['enabled'])")
    started = engine.request_scan()
    return {"started": started, "message": "Scan started" if started else "A scan is already running"}


# Pre-market: scanner.run_premarket() runs on daily candles only (no 5-min
# data needed), so it works before 09:15 IST. The engine owns the cache and
# the daily run schedule (trading_engine.tick() kicks one off once a day, and
# seeds the watchlist from it — see trading_engine's "pre-market" section);
# these endpoints just read/trigger through it.
@app.get("/api/premarket")
def get_premarket():
    with state.lock:
        pm = dict(state.premarket)
    stale = pm["result"] is not None and time.time() - pm["result"]["ts"] > 1800
    if (pm["result"] is None or stale) and not pm["running"]:
        engine.request_premarket_scan()
    return {"result": pm["result"], "error": pm["error"], "running": pm["running"]}


@app.post("/api/premarket/refresh")
def refresh_premarket():
    started = engine.request_premarket_scan()
    return {"started": started, "message": "Pre-market scan started" if started else "A pre-market scan is already running"}


@app.get("/api/news/{symbol}")
def get_news(symbol: str):
    sym = symbol.upper()
    if sym not in universe.by_symbol() and sym not in state.watchlist:
        raise HTTPException(status_code=404, detail=f"Unknown symbol {sym}")
    return {"symbol": sym, **news_sentiment.get_sentiment(sym)}


@app.get("/api/activity")
def get_activity(limit: int = 200):
    with state.lock:
        return state.activity[:limit]


@app.get("/api/methods")
def get_methods():
    """Every technique Sahab's Dimaag actually trades on, assembled from the
    real constants those modules use — not a hand-written page that could
    drift out of sync with the code."""
    return methods.get_methods()


class FnoUpdate(BaseModel):
    enabled: bool


@app.post("/api/fno/enable")
def set_fno_enabled(update: FnoUpdate):
    """Separate opt-in from paper_mode/the Live toggle — an F&O order only
    ever reaches Kite when BOTH this is True AND state.paper_mode is False."""
    config.FNO["enabled"] = update.enabled
    state.log("system", f"F&O (options-buying) {'enabled' if update.enabled else 'disabled'} via the dashboard",
              level="warn" if update.enabled else "info")
    return {"enabled": config.FNO["enabled"]}


class LlmSentimentUpdate(BaseModel):
    enabled: bool


@app.post("/api/llm-sentiment/enable")
def set_llm_sentiment_enabled(update: LlmSentimentUpdate):
    if update.enabled and not config.NEWS.get("anthropic_api_key"):
        raise HTTPException(status_code=400, detail="Set ANTHROPIC_API_KEY first — there's no key to call with.")
    enabled = llm_sentiment.set_enabled(update.enabled)
    state.log("system", f"LLM news sentiment {'enabled' if enabled else 'disabled'} via the dashboard")
    return llm_sentiment.stats()


@app.get("/api/llm-sentiment/status")
def llm_sentiment_status():
    """Live usage check: real token counts and the cost they actually imply
    at Haiku 4.5's published rate — poll this any time, not just on the
    Technical Analysis page load."""
    return llm_sentiment.stats()


@app.get("/api/portfolio/diagnostic")
def portfolio_diagnostic_endpoint():
    """A technical read of your actual Kite holdings, using the same
    indicators the scanner runs on the NIFTY 100 — deliberately not a buy/
    sell call or a return forecast, see portfolio_diagnostic.py's docstring."""
    if not config.KITE_ACCESS_TOKEN:
        raise HTTPException(status_code=400, detail="Connect Kite first — this reads your real holdings.")
    holdings = engine._ensure_kite().get_holdings()
    return portfolio_diagnostic.run(holdings)


@app.get("/api/fno/journal")
def fno_journal():
    """The F&O-equivalent of /api/journal/summary: how much evidence has
    accumulated (every evaluation, not just executed trades), and — once
    there are enough closed trades — whether the confidence score has
    actually ranked outcomes better than chance."""
    return database.fno_journal_summary()


@app.get("/api/fno/status")
def fno_status():
    """Whether F&O (options-buying only) is turned on, and the current
    Dimaag Scorecard-driven confidence gate that has to clear before any
    order fires — see confidence.py and fno_risk.py."""
    return {
        "enabled": config.FNO["enabled"],
        "kite_connected": bool(config.KITE_ACCESS_TOKEN),
        "capital": config.FNO["capital"],
        "min_confidence_to_trade": config.FNO["min_confidence_to_trade"],
        "max_premium_risk_pct": config.FNO["max_premium_risk_pct"],
        "open_positions": state.fno_positions,
    }


@app.get("/api/fno/pcr")
def fno_pcr():
    """Real Put/Call open-interest ratio for the configured index
    underlyings, near-the-money strikes only — informational context, not
    a score. See fno_instruments.index_pcr()'s docstring for the honest
    evidence caveat (a real, widely-used practitioner heuristic, not
    something with rigorous backtested evidence behind it)."""
    if not config.KITE_ACCESS_TOKEN:
        return {"error": "Kite not connected"}
    kite = engine._ensure_kite()
    out = {}
    for underlying in config.FNO.get("index_underlyings", []):
        try:
            expiry = fno_instruments.nearest_expiry(
                underlying, config.FNO["min_days_to_expiry"], config.FNO["max_days_to_expiry"],
                prefer_weekly=config.FNO["prefer_weekly_for_index"])
            if not expiry:
                continue
            spot = kite.get_index_spot(underlying)
            pcr = fno_instruments.index_pcr(underlying, spot, expiry, kite.get_quotes)
            if pcr:
                out[underlying] = pcr
        except Exception as exc:
            out[underlying] = {"error": str(exc)}
    return out


@app.get("/api/portfolio")
def get_portfolio():
    """Real Kite holdings + margins when Kite is connected (free Kite Connect
    endpoints); always includes today's paper/live intraday positions from
    state, which exist regardless of Kite."""
    with state.lock:
        positions = {sym: pos for sym, pos in state.positions.items() if pos["quantity"] != 0}
        fno_positions = dict(state.fno_positions)
        capital_sync = dict(state.capital_sync) if state.capital_sync else None
    out = {
        "paper_positions": positions, "fno_positions": fno_positions, "kite_connected": bool(config.KITE_ACCESS_TOKEN),
        "risk_total_capital": config.RISK["total_capital"], "capital_sync": capital_sync,
        "sync_capital_with_kite": config.RISK.get("sync_capital_with_kite", False),
    }
    if config.KITE_ACCESS_TOKEN:
        try:
            kite = engine._ensure_kite()
            out["holdings"] = kite.get_holdings()
            out["margins"] = kite.get_margins()
        except Exception as exc:
            out["error"] = f"Could not reach Kite: {exc}"
    return out


@app.get("/api/day-plan")
def get_day_plan(capital: float = 5000.0):
    """Not a prediction — see day_plan.py's docstring for why. Splits into a
    'plan' (the risk model's own boundaries and real position sizes at the
    capital you pass) and an 'outcome' (today's actual fills, measured
    against the real capital that actually sized them, not the hypothetical
    one in 'plan')."""
    with state.lock:
        scanner_result, premarket_result, pm_running = state.scanner, state.premarket.get("result"), state.premarket.get("running")
    if scanner_result is None and premarket_result is None and not pm_running:
        engine.request_premarket_scan()
    rows, source = day_plan.pick_rows(scanner_result, premarket_result)
    plan_data = day_plan.plan(capital, rows)
    plan_data["source"] = source
    outcome_data = day_plan.outcome(config.RISK["total_capital"], paper_mode=state.paper_mode)
    return {"plan": plan_data, "outcome": outcome_data}


@app.get("/api/journal/summary")
def journal_summary():
    """Sahab's Journal — the knowledge base built from everything logged to
    database.py: every scan, every checklist read (not just executed
    trades), and every fill, so it grows far faster than the trade count
    alone. Win rate/expectancy need closed trades; the Information
    Coefficient needs the scanner to have seen the same stock on two
    different sessions, and says so honestly when there isn't enough yet."""
    return database.journal_summary()


@app.get("/api/journal/trades")
def journal_trades(limit: int = 200):
    """Trade history that survives a restart — unlike state.trades, which
    resets to empty every time the process restarts."""
    return database.recent_trades(limit)


@app.get("/api/journal/trades.csv")
def journal_trades_csv():
    """Every logged trade (paper and live both — the mode column says which)
    as a real CSV, for the user's own tax-filing use. Added after a product
    review flagged there was no way to get trade history out of the app at
    all short of reading the SQLite file directly."""
    trades = database.recent_trades(limit=1_000_000)
    buf = io.StringIO()
    cols = ["ts", "symbol", "side", "quantity", "price", "mode", "reason", "note", "realized", "charges", "r_multiple"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for t in reversed(trades):  # oldest first, natural for a ledger
        row = dict(t)
        if row.get("ts"):
            row["ts"] = datetime.fromtimestamp(row["ts"], IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow(row)
    filename = f"trader_sahab_trades_{datetime.now(IST_TZ).date().isoformat()}.csv"
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


class ModeUpdate(BaseModel):
    paper_mode: bool


@app.post("/api/mode")
def set_mode(update: ModeUpdate):
    with state.lock:
        state.paper_mode = update.paper_mode
    mode = "PAPER" if update.paper_mode else "LIVE"
    logger.warning(f"Mode switched to {mode} via dashboard")
    state.log("system", f"Mode switched to {mode} via dashboard", level="warn")
    return {"paper_mode": state.paper_mode}


class WatchlistUpdate(BaseModel):
    symbols: list


@app.post("/api/watchlist")
def set_watchlist(update: WatchlistUpdate):
    """With the scanner on, these become pinned symbols tracked alongside its picks."""
    symbols = [str(s).strip().upper() for s in update.symbols if str(s).strip()]
    held = [s for s, p in state.positions.items() if p["quantity"] != 0]
    if engine.scanner:
        config.SCANNER["pinned"] = symbols
        active = (state.scanner or {}).get("active", [])
        state.set_watchlist(list(dict.fromkeys(symbols + active + held)))
    else:
        state.set_watchlist(list(dict.fromkeys(symbols + held)))
    state.log("watchlist", f"Pinned symbols set to {', '.join(symbols) or 'none'} via dashboard")
    return {"watchlist": state.watchlist}


@app.get("/api/kite/status")
def kite_status():
    return {
        "app_configured": bool(config.KITE_API_KEY and config.KITE_API_SECRET),
        "connected": bool(config.KITE_ACCESS_TOKEN),
        "using_live_data": data_provider.kite_data_active(),
        "generated_at": config.KITE_SESSION_GENERATED_AT,
        "redirect_url": config.KITE_REDIRECT_URL,
    }


@app.get("/kite/login")
def kite_login():
    """Step 1 of the in-app 'Connect Kite' flow — redirects to Zerodha's login page."""
    if not config.KITE_API_KEY:
        return HTMLResponse(
            "<h3>Kite isn't set up yet</h3>"
            "<p>Create an app at <a href='https://developers.kite.trade' target='_blank'>"
            "developers.kite.trade</a> (needs your Zerodha login + the paid Kite Connect "
            f"subscription), set its Redirect URL to <code>{config.KITE_REDIRECT_URL}</code>, "
            "then export <code>KITE_API_KEY</code> and <code>KITE_API_SECRET</code> and "
            "restart the backend before connecting.</p>",
            status_code=400,
        )
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=config.KITE_API_KEY)
    return RedirectResponse(kite.login_url())


@app.get("/kite/callback")
def kite_callback(request_token: Optional[str] = None, status: Optional[str] = None):
    """Step 2 — Kite redirects here after login (must match the app's registered Redirect URL)."""
    if status != "success" or not request_token:
        return HTMLResponse(
            "<h3>Kite login didn't complete</h3><p>Close this tab and try again from the dashboard.</p>",
            status_code=400,
        )
    if not config.KITE_API_SECRET:
        return HTMLResponse(
            "<h3>KITE_API_SECRET isn't set</h3><p>Export it and restart the backend, then retry.</p>",
            status_code=400,
        )

    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=config.KITE_API_KEY)
    try:
        session = kite.generate_session(request_token, api_secret=config.KITE_API_SECRET)
    except Exception as exc:
        logger.exception("Kite session exchange failed")
        return HTMLResponse(f"<h3>Could not complete Kite login</h3><p>{exc}</p>", status_code=400)

    config.save_kite_session(session["access_token"])
    data_provider.reset_kite_client()
    engine.reset_kite_executor()
    logger.warning("Kite connected via the dashboard's in-app login flow")
    state.log("system", "Kite connected — real-time data and live order routing available")

    return HTMLResponse(
        "<h3>Kite connected ✓</h3>"
        "<p>Real-time data and live order placement are ready. You can close this tab "
        "and return to the dashboard.</p>"
        "<script>setTimeout(() => window.close(), 1200)</script>"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # BaseHTTPMiddleware (ApiKeyMiddleware, above) never sees websocket-scope
    # connections, so the key is checked here instead, as a query param
    # (browsers can't set a custom header on a WebSocket handshake).
    if websocket.query_params.get("key") != config.DASHBOARD_API_KEY:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(state.snapshot())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
