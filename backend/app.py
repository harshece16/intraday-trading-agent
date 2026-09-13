"""
FastAPI app. Serves the dashboard's REST endpoints + a WebSocket that pushes
state updates, and runs the trading engine loop in the background.

Run with:
    uvicorn app:app --reload --port 8000
Then open frontend/index.html (or serve it — see README) in a browser.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import config
import data_provider
import news_sentiment
import universe
from state import AppState
from trading_engine import TradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trading_bot")

initial_watchlist = list(config.SCANNER.get("pinned", [])) if config.SCANNER.get("enabled") else config.WATCHLIST
state = AppState(watchlist=initial_watchlist, paper_mode=config.PAPER_MODE_DEFAULT)
engine = TradingEngine(state)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(engine.run_forever())
    yield
    state.running = False
    task.cancel()


app = FastAPI(title="Intraday Trading Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this if you deploy anywhere beyond localhost
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(state.snapshot())
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
