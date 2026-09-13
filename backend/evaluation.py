"""
Statistical honesty for backtests, following ML4Trading's "evidence boundary"
(ch 1: separating exploration/tuning from confirmation/evaluation) and
Bailey & López de Prado's Deflated Sharpe Ratio (cited in the same chapter).

We have run many backtest configurations this week — strategies, entry
modes, universes, intervals. Each run is a trial: if you try enough
configurations, one will look good by chance alone, even with zero real
edge. The Deflated Sharpe Ratio corrects for that by asking "how good would
the *best* of N random trials look, purely from luck?" and only crediting
a strategy with skill above that bar.

This does not require new data — it is a more honest way to read the
backtests we already have.
"""

import json
import math
import statistics
from pathlib import Path

TRIAL_LOG_PATH = Path(__file__).parent / "data" / "backtest_trials.json"
_NORMAL = statistics.NormalDist()


def sharpe_of_r_multiples(r_values):
    """Sharpe ratio computed on a list of per-trade R-multiples (mean / stdev,
    not annualized) — the natural unit for a strategy evaluated trade by
    trade rather than day by day."""
    if len(r_values) < 2:
        return None
    mean = statistics.mean(r_values)
    sd = statistics.stdev(r_values)
    return mean / sd if sd > 0 else None


def _moments(r_values):
    n = len(r_values)
    mean = statistics.mean(r_values)
    sd = statistics.stdev(r_values) if n > 1 else 0.0
    if sd == 0:
        return 0.0, 3.0
    skew = sum((x - mean) ** 3 for x in r_values) / n / sd ** 3
    kurt = sum((x - mean) ** 4 for x in r_values) / n / sd ** 4  # 3.0 = normal
    return skew, kurt


def expected_max_sharpe(n_trials, sharpe_std):
    """The Sharpe ratio you'd expect the BEST of n_trials independent, no-edge
    strategies to show, purely from luck (Bailey & López de Prado, 2014)."""
    if n_trials <= 1:
        return 0.0
    euler_mascheroni = 0.5772156649
    return sharpe_std * (
        (1 - euler_mascheroni) * _NORMAL.inv_cdf(1 - 1 / n_trials)
        + euler_mascheroni * _NORMAL.inv_cdf(1 - 1 / (n_trials * math.e))
    )


def deflated_sharpe_ratio(r_values, n_trials, sharpe_std=None):
    """Probability that the strategy's true Sharpe ratio exceeds the luck
    baseline for n_trials attempts, given the non-normality of the actual
    trade returns. Returns None with a reason when there isn't enough data
    to say anything — never a fabricated confidence number."""
    n = len(r_values)
    if n < 10:
        return {"dsr": None, "note": f"Only {n} trades — need at least 10 before a Sharpe ratio means anything."}
    sr = sharpe_of_r_multiples(r_values)
    if sr is None:
        return {"dsr": None, "note": "All trades had the same result; no variance to measure."}
    skew, kurt = _moments(r_values)
    sharpe_std = sharpe_std if sharpe_std is not None else abs(sr) / 2 or 0.5
    sr0 = expected_max_sharpe(max(n_trials, 1), sharpe_std)
    denom = math.sqrt(max(1e-9, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    dsr = _NORMAL.cdf(z)
    return {
        "dsr": round(dsr, 3), "sharpe": round(sr, 3), "luck_baseline_sharpe": round(sr0, 3),
        "n_trials": n_trials, "n_trades": n,
        "note": "DSR is the probability the true Sharpe ratio beats what pure luck would produce "
                f"across {n_trials} attempted configurations. Below 0.95, don't trust the backtest.",
    }


def trial_count() -> int:
    """How many backtester.py runs have been logged, without adding one — for
    read-only callers like the dashboard scorecard."""
    if not TRIAL_LOG_PATH.exists():
        return 0
    try:
        return len(json.loads(TRIAL_LOG_PATH.read_text()))
    except (json.JSONDecodeError, OSError):
        return 0


def scorecard(trade_stats, dsr, ic):
    """A report card across the distinct things a trading system's quality
    actually rests on. This is deliberately NOT a single 'IQ' number — no
    validated psychometric like that exists for a trading system, and
    compressing independent, differently-uncertain measurements into one
    score would hide exactly the uncertainty this codebase has otherwise
    tried hard to keep visible (see backend/evaluation.py's own docstring).
    Every row is graded against a bar already used elsewhere in this code,
    computed from real logged data, and says "not enough data yet" rather
    than guessing when there isn't enough to grade."""
    rows = []

    n = trade_stats.get("closed_trades", 0)
    if n < 10:
        rows.append({
            "criterion": "Trading edge (expectancy)", "status": "not_enough_data",
            "detail": f"Only {n} closed trade{'s' if n != 1 else ''} — Van Tharp (Trade Your Way to "
                      f"Financial Freedom, ch 6) needs a real sample before expectancy means anything.",
        })
    else:
        exp = trade_stats.get("expectancy_r")
        ok = exp is not None and exp > 0
        rows.append({
            "criterion": "Trading edge (expectancy)", "status": "pass" if ok else "fail",
            "detail": f"Expectancy {exp:+.2f}R over {n} closed trades (Van Tharp, Trade Your Way to "
                      f"Financial Freedom, ch 6). {'Positive' if ok else 'Not positive'} — the bare "
                      f"minimum for a system worth sizing up.",
        })

    if dsr.get("dsr") is None:
        rows.append({"criterion": "Statistical significance (Deflated Sharpe Ratio)",
                     "status": "not_enough_data", "detail": dsr.get("note", "")})
    else:
        ok = dsr["dsr"] >= 0.95
        rows.append({
            "criterion": "Statistical significance (Deflated Sharpe Ratio)", "status": "pass" if ok else "fail",
            "detail": f"DSR {dsr['dsr']:.2f} across {dsr['n_trials']} backtest trials (Bailey & López de "
                      f"Prado, 2014, cited in Jansen, Machine Learning for Trading, ch 1) — "
                      f"{'clears' if ok else 'below'} the 0.95 confidence bar this codebase requires "
                      f"before trusting a backtested Sharpe ratio.",
        })

    if ic.get("ic") is None:
        rows.append({"criterion": "Predictive skill (Information Coefficient)",
                     "status": "not_enough_data", "detail": ic.get("note", "")})
    else:
        ok = ic["ic"] > 0
        rows.append({
            "criterion": "Predictive skill (Information Coefficient)", "status": "pass" if ok else "fail",
            "detail": f"IC {ic['ic']:+.3f} across {ic['pairs']} session pairs (Grinold's fundamental law "
                      f"of active management, cited in Jansen, Machine Learning for Trading, ch 1) — "
                      f"{'ranks stocks better than chance' if ok else 'no better than chance yet'} "
                      f"(0 = none, ±1 = perfect).",
        })

    return rows


def log_trial(label) -> int:
    """Every backtester.py run is a trial in the evidence-boundary sense —
    count it, so the Deflated Sharpe Ratio has an honest n_trials without
    the user having to track it by hand."""
    TRIAL_LOG_PATH.parent.mkdir(exist_ok=True)
    trials = []
    if TRIAL_LOG_PATH.exists():
        try:
            trials = json.loads(TRIAL_LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            trials = []
    trials.append({"n": len(trials) + 1, "label": label})
    TRIAL_LOG_PATH.write_text(json.dumps(trials, indent=1))
    return len(trials)
