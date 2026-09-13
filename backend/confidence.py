"""
A per-trade confidence check — deliberately NOT a probability of profit.
Nothing in this codebase has enough closed trades yet to calibrate a real
probability (see evaluation.py's own docstring on the evidence boundary),
so presenting one would be exactly the fabricated-precision this project
has repeatedly avoided. What this produces instead is a transparent,
reproducible composite of two honest things:

  1. Local setup strength — how far past its own bar this specific
     checklist read cleared (edge margin, category breadth, regime
     clarity). This is knowable today from one candle.
  2. System-wide evidence — whether the Dimaag Scorecard's own three
     statistics (expectancy, Deflated Sharpe Ratio, Information
     Coefficient) currently show a real, proven edge at all.

A trade can only earn a high confidence score if BOTH are true. A locally
"perfect" checklist pass on a system with zero proven edge is capped low —
because a clean-looking setup means nothing statistically until the system
around it has demonstrated it can tell winners from losers better than
chance. This is what gates whether an F&O order is allowed to fire
(config.FNO["min_confidence_to_trade"]).
"""

import trader_brain

_DEFAULTS = trader_brain.DEFAULTS


def _local_setup_score(analysis: dict, side: str) -> dict:
    p = analysis
    win_score = p.get("bull_score") if side == "LONG" else p.get("bear_score")
    lose_score = p.get("bear_score") if side == "LONG" else p.get("bull_score")
    min_edge = _DEFAULTS["min_edge"]
    min_confirmations = _DEFAULTS["min_confirmations"]
    if win_score is None or lose_score is None:
        return {"score": 0, "edge_margin_pts": None, "categories": None, "regime_clarity_pct": None,
                "note": "No live checklist read for this side yet."}

    edge = win_score - lose_score
    edge_margin = max(0.0, edge - min_edge)               # how far past the minimum required edge
    edge_component = min(40.0, edge_margin * 8)            # 5 pts of extra edge -> full 40 credit

    cats = p.get("confirmations" if side == "LONG" else "bear_confirmations") or []
    breadth_component = min(30.0, len(cats) / max(min_confirmations, 1) * 30)

    adx = p.get("adx") or 0
    adx_trend = _DEFAULTS["adx_trend"]
    regime_clarity = min(1.0, adx / adx_trend) if adx_trend else 0.0
    regime_component = regime_clarity * 30

    score = round(edge_component + breadth_component + regime_component)
    return {
        "score": min(100, score),
        "edge_margin_pts": round(edge_margin, 1),
        "categories": f"{len(cats)} confirming ({', '.join(cats) or 'none'})",
        "regime_clarity_pct": round(regime_clarity * 100),
    }


def _system_multiplier(scorecard: list) -> dict:
    if not scorecard:
        return {"multiplier": 0.25, "reason": "No Dimaag Scorecard data yet — treat every trade as unproven."}
    statuses = [row["status"] for row in scorecard]
    if all(s == "pass" for s in statuses):
        return {"multiplier": 1.0, "reason": "All three Scorecard statistics currently pass — the system "
                                             "has shown real, measured edge, not just a clean-looking setup."}
    if any(s == "fail" for s in statuses):
        failing = [row["criterion"] for row in scorecard if row["status"] == "fail"]
        return {"multiplier": 0.25, "reason": f"Scorecard currently FAILS on: {', '.join(failing)} — a strong "
                                              f"local setup can't outweigh proven-absent system edge."}
    return {"multiplier": 0.5, "reason": "Scorecard has no failures yet, but not enough data to confirm a real "
                                         "edge either — confidence is capped until it does."}


def score_trade(analysis: dict, side: str, scorecard: list) -> dict:
    """Full confidence breakdown for one candidate trade. `analysis` is a
    trader_brain analysis dict (state.indicators[symbol] shape); `side` is
    "LONG" or "SHORT"; `scorecard` is database.journal_summary()['scorecard']."""
    local = _local_setup_score(analysis, side)
    sysm = _system_multiplier(scorecard)
    final = round(local["score"] * sysm["multiplier"])
    label = ("High, evidence-backed" if final >= 75 else
             "Moderate" if final >= 50 else
             "Low" if final >= 25 else "Very low")
    return {
        "score": final, "label": label,
        "local_setup": local, "system_evidence": sysm,
        "explanation": f"Local setup scored {local['score']}/100, scaled by a "
                       f"{sysm['multiplier']:.2f}x system-evidence factor ({sysm['reason']})",
    }
