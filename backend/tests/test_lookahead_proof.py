"""
Step 1b — proof that the nine pre-open scanner features contain no lookahead.

Pre-registered in docs/research/prereg-lookahead.md before this ran.

The assertion is stronger than "the code filters by date". A feature computed
for session T must be **bit-identical whether or not the input series contains
session T and everything after it**. If any later bar influences the value —
day T's own bar, a confirmation bar after a pattern, a 52-week extreme that
includes the future — the two computations diverge and the test fails.

Run against real cached Kite daily bars, not synthetic series, because the
failure modes here are about real data shapes: holidays, gaps, thin history.

Features covered (`scanner.premarket_score`):
  1 seasonality (March)      2 daily trend EMA20/50    3 rs10 vs NIFTY
  4 52-week high/low prox.   5 NR7 / inside day        6 Bulkowski patterns
  7 Murphy reversal day      8 daily RSI zone          9 daily ATR% band

A feature that fails is excluded from step 2, not repaired.
"""
import pytest

import scanner
import seasonality


def _date(bar):
    return bar["time"][:10]


@pytest.fixture(scope="module")
def daily_bars():
    """Real daily bars. yfinance daily was never subject to the 60-day
    intraday cap, and it is what premarket_picks() actually reads."""
    syms = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ITC", "SBIN"]
    raw = scanner.download_batch([scanner.yf_ticker(s) for s in syms] + [scanner.NIFTY], "2y", "1d")
    out = {s: raw.get(scanner.yf_ticker(s), []) for s in syms}
    out = {s: b for s, b in out.items() if len(b) >= 300}
    if not out:
        pytest.skip("no daily bars available offline")
    return out, raw.get(scanner.NIFTY, [])


def _profiles(bars, nifty, session, truncate_at=None):
    """Profile for `session`, optionally from a series physically truncated."""
    series = bars if truncate_at is None else [b for b in bars if _date(b) < truncate_at]
    nseries = nifty if truncate_at is None else [b for b in nifty if _date(b) < truncate_at]
    ndates = [_date(b) for b in nseries]
    ncloses = [b["close"] for b in nseries]
    return scanner.daily_profile(series, ndates, ncloses, session)


def _sample_sessions(bars, n=12):
    """Sessions late enough to have 60+ prior bars and early enough to have
    future bars available to (wrongly) leak in."""
    dates = [_date(b) for b in bars]
    lo, hi = 260, len(dates) - 30
    if hi <= lo:
        pytest.skip("not enough daily history")
    step = max(1, (hi - lo) // n)
    return dates[lo:hi:step][:n]


def test_the_profile_is_identical_with_and_without_future_bars(daily_bars):
    """The core lookahead assertion, across every profile field at once.

    Computing session T's profile from the FULL series must equal computing it
    from a series with T and everything after it physically removed. Any leak
    — day T's own bar, a later confirmation bar, a 52-week window that reaches
    forward — shows up as a mismatch."""
    bars_by_sym, nifty = daily_bars
    compared = 0
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars):
            full = _profiles(bars, nifty, session)
            truncated = _profiles(bars, nifty, session, truncate_at=session)
            if full is None and truncated is None:
                continue
            assert (full is None) == (truncated is None), f"{sym} {session}: one side returned None"
            assert full == truncated, (
                f"LOOKAHEAD in {sym} on {session}: the profile changes when future "
                f"bars are removed.\n  with future: {full}\n  without:     {truncated}")
            compared += 1
    assert compared >= 20, f"only {compared} comparisons made — sample too thin to prove anything"


@pytest.mark.parametrize("field", [
    "trend", "rs10", "pct_from_high", "pct_from_low", "nr7",
    "inside_day", "rsi", "atr_pct", "swing_patterns", "reversal_day",
])
def test_each_feature_field_is_unchanged_by_future_bars(daily_bars, field):
    """Same assertion per field, so a failure names the guilty feature rather
    than just saying the profile differs."""
    bars_by_sym, nifty = daily_bars
    checked = 0
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars, n=8):
            full = _profiles(bars, nifty, session)
            trunc = _profiles(bars, nifty, session, truncate_at=session)
            if full is None or trunc is None:
                continue
            assert full[field] == trunc[field], (
                f"LOOKAHEAD in feature '{field}' for {sym} on {session}: "
                f"{full[field]!r} with future bars vs {trunc[field]!r} without")
            checked += 1
    assert checked >= 10, f"only {checked} comparisons for '{field}'"


