"""
The liquidity check: can this position be entered AND exited at its size,
at the cost the rest of the system assumes?

Everything upstream sizes and prices a trade as if a market order fills at
the last traded price plus config.COSTS["slippage_pct"] per leg, 3 bp. That
figure has never been measured, because no real-money order has been placed,
and it is what the 16.60 bp round-trip hurdle rests on. The only liquidity
check before this was the scanner's daily turnover floor (Rs 50 cr), which
says nothing about the book at the moment of entry.

This reads Kite's five-level market depth just before an entry and refuses
the trade when:

- the quoted spread is wider than twice the modelled slippage (a market
  order pays about half the spread, so a spread over 6 bp means the cost
  model is understating this fill);
- walking the book for our quantity moves the fill further from the mid than
  the modelled slippage (impact, not just spread);
- the entry side of the book, or the side we would exit into, holds less
  than `min_depth_multiple` times our quantity across five levels.

Every reading is written to the journal (liquidity_checks), whether it
passes or not. That is the first measured spread and impact data this
project has, and it is the input issue #66 needs to price slippage per
symbol instead of assuming 3 bp for all of them.

When there is no depth to read (no live Kite session, or a data error), a
paper-mode entry goes ahead and the check is recorded as "unchecked"; a live
entry is refused. Never place a real order on a book nobody looked at.

An option buy (check_option, #157) is judged on its own contract's NFO book.
The option tariff models no slippage, so "twice the modelled slippage" would
refuse every option; the cap is config.FNO["max_spread_pct_of_premium"] of
the mid premium instead, the walk may cost at most half of it, and the depth
rule is the same multiple of the order as for cash.
"""

import logging

import config
import database

logger = logging.getLogger("trading_bot")


def _cfg():
    return getattr(config, "LIQUIDITY", {})


def max_spread_bp(costs_cfg=None):
    """Twice the modelled per-leg slippage, in bp. Derived, not typed in, for
    the same reason as trader_brain's cost_pct (#74): a separate constant
    drifts away from the cost model it is supposed to protect."""
    costs_cfg = costs_cfg or config.COSTS
    return 2 * costs_cfg.get("slippage_pct", 0.0) * 100


def _walk(levels, qty):
    """Volume-weighted price of filling `qty` against `levels` (best first),
    and whether the five levels held enough to fill it at all."""
    left, cost = qty, 0.0
    for lv in levels:
        take = min(left, lv.get("quantity") or 0)
        cost += take * lv["price"]
        left -= take
        if left <= 0:
            return cost / qty, True
    filled = qty - left
    return (cost / filled if filled else None), False


def assess(depth, side, qty, costs_cfg=None):
    """Pure check on a Kite depth dict ({"buy": [...], "sell": [...]}, best
    level first). `side` is "LONG" or "SHORT". Returns a result dict with
    ok, reason and the measured spread/impact/depth numbers."""
    cfg = _cfg()
    min_mult = cfg.get("min_depth_multiple", 3.0)
    spread_cap = max_spread_bp(costs_cfg)
    slip_bp = (costs_cfg or config.COSTS).get("slippage_pct", 0.0) * 100
    bids = [lv for lv in (depth or {}).get("buy", []) if lv.get("price") and lv.get("quantity")]
    asks = [lv for lv in (depth or {}).get("sell", []) if lv.get("price") and lv.get("quantity")]
    out = {"ok": False, "reason": None, "spread_bp": None, "impact_bp": None,
           "entry_depth": None, "exit_depth": None, "max_spread_bp": spread_cap, "qty": qty}
    if not bids or not asks:
        out["reason"] = "the order book is empty on one side"
        return out

    bid, ask = bids[0]["price"], asks[0]["price"]
    mid = (bid + ask) / 2
    out["spread_bp"] = round((ask - bid) / mid * 1e4, 2)
    # A long buys into the asks and exits into the bids; a short the reverse.
    entry_book, exit_book = (asks, bids) if side == "LONG" else (bids, asks)
    out["entry_depth"] = sum(lv["quantity"] for lv in entry_book)
    out["exit_depth"] = sum(lv["quantity"] for lv in exit_book)
    vwap, filled = _walk(entry_book, qty)
    if vwap is not None:
        out["impact_bp"] = round(abs(vwap - mid) / mid * 1e4, 2)

    if out["spread_bp"] > spread_cap:
        out["reason"] = (f"spread is {out['spread_bp']:.1f} bp, over the {spread_cap:g} bp the cost model's "
                         f"{slip_bp:g} bp-per-leg slippage allows")
    elif not filled:
        out["reason"] = f"five levels hold only {out['entry_depth']} against an order for {qty}"
    elif out["impact_bp"] > slip_bp:
        out["reason"] = (f"filling {qty} walks the book {out['impact_bp']:.1f} bp from the mid, over the "
                         f"{slip_bp:g} bp slippage the cost model assumes")
    elif min(out["entry_depth"], out["exit_depth"]) < min_mult * qty:
        thin = "entry" if out["entry_depth"] <= out["exit_depth"] else "exit"
        out["reason"] = (f"the {thin} side holds {min(out['entry_depth'], out['exit_depth'])} across five levels, "
                         f"under {min_mult:g}× the {qty} we'd trade")
    else:
        out["ok"] = True
    return out


