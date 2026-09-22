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
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import config
import confidence
import costs
import data_provider
import database
import fno_instruments
import fno_risk
import fundamentals
import holidays
import news_sentiment
import options_pricing
from kiteconnect.exceptions import TokenException
from paper_broker import execute_paper_order
from risk_manager import RiskManager
from scanner import Scanner, run_premarket
import trader_brain
import universe
from state import AppState
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
SQUARE_OFF_T = _parse_hhmm(config.SQUARE_OFF_TIME)


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
        self.strategy_fn = STRATEGY_FUNCTIONS[config.STRATEGY]
        self.strategy_params = config.STRATEGY_PARAMS[config.STRATEGY]
        self.kite_executor = None
        self._last_day = datetime.now(IST).date()
        self._last_holiday_logged = None
        self._last_session_summary_date = None
        self.scanner = Scanner(config.SCANNER) if config.SCANNER.get("enabled") else None
        self._scan_thread = None
        self.size_multiplier = 1.0
        self._last_errors = {}
        self._last_capital_sync = 0.0
        self._last_token_alert = 0.0
        self._reconciliation_alerted = set()
        self._untracked_kite_positions = set()
        self._last_synced_paper_mode = None
        self._premarket_thread = None
        self._last_premarket_run_date = None
        self._last_premarket_seed_date = None
        self._tick_started_at = None
        self._stall_reported_for = None
        # Symbols whose exit one thread has claimed. Until the tick stream
        # existed only the poll loop ever closed a position, so "read the
        # quantity, then place the closing order" was safe without a lock
        # across both steps. It isn't any more: two threads seeing the same
        # breached stop would each send a full closing order and turn a flat
        # exit into a reversed position. See _claim_exit().
        self._exiting = set()
        self.stop_watcher = None

    def _ensure_kite(self):
        if self.kite_executor is None:
            from kite_broker import KiteExecutor
            self.kite_executor = KiteExecutor(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
        return self.kite_executor

    def reset_kite_executor(self):
        """Drop the cached executor so the next order rebuilds it with
        whatever access token config now holds."""
        self.kite_executor = None

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
            if time.time() - self._last_token_alert > 900:
                self._last_token_alert = time.time()
                self.state.log("error", "Kite session has expired — click Reconnect in the header. Until then, "
                                        "prices fall back to delayed data and live orders will fail.", level="error")
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

        if not self.state.paper_mode:
            self._check_position_reconciliation()

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
        with self.state.lock:
            tracked = {sym for sym, pos in self.state.positions.items() if pos["quantity"] != 0}
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

    def request_premarket_scan(self) -> bool:
        if self._premarket_thread and self._premarket_thread.is_alive():
            return False
        self._premarket_thread = threading.Thread(target=self._run_premarket_scan, name="premarket-scan", daemon=True)
        self._premarket_thread.start()
        return True

    def _run_premarket_scan(self):
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
        self._maybe_seed_watchlist_from_premarket(result)

    def _maybe_seed_watchlist_from_premarket(self, result):
        """Primes state.watchlist with the pre-market shortlist for the gap
        between process start and the first live intraday scan — only while
        that gap is real (no live scan has run yet today) and only once a
        day, so it never fights the live scanner once that takes over."""
        today = datetime.now(IST).date()
        if self._last_premarket_seed_date == today:
            return
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

    def _execute(self, symbol, side, qty, price, reason="signal", note=None, checklist_snapshot=None,
                position_id=None, initial_risk=None):
        # backtester.py has always applied costs.apply_slippage() to every
        # fill; this function — every live and paper trade's one real path
        # — never did, only leg_cost() (brokerage/STT/exchange charges).
        # That broke the "same code, same costs" property the backtester is
        # praised for elsewhere: live/paper P&L (including BEL's first real
        # trade) was silently held to a laxer cost standard than backtested
        # performance is. price stays the raw signal/stop/target price for
        # logging the plan; fill_price is what P&L and the journal actually
        # use, same as backtester.py already does for both entries and exits.
        fill_price = costs.apply_slippage(side, price, config.COSTS)
        charges = costs.leg_cost(side, fill_price, qty, config.COSTS)
        if self.state.paper_mode:
            fill = execute_paper_order(self.state, symbol, side, qty, fill_price, reason=reason, note=note,
                                       charges=charges, checklist_snapshot=checklist_snapshot,
                                       position_id=position_id, initial_risk=initial_risk)
        else:
            executor = self._ensure_kite()
            executor.place_order(symbol, side, qty)
            fill = self.state.apply_fill(symbol, side, qty, fill_price, charges=charges)
            r_multiple = (fill["net"] / (initial_risk * qty)) if initial_risk and qty else None
            self.state.record_trade(symbol, side, qty, fill_price, mode="live", reason=reason, note=note,
                                    realized=fill["net"], realized_gross=fill["gross"], charges=charges,
                                    position_id=position_id, initial_risk=initial_risk, r_multiple=r_multiple,
                                    checklist_snapshot=checklist_snapshot)
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

    def _square_off_all(self):
        for symbol, pos in list(self.state.positions.items()):
            if pos["quantity"] == 0:
                continue
            side = "SELL" if pos["quantity"] > 0 else "BUY"
            try:
                price = data_provider.get_ltp(symbol)
            except Exception:
                price = pos["avg_price"]
            self._execute(symbol, side, abs(pos["quantity"]), price, reason="auto_square_off",
                         position_id=pos.get("position_id"), initial_risk=pos.get("initial_risk"))
        self.risk.open_positions_count = 0

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
        a stop, a target, a brain exit, the 15:15 square-off — goes through
        here so the claim above is never bypassed."""
        if not self._claim_exit(symbol):
            return False
        try:
            with self.state.lock:
                pos = self.state.positions[symbol]
                qty = pos["quantity"]
                position_id, initial_risk = pos.get("position_id"), pos.get("initial_risk")
            if qty == 0:
                return False
            self._execute(symbol, "SELL" if qty > 0 else "BUY", abs(qty), ltp, reason=reason,
                          note=note, position_id=position_id, initial_risk=initial_risk)
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

    def _try_enter(self, symbol, side, ltp, candles, analysis):
        """side is "LONG" (buy) or "SHORT" (intraday MIS sell, squared off by 15:15).
        Returns True if a real order was placed, False if blocked for any reason —
        _process_symbol() uses this to roll back the entries_today count trader_brain
        already spent on this signal when nothing was actually entered."""
        if self.state.positions[symbol]["quantity"] != 0:
            return False
        if symbol in self._untracked_kite_positions:
            return self._blocked(symbol, f"{analysis.get('setup', 'Entry')} ({side.lower()})",
                                 "Kite shows an untracked open position in this symbol (see the reconciliation "
                                 "alert) — entries blocked until that's resolved, to avoid doubling up on real exposure")
        setup = f"{analysis.get('setup', 'Entry')} ({side.lower()})"
        row = self._scan_row(symbol)
        mkt = self.state.market or {}
        reasons_txt = "; ".join(mkt.get("reasons", [])[:2])
        if row and row.get("excluded"):
            return self._blocked(symbol, setup, row["excluded"])
        if row and row.get("side") and row["side"] != side:
            return self._blocked(symbol, setup, f"scanner favours {row['side']} for this stock today")
        if side == "LONG" and mkt.get("bias") == "risk-off" and config.MARKET_FILTER["block_new_longs_when_risk_off"]:
            return self._blocked(symbol, setup, f"no new longs — market is risk-off ({reasons_txt})")
        if side == "SHORT" and mkt.get("bias") == "risk-on" and config.MARKET_FILTER.get("block_new_shorts_when_risk_on", True):
            return self._blocked(symbol, setup, f"no new shorts — market is risk-on ({reasons_txt})")
        if self.risk.daily_loss_limit_hit():
            return self._blocked(symbol, setup, "daily loss limit reached")
        if self.risk.open_positions_count >= config.RISK["max_open_positions"]:
            return self._blocked(symbol, setup, f"already at the max of {config.RISK['max_open_positions']} open positions")

        # A multi-expert review flagged that max_open_positions alone doesn't stop 3
        # concurrent positions from being the same sector — which the scanner's own
        # sector-momentum ranking makes the *likely* outcome on a strong-trend day,
        # undermining the 2% daily-loss cap's implicit assumption that positions are
        # roughly independent. Cap same-industry concurrent positions too.
        max_per_sector = config.RISK.get("max_positions_per_sector")
        industry = self._industry_for(symbol, row)
        if industry and max_per_sector:
            same_sector = sum(
                1 for sym, pos in self.state.positions.items()
                if pos["quantity"] != 0 and self._industry_for(sym, self._scan_row(sym)) == industry
            )
            if same_sector >= max_per_sector:
                return self._blocked(symbol, setup, f"already at the max of {max_per_sector} open position(s) in "
                                                     f"{industry} — avoids concentrating risk in one sector")

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
        self._execute(symbol, "BUY" if side == "LONG" else "SELL", qty, ltp, reason=setup, note=note,
                      checklist_snapshot=analysis.get("checklist"), position_id=position_id)
        with self.state.lock:
            pos = self.state.positions[symbol]
            pos["entry_atr"] = atr_val
            pos["stop_price"] = stop_price
            pos["target_price"] = plan["target"] if plan else None
            pos["initial_risk"] = abs(ltp - stop_price) if stop_price else self.risk._stop_distance(ltp, atr_val)
            pos["position_id"] = position_id
        self.risk.open_positions_count += 1
        return True

    # ---- F&O (options-buying only — see fno_risk.py) ---------------------

    def _fno_active(self) -> bool:
        return bool(config.FNO.get("enabled")) and fno_instruments.available()

    def _fno_underlyings(self):
        explicit = config.FNO.get("underlyings") or []
        if explicit:
            return explicit
        return list((self.state.scanner or {}).get("active", []))

    def _record_fno_trade(self, symbol, side, quantity, price, reason, note, realized, position_id,
                          initial_risk, checklist_snapshot=None):
        r_multiple = (realized / (initial_risk * quantity)) if realized is not None and initial_risk and quantity else None
        mode = "paper" if self.state.paper_mode else "live"
        trade = {
            "id": database.new_position_id(), "position_id": position_id, "ts": time.time(),
            "symbol": symbol, "side": side, "quantity": quantity, "price": price, "mode": mode,
            # F&O charges aren't modelled yet (₹20/leg brokerage + STT on the
            # premium), so gross == net here — unlike the equity path, which
            # deducts real charges since issue #21.
            "reason": reason, "note": note, "realized": realized, "realized_gross": realized,
            "charges": 0.0, "initial_risk": initial_risk, "r_multiple": r_multiple,
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

    def _fno_ltp(self, tradingsymbol):
        if self.state.paper_mode:
            # No separate paper data feed for options premium — approximate with the last
            # Black-Scholes premium computed at entry-time IV; good enough for a paper fill,
            # never used for a live order (live always reads a real quote below).
            return None
        return self._ensure_kite().get_fno_ltp(tradingsymbol)

    def _close_fno(self, underlying, reason, note=None):
        pos = self.state.fno_positions.get(underlying)
        if not pos:
            return
        ltp = self._fno_ltp(pos["tradingsymbol"]) or pos.get("ltp") or pos["entry_premium"]
        if not self.state.paper_mode:
            self._ensure_kite().place_fno_order(pos["tradingsymbol"], "SELL", pos["lots"], pos["lot_size"])
        realized = (ltp - pos["entry_premium"]) * pos["lots"] * pos["lot_size"]
        r_multiple = self._record_fno_trade(pos["tradingsymbol"], "SELL", pos["lots"] * pos["lot_size"], ltp,
                                            reason, note, realized, pos["position_id"], pos["entry_premium"])
        try:
            database.record_fno_exit(pos["position_id"], ltp, reason, realized, r_multiple)
        except Exception:
            logger.exception(f"Failed to journal F&O exit for {underlying}")
        with self.state.lock:
            self.state.fno_positions.pop(underlying, None)
        self.risk.open_positions_count = max(0, self.risk.open_positions_count - 1)

    def _check_fno_stop_take(self, underlying):
        pos = self.state.fno_positions.get(underlying)
        if not pos:
            return False
        ltp = self._fno_ltp(pos["tradingsymbol"])
        if ltp is None:
            return False
        with self.state.lock:
            pos["ltp"] = ltp
            pos["unrealized_pnl"] = (ltp - pos["entry_premium"]) * pos["lots"] * pos["lot_size"]
        if ltp <= pos["stop_premium"]:
            self._close_fno(underlying, "fno_stop_loss", f"premium fell to {ltp:.2f} (stop {pos['stop_premium']:.2f})")
            return True
        if ltp >= pos["target_premium"]:
            self._close_fno(underlying, "fno_take_profit", f"premium rose to {ltp:.2f} (target {pos['target_premium']:.2f})")
            return True
        return False

    def _try_enter_fno(self, underlying, side, analysis):
        cfg = config.FNO
        if underlying in self.state.fno_positions:
            return  # one open contract per underlying at a time
        if self.risk.daily_loss_limit_hit() or self.risk.open_positions_count >= config.RISK["max_open_positions"]:
            return
        scorecard = database.journal_summary().get("scorecard", [])
        conf = confidence.score_trade(analysis, side, scorecard)

        def log_eval(executed, block_reason=None):
            try:
                database.record_fno_evaluation(underlying, side, conf, executed, block_reason)
            except Exception:
                logger.exception(f"Failed to journal F&O evaluation for {underlying}")

        if conf["score"] < cfg["min_confidence_to_trade"]:
            reason = f"confidence {conf['score']}/100 below the {cfg['min_confidence_to_trade']} bar"
            self.state.log("blocked", f"F&O {side} skipped — {reason} ({conf['explanation']})",
                           symbol=underlying, level="warn")
            log_eval(False, reason)
            return

        is_call = side == "LONG"
        expiry = fno_instruments.nearest_expiry(
            underlying, cfg["min_days_to_expiry"], cfg["max_days_to_expiry"],
            prefer_weekly=cfg["prefer_weekly_for_index"] and underlying in cfg["index_underlyings"])
        if not expiry:
            self._blocked(underlying, "F&O entry", "no listed expiry in the configured day-range")
            return log_eval(False, "no listed expiry in range")
        spot = analysis.get("ltp") or self.state.indicators.get(underlying, {}).get("ltp")
        if not spot:
            return log_eval(False, "no live spot price")

        def delta_at_strike(spot_, strike_, t_years_, is_call_):
            return options_pricing.greeks(spot_, strike_, t_years_, 0.20, cfg["risk_free_rate_pct"] / 100, is_call_)["delta"]

        contract = fno_instruments.find_contract(underlying, spot, expiry, is_call, cfg["target_delta"], delta_at_strike)
        if not contract:
            self._blocked(underlying, "F&O entry", "no matching strike found for this expiry")
            return log_eval(False, "no matching strike")

        t_years = max((expiry - datetime.now(IST).date()).days, 1) / 365
        premium = self._fno_ltp(contract["tradingsymbol"])
        if premium is None:
            if self.state.paper_mode:
                premium = options_pricing.price(spot, contract["strike"], t_years, 0.20,
                                                cfg["risk_free_rate_pct"] / 100, is_call)
            else:
                self._blocked(underlying, "F&O entry", "could not fetch a live premium quote")
                return log_eval(False, "no live premium quote")
        if not premium or premium <= 0:
            return log_eval(False, "non-positive premium")

        lots = fno_risk.lots_to_buy(cfg["capital"], cfg["max_premium_risk_pct"], premium, contract["lot_size"])
        if lots <= 0:
            reason = (f"premium {premium:.2f} x lot {contract['lot_size']} too large for the "
                     f"{cfg['max_premium_risk_pct']}% of ₹{cfg['capital']:,.0f} F&O allocation")
            self._blocked(underlying, "F&O entry", reason)
            return log_eval(False, reason)

        exits = fno_risk.stop_and_target_premium(premium, cfg["stop_loss_pct_of_premium"], cfg["target_pct_of_premium"])
        max_loss = fno_risk.max_loss(premium, lots, contract["lot_size"])
        entry_greeks = options_pricing.analyze(premium, spot, contract["strike"], t_years,
                                               cfg["risk_free_rate_pct"] / 100, is_call)
        if not self.state.paper_mode:
            self._ensure_kite().place_fno_order(contract["tradingsymbol"], "BUY", lots, contract["lot_size"])
        position_id = database.new_position_id()
        note = (f"{'Call' if is_call else 'Put'} bought on a {side.lower()} signal, confidence {conf['score']}/100 "
                f"({conf['label']}). Max loss capped at ₹{max_loss:,.0f} (the premium paid) — "
                f"stop {exits['stop_premium']:.2f}, target {exits['target_premium']:.2f}.")
        self._record_fno_trade(contract["tradingsymbol"], "BUY", lots * contract["lot_size"], premium,
                               f"fno_{side.lower()}", note, None, position_id, None,
                               checklist_snapshot=analysis.get("checklist"))
        pos = {
            "tradingsymbol": contract["tradingsymbol"], "underlying": underlying, "is_call": is_call,
            "strike": contract["strike"], "expiry": expiry.isoformat(),
            "lots": lots, "lot_size": contract["lot_size"], "entry_premium": premium,
            "stop_premium": exits["stop_premium"], "target_premium": exits["target_premium"],
            "ltp": premium, "unrealized_pnl": 0.0, "confidence": conf, "entry_greeks": entry_greeks,
            "max_loss": max_loss, "position_id": position_id,
        }
        with self.state.lock:
            self.state.fno_positions[underlying] = pos
        self.risk.open_positions_count += 1
        log_eval(True)
        try:
            database.record_fno_entry(position_id, pos)
        except Exception:
            logger.exception(f"Failed to journal F&O entry for {underlying}")

    def _process_fno(self):
        if not self._fno_active():
            return
        for underlying in list(self.state.fno_positions.keys()):
            try:
                self._check_fno_stop_take(underlying)
            except Exception:
                logger.exception(f"F&O stop/target check failed for {underlying}")
        for underlying in self._fno_underlyings():
            analysis = self.state.strategy_state.get(underlying)
            if not analysis or "bull_score" not in analysis:
                continue
            side = "LONG" if analysis.get("long_ok") else "SHORT" if analysis.get("short_ok") else None
            if not side:
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

        if self._last_premarket_run_date != now.date() and self.scanner:
            # Runs every day, holiday included — it's a read on the last
            # completed session, which is just as valid context on a
            # holiday (planning ahead to the next trading day) as any other.
            self.request_premarket_scan()

        if self.scanner and self.scanner.due(phase != "closed"):
            self.request_scan()

        if phase == "square_off_window":
            if any(p["quantity"] for p in self.state.positions.values()):
                self.state.log("risk", "Square-off time — closing all open positions", level="warn")
                self._square_off_all()
            for underlying in list(self.state.fno_positions.keys()):
                self._close_fno(underlying, "fno_auto_square_off")
        elif phase == "open":
            watchlist = list(self.state.watchlist)
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
            # Keep the tick stream subscribed to exactly what we hold, so a
            # position opened this cycle is under tick-by-tick stop watch
            # within a second of its order going in.
            try:
                if self.stop_watcher is not None:
                    self.stop_watcher.sync()
            except Exception:
                logger.exception("Stop watcher sync failed — stops still covered by this poll")

        with self.state.lock:
            self.state.last_update_ts = now.timestamp()

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
