"""
Chronological splits for research backtests.

`backtester.py` has no selection/held-out split — only `swing_backtester.py`
does — so the verdict phase produced its both-halves figures from a throwaway
script. This is that logic, committed and tested, so phase-2 results are
reproducible and the two harnesses agree on where the boundary sits.

RESEARCH ONLY. Nothing in the live path may import from `backend.research`;
`tests/test_research_isolation.py` asserts it.

The held-out split is not pristine
----------------------------------
The prior phase already ran against 2026-01-02 onward (its swing backtest
reports held-out rows explicitly). Anything measured on the same window is
therefore a *second* look at data that has been seen, and carries less
evidential weight than the term "held-out" normally implies. Every write-up
using these splits has to say so.

The only genuinely unseen sample is data accruing **after 2026-09-20**, the
last session in the cache at the time this was written. Keeping the candle
cache updating is what will eventually produce a clean confirmation set.
"""
from datetime import date, timedelta

# One boundary, named once. swing_backtester.py uses --held-out-frac 0.4 over
# its own session list; this constant pins the same 60/40 idea to an explicit
# date so every phase-2 run reports against the same line, whatever window of
# sessions it happens to load.
HELD_OUT_START = "2026-01-02"

# The last session the cache held when phase 2 began. Anything after this is
# the only data no strategy decision in this project has ever seen.
CACHE_FROZEN_AT = "2026-09-18"
UNSEEN_AFTER = "2026-09-20"

# Sessions dropped either side of a boundary so a multi-day hold opened before
# it cannot resolve after it. Five sessions covers the longest hold tested
# (5 days) with no overlap.
EMBARGO_SESSIONS = 5


def selection_holdout(sessions, boundary=HELD_OUT_START, embargo=0):
    """Split an ordered list of session dates at `boundary`.

    Returns (selection, held_out). With `embargo` > 0, that many sessions are
    dropped from the END of selection, so a position opened in selection and
    held for up to `embargo` sessions cannot resolve inside held-out. The
    embargo is taken out of selection rather than held-out because held-out is
    the scarcer sample.
    """
    sessions = sorted(sessions)
    selection = [s for s in sessions if s < boundary]
    held_out = [s for s in sessions if s >= boundary]
    if embargo > 0 and selection:
        selection = selection[:-embargo] if embargo < len(selection) else []
    return selection, held_out


def halves(sessions, embargo=0):
    """Split an ordered list of session dates into two chronological halves.

    This is the both-halves stability check, which is a different question
    from selection/held-out: it asks whether a result exists in both periods,
    not whether it survives out of sample.
    """
    sessions = sorted(sessions)
    mid = len(sessions) // 2
    first, second = sessions[:mid], sessions[mid:]
    if embargo > 0 and first:
        first = first[:-embargo] if embargo < len(first) else []
    return first, second


def boundary_date(sessions, boundary=HELD_OUT_START):
    """The first held-out session actually present, or None. Useful for write-ups:
    the constant is a calendar date, but the realised boundary is a session."""
    later = [s for s in sorted(sessions) if s >= boundary]
    return later[0] if later else None


def slice_data(preloaded, picks, sessions):
    """Candles and picks restricted to `sessions`.

    Built as one new dict rather than three simultaneous copies: the cache
    holds ~3.6M candle dicts, and materialising every split at once runs to
    several GB and sends the machine into swap instead of backtesting. Callers
    should build one slice, run it, drop it, then build the next.
    """
    keep = set(sessions)
    candles = {sym: [c for c in bars if c["time"][:10] in keep]
               for sym, bars in preloaded.items()}
    candles = {sym: bars for sym, bars in candles.items() if bars}
    allowed = {d: v for d, v in (picks or {}).items() if d in keep}
    return candles, allowed


def sessions_in(preloaded):
    """Every session date present in a preloaded candle map, ordered."""
    return sorted({c["time"][:10] for bars in preloaded.values() for c in bars})


def describe_split(name, sessions):
    """One line a write-up can quote verbatim, including the contamination note."""
    if not sessions:
        return f"{name}: no sessions"
    seen = " (already seen by earlier work)" if sessions[-1] >= HELD_OUT_START else ""
    return (f"{name}: {len(sessions)} sessions, {sessions[0]} to {sessions[-1]}{seen}")


def required_trades(spread_r, edge_r, power=0.80, alpha=0.05):
    """Trades needed to detect `edge_r` at two-sided `alpha` with `power`.

    Amendment 1: the per-trade spread must come from the hypothesis being
    tested, not inherited from the old brackets (whose spread was 1.41R).
    Two-sided 5% and 80% power give (1.96 + 0.8416)^2 = 7.849.
    """
    if not edge_r:
        return None
    z_alpha, z_beta = 1.959964, 0.841621
    return int(round(((z_alpha + z_beta) * spread_r / abs(edge_r)) ** 2))


def trades_per_session_bar(spread_r, edge_r, n_sessions, power=0.80):
    """The trade rate a hypothesis must reach to be confirmable on `n_sessions`.

    Below this it is *untestable at this frequency* — which is a finding to
    report, not a strategy to pursue.
    """
    need = required_trades(spread_r, edge_r, power=power)
    return None if not need or not n_sessions else need / n_sessions