def assess_option(depth, qty, max_spread_pct, min_depth_multiple):
    """The option buy's version of assess(): the spread as a % of the mid
    premium, at most `max_spread_pct`; walking the asks for `qty` moves the
    fill at most half that from the mid; both sides hold `min_depth_multiple`
    times `qty` across five levels. A buy enters into the asks and exits into
    the bids. The bp fields are filled too, so the journal row reads like a
    cash one."""
    bids = [lv for lv in (depth or {}).get("buy", []) if lv.get("price") and lv.get("quantity")]
    asks = [lv for lv in (depth or {}).get("sell", []) if lv.get("price") and lv.get("quantity")]
    out = {"ok": False, "reason": None, "spread_bp": None, "impact_bp": None, "entry_depth": None,
           "exit_depth": None, "max_spread_bp": max_spread_pct * 100, "qty": qty}
    if not bids or not asks:
        out["reason"] = "the option's order book is empty on one side"
        return out
    bid, ask = bids[0]["price"], asks[0]["price"]
    mid = (bid + ask) / 2
    spread_pct = (ask - bid) / mid * 100
    out["spread_bp"] = round(spread_pct * 100, 2)
    out["entry_depth"] = sum(lv["quantity"] for lv in asks)
    out["exit_depth"] = sum(lv["quantity"] for lv in bids)
    vwap, filled = _walk(asks, qty)
    impact_pct = abs(vwap - mid) / mid * 100 if vwap is not None else None
    if impact_pct is not None:
        out["impact_bp"] = round(impact_pct * 100, 2)
    if spread_pct > max_spread_pct:
        out["reason"] = (f"the option's spread is {spread_pct:.2f}% of the premium ({bid:.2f} / {ask:.2f}), "
                         f"over the {max_spread_pct:g}% cap")
    elif not filled:
        out["reason"] = f"five levels of the option's book hold only {out['entry_depth']} against an order for {qty}"
    elif impact_pct > max_spread_pct / 2:
        out["reason"] = (f"buying {qty} walks the option's book {impact_pct:.2f}% from the mid, over half "
                         f"the {max_spread_pct:g}% spread cap")
    elif min(out["entry_depth"], out["exit_depth"]) < min_depth_multiple * qty:
        thin = "entry" if out["entry_depth"] <= out["exit_depth"] else "exit"
        out["reason"] = (f"the option's {thin} side holds {min(out['entry_depth'], out['exit_depth'])} across "
                         f"five levels, under {min_depth_multiple:g}× the {qty} we'd trade")
    else:
        out["ok"] = True
    return out


def _fetch_depth(symbol):
    import data_provider
    if not data_provider.kite_data_active():
        return None
    q = data_provider._get_kite().quote([f"NSE:{symbol}"]).get(f"NSE:{symbol}") or {}
    return q.get("depth")


def _fetch_option_depth(tradingsymbol):
    import data_provider
    if not data_provider.kite_data_active():
        return None
    q = data_provider._get_kite().quote([f"NFO:{tradingsymbol}"]).get(f"NFO:{tradingsymbol}") or {}
    return q.get("depth")


def check_option(tradingsymbol, qty, premium, paper_mode, fetch=None):
    """check() for an option buy (#157): the contract's own book, judged by
    assess_option(). Same rule when there is no book to read: paper goes
    ahead, recorded as unchecked, and live is refused."""
    return check(tradingsymbol, "LONG", qty, premium, paper_mode, fetch=fetch or _fetch_option_depth,
                 judge=lambda depth: assess_option(depth, qty, config.FNO["max_spread_pct_of_premium"],
                                                   _cfg().get("min_depth_multiple", 3.0)))


def check(symbol, side, qty, ltp, paper_mode, fetch=_fetch_depth, judge=None):
    """The entry-time gate. Returns (ok, reason, result). Records every
    reading, including the ones it could not take. `judge` replaces
    assess() for a book that isn't a cash stock's (check_option)."""
    if not _cfg().get("enabled", True):
        return True, None, {"status": "disabled"}
    try:
        depth = fetch(symbol)
    except Exception as exc:
        logger.warning(f"Liquidity check could not read depth for {symbol}: {exc}")
        depth = None
    if depth is None:
        result = {"status": "unchecked", "ok": paper_mode, "qty": qty,
                  "reason": None if paper_mode else "no market depth available — a live order needs a checked book"}
    else:
        result = {**(judge(depth) if judge else assess(depth, side, qty)), "status": "checked"}
    try:
        database.record_liquidity_check(symbol, side, qty, ltp, "paper" if paper_mode else "live", result)
    except Exception as exc:
        logger.warning(f"Could not record liquidity check for {symbol}: {exc}")
    return bool(result["ok"]), result.get("reason"), result
