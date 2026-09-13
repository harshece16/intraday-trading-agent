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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import config
import data_provider
from state import AppState
from trading_engine import TradingEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trading_bot")

state = AppState(watchlist=config.WATCHLIST, paper_mode=config.PAPER_MODE_DEFAULT)
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
        return {"symbol": symbol, "candles": state.candles.get(symbol, [])}


class ModeUpdate(BaseModel):
    paper_mode: bool


@app.post("/api/mode")
def set_mode(update: ModeUpdate):
    with state.lock:
        state.paper_mode = update.paper_mode
    logger.warning(f"Mode switched to {'PAPER' if update.paper_mode else 'LIVE'} via dashboard")
    return {"paper_mode": state.paper_mode}


class WatchlistUpdate(BaseModel):
    symbols: list[str]


@app.post("/api/watchlist")
def set_watchlist(update: WatchlistUpdate):
    with state.lock:
        state.watchlist = update.symbols
        for s in update.symbols:
            state.candles.setdefault(s, [])
            state.strategy_state.setdefault(s, None)
            state.indicators.setdefault(s, {})
            state.positions.setdefault(s, {"quantity": 0, "avg_price": 0.0, "entry_atr": None})
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
    """Step 1 of the in-app 'Connect Kite' flow — redirects to Zerodha's
    login page. Requires KITE_API_KEY to already be set (from creating an
    app at developers.kite.trade); this endpoint can't create that app for
    you, only use it once it exists."""
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
    """Step 2 — Kite redirects here after login. This URL must be
    registered as the app's exact Redirect URL in the Kite Connect
    dashboard, or Kite will refuse to send the user back here at all."""
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
