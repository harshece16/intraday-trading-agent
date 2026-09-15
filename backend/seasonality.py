"""
Seasonality — real, cited calendar effects only. Before anything went in
here, the commonly-repeated "seasonal" claims for Indian markets were
checked against actual published research, not assumed:

  Muhurat trading "always green"         Once a year -> ~10-20 data points
                                          ever, and every source found was
                                          broker marketing content, not a
                                          study. REJECTED — not encoded.
  Festival gold demand -> stock price    Physical gold-demand seasonality
  (e.g. Titan around Akshaya Tritiya)    around Akshaya Tritiya/Dhanteras is
                                          real (World Gold Council data), but
                                          every source connecting that to a
                                          tradable stock-price move was
                                          pre-festival news hype, not a
                                          backtested study. REJECTED.
  Halloween Indicator / Sell in May      Genuinely strong evidence globally
                                          (Bouman & Jacobsen, American
                                          Economic Review 2002, replicated
                                          since) — but multiple sources
                                          confirm India was an exception
                                          where it did NOT hold. REJECTED
                                          for this market.
  Day-of-week effects                    Real in older NSE studies; a
                                          2010-2019 study found the effect
                                          had decayed to nothing. REJECTED.

Two effects cleared the bar — real, cited, statistically stated (not
folklore) — and are encoded below, each sized as a single real study, not
proof: a small, honest weight relative to a confirmed Bulkowski pattern
(15-20 pts) or a Murphy reversal day (10-18 pts) elsewhere in the scanner.
Like every other evidence source here, this doesn't get to assume it
helps — database.factor_ic() measures whether it actually does.
"""

MARCH_EFFECT_POINTS = 4.0
# Elangovan, Irudayasamy & Parayitam (2022), Asia-Pacific Financial Markets,
# S&P BSE 500 + NIFTY 500, Apr 2011-Mar 2021, GARCH model: a real,
# significant NEGATIVE March return (BSE 500 coefficient -3.04, t=-1.84;
# NIFTY 500 -3.00, t=-1.82; p<.01). All other months insignificant.
# Mechanism contested — the authors point to Union Budget assimilation lag
# (the Budget is presented Feb 1, effects lingering into March), though
# India's fiscal-year-end (Mar 31) institutional rebalancing is an equally
# plausible confound the paper doesn't fully rule out. Single study,
# moderate confidence — sized accordingly.


def march_effect(month: int, side: str):
    """Returns (points, reason) for the given calendar month (1-12) and
    side ("long"/"short"), or None outside March. Negative March bias helps
    shorts, works against longs."""
    if month != 3:
        return None
    s = -1.0 if side == "long" else 1.0
    return (
        MARCH_EFFECT_POINTS * s,
        "March has shown a real, statistically significant negative NIFTY 500/BSE 500 return "
        "(Elangovan et al. 2022, p<.01) — " + ("longs fight this seasonal headwind" if s < 0 else "a modest tailwind for shorts"),
    )


def budget_day_note(date_iso: str):
    """India's Union Budget is presented Feb 1 (fixed date since the 2017
    reform). Historical direction on the day itself is close to a coin flip
    (Samco/Arihant Budget-day studies: Sensex positive 7 of the last 14
    Budget days since 2014) — real data, but no usable directional edge.
    What IS more consistent is elevated volatility around the announcement,
    typically easing afterward — but not measured here precisely enough to
    size a real multiplier, so this stays informational only: a plain note
    in the market read, never a score or size adjustment. Doesn't attempt
    to detect a same-day date shift if Feb 1 falls on a holiday."""
    if date_iso[5:10] == "02-01":
        return "Union Budget day — historically close to a coin flip in direction, but expect elevated volatility around the announcement"
    return None