def test_day_T_own_bar_is_excluded_not_merely_the_future(daily_bars):
    """A subtler failure than using future data: using session T's OWN bar,
    which is not known before T's open. The last bar feeding the profile must
    be strictly earlier than the session being scored."""
    bars_by_sym, nifty = daily_bars
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars, n=6):
            series = [b for b in bars if _date(b) < session]
            if len(series) < 60:
                continue
            assert _date(series[-1]) < session
            # and the profile's own close must be that earlier bar's close
            prof = _profiles(bars, nifty, session)
            if prof:
                assert prof["close"] == series[-1]["close"], (
                    f"{sym} {session}: profile close is not the last PRIOR bar's close")


def test_bulkowski_patterns_use_no_confirmation_bar_after_the_signal(daily_bars):
    """Pattern libraries often require a confirming bar AFTER the pattern. If
    scan_daily_patterns did that, a pattern reported for session T would need
    a bar at or after T, and removing future bars would change the list."""
    bars_by_sym, nifty = daily_bars
    seen_any = 0
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars, n=10):
            full = _profiles(bars, nifty, session)
            trunc = _profiles(bars, nifty, session, truncate_at=session)
            if not full or not trunc:
                continue
            names_full = sorted(p["name"] for p in full["swing_patterns"])
            names_trunc = sorted(p["name"] for p in trunc["swing_patterns"])
            assert names_full == names_trunc, (
                f"{sym} {session}: pattern set changes without future bars — "
                f"{names_full} vs {names_trunc}")
            seen_any += len(names_full)
    # Not an assertion about edge, just that the test exercised real patterns
    # rather than passing because nothing ever fires.
    assert seen_any > 0, "no swing pattern fired in the sample — test proved nothing"


def test_reversal_day_uses_no_future_bar(daily_bars):
    bars_by_sym, nifty = daily_bars
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars, n=8):
            full = _profiles(bars, nifty, session)
            trunc = _profiles(bars, nifty, session, truncate_at=session)
            if not full or not trunc:
                continue
            assert full["reversal_day"] == trunc["reversal_day"], f"{sym} {session}"


def test_seasonality_is_a_published_constant_not_an_in_sample_estimate():
    """March effect must come from a fixed, cited figure — not from fitting
    the same sample the strategy is tested on, which would be lookahead of the
    worst kind: the answer derived from the data it is then scored against."""
    import inspect
    src = inspect.getsource(seasonality.march_effect)
    # it takes a month and a side, and no price data
    sig = inspect.signature(seasonality.march_effect)
    assert list(sig.parameters) == ["month", "side"], sig
    assert "MARCH_EFFECT_POINTS" in src
    assert isinstance(seasonality.MARCH_EFFECT_POINTS, (int, float))
    # nothing resembling estimation
    for banned in ("mean(", "stdev(", "fit(", "regress", "sum(", "bars", "closes"):
        assert banned not in src, f"march_effect appears to compute from data: {banned!r}"
    # and it only fires in March
    assert seasonality.march_effect(3, "long") is not None
    assert all(seasonality.march_effect(m, "long") is None for m in range(1, 13) if m != 3)


def test_the_score_itself_is_unchanged_by_future_bars(daily_bars):
    """End to end: the number premarket_picks() ranks on."""
    bars_by_sym, nifty = daily_bars
    cfg = scanner.config.SCANNER
    compared = 0
    for sym, bars in bars_by_sym.items():
        for session in _sample_sessions(bars, n=8):
            full = _profiles(bars, nifty, session)
            trunc = _profiles(bars, nifty, session, truncate_at=session)
            if not full or not trunc:
                continue
            for side in ("long", "short"):
                a = scanner.premarket_score(full, cfg, side, date_iso=session)
                b = scanner.premarket_score(trunc, cfg, side, date_iso=session)
                assert a[0] == b[0], f"{sym} {session} {side}: score {a[0]} vs {b[0]}"
                compared += 1
    assert compared >= 16
