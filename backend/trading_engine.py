"""
The trading engine — a background loop that, every POLL_INTERVAL_SECONDS:
  1. Checks the market phase (open / square-off window / closed).
  2. Kicks off a market scan in a background thread when one is due — the
     scanner picks WHAT to trade and publishes market context (it also runs
     while the market is closed, so the dashboard always shows a plan).
  3. For each active-watchlist symbol: refreshes candles, enforces
     stop-loss / take-profit, runs the strategy to decide WHEN.
  4. Applies market filters and risk sizing, executes paper or live.
  5. Writes analysis, trades, and a plain-English activity log into AppState.
"""

import asyncio
import logging
import math
import sys
import threading
import time
import traceback
from datetime import date, datetime, time as dtime
from zoneinfo import ZoneInfo

import config
import confidence
import costs
import data_provider
import depth_sampler
import momentum_book
import chaywanaprash
import jev_book
import database
import telegram_alerts
import fno_instruments
import fno_risk
import fundamentals
import holidays
import liquidity
import news_sentiment
import nse_feed
import options_pricing
import review_queue
from kiteconnect.exceptions import TokenException
from kite_broker import ORDER_FINAL, ORDER_UNKNOWN, OrderNotFilled, OrderUnconfirmed
from paper_broker import execute_paper_order
from risk_manager import RiskManager
from scanner import Scanner, run_premarket, selection_mode
import trader_brain
import universe
from state import AppState, _STOP_TARGET_RE, _new_position
from strategy_engine import STRATEGY_FUNCTIONS, atr as compute_atr

logger = logging.getLogger("trading_bot")
IST = ZoneInfo("Asia/Kolkata")

# A normal tick takes seconds; one past this has stalled and needs its stacks logged.
TICK_STALL_SECONDS = 120
TICK_WATCHDOG_INTERVAL_SECONDS = 15


def _parse_hhmm(s: str) -> dtime:
    h, m = map(int, s.split(":"))
    return dtime(h, m)


MARKET_OPEN_T = _parse_hhmm(config.MARKET_OPEN)
MARKET_CLOSE_T = _parse_hhmm(config.MARKET_CLOSE)

# The expired-Kite alert used to repeat on a flat 15-minute throttle for as
# long as the token stayed dead — 40 identical rows on 2026-09-21, 4 an hour
# from midnight to 08:00, and ~95% of the entire error channel across the
# sample. A token dies at 06:00 IST daily and nobody can click Reconnect at
# 03:00, so the tenth copy carries nothing the first did not. Keep the first
# alert loud, then double the interval up to a cap; reconnecting resets it so
# a NEW expiry is loud again. Issue #71.
TOKEN_ALERT_MIN_INTERVAL = 900          # 15 min — unchanged first gap
TOKEN_ALERT_MAX_INTERVAL = 4 * 3600     # stop stretching at 4 h
SQUARE_OFF_T = _parse_hhmm(config.SQUARE_OFF_TIME)
PREOPEN_KITE_CHECK_T = _parse_hhmm(config.PREOPEN_KITE_CHECK_TIME)


def next_session_open(now=None) -> str:
    """ISO datetime (IST) of the next moment trading opens — later today if
    we're before today's open on a trading day, otherwise the next date that
    isn't a weekend or an NSE holiday. Powers the dashboard's countdown."""
    now = now or datetime.now(IST)
    if now.weekday() < 5 and not holidays.is_holiday(now) and now.time() < MARKET_OPEN_T:
        open_date = now.date()
    else:
        open_date = holidays.next_trading_day(now)
    return datetime.combine(open_date, MARKET_OPEN_T, tzinfo=IST).isoformat()


def market_phase(now=None) -> str:
    now = now or datetime.now(IST)
    if now.weekday() >= 5 or holidays.is_holiday(now):
        return "closed"
    t = now.time()
    if t < MARKET_OPEN_T or t >= MARKET_CLOSE_T:
        return "closed"
    if t >= SQUARE_OFF_T:
        return "square_off_window"
    return "open"


class TradingEngine:
    def __init__(self, state: AppState):
        self.state = state
        self.risk = RiskManager(config.RISK)
        # state.__init__ already reloaded today's real fills from the
        # journal (state._rehydrate_today(), see its docstring for the bug
        # this closes) — seed the daily-loss counter from that instead of
        # the RiskManager default 0.0, so a restart mid-session can't erase
        # today's real losses from the max_daily_loss_pct safety check.
        # Same reasoning for _last_day below: leaving it None made the very
        # first tick after any restart think a new day had started, which
        # zeroed this same counter right back out a moment later.
        self.risk.daily_realized_pnl = state.realized_pnl_today
        # Open positions restored from today's journal (state._rehydrate_open_positions)
        # count against max_open_positions and get their stops watched again.
        restored = getattr(state, "restored_positions", []) or []
        restored_fno = getattr(state, "restored_fno_positions", []) or []
        self.risk.open_positions_count = len(restored) + len(restored_fno)
        if restored:
            state.log("risk", f"Restored {len(restored)} open position(s) from today's journal after a restart: "
                              f"{', '.join(restored)} — stops, targets and the square-off are watching them again.",
                      level="warn")
        # Restored live positions come from the journal, which can't know what
        # happened in Kite while the engine was down. Until Kite confirms one
        # is still open, no order is sent for it. See _verify_live_position().
        self._unverified_live = {s for s in restored if state.positions[s].get("live")}
        if self._unverified_live:
            state.log("error", f"A LIVE position is open ({', '.join(sorted(self._unverified_live))}) and the engine "
                               f"restarted in {'Paper' if state.paper_mode else 'Live'}. It is still watched: its "
                               f"stop, target and the square-off will close it with a real order, once Kite "
                               f"confirms it is still open. Check Kite.", level="error")
        # Open option positions come back the same way (#187), keyed by underlying.
        if restored_fno:
            state.log("risk", f"Restored {len(restored_fno)} open F&O position(s) from today's journal after a "
                              f"restart: {', '.join(state.fno_positions[u]['tradingsymbol'] for u in restored_fno)} "
                              f"— premium stops, targets and the square-off are watching them again.", level="warn")
        self._unverified_live_fno = {u for u in restored_fno if state.fno_positions[u].get("live")}
        if self._unverified_live_fno:
            names = ", ".join(sorted(state.fno_positions[u]["tradingsymbol"] for u in self._unverified_live_fno))
            state.log("error", f"A LIVE option position is open ({names}) and the engine restarted in "
                               f"{'Paper' if state.paper_mode else 'Live'}. It is still watched: its premium stop, "
                               f"target and the square-off will close it with a real order, once Kite confirms "
                               f"it is still open. Check Kite.", level="error")
        self.strategy_fn = STRATEGY_FUNCTIONS[config.STRATEGY]
        self.strategy_params = config.STRATEGY_PARAMS[config.STRATEGY]
        self.kite_executor = None
        self._last_day = datetime.now(IST).date()
        self._last_holiday_logged = None
        self._last_session_summary_date = None
        self._preopen_kite_checked_date = None
        self.scanner = Scanner(config.SCANNER) if config.SCANNER.get("enabled") else None
        self._scan_thread = None
        self.size_multiplier = 1.0
        self._last_errors = {}
        self._last_capital_sync = 0.0
        self._last_token_alert = 0.0
        self._token_alert_interval = TOKEN_ALERT_MIN_INTERVAL
        self._reconciliation_alerted = set()
        self._untracked_kite_positions = set()
        self._last_synced_paper_mode = None
        self._premarket_thread = None
        self._last_premarket_run_date = None
        self._last_premarket_seed_date = None
        self._list_fix_attempt_ts = 0.0
        self._closes_recorded_for = None       # the session whose 15:08 prices are in session_closes
        self._closes_missing_logged = None
        self._tick_started_at = None
        self._stall_reported_for = None
        # Symbols whose exit one thread has claimed. Until the tick stream
        # existed only the poll loop ever closed a position, so "read the
        # quantity, then place the closing order" was safe without a lock
        # across both steps. It isn't any more: two threads seeing the same
        # breached stop would each send a full closing order and turn a flat
        # exit into a reversed position. See _claim_exit().
        self._exiting = set()
        # Symbols a manual approval is entering right now. The API thread and
        # the engine's tick both reach the order path; this keeps them from
        # both opening the same stock. See approve_review().
        self._entering = set()
        # symbol -> a live order that was sent but whose outcome Kite never
        # confirmed, with everything needed to book it once it does. While a
        # symbol is here the engine sends no other order in it. See _live_fill().
        self._unconfirmed_orders = {}
        # underlying -> "LONG"/"SHORT": this tick's edge-triggered entry signals,
        # left by _process_symbol() for _process_fno() (#157).
        self._fno_signals = {}
        self.review_queue = review_queue.ReviewQueue()
        state.review_queue = self.review_queue
        self._last_shadow_update = 0.0
        # Set by stop_and_flatten(): the next open-market tick closes anything
        # still open. An entry already past the pause check when the API thread
        # flattened would otherwise survive the kill switch.
        self._reflatten_pending = False
        try:
            state.entries_paused = bool(database.get_control("entries_paused", False))
        except Exception:
            logger.exception("Couldn't read the persisted entry pause — starting unpaused")
        try:
            telegram_alerts.enabled = bool(database.get_control("telegram_enabled", True))
        except Exception:
            logger.exception("Couldn't read the Telegram alert setting — leaving it on")
        self.stop_watcher = None
        self._restore_day_list()

    def _ensure_kite(self):
        if self.kite_executor is None:
            from kite_broker import KiteExecutor
            self.kite_executor = KiteExecutor(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
        return self.kite_executor

    def reset_kite_executor(self):
        """Drop the cached executor so the next order rebuilds it with
        whatever access token config now holds. Called on a successful
        reconnect, which is also the moment to make the expired-session
        alert loud again — a fresh expiry after this is new information,
        so it must not inherit the stretched interval (issue #71)."""
        self.kite_executor = None
        self._last_token_alert = 0.0
        self._token_alert_interval = TOKEN_ALERT_MIN_INTERVAL

    def _sync_capital(self):
        """Refreshes RISK['total_capital'] — the real Kite equity balance in
        LIVE mode (see config.RISK['sync_capital_with_kite']'s docstring for
        why), or the fixed config.RISK['paper_capital'] in PAPER mode (see
        that key's docstring — real accounts are often funded too low for a
        realistic test day). Always fetches the real balance regardless of
        mode and stores it separately on state.real_capital, so the dashboard
        can show "what going live would actually use" even while paper mode
        is sized against a different, bigger number. RiskManager holds a
        reference to config.RISK, not a copy, so mutating total_capital in
        place — same pattern as config.FNO['enabled'] — takes effect on the
        very next position_size() call, no restart needed. Throttled to once
        every 5 minutes since margins() is a live network call."""
        if not config.RISK.get("sync_capital_with_kite") or not config.KITE_ACCESS_TOKEN:
            return
        now = time.time()
        # Never let a fresh Paper<->Live switch wait out the throttle — capital
        # must reflect the new mode immediately, not up to 5 minutes later.
        mode_changed = self.state.paper_mode != self._last_synced_paper_mode
        if not mode_changed and now - self._last_capital_sync < 300:
            return
        self._last_capital_sync = now
        self._last_synced_paper_mode = self.state.paper_mode
        try:
            margins = self._ensure_kite().get_margins()
            live_balance = float(margins["equity"]["available"]["live_balance"])
        except TokenException:
            data_provider.mark_kite_token_rejected()
            # Kite sessions expire daily — this is the expected way that shows up,
            # usually mid-session the morning after. A generic per-symbol error
            # would bury this; it needs its own clear, high-visibility alert since
            # it silently degrades to delayed yfinance data and blocks live orders
            # until reconnected. Throttled to once per 15 min so it doesn't spam.
            if time.time() - self._last_token_alert > self._token_alert_interval:
                self._last_token_alert = time.time()
                self.state.log("error", "Kite session has expired — click Reconnect in the header. Until then, "
                                        "prices fall back to delayed data and live orders will fail.", level="error")
                self._token_alert_interval = min(self._token_alert_interval * 2, TOKEN_ALERT_MAX_INTERVAL)
            return
        except Exception as exc:
            logger.warning(f"Capital sync with Kite failed: {exc}")
            return

        with self.state.lock:
            self.state.real_capital = live_balance

        if self.state.paper_mode:
            effective, source = float(config.RISK.get("paper_capital", live_balance)), "paper_capital_config"
        else:
            effective, source = live_balance, "kite"

        changed = config.RISK["total_capital"] != effective
        config.RISK["total_capital"] = effective
        with self.state.lock:
            self.state.capital_sync = {"amount": effective, "synced_at": now, "source": source, "real_kite_balance": live_balance}
        if changed:
            if source == "paper_capital_config":
                self.state.log("risk", f"Paper capital set to ₹{effective:,.0f} (real Kite balance is ₹{live_balance:,.0f})")
            else:
                self.state.log("risk", f"Risk capital synced to real Kite balance: ₹{effective:,.0f}")

        if not self.state.paper_mode or self._holds_live():
            self._check_position_reconciliation()

    def _holds_live(self):
        with self.state.lock:
            return (any(p["quantity"] and p.get("live") for p in self.state.positions.values())
                    or any(p.get("live") for p in self.state.fno_positions.values()))

    def _verify_live_position(self, symbol, kite_positions=None):
        """Bring a restored live position in line with what Kite holds, before
        any order is sent for it. The closing order is sized from the
        journal; if the position was closed or cut in Kite while the engine
        was down, that order would open a new position the other way.

        Kite flat: the position is dropped and no order is sent. Kite smaller,
        same side: the quantity is cut to Kite's. Kite bigger or on the other
        side: left alone and reported, as that isn't ours to guess at. Raises
        if Kite can't be read, so the caller sends nothing."""
        if kite_positions is None:
            kite_positions = {p["tradingsymbol"]: p for p in self._ensure_kite().get_positions()}
        held = int((kite_positions.get(symbol) or {}).get("quantity") or 0)
        with self.state.lock:
            pos = self.state.positions[symbol]
            ours = pos["quantity"]
            if held == 0:
                pos.update(_new_position())
                self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
            elif held * ours > 0 and abs(held) < abs(ours):
                pos["charges"] = pos.get("charges", 0.0) * abs(held) / abs(ours)
                pos["quantity"] = held
            self._unverified_live.discard(symbol)
        if held == 0:
            self.state.log("error", f"Kite shows no open position in {symbol}, but today's journal has an open "
                                    f"live leg of {ours:+d}. It was closed outside the engine. The engine has "
                                    f"stopped watching it and sent no order; its exit is not in the journal.",
                           symbol=symbol, level="error")
        elif held != ours:
            self.state.log("error", f"Kite holds {held:+d} in {symbol}; today's journal says {ours:+d}. "
                                    + (f"The engine now watches {held:+d}." if held * ours > 0 and abs(held) < abs(ours)
                                       else "The engine keeps watching its own figure. Check Kite."),
                           symbol=symbol, level="error")
        else:
            self.state.log("risk", f"Kite confirms the restored live position in {symbol} ({held:+d}).", symbol=symbol)
        return held

    def _check_position_reconciliation(self):
        """A review flagged that live positions reset on restart and are
        never checked against what Kite actually shows — a real correctness
        risk if the process restarts mid-session with a real position open
        (this engine's own risk sizing, stop/target checks, and square-off
        logic would have no idea it exists). Deliberately does NOT try to
        auto-heal by guessing an entry price, stop, or target this process
        never saw — that could be actively worse than doing nothing, sizing
        risk off a fabricated number. Two things instead: a clear,
        high-visibility alert naming exactly which symbols disagree (once
        per symbol, not repeated every cycle), and — found while auditing
        this for other bugs — self._untracked_kite_positions is kept live
        (added/removed each check, not just alerted once) and _try_enter()
        checks it before any new entry, so the engine can't silently open a
        SECOND real position in a symbol Kite already shows one open in."""
        try:
            kite_positions = {p["tradingsymbol"]: p for p in self._ensure_kite().get_positions() if p["quantity"] != 0}
        except Exception as exc:
            logger.warning(f"Position reconciliation check failed: {exc}")
            return
        for sym in list(self._unverified_live):
            try:
                self._verify_live_position(sym, kite_positions)
            except Exception:
                logger.exception(f"Couldn't verify the restored live position in {sym}")
        for underlying in list(self._unverified_live_fno):
            try:
                self._verify_live_fno(underlying, kite_positions)
            except Exception:
                logger.exception(f"Couldn't verify the restored live option position on {underlying}")
        with self.state.lock:
            # Kite's day book lists NFO contracts too: an option the engine
            # holds is tracked, not an unknown position (#187).
            tracked = {sym for sym, pos in self.state.positions.items() if pos["quantity"] != 0}
            tracked |= {pos["tradingsymbol"] for pos in self.state.fno_positions.values()}
        untracked = set(kite_positions) - tracked

        resolved = self._untracked_kite_positions - untracked
        self._untracked_kite_positions = untracked
        for sym in resolved:
            self.state.log("risk", f"{sym}'s previously-untracked Kite position is no longer open — "
                                   f"new entries into {sym} are allowed again.", symbol=sym)

        for sym in untracked:
            if sym in self._reconciliation_alerted:
                continue
            self._reconciliation_alerted.add(sym)
            qty = kite_positions[sym]["quantity"]
            self.state.log("error", f"Kite shows an open position in {sym} ({qty:+d}) that this app isn't "
                                    f"tracking — likely from before a restart. Risk sizing, stop/target checks, "
                                    f"and square-off won't act on it, and new entries into {sym} are blocked "
                                    f"until this resolves. Check Kite directly.", symbol=sym, level="error")

    # ---- scanning -------------------------------------------------------

    def request_scan(self) -> bool:
        if not self.scanner or (self._scan_thread and self._scan_thread.is_alive()):
            return False
        self._scan_thread = threading.Thread(target=self._run_scan, name="scanner", daemon=True)
        self._scan_thread.start()
        return True

    def _run_scan(self):
        self.state.log("scan", "Scanning the NIFTY 100 universe…")
        try:
            result = self.scanner.run()
        except Exception as exc:
            logger.exception("Scan failed")
            self.state.log("error", f"Scan failed: {exc}", level="error")
            return
        try:
            database.record_scan(result)
        except Exception:
            logger.exception("Failed to journal the scan")

        held = [s for s, p in self.state.positions.items() if p["quantity"] != 0]
        new_watch = list(dict.fromkeys(list(config.SCANNER.get("pinned", [])) + result["active"] + held))
        old_watch = list(self.state.watchlist)
        mkt = result["market"]
        with self.state.lock:
            self.state.market = mkt
            self.state.scanner = result
        self.state.set_watchlist(new_watch)
        self.size_multiplier = config.MARKET_FILTER["vix_high_size_multiplier"] if mkt.get("vix_high") else 1.0

        picks = ", ".join(result["active"]) or "nothing qualifies yet"
        mood = {"risk-on": "strong", "risk-off": "weak"}.get(mkt["bias"], "mixed")
        self.state.log(
            "scan",
            f"Scanned {result['scanned']} stocks in {result['duration_s']:.0f}s. The market looks {mood}: "
            f"{'; '.join(mkt['reasons'][:2])}. {result['excluded_count']} skipped. Tracking {picks}.",
        )
        rows = {r["symbol"]: r for r in result["rows"]}
        for sym in new_watch:
            if sym in old_watch:
                continue
            row = rows.get(sym)
            if row:
                why = "; ".join(x["text"] for x in row["reasons"][:2])
                self.state.log("watchlist", f"Now tracking (score {row['final_score']:.0f}): {why}", symbol=sym)
            else:
                self.state.log("watchlist", "Now tracking (pinned or held position)", symbol=sym)
        dropped = [s for s in old_watch if s not in new_watch]
        if dropped:
            self.state.log("watchlist", f"Stopped tracking {', '.join(dropped)} — no longer among the top picks")
        if mkt.get("vix_high"):
            self.state.log("risk", f"India VIX {mkt['vix']:.1f} is elevated — new position sizes reduced", level="warn")

    # ---- pre-market ------------------------------------------------------
    #
    # scanner.run_premarket() ranks the NIFTY 100 on last session's daily
    # data alone — usable before 09:15 IST, unlike the live scanner above
    # which needs today's 5-min candles. Run once a day here (not just
    # lazily when someone opens the Pre-Market page) so its shortlist is
    # ready to seed the watchlist the moment the process is up each morning.
    #
    # Seeding is deliberately narrow: it only sets WHAT gets tracked from the
    # open, exactly like a trader building a morning watchlist off last
    # night's homework. It never buys anything by itself — _try_enter/
    # trader_brain_signal still require live intraday confirmation (the
    # checklist: candlestick pattern, volume, VWAP side, opening range) for
    # every entry, same as a symbol the live scanner finds mid-session. The
    # only thing pre-market analysis changes is the reaction time — the
    # engine is already watching a real, computed shortlist instead of only
    # pinned/held symbols for the gap before the first live scan completes.

    def request_premarket_scan(self, fix_list_for=None) -> bool:
        if self._premarket_thread and self._premarket_thread.is_alive():
            return False
        self._premarket_thread = threading.Thread(target=self._run_premarket_scan, args=(fix_list_for,),
                                                  name="premarket-scan", daemon=True)
        self._premarket_thread.start()
        return True

    def should_fix_list(self, now, holiday) -> bool:
        """True in the window before the open on a trading day, until the
        day's list is fixed. A failed read is tried again after five minutes."""
        if not self.scanner or holiday or now.weekday() >= 5 or selection_mode(config.SCANNER) != "liquidity":
            return False
        if not config.SCANNER.get("fix_list_from", "08:45") <= now.strftime("%H:%M") < config.MARKET_OPEN:
            return False
        if self.scanner.list_fixed_for(now.date().isoformat()):
            return False
        return time.time() - self._list_fix_attempt_ts >= 300

    def _fix_day_list(self, session, result):
        """The pre-market read's shortlist becomes the day's list, and the
        engine watches it from the open. The scanner writes it to the journal,
        so a restart keeps it (#198)."""
        if not self.scanner.fix_day_list(session, result["watchlist"]):
            return
        symbols = self.scanner.day_list["symbols"]
        self._watch_day_list(symbols)
        self.state.log("watchlist", f"The day's list is fixed before the open, from daily data: "
                                    f"{', '.join(symbols) or 'nothing qualifies'}. "
                                    f"It does not change during the session.")

    def _watch_day_list(self, symbols):
        held = [s for s, p in self.state.positions.items() if p["quantity"] != 0]
        self.state.set_watchlist(list(dict.fromkeys(list(config.SCANNER.get("pinned", [])) + list(symbols) + held)))

    def _restore_day_list(self):
        """After a restart, the list already fixed for today, read back from
        the journal, is watched from the first tick (#198). Without this the
        watchlist held only the pinned stocks until the first scan, and the
        ordinary pre-market read could seed it with a list chosen again."""
        today = datetime.now(IST).date().isoformat()
        if not self.scanner or not self.scanner.list_fixed_for(today):
            return
        dl = self.scanner.day_list
        self._watch_day_list(dl["symbols"])
        at = datetime.fromtimestamp(dl["fixed_ts"], IST).strftime("%H:%M")
        self.state.log("watchlist", f"The day's list, fixed {dl.get('when') or 'earlier'} at {at}, was read back "
                                    f"from the journal after a restart: {', '.join(dl['symbols']) or 'nothing'}. "
                                    f"It is not chosen again.")

    def _run_premarket_scan(self, fix_list_for=None):
        with self.state.lock:
            self.state.premarket["running"] = True
        try:
            result = run_premarket(config.SCANNER)
        except Exception as exc:
            logger.exception("Pre-market scan failed")
            with self.state.lock:
                self.state.premarket = {"result": self.state.premarket.get("result"), "error": str(exc), "running": False}
            return
        with self.state.lock:
            self.state.premarket = {"result": result, "error": None, "running": False}
        self._last_premarket_run_date = datetime.now(IST).date()
        picks = ", ".join(result["watchlist"]) or "nothing qualifies yet"
        self.state.log("scan", f"Pre-market read ({result['market']['bias']}): shortlist is {picks}.")
        if fix_list_for:
            self._fix_day_list(fix_list_for, result)
        self._maybe_seed_watchlist_from_premarket(result)

    def _maybe_seed_watchlist_from_premarket(self, result):
        """Primes state.watchlist with the pre-market shortlist for the gap
        between process start and the first live intraday scan — only while
        that gap is real (no live scan has run yet today) and only once a
        day, so it never fights the live scanner once that takes over."""
        today = datetime.now(IST).date()
        if self._last_premarket_seed_date == today:
            return
        if self.scanner and self.scanner.list_fixed_for(today.isoformat()):
            return          # the watchlist already follows the day's fixed list (#198)
        live_scan_done_today = self.state.scanner and self.state.scanner.get("session_date") == today.isoformat()
        if live_scan_done_today:
            return
        self._last_premarket_seed_date = today
        held = [s for s, p in self.state.positions.items() if p["quantity"] != 0]
        new_watch = list(dict.fromkeys(list(config.SCANNER.get("pinned", [])) + result["watchlist"] + held))
        old_watch = list(self.state.watchlist)
        if new_watch == old_watch:
            return
        self.state.set_watchlist(new_watch)
        added = [s for s in new_watch if s not in old_watch]
        if added:
            self.state.log("watchlist", f"Pre-market shortlist seeded: {', '.join(added)} — tracking from the "
                                        f"open; entries still wait for live checklist confirmation.")

    def _industry_for(self, symbol, row):
        """The sector-concentration cap silently no-ops if it only looks at
        today's live scan row — which is None for a symbol the scanner
        hasn't ranked yet this cycle (a data-fetch gap, or right at process
        start before the first scan completes), giving it zero
        diversification protection exactly when data is spottiest. Falls
        back to the static NIFTY 100 universe list (same industry field,
        always available) so the cap still applies."""
        if row and row.get("industry"):
            return row["industry"]
        if not hasattr(self, "_industry_map"):
            self._industry_map = {u["symbol"]: u["industry"] for u in universe.load()}
        return self._industry_map.get(symbol)

    def _scan_row(self, symbol):
        result = self.state.scanner
        if not result:
            return None
        return next((r for r in result["rows"] if r["symbol"] == symbol), None)

    # ---- execution ------------------------------------------------------

    def _live_fill(self, symbol, side, qty, price, context):
        """Send a live order and return what Kite executed: (filled quantity,
        average price, order id). Before #155 the engine booked every live
        order as filled in full at the modelled price and never read Kite's
        answer, so a rejected order became a position the account didn't hold.

        Raises OrderNotFilled when Kite confirms nothing was bought or sold,
        and OrderUnconfirmed when the outcome can't be read. An unconfirmed
        order is kept in _unconfirmed_orders with its `context`, and the
        symbol takes no other order until _resolve_unconfirmed_orders() has
        settled it: sending a second closing order on top of one that did
        fill would flip the position."""
        if symbol in self._unconfirmed_orders:
            raise OrderUnconfirmed(f"order {self._unconfirmed_orders[symbol]['order_id']} in {symbol} is still "
                                   f"unconfirmed, so no new order is sent")
        if symbol in self._unverified_live:
            try:
                held = self._verify_live_position(symbol)
            except Exception as exc:
                raise OrderUnconfirmed(f"Kite couldn't confirm the restored position in {symbol} is still open, "
                                       f"so no order is sent: {exc}")
            if held == 0:
                raise OrderNotFilled(f"Kite holds no position in {symbol}; there is nothing to close")
            qty = min(qty, abs(held))
        executor = self._ensure_kite()
        order_id = executor.place_order(symbol, side, qty)
        result = executor.wait_for_fill(order_id)
        if result["status"] == ORDER_UNKNOWN:
            self._unconfirmed_orders[symbol] = {"order_id": order_id, "side": side, "qty": qty, "price": price,
                                                "context": context}
            self.state.log("error", f"Kite hasn't confirmed what happened to the {side} {qty} order ({order_id}). "
                                    f"Nothing is booked and no other order is sent in {symbol} until it does. "
                                    f"Check Kite.", symbol=symbol, level="error")
            raise OrderUnconfirmed(f"order {order_id} is unconfirmed: {result['message'] or 'Kite did not answer'}")
        return self._confirmed_fill(symbol, side, qty, order_id, result)

    def _confirmed_fill(self, symbol, side, qty, order_id, result):
        filled, avg = result["filled_quantity"], result["average_price"]
        if filled <= 0 or avg <= 0:
            self.state.log("error", f"Kite did not fill the {side} {qty} order ({order_id}): {result['status']}"
                                    + (f" — {result['message']}" if result["message"] else "")
                                    + ". Nothing is booked.", symbol=symbol, level="error")
            raise OrderNotFilled(f"Kite {result['status'].lower()} the order"
                                 + (f": {result['message']}" if result["message"] else ""))
        if filled < qty:
            self.state.log("risk", f"Kite filled {filled} of {qty} on the {side} order ({order_id}); the rest was "
                                   f"cancelled. {filled} booked.", symbol=symbol, level="warn")
        return filled, avg, order_id

    def _resolve_unconfirmed_orders(self):
        """Ask Kite again about every order it never confirmed, and book or
        drop each one that has now ended. Called at the start of every tick.
        Never raises."""
        for symbol, pending in list(self._unconfirmed_orders.items()):
            try:
                result = self._ensure_kite().order_state(pending["order_id"])
                if result["status"] not in ORDER_FINAL:
                    continue
                del self._unconfirmed_orders[symbol]
                try:
                    confirmed = self._confirmed_fill(symbol, pending["side"], pending["qty"],
                                                     pending["order_id"], result)
                except OrderNotFilled:
                    if pending.get("fno", {}).get("kind") == "entry":
                        self._journal_fno_eval(pending["fno"], False, f"Kite {result['status'].lower()} the order")
                    continue
                if pending.get("fno"):
                    self._book_fno_fill(pending["fno"], *confirmed)
                    self.state.log("risk", f"Kite confirmed order {pending['order_id']}; it is now booked.",
                                   symbol=pending["fno"]["underlying"], level="warn")
                    continue
                with self.state.lock:
                    was_flat = self.state.positions.get(symbol, {}).get("quantity", 0) == 0
                self._execute(symbol, pending["side"], confirmed[0], pending["price"], confirmed=confirmed,
                              **pending["context"])
                with self.state.lock:
                    pos = self.state.positions[symbol]
                    if was_flat and pos["quantity"] != 0:
                        # The entry path never got to set these: the order raised first.
                        m = _STOP_TARGET_RE.findall(pending["context"].get("note") or "")
                        if m:
                            pos["stop_price"], pos["target_price"] = float(m[-1][0]), float(m[-1][1])
                            pos["initial_risk"] = abs(pos["avg_price"] - pos["stop_price"])
                        pos["position_id"] = pending["context"].get("position_id")
                        self.risk.open_positions_count += 1
                    elif not was_flat and pos["quantity"] == 0:
                        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
                self.state.log("risk", f"Kite confirmed order {pending['order_id']}; it is now booked.",
                               symbol=symbol, level="warn")
            except Exception:
                logger.exception(f"Couldn't resolve the unconfirmed order in {symbol}")

    def _execute(self, symbol, side, qty, price, reason="signal", note=None, checklist_snapshot=None,
                position_id=None, initial_risk=None, confirmed=None, live=None):
        """`confirmed` is a fill Kite has already reported, as (quantity,
        price, order id); it is booked as a live fill and no order is sent.
        `live` says where the order goes; None follows the engine's mode. An
        exit passes the position's own flag, so real money is closed with a
        real order and a paper position never sends one, whatever the mode
        has been switched to since it opened (#156)."""
        if live is None:
            live = not self.state.paper_mode
        # backtester.py has always applied costs.apply_slippage() to every
        # fill; this function — every live and paper trade's one real path
        # — never did, only leg_cost() (brokerage/STT/exchange charges).
        # That broke the "same code, same costs" property the backtester is
        # praised for elsewhere: live/paper P&L (including BEL's first real
        # trade) was silently held to a laxer cost standard than backtested
        # performance is. price stays the raw signal/stop/target price for
        # logging the plan; fill_price is what P&L and the journal actually
        # use, same as backtester.py already does for both entries and exits.
        if confirmed is None and not live:
            fill_price = costs.apply_slippage(side, price, config.COSTS)
            charges = costs.leg_cost(side, fill_price, qty, config.COSTS)
            fill = execute_paper_order(self.state, symbol, side, qty, fill_price, reason=reason, note=note,
                                       charges=charges, checklist_snapshot=checklist_snapshot,
                                       position_id=position_id, initial_risk=initial_risk, signal_price=price)
        else:
            # Live: the quantity and price are Kite's, not the model's (#155).
            qty, fill_price, order_id = confirmed or self._live_fill(
                symbol, side, qty, price,
                {"reason": reason, "note": note, "checklist_snapshot": checklist_snapshot,
                 "position_id": position_id, "initial_risk": initial_risk})
            charges = costs.leg_cost(side, fill_price, qty, config.COSTS)
            fill = self.state.apply_fill(symbol, side, qty, fill_price, charges=charges)
            r_multiple = (fill["net"] / (initial_risk * qty)) if initial_risk and qty else None
            slip_bp = (fill_price - price) / price * 1e4 * (1 if side == "BUY" else -1) if price else 0.0
            note = f"{note + ' — ' if note else ''}Kite filled at {fill_price:.2f}, {slip_bp:+.1f} bp against " \
                   f"the signal price {price:.2f}"
            self.state.record_trade(symbol, side, qty, fill_price, mode="live", reason=reason, note=note,
                                    realized=fill["net"], realized_gross=fill["gross"], charges=charges,
                                    position_id=position_id, initial_risk=initial_risk, r_multiple=r_multiple,
                                    checklist_snapshot=checklist_snapshot, signal_price=price, order_id=order_id)
        with self.state.lock:
            if self.state.positions[symbol]["quantity"] != 0:
                self.state.positions[symbol]["live"] = bool(confirmed or live)
        # net of both legs' charges, so the daily loss limit and the log agree
        # with what the account actually did (issue #21).
        realized = fill["net"]
        if realized:
            self.risk.record_realized_pnl(realized)
        pnl = f" · P&L ₹{realized:,.0f} after ₹{fill['charges_deducted']:,.0f} charges" if realized else ""
        logger.info(f"{reason}: {side} {qty} {symbol} @ {fill_price:.2f}{pnl}")
        self.state.log("trade", f"{side} {qty} @ {fill_price:.2f} ({reason}){pnl}" + (f" — {note}" if note else ""),
                       symbol=symbol, level="trade")
        return realized

    def _square_off_all(self, reason="auto_square_off"):
        """Close every cash position. Goes through _exit_position() like every
        other exit, so a stop firing on the tick thread during the square-off
        can't send a second closing order and flip the position. Returns the
        symbols it closed."""
        closed = []
        for symbol, pos in list(self.state.positions.items()):
            if pos["quantity"] == 0:
                continue
            try:
                price = data_provider.get_ltp(symbol)
            except Exception:
                price = pos["avg_price"]
            if self._exit_position(symbol, price, reason=reason):
                closed.append(symbol)
        return closed

    def set_entries_paused(self, paused: bool, source="dashboard"):
        """Stop (or resume) opening new positions. Open positions keep their
        stops, targets and the square-off either way. Persisted, so a
        restart doesn't quietly resume trading after the owner paused it."""
        with self.state.lock:
            self.state.entries_paused = bool(paused)
        try:
            database.set_control("entries_paused", bool(paused))
        except Exception:
            logger.exception("Couldn't persist the entry pause — it holds until the next restart only")
        self.state.log("risk" if paused else "system",
                       f"New entries {'paused' if paused else 'resumed'} via the {source}",
                       level="warn" if paused else "info")

    def stop_and_flatten(self):
        """The kill switch: pause entries, close every cash and F&O position
        at market, then return to Paper. Positions close while still in the
        current mode, so a live position gets a real closing order before the
        mode flips."""
        self.set_entries_paused(True, source="kill switch")
        self.state.log("risk", "Kill switch — closing every open position now", level="warn")
        closed, failed = [], []
        for symbol in [s for s, p in list(self.state.positions.items()) if p["quantity"]]:
            try:
                closed += self._square_off_all_one(symbol)
            except Exception as exc:
                logger.exception(f"Kill switch couldn't close {symbol}")
                failed.append({"symbol": symbol, "error": str(exc)})
        for underlying in list(self.state.fno_positions.keys()):
            try:
                done = self._close_fno(underlying, "kill_switch")
                if done:
                    closed.append(underlying)
                elif done is False:
                    failed.append({"symbol": underlying, "error": "Kite sold only part of the option position"})
            except Exception as exc:
                logger.exception(f"Kill switch couldn't close F&O {underlying}")
                failed.append({"symbol": underlying, "error": str(exc)})
        self._reflatten_pending = True
        was_live = not self.state.paper_mode
        if not failed:
            with self.state.lock:
                self.state.paper_mode = True
            if was_live:
                self.state.log("system", "Mode switched to PAPER by the kill switch", level="warn")
        else:
            # Leave live mode on: the engine needs it to keep retrying real
            # closing orders, and the owner has to see the failure.
            self.state.log("error", "Kill switch could not close: " +
                           ", ".join(f["symbol"] for f in failed) + " — still LIVE, close these in Kite",
                           level="error")
        return {"closed": closed, "failed": failed, "paper_mode": self.state.paper_mode}

    def live_readiness(self, probe=False):
        """What must be true before real orders are allowed to start. The
        dashboard's confirm() was the only gate: it would go live on a dead
        Kite session (every order then fails) or after today's loss limit was
        already hit. `probe` spends one Kite call to confirm the session."""
        blockers = []
        kite = data_provider.kite_session_status(probe=probe)
        if not kite.get("connected"):
            blockers.append(f"Kite isn't usable: {kite.get('reason') or kite.get('state')}")
        if self.risk.daily_loss_limit_hit():
            blockers.append("Today's daily loss limit is already hit — live trading can start next session")
        if probe and kite.get("connected"):
            # Otherwise the first look at Kite's positions is the capital sync
            # after the switch, and going live isn't held back by them (#156).
            self._check_position_reconciliation()
        if self._untracked_kite_positions:
            blockers.append("Kite holds positions the engine isn't tracking ("
                            + ", ".join(sorted(self._untracked_kite_positions)) + ") — resolve them in Kite first")
        return {"ready": not blockers, "blockers": blockers, "entries_paused": self.state.entries_paused}

    def _square_off_all_one(self, symbol):
        pos = self.state.positions.get(symbol) or {}
        try:
            price = data_provider.get_ltp(symbol)
        except Exception:
            price = pos.get("avg_price")
        return [symbol] if self._exit_position(symbol, price, reason="kill_switch") else []

    def _claim_exit(self, symbol) -> bool:
        """Claim the right to close `symbol`, so exactly one thread sends the
        closing order. The poll loop and the tick stream both watch the same
        stops; without this, one breached stop becomes two full closing orders
        and the position flips instead of going flat. Returns False when
        another thread already holds the claim or the position is already
        flat — in both cases there is nothing for this caller to do."""
        with self.state.lock:
            if symbol in self._exiting:
                return False
            if self.state.positions.get(symbol, {}).get("quantity", 0) == 0:
                return False
            self._exiting.add(symbol)
            return True

    def _release_exit(self, symbol):
        with self.state.lock:
            self._exiting.discard(symbol)

    def _exit_position(self, symbol, ltp, reason, note=None) -> bool:
        """The single way out of a cash position. Everything that closes one —
        a stop, a target, a brain exit, the square-off — goes through
        here so the claim above is never bypassed."""
        if not self._claim_exit(symbol):
            return False
        try:
            with self.state.lock:
                pos = self.state.positions[symbol]
                qty = pos["quantity"]
                position_id, initial_risk = pos.get("position_id"), pos.get("initial_risk")
                live = pos.get("live")
            if qty == 0:
                return False
            self._execute(symbol, "SELL" if qty > 0 else "BUY", abs(qty), ltp, reason=reason,
                          note=note, position_id=position_id, initial_risk=initial_risk, live=live)
            # A live order can fill in part; what is left stays open and watched.
            if self.state.positions[symbol]["quantity"] == 0:
                self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
            return True
        finally:
            self._release_exit(symbol)

    def _check_stop_take(self, symbol, ltp) -> bool:
        """Called by the 30-second poll and, when Kite's tick stream is up, by
        stop_watcher on every tick for a symbol we hold."""
        pos = self.state.positions[symbol]
        qty = pos["quantity"]
        if qty == 0:
            return False
        side = "BUY" if qty > 0 else "SELL"
        sign = 1 if qty > 0 else -1
        atr_val = pos.get("entry_atr")
        stop = pos.get("stop_price") or self.risk.stop_loss_price(pos["avg_price"], side, atr=atr_val)
        target = pos.get("target_price") or self.risk.take_profit_price(pos["avg_price"], side, atr=atr_val)
        hit_stop = (ltp - stop) * sign <= 0
        hit_target = (ltp - target) * sign >= 0
        if not (hit_stop or hit_target):
            self._trail_stop(symbol, pos, ltp, stop, sign)
            return False
        return self._exit_position(symbol, ltp, reason="stop_loss" if hit_stop else "take_profit",
                                   note=f"stop {stop:.2f} / target {target:.2f}")

    def check_stop_from_tick(self, symbol, ltp) -> bool:
        """Entry point for stop_watcher, called on the tick stream's thread.

        Deliberately narrow: it can only ever close a position that is already
        open, and only through the same _check_stop_take() the poll uses, so
        the fast path and the slow path can never disagree about what a stop
        means. Exceptions are swallowed rather than raised, because raising
        would kill the tick stream and take the fast stops down with it."""
        try:
            if self.state.positions.get(symbol, {}).get("quantity", 0) == 0:
                return False
            return self._check_stop_take(symbol, ltp)
        except Exception:
            logger.exception(f"Tick-driven stop check failed for {symbol}")
            return False

    def _trail_stop(self, symbol, pos, ltp, stop, sign):
        """Step trailing stop (Varsity Futures ch 7): after `trail_after_r` R in profit, lock in
        everything beyond that many R, one R at a time."""
        after = config.RISK.get("trail_after_r")
        r = pos.get("initial_risk")
        if not after or not r:
            return
        steps = math.floor((ltp - pos["avg_price"]) * sign / r)
        if steps < after:
            return
        new_stop = pos["avg_price"] + sign * r * (steps - after)
        if (new_stop - stop) * sign > 0:
            with self.state.lock:
                pos["stop_price"] = new_stop
            self.state.log("risk", f"Trailing stop moved to {new_stop:.2f} after a {steps}R move", symbol=symbol)

    def _blocked(self, symbol, setup, why):
        self.state.log("blocked", f"{setup} signal skipped — {why}", symbol=symbol, level="warn")
        return False

    def _close(self, symbol, ltp, reason, note=None):
        self._exit_position(symbol, ltp, reason, note)

    def _entry_block_reason(self, symbol, side):
        """The first rule outside the checklist and the confidence gate that
        stops a new entry, or None. _try_enter() and approve_review() both
        call this, so a manual approval can't slip past a risk limit the
        engine itself would have applied."""
        if self.state.entries_paused:
            return "new entries are paused from the dashboard"
        if symbol in self._untracked_kite_positions:
            return ("Kite shows an untracked open position in this symbol (see the reconciliation "
                    "alert) — entries blocked until that's resolved, to avoid doubling up on real exposure")
        row = self._scan_row(symbol)
        mkt = self.state.market or {}
        reasons_txt = "; ".join(mkt.get("reasons", [])[:2])
        if row and row.get("excluded"):
            return row["excluded"]
        # The scanner sets no side (README §115, audit rule 3.8): its old score
        # was measured to carry no information, so the checklist's own reading
        # picks the side. What remains is tradability.
        if side == "SHORT" and row and row.get("long_only"):
            return "this stock has a fixed price band, so it is long-only: a short caught at the band cannot be covered"
        if side == "SHORT" and not config.SCANNER.get("allow_shorts", True):
            return "shorts are switched off in the scanner settings"
        if side == "LONG" and mkt.get("bias") == "risk-off" and config.MARKET_FILTER["block_new_longs_when_risk_off"]:
            return f"no new longs — market is risk-off ({reasons_txt})"
        if side == "SHORT" and mkt.get("bias") == "risk-on" and config.MARKET_FILTER.get("block_new_shorts_when_risk_on", True):
            return f"no new shorts — market is risk-on ({reasons_txt})"
        if self.risk.daily_loss_limit_hit():
            return "daily loss limit reached"
        if self.risk.open_positions_count >= config.RISK["max_open_positions"]:
            return f"already at the max of {config.RISK['max_open_positions']} open positions"

        # A multi-expert review flagged that max_open_positions alone doesn't stop 3
        # concurrent positions from being the same sector — which the scanner's own
        # sector-momentum ranking makes the *likely* outcome on a strong-trend day,
        # undermining the 2% daily-loss cap's implicit assumption that positions are
        # roughly independent. Cap same-industry concurrent positions too.
        # An open option counts in its underlying's industry (#157).
        max_per_sector = config.RISK.get("max_positions_per_sector")
        industry = self._industry_for(symbol, row)
        if industry and max_per_sector:
            same_sector = sum(
                1 for sym, pos in self.state.positions.items()
                if pos["quantity"] != 0 and self._industry_for(sym, self._scan_row(sym)) == industry
            ) + sum(1 for u in list(self.state.fno_positions) if self._industry_for(u, self._scan_row(u)) == industry)
            if same_sector >= max_per_sector:
                return (f"already at the max of {max_per_sector} open position(s) in "
                        f"{industry} — avoids concentrating risk in one sector")
        return None

    def _try_enter(self, symbol, side, ltp, candles, analysis):
        """side is "LONG" (buy) or "SHORT" (intraday MIS sell, squared off at SQUARE_OFF_TIME).
        Returns True if a real order was placed, False if blocked for any reason —
        _process_symbol() uses this to roll back the entries_today count trader_brain
        already spent on this signal when nothing was actually entered."""
        if self.state.positions[symbol]["quantity"] != 0 or symbol in self._entering:
            return False
        setup = f"{analysis.get('setup', 'Entry')} ({side.lower()})"
        why = self._entry_block_reason(symbol, side)
        if why:
            return self._blocked(symbol, setup, why)

        # Same confidence.py gate F&O already used (config.FNO["min_confidence_to_trade"])
        # now applies to cash equity too: a clean-looking checklist pass means nothing
        # statistically until the Dimaag Scorecard has shown a real, proven edge. Before
        # this, cash equity fired on checklist-pass alone while F&O correctly didn't —
        # the same evidence, gating one instrument and not the other.
        scorecard = database.journal_summary().get("scorecard", [])
        conf = confidence.score_trade(analysis, side, scorecard)
        min_conf = config.RISK.get("min_confidence_to_trade", 60)
        if conf["score"] < min_conf:
            reason = f"confidence {conf['score']}/100 below the {min_conf} bar ({conf['explanation']})"
            if self.review_queue.enabled() and analysis.get("entry_mode") == "checklist":
                try:
                    blocker = {"key": "confidence", "label": f"Confidence at least {min_conf}",
                               "detail": f"{conf['score']}/100 (local setup {conf['local_setup']['score']} × "
                                         f"{conf['system_evidence']['multiplier']:.2f} system evidence)",
                               "value": conf["score"], "need": min_conf}
                    self._offer_review(symbol, side, (analysis.get("checklist") or {}).get(side.lower()),
                                       blocker, ltp, candles, analysis, conf=conf)
                except Exception:
                    logger.exception(f"Review queue: couldn't offer the confidence-blocked {symbol} setup")
            return self._blocked(symbol, setup, reason)

        atr_val = compute_atr(candles, config.RISK.get("atr_period", 14)) if config.RISK.get("use_atr_risk") else None
        plan = None
        if analysis.get("entry_mode") == "checklist":
            plan = (analysis.get("checklist") or {}).get(side.lower())
            if not plan or plan.get("stop") is None:
                plan = None
        live = None
        if plan:
            live = trader_brain.recheck_plan(plan, side.lower(), ltp, self.strategy_params)
            if not live["ok"]:
                return self._blocked(symbol, setup, live["reason"])
        stop_price = plan["stop"] if plan else None
        size_factor = plan["size_factor"] if plan else 1.0
        qty = self.risk.position_size(ltp, atr=atr_val, stop_price=stop_price,
                                      size_factor=self.size_multiplier * size_factor)
        if qty <= 0:
            # Say which of the two reasons it was: a setup the checklist wants
            # taken smaller, or a stock too expensive for the notional cap.
            full = self.risk.position_size(ltp, atr=atr_val, stop_price=stop_price)
            if full > 0:
                return self._blocked(symbol, setup,
                                     f"position size rounds to 0 shares at {self.size_multiplier * size_factor:.0%} size "
                                     f"(full size would be {full}) — a setup the checklist wants smaller isn't "
                                     f"worth taking at full size")
            cap_pct = config.RISK.get("max_position_notional_pct")
            return self._blocked(symbol, setup,
                                 f"position size rounds to 0 shares: at {ltp:,.2f} even one share is more than the "
                                 f"{cap_pct:g}% cap on one position (₹{config.RISK['total_capital'] * cap_pct / 100:,.0f})"
                                 if cap_pct else "position size rounds to 0 shares")

        # Last gate before the order: is the book deep and tight enough to get in
        # and out at the cost everything above assumed? See liquidity.py.
        liq_ok, liq_reason, _ = liquidity.check(symbol, side, qty, ltp, self.state.paper_mode)
        if not liq_ok:
            return self._blocked(symbol, setup, f"liquidity: {liq_reason}")

        if plan:
            bar = (analysis.get("bar_time") or "")[11:16]
            note = (f"Varsity checklist passed on the {bar} candle: stop {plan['stop']:.2f}, target {plan['target']:.2f}, "
                    f"reward-to-risk {live['rrr']:.2f} at the entry price, {size_factor:.0%} size, "
                    f"confidence {conf['score']}/100 ({conf['label']})")
        else:
            key = "reasons" if side == "LONG" else "bear_reasons"
            why = "; ".join(r["text"] for r in analysis.get(key, [])[:3])
            note = f"bull {analysis['bull_score']:.1f} vs bear {analysis['bear_score']:.1f} — {why}, " \
                   f"confidence {conf['score']}/100 ({conf['label']})" if "bull_score" in analysis else \
                   f"confidence {conf['score']}/100 ({conf['label']})"
        position_id = database.new_position_id()
        try:
            self._execute(symbol, "BUY" if side == "LONG" else "SELL", qty, ltp, reason=setup, note=note,
                          checklist_snapshot=analysis.get("checklist"), position_id=position_id)
        except OrderNotFilled as exc:
            return self._blocked(symbol, setup, str(exc))
        except OrderUnconfirmed:
            # An order did go out, so today's entry in this stock stays spent.
            return True
        with self.state.lock:
            pos = self.state.positions[symbol]
            pos["entry_atr"] = atr_val
            pos["stop_price"] = stop_price
            pos["target_price"] = plan["target"] if plan else None
            # Risk per share from the price actually paid, not the signal
            # price: the stop is a chart level and doesn't move with the fill.
            entry = pos["avg_price"]
            pos["initial_risk"] = abs(entry - stop_price) if stop_price else self.risk._stop_distance(entry, atr_val)
            pos["position_id"] = position_id
        self.risk.open_positions_count += 1
        return True

    # ---- manual review queue (review_queue.py) ---------------------------

    def _offer_near_misses(self, symbol, ltp, bars, analysis):
        """Offer a card for each side that failed exactly one required
        checklist item, inside the entry window, on a stock not yet traded today."""
        if analysis.get("entry_mode") != "checklist":
            return
        params = {**trader_brain.DEFAULTS, **self.strategy_params}
        hhmm = (analysis.get("bar_time") or "")[11:16]
        if not hhmm or not trader_brain.entry_window_open(hhmm, params):
            return
        st = self.state.strategy_state.get(symbol) or {}
        if st.get("entries_today", 0) >= params["max_entries_per_day"]:
            return
        for key, side in (("long", "LONG"), ("short", "SHORT")):
            if side == "SHORT" and not params.get("allow_shorts", True):
                continue
            plan = (analysis.get("checklist") or {}).get(key)
            blocker = review_queue.single_blocker(plan)
            if blocker:
                self._offer_review(symbol, side, plan, blocker, ltp, bars, analysis)

    def _offer_review(self, symbol, side, plan, blocker, ltp, bars, analysis, conf=None):
        """Put one card in front of the user, if it could actually be taken:
        the plan has a stop and a target the price hasn't passed, no other
        rule would stop it, and it sizes to at least one share. A card blocked
        on reward-to-risk must also clear the queue's R:R floor at this price;
        one that doesn't is held back instead: journaled and replayed, not
        offered (#166)."""
        q = self.review_queue
        if not q.enabled() or not plan:
            return None
        stop, target = plan.get("stop"), plan.get("target")
        if stop is None or target is None:
            return None
        s = 1 if side == "LONG" else -1
        if (ltp - stop) * s <= 0 or (target - ltp) * s <= 0:
            return None
        params = {**trader_brain.DEFAULTS, **self.strategy_params}
        rrr = trader_brain._net_rrr(ltp, stop, target, params["cost_pct"])
        held = review_queue.floor_reason(blocker, rrr)
        # Cheap checks first: most ticks, this stock and side has nothing new to ask.
        if held:
            if q.held_back(symbol, side):
                return None
        elif not q.can_offer(symbol, side, review_queue.progress(blocker, rrr), analysis.get("bar_time")):
            return None
        if self._entry_block_reason(symbol, side):
            return None
        atr_val = compute_atr(bars, config.RISK.get("atr_period", 14)) if config.RISK.get("use_atr_risk") and bars else None
        qty = self.risk.position_size(ltp, atr=atr_val, stop_price=stop,
                                      size_factor=self.size_multiplier * plan.get("size_factor", 1.0))
        if qty <= 0:
            return None
        if conf is None:
            conf = confidence.score_trade(analysis, side, database.journal_summary().get("scorecard", []))
        card = review_queue.build_card(
            symbol, side, plan, blocker, ltp, params["cost_pct"], qty,
            setup=plan.get("pattern") or analysis.get("setup"),
            confidence={"score": conf["score"], "bar": config.RISK.get("min_confidence_to_trade", 60),
                        "local": conf["local_setup"]["score"],
                        "multiplier": conf["system_evidence"]["multiplier"]},
            mode="paper" if self.state.paper_mode else "live", bar_time=analysis.get("bar_time"))
        card["checklist"] = analysis.get("checklist")
        if held:
            if q.hold(card, held) is not None:
                self.state.log("review", f"{card['setup']} ({side.lower()}) not offered for review: {held}. "
                                         f"{card['money']} Its outcome is still replayed.",
                               symbol=symbol, level="info")
            return None
        if q.add(card) is None:
            return None
        mins = max(1, config.REVIEW_QUEUE["expiry_seconds"] // 60)
        self.state.log("review", f"{card['setup']} ({side.lower()}) is waiting for your decision: it failed only "
                                 f"\"{blocker['label']}\" ({blocker['detail']}). {card['money']} {card['verdict']} "
                                 f"Approve or reject it on the Overview page within {mins} min.",
                       symbol=symbol, level="warn")
        return card

    def _refuse_review(self, review_id, reason, **detail):
        """Close the card as refused, in the journal too, with the reason and
        any numbers behind it (`detail`)."""
        card = self.review_queue.decide(review_id, "refused", outcome={"reason": reason, **detail})
        if card:
            self.state.log("review", f"Your approval of {card['setup']} ({card['side'].lower()}) could not be "
                                     f"placed: {reason}", symbol=card["symbol"], level="info")
        return {"ok": False, "status": "refused", "reason": reason, **detail}

    def reject_review(self, review_id):
        card = self.review_queue.get(review_id)
        if card is None:
            return {"ok": False, "status": None, "reason": "No such review card (it may be from an earlier day)."}
        if card["status"] != "pending":
            return {"ok": False, "status": card["status"], "reason": f"This card is already {card['status']}."}
        self.review_queue.decide(review_id, "rejected")
        self.state.log("review", f"You rejected {card['setup']} ({card['side'].lower()}).", symbol=card["symbol"])
        return {"ok": True, "status": "rejected"}

    def approve_review(self, review_id, confirm_live=False):
        """The user's Approve click. Overrides only the card's blocker and the
        confidence gate: every other entry rule is re-checked here, at the
        live price, and the order goes through the same _execute() path as
        any engine entry. A card blocked on reward-to-risk must clear the R:R
        floor again at the live price (#211). In live mode it needs
        confirm_live=True."""
        card = self.review_queue.get(review_id)
        if card is None:
            return {"ok": False, "status": None, "reason": "No such review card (it may be from an earlier day)."}
        if card["status"] != "pending":
            return {"ok": False, "status": card["status"], "reason": f"This card is already {card['status']}."}
        if review_queue.now_ist().timestamp() > card["expires_ts"]:
            self.review_queue.decide(review_id, "expired")
            return {"ok": False, "status": "expired",
                    "reason": "This card expired — the price has moved since it was offered."}
        if not self.state.paper_mode and not confirm_live:
            return {"ok": False, "status": "pending",
                    "reason": "Live mode: approving places a REAL Kite order. It needs your explicit "
                              "real-money confirmation."}
        symbol = card["symbol"]
        with self.state.lock:
            pos = self.state.positions.get(symbol)
            busy = pos is None or pos["quantity"] != 0 or symbol in self._entering
            if not busy:
                self._entering.add(symbol)
        if busy:
            return self._refuse_review(review_id, "this stock is no longer tracked, already has an open position, "
                                                  "or is being entered right now")
        try:
            return self._approve_claimed(card)
        finally:
            with self.state.lock:
                self._entering.discard(symbol)

    def _approve_claimed(self, card):
        symbol, side, review_id = card["symbol"], card["side"], card["id"]
        s = 1 if side == "LONG" else -1
        params = {**trader_brain.DEFAULTS, **self.strategy_params}
        if self.state.market_status != "open":
            return self._refuse_review(review_id, "the market isn't open")
        now = review_queue.now_ist()
        if not trader_brain.entry_window_open(now.strftime("%H:%M"), params):
            return self._refuse_review(review_id, f"outside the entry window ({params['no_entry_before']}–"
                                                  f"{params['last_entry_time']})")
        today = now.date().isoformat()
        st = self.state.strategy_state.get(symbol) or {}
        taken = st.get("entries_today", 0) if st.get("entry_day") in (None, today) else 0
        if taken >= params["max_entries_per_day"]:
            return self._refuse_review(review_id, "this stock was already traded today (one entry per stock per day)")
        why = self._entry_block_reason(symbol, side)
        if why:
            return self._refuse_review(review_id, why)
        try:
            ltp = data_provider.get_ltp(symbol)
        except Exception as exc:
            return self._refuse_review(review_id, f"couldn't read a live price ({exc})")
        stop, target = card["stop"], card["target"]
        if (ltp - stop) * s <= 0:
            return self._refuse_review(review_id, f"the price {ltp:.2f} has already passed the stop {stop:.2f}")
        if (target - ltp) * s <= 0:
            return self._refuse_review(review_id, f"the price {ltp:.2f} has already reached the target {target:.2f}")
        # The same round-trip cost the offer deducted, so the R:R here and on
        # the card differ only by the price.
        cost_pct = card["cost_pct"] if card.get("cost_pct") is not None else params["cost_pct"]
        rrr = trader_brain._net_rrr(ltp, stop, target, cost_pct)
        # The offer held an R:R card to the floor at its own price; a price that
        # has since moved toward the target can leave the fill below it (#211).
        below = review_queue.floor_reason(card["blocker"], rrr, at=f"at the live price {ltp:.2f}")
        if below:
            was = f" (it was {card['net_rrr']:.2f} at the offer)" if card.get("net_rrr") is not None else ""
            return self._refuse_review(review_id, below + was, net_rrr_live=round(rrr, 3), live_price=round(ltp, 2))
        candles = self.state.candles.get(symbol) or []
        atr_val = compute_atr(candles, config.RISK.get("atr_period", 14)) \
            if config.RISK.get("use_atr_risk") and candles else None
        qty = self.risk.position_size(ltp, atr=atr_val, stop_price=stop,
                                      size_factor=self.size_multiplier * card.get("size_factor", 1.0))
        if qty <= 0:
            return self._refuse_review(review_id, "the position sizes to 0 shares at the live price")
        liq_ok, liq_reason, _ = liquidity.check(symbol, side, qty, ltp, self.state.paper_mode)
        if not liq_ok:
            return self._refuse_review(review_id, f"liquidity: {liq_reason}")

        b = card["blocker"]
        note = (f"Manually approved — overrode \"{b['label']}\" ({b['detail']}). Stop {stop:.2f}, "
                f"target {target:.2f}, reward-to-risk {rrr:.2f} at the entry price. The confidence gate was not applied.")
        position_id = database.new_position_id()
        try:
            self._execute(symbol, "BUY" if side == "LONG" else "SELL", qty, ltp,
                          reason=f"{card['setup']} ({side.lower()}, manual approval)", note=note,
                          checklist_snapshot=card.get("checklist"), position_id=position_id)
        except Exception as exc:
            logger.exception(f"Manual approval of {symbol} failed at the order")
            self.review_queue.decide(review_id, "failed", outcome={"reason": str(exc)})
            self.state.log("error", f"Your approved {side.lower()} in {symbol} was not placed: {exc}",
                           symbol=symbol, level="error")
            return {"ok": False, "status": "failed", "reason": f"the order failed: {exc}"}
        with self.state.lock:
            pos = self.state.positions[symbol]
            pos["entry_atr"] = atr_val
            pos["stop_price"] = stop
            pos["target_price"] = target
            pos["initial_risk"] = abs(pos["avg_price"] - stop)
            pos["position_id"] = position_id
            fill_price, qty = pos["avg_price"], abs(pos["quantity"])
            st = self.state.strategy_state.get(symbol)
            if not isinstance(st, dict):
                st = {}
                self.state.strategy_state[symbol] = st
            st["entries_today"], st["entry_day"] = taken + 1, today
        self.risk.open_positions_count += 1
        outcome = {"fill_price": round(fill_price, 2), "qty": qty, "net_rrr_at_fill": round(rrr, 2),
                   "mode": "paper" if self.state.paper_mode else "live"}
        self.review_queue.decide(review_id, "approved", position_id=position_id, outcome=outcome)
        return {"ok": True, "status": "approved", "position_id": position_id, **outcome}

    # ---- F&O (options-buying only — see fno_risk.py) ---------------------

    def _fno_active(self) -> bool:
        return bool(config.FNO.get("enabled")) and fno_instruments.available()

    def _fno_underlyings(self):
        explicit = config.FNO.get("underlyings") or []
        if explicit:
            return explicit
        return list((self.state.scanner or {}).get("active", []))

    def _fno_live(self, pos):
        """Whether an option position is real money: its own flag, set by the
        order that opened it, else the engine's mode (#187, as #156 for cash)."""
        live = pos.get("live")
        return (not self.state.paper_mode) if live is None else bool(live)

    def _record_fno_trade(self, symbol, side, quantity, price, reason, note, realized, position_id,
                          initial_risk, checklist_snapshot=None, charges=0.0, realized_gross=None,
                          live=None, signal_price=None, order_id=None):
        """One F&O leg. Same convention as the equity path (#21, #35): each row
        carries its own leg's charges; on the exit row `realized` is NET of both
        legs' charges and `realized_gross` is before them, so the daily loss
        limit, the journal and the F&O confidence IC all see net figures. A live
        leg carries the quoted premium it was sent at and Kite's order id (#186)."""
        r_multiple = (realized / (initial_risk * quantity)) if realized is not None and initial_risk and quantity else None
        if live is None:
            live = not self.state.paper_mode
        trade = {
            "id": database.new_position_id(), "position_id": position_id, "ts": time.time(),
            "symbol": symbol, "side": side, "quantity": quantity, "price": price, "mode": "live" if live else "paper",
            "reason": reason, "note": note, "realized": realized,
            "realized_gross": realized_gross if realized_gross is not None else realized,
            "charges": charges, "initial_risk": initial_risk, "r_multiple": r_multiple,
            "signal_price": signal_price, "order_id": order_id,
        }
        database.record_trade(trade, checklist_snapshot=checklist_snapshot)
        with self.state.lock:
            self.state.trades.insert(0, trade)
        if realized:
            self.risk.record_realized_pnl(realized)
            with self.state.lock:
                self.state.realized_pnl_today += realized
        self.state.log("trade", f"[F&O] {side} {quantity} {symbol} @ {price:.2f} ({reason})"
                       + (f" — {note}" if note else ""), symbol=symbol, level="trade")
        return r_multiple

    def _fno_ltp(self, tradingsymbol, live=None):
        """Kite's premium for a live position. None for a paper one: there is
        no paper data feed for premiums, so it is repriced by _paper_fno_premium()."""
        if live is None:
            live = not self.state.paper_mode
        if not live:
            return None
        return self._ensure_kite().get_fno_ltp(tradingsymbol)

    def _paper_fno_premium(self, pos):
        """Paper premium for an open position, or None when it can't be priced
        this tick. A MODEL price, not a market price: Black-Scholes at the entry
        IV on the live underlying spot. It ignores changes in implied volatility
        and the bid-ask spread (#154). An index's spot is read under its quote
        name (data_provider.kite_quote_key, #189)."""
        try:
            expiry = datetime.strptime(pos["expiry"], "%Y-%m-%d").date()
            t_years = max((expiry - datetime.now(IST).date()).days, 1) / 365
            strike, vol = pos["strike"], pos["entry_iv"]
            spot = data_provider.get_ltp(pos["underlying"])
            if not spot or spot <= 0:
                raise ValueError(f"spot {spot!r}")
            premium = options_pricing.price(spot, strike, t_years, vol,
                                            config.FNO["risk_free_rate_pct"] / 100, pos["is_call"])
        except Exception as exc:
            if not pos.get("reprice_failure_logged"):
                pos["reprice_failure_logged"] = True
                self.state.log("risk", f"[F&O] can't reprice {pos.get('tradingsymbol')} ({exc}) — stop and target "
                               "are not checked until the underlying's price is readable again",
                               symbol=pos.get("underlying"), level="warn")
            return None
        pos["reprice_failure_logged"] = False
        return round(premium, 2)

    # -- live NFO orders (#186) --

    def _fno_order_pending(self, underlying):
        return any((p.get("fno") or {}).get("underlying") == underlying for p in self._unconfirmed_orders.values())

    def _live_fno_fill(self, underlying, tradingsymbol, side, lots, lot_size, context):
        """_live_fill() for an NFO order: send it, wait for Kite's answer, and
        return what Kite executed as (filled quantity, average premium, order
        id). Before #186 the engine ignored the order id and booked the premium
        quoted before the order, so a rejected option order became a position.

        Raises OrderNotFilled when Kite confirms nothing traded, and
        OrderUnconfirmed when the outcome can't be read. An unconfirmed order
        is kept in _unconfirmed_orders under the contract, with `context` to
        book it later, and the underlying takes no other option order until
        _resolve_unconfirmed_orders() has settled it."""
        if self._fno_order_pending(underlying):
            raise OrderUnconfirmed(f"an option order on {underlying} is still unconfirmed, so no new order is sent")
        qty = lots * lot_size
        executor = self._ensure_kite()
        order_id = executor.place_fno_order(tradingsymbol, side, lots, lot_size)
        result = executor.wait_for_fill(order_id)
        if result["status"] == ORDER_UNKNOWN:
            self._unconfirmed_orders[tradingsymbol] = {"order_id": order_id, "side": side, "qty": qty,
                                                       "price": context.get("signal_price"), "fno": context}
            self.state.log("error", f"[F&O] Kite hasn't confirmed what happened to the {side} {qty} {tradingsymbol} "
                                    f"order ({order_id}). Nothing is booked and no other option order is sent on "
                                    f"{underlying} until it does. Check Kite.", symbol=underlying, level="error")
            raise OrderUnconfirmed(f"order {order_id} is unconfirmed: {result['message'] or 'Kite did not answer'}")
        return self._confirmed_fill(tradingsymbol, side, qty, order_id, result)

    def _book_fno_fill(self, ctx, filled, premium, order_id):
        """Book an option order Kite confirmed after the fact."""
        if ctx["kind"] == "entry":
            # today's entry on the underlying was spent when the order went out
            booked = self._book_fno_entry(ctx, filled, premium, order_id)
            self._journal_fno_eval(ctx, booked, None if booked else f"Kite filled {filled}, less than one lot")
            return
        pos = self.state.fno_positions.get(ctx["underlying"])
        if not pos or pos.get("position_id") != ctx["position_id"]:
            self.state.log("error", f"[F&O] Kite confirmed a sale of {filled} (order {order_id}) for a position the "
                                    f"engine no longer holds. Nothing is booked. Check Kite.",
                           symbol=ctx["underlying"], level="error")
            return
        self._book_fno_exit(ctx["underlying"], filled, premium, ctx["reason"], ctx.get("note"),
                            signal_price=ctx.get("signal_price"), order_id=order_id)

    def _verify_live_fno(self, underlying, kite_positions=None):
        """_verify_live_position() for a restored live option position (#187):
        before any order is sent for it, bring it in line with Kite's day
        book. Kite flat: dropped, no order. Kite smaller: cut to Kite's lots.
        Anything else: left alone and reported. Raises if Kite can't be read."""
        if kite_positions is None:
            kite_positions = {p["tradingsymbol"]: p for p in self._ensure_kite().get_positions()}
        with self.state.lock:
            pos = self.state.fno_positions.get(underlying)
            self._unverified_live_fno.discard(underlying)
            if pos is None:
                return 0
            ts, lot = pos["tradingsymbol"], pos["lot_size"]
            ours = pos["lots"] * lot
            held = int((kite_positions.get(ts) or {}).get("quantity") or 0)
            if held == 0:
                self.state.fno_positions.pop(underlying, None)
                self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
            elif lot <= held < ours:
                pos["entry_charges"] = (pos.get("entry_charges") or 0.0) * (held // lot * lot) / ours
                pos["lots"] = held // lot
        if held == 0:
            self.state.log("error", f"Kite shows no open position in {ts}, but today's journal has an open live "
                                    f"option leg of {ours}. It was closed outside the engine. The engine has stopped "
                                    f"watching it and sent no order; its exit is not in the journal.",
                           symbol=underlying, level="error")
        elif held != ours:
            self.state.log("error", f"Kite holds {held:+d} of {ts}; today's journal says {ours:+d}. "
                                    + (f"The engine now watches {held // lot * lot}." if lot <= held < ours
                                       else "The engine keeps watching its own figure. Check Kite."),
                           symbol=underlying, level="error")
        else:
            self.state.log("risk", f"Kite confirms the restored live option position {ts} ({held:+d}).",
                           symbol=underlying)
        return held

    # -- booking --

    def _journal_fno_eval(self, ctx, executed, block_reason=None):
        try:
            database.record_fno_evaluation(ctx["underlying"], ctx["side"], ctx.get("conf") or {}, executed,
                                           block_reason)
        except Exception:
            logger.exception(f"Failed to journal F&O evaluation for {ctx['underlying']}")

    def _book_fno_entry(self, ctx, filled, premium, order_id=None):
        """Open the position at the premium actually paid: Kite's average for a
        live buy, the quoted or model premium for a paper one. The premium stop
        and target, the max loss and the entry Greeks are all worked out from
        it, since they are defined on the premium paid."""
        cfg = config.FNO
        contract, underlying, side, is_call = ctx["contract"], ctx["underlying"], ctx["side"], ctx["is_call"]
        lot_size, live, quoted = contract["lot_size"], ctx["live"], ctx.get("signal_price")
        lots = filled // lot_size
        if filled % lot_size:
            self.state.log("error", f"[F&O] Kite filled {filled} of {contract['tradingsymbol']}, not a whole number "
                                    f"of lots of {lot_size}. The engine watches {lots * lot_size}. Check Kite.",
                           symbol=underlying, level="error")
        if lots <= 0:
            return False
        qty = lots * lot_size
        expiry = date.fromisoformat(ctx["expiry"])
        t_years = max((expiry - datetime.now(IST).date()).days, 1) / 365
        exits = fno_risk.stop_and_target_premium(premium, cfg["stop_loss_pct_of_premium"], cfg["target_pct_of_premium"])
        max_loss = fno_risk.max_loss(premium, lots, lot_size)
        entry_greeks = options_pricing.analyze(premium, ctx["spot"], contract["strike"], t_years,
                                               cfg["risk_free_rate_pct"] / 100, is_call)
        conf = ctx["conf"]
        note = (f"{'Call' if is_call else 'Put'} bought on a {side.lower()} signal, confidence {conf['score']}/100 "
                f"({conf['label']}). Max loss capped at ₹{max_loss:,.0f} (the premium paid) — "
                f"stop {exits['stop_premium']:.2f}, target {exits['target_premium']:.2f}.")
        if live and quoted:
            note += (f" Kite filled at {premium:.2f}, {(premium - quoted) / quoted * 1e4:+.1f} bp against the "
                     f"quoted premium {quoted:.2f}.")
        entry_charges = costs.leg_cost("BUY", premium, qty, costs.FNO_OPTION_COSTS)
        position_id = ctx["position_id"]
        self._record_fno_trade(contract["tradingsymbol"], "BUY", qty, premium, f"fno_{side.lower()}", note, None,
                               position_id, None, checklist_snapshot=ctx.get("checklist"), charges=entry_charges,
                               live=live, signal_price=quoted if live else None, order_id=order_id)
        pos = {
            "tradingsymbol": contract["tradingsymbol"], "underlying": underlying, "is_call": is_call,
            "strike": contract["strike"], "expiry": ctx["expiry"],
            "lots": lots, "lot_size": lot_size, "entry_lots": lots, "entry_premium": premium,
            "stop_premium": exits["stop_premium"], "target_premium": exits["target_premium"],
            "ltp": premium, "unrealized_pnl": 0.0, "confidence": conf, "entry_greeks": entry_greeks,
            "entry_charges": entry_charges, "realized_so_far": 0.0, "live": live,
            # the vol the paper premium was priced at; _paper_fno_premium reprices with it
            "entry_iv": (entry_greeks.get("iv_pct") or 0) / 100 or None if live else fno_risk.PAPER_VOL,
            "max_loss": max_loss, "position_id": position_id,
        }
        with self.state.lock:
            self.state.fno_positions[underlying] = pos
        self.risk.open_positions_count += 1
        try:
            database.record_fno_entry(position_id, pos)
        except Exception:
            logger.exception(f"Failed to journal F&O entry for {underlying}")
        return True

    def _book_fno_exit(self, underlying, filled, premium, reason, note=None, signal_price=None, order_id=None):
        """Book a sale of `filled` units at `premium`. Net of both legs'
        charges: the entry charges are released in proportion to what was
        sold. A part-filled live exit leaves the rest open and watched; the
        fno_trades row gets its exit once nothing is left, with the realized
        figure of every exit leg. Returns True when the position is closed."""
        with self.state.lock:
            pos = self.state.fno_positions.get(underlying)
        if not pos:
            return True
        lot_size = pos["lot_size"]
        held = pos["lots"] * lot_size
        qty = min(filled, held)
        live = self._fno_live(pos)
        gross = (premium - pos["entry_premium"]) * qty
        entry_charges = pos.get("entry_charges")
        if entry_charges is None:
            entry_charges = costs.leg_cost("BUY", pos["entry_premium"], held, costs.FNO_OPTION_COSTS)
        entry_share = entry_charges * qty / held if held else 0.0
        exit_charges = costs.leg_cost("SELL", premium, qty, costs.FNO_OPTION_COSTS)
        realized = gross - entry_share - exit_charges
        if live and signal_price:
            note = ((note + "; ") if note else "") + (
                f"Kite filled at {premium:.2f}, {(signal_price - premium) / signal_price * 1e4:+.1f} bp against the "
                f"quoted premium {signal_price:.2f}")
        self._record_fno_trade(pos["tradingsymbol"], "SELL", qty, premium, reason, note, realized,
                               pos["position_id"], pos["entry_premium"], charges=exit_charges,
                               realized_gross=gross, live=live, signal_price=signal_price if live else None,
                               order_id=order_id)
        left = held - qty
        if left >= lot_size:
            with self.state.lock:
                pos["lots"] = left // lot_size
                pos["entry_charges"] = entry_charges - entry_share
                pos["realized_so_far"] = pos.get("realized_so_far", 0.0) + realized
            self.state.log("risk", f"[F&O] Kite sold {qty} of {held} {pos['tradingsymbol']}; the other {left} are "
                                   f"still open and watched.", symbol=underlying, level="warn")
            return False
        if left > 0:
            self.state.log("error", f"[F&O] Kite left {left} of {pos['tradingsymbol']} unsold, less than one lot of "
                                    f"{lot_size}. The engine has stopped watching it. Check Kite.",
                           symbol=underlying, level="error")
        total = pos.get("realized_so_far", 0.0) + realized
        entry_qty = (pos.get("entry_lots") or pos["lots"]) * lot_size
        r_total = total / (pos["entry_premium"] * entry_qty) if pos["entry_premium"] and entry_qty else None
        try:
            database.record_fno_exit(pos["position_id"], premium, reason, total, r_total)
        except Exception:
            logger.exception(f"Failed to journal F&O exit for {underlying}")
        with self.state.lock:
            self.state.fno_positions.pop(underlying, None)
        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)
        self._last_errors.pop(f"F&O:{underlying}", None)
        return True

    # -- exits --

    def _claim_fno_exit(self, underlying):
        """_claim_exit() for an option: the kill switch runs on the API thread
        and the square-off on the engine's, and two closing orders would sell
        the position twice."""
        key = f"F&O:{underlying}"
        with self.state.lock:
            if key in self._exiting or underlying not in self.state.fno_positions:
                return None
            self._exiting.add(key)
            return key

    def _close_fno(self, underlying, reason, note=None):
        """Close an option position: a real SELL for a live one, booked at
        Kite's executed premium (#186); a model premium for a paper one.
        Returns True when it is closed, False when Kite sold only part of it,
        None when there was nothing to do. A live sale Kite rejects or never
        confirms raises OrderNotFilled / OrderUnconfirmed, and the position
        stays open and watched."""
        key = self._claim_fno_exit(underlying)
        if key is None:
            return None
        try:
            pos = self.state.fno_positions[underlying]
            qty = pos["lots"] * pos["lot_size"]
            if not self._fno_live(pos):
                ltp = self._paper_fno_premium(pos)
                if ltp is None:
                    ltp = pos.get("ltp") or pos["entry_premium"]
                    note = ((note + "; ") if note else "") + (
                        f"no fresh underlying price at exit, booked at the last repriced premium {ltp:.2f}")
                return self._book_fno_exit(underlying, qty, ltp, reason, note)
            if underlying in self._unverified_live_fno:
                try:
                    self._verify_live_fno(underlying)
                except Exception as exc:
                    raise OrderUnconfirmed(f"Kite couldn't confirm the restored option position on {underlying} is "
                                           f"still open, so no order is sent: {exc}")
                pos = self.state.fno_positions.get(underlying)
                if pos is None:
                    return True     # Kite holds none: nothing to sell
                qty = pos["lots"] * pos["lot_size"]
            try:
                quoted = self._fno_ltp(pos["tradingsymbol"], live=True)
            except Exception as exc:
                logger.warning(f"[F&O] no quote for {pos['tradingsymbol']} before its exit: {exc}")
                quoted = None
            quoted = quoted or pos.get("ltp") or pos["entry_premium"]
            ctx = {"kind": "exit", "underlying": underlying, "reason": reason, "note": note,
                   "signal_price": quoted, "position_id": pos["position_id"]}
            filled, premium, order_id = self._live_fno_fill(underlying, pos["tradingsymbol"], "SELL", pos["lots"],
                                                            pos["lot_size"], ctx)
            return self._book_fno_exit(underlying, filled, premium, reason, note, signal_price=quoted,
                                       order_id=order_id)
        finally:
            with self.state.lock:
                self._exiting.discard(key)

    def _check_fno_stop_take(self, underlying):
        pos = self.state.fno_positions.get(underlying)
        if not pos:
            return False
        live = self._fno_live(pos)
        ltp = self._fno_ltp(pos["tradingsymbol"], live=True) if live else self._paper_fno_premium(pos)
        if ltp is None:
            return False
        with self.state.lock:
            pos["ltp"] = ltp
            pos["unrealized_pnl"] = (ltp - pos["entry_premium"]) * pos["lots"] * pos["lot_size"]
        try:
            if ltp <= pos["stop_premium"]:
                self._close_fno(underlying, "fno_stop_loss",
                                f"premium fell to {ltp:.2f} (stop {pos['stop_premium']:.2f})")
                return True
            if ltp >= pos["target_premium"]:
                self._close_fno(underlying, "fno_take_profit",
                                f"premium rose to {ltp:.2f} (target {pos['target_premium']:.2f})")
                return True
        except (OrderNotFilled, OrderUnconfirmed) as exc:
            self._fno_error(underlying, f"[F&O] couldn't close {pos['tradingsymbol']}: {exc}. It is still open "
                                        f"and watched.")
            return False
        return False

    def _fno_error(self, underlying, message):
        """An F&O order failure for the live log, once per distinct message,
        as _process_symbol() does for a cash symbol: the square-off retries
        every tick for 20 minutes."""
        key = f"F&O:{underlying}"
        if self._last_errors.get(key) != message:
            self._last_errors[key] = message
            self.state.log("error", message, symbol=underlying, level="error")

    # -- entries --

    def _entries_today(self, symbol):
        today = datetime.now(IST).date().isoformat()
        st = self.state.strategy_state.get(symbol) or {}
        return st.get("entries_today", 0) if st.get("entry_day") in (None, today) else 0

    def _spend_entry(self, symbol):
        """Count an option entry against its underlying's one-entry-per-day cap
        (ENT-07), the same counter a cash entry and a review approval use."""
        today = datetime.now(IST).date().isoformat()
        with self.state.lock:
            st = self.state.strategy_state.get(symbol)
            if not isinstance(st, dict):
                st = {}
                self.state.strategy_state[symbol] = st
            taken = st.get("entries_today", 0) if st.get("entry_day") in (None, today) else 0
            st["entries_today"], st["entry_day"] = taken + 1, today

    def _fno_entry_block_reason(self, underlying, side):
        """The cash entry rules an option buy must also pass (#157), or None.
        A call is a LONG and a put a SHORT for every rule. Applies the
        one-entry-per-stock-per-day cap on the underlying (shared with cash),
        then all of _entry_block_reason() on the underlying: the pause, an
        untracked Kite position in the stock, the scanner's exclusion and
        short limits, the market bias, the daily loss limit, the open-position cap and
        the sector cap (which counts cash and option positions together).
        Then an untracked Kite position in any contract on the underlying."""
        params = {**trader_brain.DEFAULTS, **self.strategy_params}
        taken = self._entries_today(underlying)
        if taken >= params["max_entries_per_day"]:
            return f"{underlying} was already traded today (one entry per stock per day, cash and F&O together)"
        why = self._entry_block_reason(underlying, side)
        if why:
            return why
        untracked = sorted(s for s in self._untracked_kite_positions if fno_risk.contract_on(s, underlying))
        if untracked:
            return (f"Kite shows an untracked open position in {', '.join(untracked)} (see the reconciliation "
                    f"alert) — entries blocked until that's resolved, to avoid doubling up on real exposure")
        return None

    def _try_enter_fno(self, underlying, side, analysis):
        """Buy a call on a LONG signal or a put on a SHORT one. Returns True
        when an order was placed (or a paper position opened)."""
        cfg = config.FNO
        if underlying in self.state.fno_positions or self._fno_order_pending(underlying):
            return False  # one open contract per underlying at a time; an unconfirmed order counts as one
        conf = {}

        def log_eval(executed, block_reason=None):
            self._journal_fno_eval({"underlying": underlying, "side": side, "conf": conf}, executed, block_reason)

        why = self._fno_entry_block_reason(underlying, side)
        if why:
            self._blocked(underlying, "F&O entry", why)
            log_eval(False, why)
            return False

        scorecard = database.journal_summary().get("scorecard", [])
        conf = confidence.score_trade(analysis, side, scorecard)
        if conf["score"] < cfg["min_confidence_to_trade"]:
            reason = f"confidence {conf['score']}/100 below the {cfg['min_confidence_to_trade']} bar"
            self.state.log("blocked", f"F&O {side} skipped — {reason} ({conf['explanation']})",
                           symbol=underlying, level="warn")
            log_eval(False, reason)
            return False

        # NSE's MWPL ban (FNO-08), read from the same list as the scanner's ban
        # guard. Checked before any contract lookup, quote or order. While the
        # list can't be fetched, this returns at once until the retry time (#212).
        ban = nse_feed.fno_ban_list()
        unknown_why = nse_feed.failure_text(nse_feed.last_failure(nse_feed.FNO_BAN_URL)) if ban is None else ""
        mwpl = fno_risk.mwpl_block_reason(underlying, ban, datetime.now(IST).date().isoformat(),
                                          cfg["index_underlyings"], unknown_why=unknown_why)
        if mwpl:
            self._blocked(underlying, "F&O entry", mwpl)
            log_eval(False, mwpl)
            return False

        is_call = side == "LONG"
        live = not self.state.paper_mode
        expiry = fno_instruments.nearest_expiry(
            underlying, cfg["min_days_to_expiry"], cfg["max_days_to_expiry"],
            prefer_weekly=cfg["prefer_weekly_for_index"] and underlying in cfg["index_underlyings"])
        if not expiry:
            self._blocked(underlying, "F&O entry", "no listed expiry in the configured day-range")
            log_eval(False, "no listed expiry in range")
            return False
        spot = analysis.get("ltp") or self.state.indicators.get(underlying, {}).get("ltp")
        if not spot:
            log_eval(False, "no live spot price")
            return False

        def delta_at_strike(spot_, strike_, t_years_, is_call_):
            return options_pricing.greeks(spot_, strike_, t_years_, fno_risk.PAPER_VOL,
                                          cfg["risk_free_rate_pct"] / 100, is_call_)["delta"]

        contract = fno_instruments.find_contract(underlying, spot, expiry, is_call, cfg["target_delta"], delta_at_strike)
        if not contract:
            self._blocked(underlying, "F&O entry", "no matching strike found for this expiry")
            log_eval(False, "no matching strike")
            return False

        t_years = max((expiry - datetime.now(IST).date()).days, 1) / 365
        premium = self._fno_ltp(contract["tradingsymbol"], live=live)
        if premium is None:
            if not live:
                premium = options_pricing.price(spot, contract["strike"], t_years, fno_risk.PAPER_VOL,
                                                cfg["risk_free_rate_pct"] / 100, is_call)
            else:
                self._blocked(underlying, "F&O entry", "could not fetch a live premium quote")
                log_eval(False, "no live premium quote")
                return False
        if not premium or premium <= 0:
            log_eval(False, "non-positive premium")
            return False

        lots = fno_risk.lots_to_buy(cfg["capital"], cfg["max_premium_risk_pct"], premium, contract["lot_size"])
        if lots <= 0:
            reason = (f"premium {premium:.2f} x lot {contract['lot_size']} too large for the "
                      f"{cfg['max_premium_risk_pct']}% of ₹{cfg['capital']:,.0f} F&O allocation")
            self._blocked(underlying, "F&O entry", reason)
            log_eval(False, reason)
            return False

        # Last gate before the order, as for cash: can the contract be bought
        # and sold at this size without paying away the premium stop? (#157)
        qty = lots * contract["lot_size"]
        liq_ok, liq_reason, _ = liquidity.check_option(contract["tradingsymbol"], qty, premium, not live)
        if not liq_ok:
            reason = f"liquidity: {liq_reason}"
            self._blocked(underlying, "F&O entry", reason)
            log_eval(False, reason)
            return False

        ctx = {"kind": "entry", "underlying": underlying, "side": side, "contract": contract,
               "expiry": expiry.isoformat(), "is_call": is_call, "spot": spot, "conf": conf,
               "checklist": analysis.get("checklist"), "signal_price": premium, "live": live,
               "position_id": database.new_position_id()}
        if live:
            try:
                filled, premium, order_id = self._live_fno_fill(underlying, contract["tradingsymbol"], "BUY", lots,
                                                                contract["lot_size"], ctx)
            except OrderNotFilled as exc:
                self._blocked(underlying, "F&O entry", str(exc))
                log_eval(False, str(exc))
                return False
            except OrderUnconfirmed:
                # An order did go out, so today's entry in this stock stays
                # spent; the evaluation is journaled when Kite answers.
                self._spend_entry(underlying)
                return True
        else:
            filled, order_id = qty, None
        self._spend_entry(underlying)
        booked = self._book_fno_entry(ctx, filled, premium, order_id)
        log_eval(booked, None if booked else f"Kite filled {filled}, less than one lot")
        return True

    def _process_fno(self):
        """Open option positions are watched whether or not F&O is switched
        on: the switch is in memory, so a restart turns it off with a
        restored position still open (#187). New entries need it on, and
        act only on this tick's edge-triggered signals (#157)."""
        signals, self._fno_signals = self._fno_signals, {}
        for underlying in list(self.state.fno_positions.keys()):
            try:
                self._check_fno_stop_take(underlying)
            except Exception:
                logger.exception(f"F&O stop/target check failed for {underlying}")
        if not self._fno_active():
            return
        allowed = set(self._fno_underlyings())
        for underlying, side in signals.items():
            if underlying not in allowed:
                continue
            analysis = self.state.strategy_state.get(underlying)
            if not analysis or "bull_score" not in analysis:
                continue
            try:
                self._try_enter_fno(underlying, side, analysis)
            except Exception:
                logger.exception(f"F&O entry check failed for {underlying}")

    def _note_forming_setup(self, symbol, prev, analysis):
        if not analysis or "bull_score" not in analysis or analysis.get("long_ok") or analysis.get("short_ok"):
            return
        near = analysis["entry_threshold"] - 1.5
        waiting = analysis["blockers"][0] if analysis.get("blockers") else "confirmation"
        for key, side in (("bull_score", "long"), ("bear_score", "short")):
            if side == "short" and not analysis.get("shorts_enabled", True):
                continue
            old = (prev or {}).get(key)
            if analysis[key] >= near and (old is None or old < near):
                self.state.log(
                    "setup",
                    f"{analysis['setup']} forming ({side}) — {key.split('_')[0]} {analysis[key]:.1f}/"
                    f"{analysis['entry_threshold']:g}; waiting on: {waiting}",
                    symbol=symbol,
                )

    def _process_symbol(self, symbol, candles=None, now=None):
        # candles is normally pre-fetched in bulk by _tick_impl() (see
        # data_provider.get_candles_batch); falling back to a single-symbol
        # fetch here keeps this method callable on its own (tests, and any
        # symbol the batch fetch happened to skip or fail on). `now` should be
        # taken before the fetch (see data_provider.closed_bars).
        if candles is None:
            now = now or datetime.now(IST)
            candles = data_provider.get_intraday_candles(symbol, interval=config.CANDLE_INTERVAL, period="5d")
        if not candles:
            return
        with self.state.lock:
            self.state.candles[symbol] = candles[-200:]
        # Stops and fills use the live price; the checklist and sizing read finished bars, like the backtester.
        ltp = candles[-1]["close"]
        bars = data_provider.closed_bars(candles, config.CANDLE_INTERVAL, now=now)

        if self._check_stop_take(symbol, ltp):
            with self.state.lock:
                self.state.indicators[symbol] = {**(self.state.strategy_state.get(symbol) or {}), "ltp": ltp}
            return
        if not bars:
            return

        params = dict(self.strategy_params)
        if getattr(self.strategy_fn, "uses_news", False) and params.get("use_news", True):
            params["news"] = news_sentiment.get_sentiment(symbol)
        if getattr(self.strategy_fn, "uses_fundamentals", False) and params.get("use_fundamentals", True):
            params["fundamentals"] = fundamentals.get_fundamentals(symbol)
        prev = self.state.strategy_state.get(symbol)
        signal, analysis = self.strategy_fn(bars, prev_state=prev, **params)
        with self.state.lock:
            self.state.strategy_state[symbol] = analysis
            self.state.indicators[symbol] = {**(analysis or {}), "ltp": ltp}
        try:
            database.record_checklist_eval(symbol, ltp, analysis)
        except Exception:
            logger.exception(f"Failed to journal the checklist read for {symbol}")

        self._note_forming_setup(symbol, prev, analysis)
        if signal:
            self.state.record_signal(symbol, signal, analysis)
        if signal in ("BUY", "SHORT"):
            # An option buy acts on the same edge-triggered signal as a cash
            # entry, taken by _process_fno() later this tick (#157). Before, it
            # read the level-triggered long_ok/short_ok on every tick.
            self._fno_signals[symbol] = "LONG" if signal == "BUY" else "SHORT"

        a = analysis or {}
        qty = self.state.positions[symbol]["quantity"]
        # Exits check the brain's exit condition every tick, not only its edge, so an
        # exit can't be missed when an entry signal for the other side fires on the same bar.
        if qty > 0 and (signal in ("SELL", "SHORT") or a.get("exit_long")):
            why = "; ".join(r["text"] for r in a.get("bear_reasons", [])[:2])
            self._close(symbol, ltp, "brain_exit", why or None)
        elif qty < 0 and (signal in ("BUY", "COVER") or a.get("exit_short")):
            why = "; ".join(r["text"] for r in a.get("reasons", [])[:2])
            self._close(symbol, ltp, "brain_cover", why or None)
        elif qty == 0 and signal in ("BUY", "SHORT"):
            entered = self._try_enter(symbol, "LONG" if signal == "BUY" else "SHORT", ltp, bars, a)
            if not entered:
                # trader_brain_signal() already counted this signal against
                # max_entries_per_day and persisted that to strategy_state
                # (line ~717, before _try_enter's own checks — confidence
                # gate, sector cap, daily-loss limit, 0-share sizing — ever
                # ran). Without this rollback, a block silently burns the
                # day's only real shot at this symbol even though no trade
                # ever happened; with the Scorecard currently failing, that
                # was going to hit almost every real signal today.
                with self.state.lock:
                    st = self.state.strategy_state.get(symbol)
                    if st and st.get("entries_today", 0) > 0:
                        st["entries_today"] -= 1

        if self.state.positions[symbol]["quantity"] == 0 and self.review_queue.enabled():
            try:
                self._offer_near_misses(symbol, ltp, bars, a)
            except Exception:
                logger.exception(f"Review queue: couldn't evaluate {symbol} for a near-miss card")

    # ---- loop -----------------------------------------------------------

    def tick(self):
        """Thin wrapper — see _tick_impl() for the real body. Every part of a
        tick used to run unguarded except the per-symbol loop and _process_fno();
        one uncaught exception anywhere else (a Kite timeout during square-off,
        a bad margins() response during capital sync) would propagate out of
        run_forever()'s while loop and kill the engine's background thread
        permanently — no more scans, no more square-offs, silently, for the
        rest of the process's life. That directly contradicts the Autonomous
        Trading card's "runs unattended" promise, so the whole tick body is
        now caught here: one bad cycle is skipped, logged, and retried next
        cycle 30s later, instead of ending the engine."""
        self._tick_started_at = time.time()
        try:
            if self._unconfirmed_orders:
                self._resolve_unconfirmed_orders()
            self._tick_impl()
        except Exception as exc:
            logger.exception("tick() failed — skipping this cycle, will retry next one")
            try:
                self.state.log("error", f"Internal error this cycle (recovered): {exc}", level="error")
            except Exception:
                pass
        finally:
            self._tick_started_at = None

    def _check_tick_stall(self, now=None):
        """Log every thread's stack, once per stuck tick, when a tick has overrun TICK_STALL_SECONDS."""
        started = self._tick_started_at
        if started is None or self._stall_reported_for == started:
            return
        running = (now or time.time()) - started
        if running < TICK_STALL_SECONDS:
            return
        self._stall_reported_for = started
        frames = sys._current_frames()
        stacks = "".join(
            f"--- thread {th.name} ---\n" + "".join(traceback.format_stack(frames[th.ident]))
            for th in threading.enumerate() if th.ident in frames
        )
        logger.error(f"Engine tick has been running for {running:.0f}s; thread stacks:\n{stacks}")
        self.state.log("error", f"The engine has been stuck on one cycle for {running / 60:.0f} min, so stops "
                                f"and entries aren't being checked. Thread stacks are in the backend log.",
                       level="error")

    def _watch_ticks(self):
        while self.state.running:
            time.sleep(TICK_WATCHDOG_INTERVAL_SECONDS)
            try:
                self._check_tick_stall()
            except Exception:
                logger.exception("Tick watchdog check failed")

    def _check_preopen_kite(self, now, holiday):
        """Once per trading day, from PREOPEN_KITE_CHECK_TIME until the close:
        if Kite is configured but its session isn't live, raise one
        error-level alert, which the dashboard pushes to the browser.

        #71's expiry alert only fires once a Kite call has failed and backs
        off after that; this one is scheduled, so a missing login is loud
        before the open rather than discovered after it. One live probe a day
        catches a token revoked from Zerodha's side, which the 06:00 clock
        can't see. Guarded in memory and against the activity table, like the
        session summary, so a restart doesn't repeat it."""
        today = now.date()
        if (holiday or now.weekday() >= 5 or self._preopen_kite_checked_date == today
                or not (PREOPEN_KITE_CHECK_T <= now.time() < MARKET_CLOSE_T)):
            return
        self._preopen_kite_checked_date = today
        if not (config.KITE_API_KEY and config.KITE_API_SECRET):
            return                       # Kite isn't set up at all; nothing to remind about
        if database.activity_kind_logged_on(database.PREOPEN_KITE_KIND, today.isoformat()):
            return
        try:
            live = bool(data_provider.kite_session_status(probe=True).get("connected"))
        except Exception as exc:
            logger.warning(f"Pre-open Kite check could not run: {exc}")
            live = data_provider.kite_session_live()
        if live:
            return
        when = (f"the market opens at {config.MARKET_OPEN}" if now.time() < MARKET_OPEN_T
                else "the market is already open")
        self.state.log(database.PREOPEN_KITE_KIND,
                       f"Kite isn't logged in and {when}. Zerodha ends every session at 06:00 IST — click "
                       f"Reconnect in the header now, or the engine runs on delayed data and live orders will fail.",
                       level="error")

    def _tick_impl(self):
        now = datetime.now(IST)
        self._sync_capital()
        if self._last_day != now.date():
            self.risk.reset_day()
            self.state.realized_pnl_today = 0.0
            self._last_day = now.date()

        phase = market_phase(now)
        self.state.market_status = "open" if phase in ("open", "square_off_window") else "closed"
        self.state.next_open = next_session_open(now)
        holiday = holidays.holiday_name(now)
        self.state.holiday = {"name": holiday, "next_trading_day": holidays.next_trading_day(now).isoformat()} \
            if holiday else None
        self._check_preopen_kite(now, holiday)
        if holiday and self._last_holiday_logged != now.date():
            self._last_holiday_logged = now.date()
            resumes = holidays.next_trading_day(now).strftime("%A, %d %b")
            self.state.log("system", f"Markets are closed today for {holiday}. Trading resumes {resumes}.")

        # End-of-session summary. Fires on the first tick after the close on a
        # day the market actually traded, so the activity stream carries a
        # standing answer to "why did nothing fire today" — which gate came
        # closest, on which stock — instead of that only being recoverable by
        # querying the journal afterwards. Guarded twice: in memory for the
        # normal case, and against the activity table so an evening restart
        # doesn't log the same summary a second time.
        if (phase == "closed" and not holiday and now.weekday() < 5
                and now.time() >= MARKET_CLOSE_T
                and self._last_session_summary_date != now.date()):
            self._last_session_summary_date = now.date()
            try:
                today = now.date().isoformat()
                if not database.session_summary_logged_on(today):
                    summary = database.session_summary(session_date=today)
                    self.state.log(database.SESSION_SUMMARY_KIND,
                                   database.session_summary_line(summary))
            except Exception:
                logger.exception("End-of-session summary failed")

        if phase == "closed" and momentum_book.maybe_start_evening_job(now, holiday):
            self.state.log("system", "Momentum book: evening job started (fetch today's bhavcopy, mark to market, "
                                     "rebalance on the first session of a month)")

        if phase == "closed" and chaywanaprash.maybe_start_review(now, holiday, self.state.log):
            self.state.log("system", "Chaywanaprash: reviewing the last two weeks of trading and every change "
                                     "merged in that time (proposes only, changes nothing)")

        if self.should_fix_list(now, holiday):
            # Before the open on a trading day: the read that fixes the
            # day's list (README section 100).
            if self.request_premarket_scan(fix_list_for=now.date().isoformat()):
                self._list_fix_attempt_ts = time.time()
        elif self._last_premarket_run_date != now.date() and self.scanner:
            # Runs every day, holiday included — it's a read on the last
            # completed session, which is just as valid context on a
            # holiday (planning ahead to the next trading day) as any other.
            self.request_premarket_scan()

        if self.scanner and self.scanner.due(phase != "closed"):
            self.request_scan()

        if phase in ("open", "square_off_window"):
            # ETF books at the overnight-hold entry and exit times; a no-op
            # outside those windows. Data collection only.
            depth_sampler.sample_windows(now, time.time())

        if phase == "open" and jev_book.maybe_decide(self.state.scanner, now, holiday):
            self.state.log("system", "Jev book: asking Jev about today's shortlist (paper test, README section 86)")
        if phase == "square_off_window" and jev_book.maybe_close(now):
            self.state.log("system", "Jev book: closed today's paper positions at the square-off")

        if phase == "square_off_window":
            if any(p["quantity"] for p in self.state.positions.values()):
                self.state.log("risk", "Square-off time — closing all open positions", level="warn")
                self._square_off_all()
            for underlying in list(self.state.fno_positions.keys()):
                try:
                    self._close_fno(underlying, "fno_auto_square_off")
                except Exception as exc:
                    if not isinstance(exc, (OrderNotFilled, OrderUnconfirmed)):
                        logger.exception(f"F&O square-off of {underlying} failed")
                    self._fno_error(underlying, f"[F&O] square-off of {underlying} failed: {exc}. "
                                                f"The next tick tries again.")
            try:
                self._record_session_closes(now)
            except Exception:
                logger.exception("Shadow log: couldn't record the 15:08 prices")
        elif phase == "open":
            watchlist = list(self.state.watchlist)
            # Order-book snapshot for every watched stock, once per tick, before
            # anything else this tick can move. Data collection only.
            depth_sampler.sample(watchlist, time.time())
            # Candles for all watched symbols are fetched concurrently up
            # front (data_provider.get_candles_batch) instead of one
            # blocking HTTP round-trip per symbol in this loop — with
            # active_count now at 25 (was 6), the old sequential fetch
            # would serialize ~25 network calls into every 30s tick.
            try:
                candles_map = data_provider.get_candles_batch(
                    watchlist, interval=config.CANDLE_INTERVAL, period="5d")
            except Exception:
                logger.exception("Batch candle fetch failed — each symbol will fetch individually this cycle")
                candles_map = {}
            for symbol in watchlist:
                try:
                    self._process_symbol(symbol, candles=candles_map.get(symbol), now=now)
                    self._last_errors.pop(symbol, None)
                except Exception as exc:
                    logger.exception(f"Error processing {symbol}: {exc}")
                    msg = str(exc)
                    with self.state.lock:
                        self.state.last_error = f"{symbol}: {msg}"
                    if self._last_errors.get(symbol) != msg:
                        self._last_errors[symbol] = msg
                        self.state.log("error", msg, symbol=symbol, level="error")
            try:
                self._process_fno()
            except Exception:
                logger.exception("F&O processing failed")
            if self._reflatten_pending:
                # Catches an entry that was already past the pause check when
                # the kill switch flattened from the API thread.
                self._reflatten_pending = False
                if self._square_off_all(reason="kill_switch"):
                    self.state.log("risk", "Kill switch — closed a position opened during the stop", level="warn")
            # Keep the tick stream subscribed to exactly what we hold, so a
            # position opened this cycle is under tick-by-tick stop watch
            # within a second of its order going in.
            try:
                if self.stop_watcher is not None:
                    self.stop_watcher.sync()
            except Exception:
                logger.exception("Stop watcher sync failed — stops still covered by this poll")

        try:
            self._update_review_shadows(now)
        except Exception:
            logger.exception("Review queue: couldn't update the hypothetical outcomes")

        with self.state.lock:
            self.state.last_update_ts = now.timestamp()

    def _record_session_closes(self, now):
        """Once a session, at the first tick of the square-off window: Kite's
        last traded price for every universe stock and the NIFTY, the outcome
        the shadow log scores each scan against (README §115, scanner audit
        rule 5.3). Kite only, never the delayed feed: a session without Kite
        has no outcome recorded, and says so once. Tried again each tick in the
        window until it succeeds; the row keeps the time it was read."""
        today = now.date().isoformat()
        if self._closes_recorded_for == today:
            return
        if database.session_closes_recorded(today):
            self._closes_recorded_for = today
            return
        quotes = data_provider.kite_quotes([u["symbol"] for u in universe.load()], indices=("NIFTY 50",)) \
            if data_provider.kite_data_active() else {}
        written = database.record_session_closes(today, quotes) if quotes else 0
        if written:
            self._closes_recorded_for = today
            self.state.log("system", f"Shadow log: recorded the {now.strftime('%H:%M')} price of {written} "
                                     f"stocks and indices, the outcome of today's scans (README section 115)")
        elif self._closes_missing_logged != today:
            self._closes_missing_logged = today
            self.state.log("system", "Shadow log: no live Kite price at the square-off yet, so today's scans have "
                                     "no 15:08 outcome recorded. Trying again each tick until the close.",
                           level="warn")

    def _update_review_shadows(self, now, min_interval=60):
        """Once a minute: replay every card of the day that wasn't approved as
        if it had been, and save the result (review_queue.shadow_outcome). A
        card's hypothetical trade stops updating once it has exited."""
        if time.time() - self._last_shadow_update < min_interval:
            return
        self._last_shadow_update = time.time()
        for card in self.review_queue.shadow_candidates():
            symbol = card["symbol"]
            bars = self.state.candles.get(symbol)
            if not bars:
                try:
                    bars = data_provider.get_intraday_candles(symbol, interval=config.CANDLE_INTERVAL, period="1d")
                except Exception:
                    logger.exception(f"Review queue: no candles for {symbol}'s hypothetical outcome")
                    continue
            if not bars:
                continue
            outcome = review_queue.shadow_outcome(card, bars, ltp=bars[-1]["close"], now=now)
            self.review_queue.set_shadow(card["id"], outcome)

    async def run_forever(self):
        self.state.running = True
        threading.Thread(target=self._watch_ticks, name="tick-watchdog", daemon=True).start()
        if config.RISK.get("tick_stops", True):
            import stop_watcher
            self.stop_watcher = stop_watcher.StopWatcher(self)
        self.state.log("system", f"Trader Sahab started in {'paper' if self.state.paper_mode else 'live'} mode "
                                 f"with {config.STRATEGY_DISPLAY_NAMES.get(config.STRATEGY, config.STRATEGY)} "
                                 f"calling the shots.")
        while self.state.running:
            try:
                await asyncio.get_event_loop().run_in_executor(None, self.tick)
            except Exception:
                # tick() already catches its own body — this is defense in
                # depth against the executor call itself misbehaving, so the
                # while loop truly cannot die from an ordinary exception.
                logger.exception("run_in_executor(tick) failed unexpectedly")
            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
