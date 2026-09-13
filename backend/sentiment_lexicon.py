"""
Finance-specific sentiment lexicon, tuned for Indian market headlines
(order wins, promoter pledges, SEBI probes, circuits, brokerage calls).
score_text() returns a value in [-1, 1].

Lexicon scoring can't read sarcasm, context or "already priced in" —
treat it as a tilt, not a signal on its own.
"""

import math
import re

POSITIVE = {
    "beats estimates": 2.0, "beat estimates": 2.0, "tops estimates": 2.0, "beats street": 1.8, "beats": 1.0,
    "record profit": 2.0, "record revenue": 1.5, "profit rises": 1.5, "profit jumps": 1.5,
    "profit surges": 1.8, "strong quarter": 1.2, "revenue growth": 1.0, "margin expansion": 1.2, "turnaround": 0.8,
    "upgrade": 1.5, "upgraded": 1.5, "upgrades": 1.5, "rating upgrade": 1.5, "outperform": 1.0, "overweight": 0.8,
    "buy rating": 1.2, "target raised": 1.2, "raises target": 1.2,
    "raises guidance": 1.8, "raises outlook": 1.8,
    "order win": 1.5, "wins order": 1.5, "bags order": 1.5, "secures order": 1.5, "receives order": 1.5,
    "letter of award": 1.3, "contract win": 1.3, "wins contract": 1.3,
    "buyback": 1.3, "buy back": 1.3, "bonus issue": 1.0, "dividend": 0.6, "stake increase": 0.8,
    "promoter buys": 1.0, "promoter increases stake": 1.0,
    "acquisition": 0.6, "acquires": 0.6, "partnership": 0.5, "expansion": 0.6, "approval": 0.8,
    "strong demand": 1.0, "debt free": 1.0, "deleveraging": 0.8,
    "surge": 1.0, "surges": 1.0, "soars": 1.0, "rallies": 0.8, "jumps": 0.8, "gains": 0.5, "rises": 0.5, "climbs": 0.5,
    "upper circuit": 1.0, "record high": 0.8, "all-time high": 0.8, "52-week high": 0.8, "bullish": 0.8,
}

NEGATIVE = {
    "misses estimates": 2.0, "miss estimates": 2.0, "misses street": 1.8, "misses": 1.0,
    "profit falls": 1.5, "profit drops": 1.5, "profit declines": 1.5, "net loss": 1.5, "loss widens": 1.8,
    "weak quarter": 1.2, "margin pressure": 1.0, "weak demand": 1.0, "headwinds": 0.8,
    "downgrade": 1.5, "downgraded": 1.5, "downgrades": 1.5, "rating downgrade": 1.5,
    "underperform": 1.0, "underweight": 0.8, "sell rating": 1.2, "target cut": 1.2, "cuts target": 1.2,
    "cuts guidance": 1.8, "lowers guidance": 1.8, "cuts outlook": 1.8,
    "probe": 1.3, "investigation": 1.2, "raid": 1.5, "fraud": 2.0, "scam": 2.0, "insolvency": 1.8,
    "penalty": 1.2, "sebi order": 1.0, "show cause": 1.0, "tax demand": 1.0, "gst notice": 1.0,
    "ban": 1.0, "lawsuit": 1.0, "default": 1.5,
    "resigns": 1.0, "resignation": 1.0, "pledge": 0.8, "stake sale": 0.8, "promoter sells": 1.0,
    "qip": 0.3, "layoffs": 0.8, "strike": 0.8, "recall": 1.0, "outage": 0.8, "warning": 0.8,
    "plunge": 1.2, "plunges": 1.2, "slumps": 1.0, "tumbles": 1.0, "crash": 1.5,
    "falls": 0.5, "drops": 0.5, "declines": 0.5, "slips": 0.5, "sheds": 0.5,
    "lower circuit": 1.0, "52-week low": 0.8, "bearish": 0.8,
}

_NEGATORS = r"(?:not|no|fails to|failed to|didn't|did not)\s+"

_PATTERNS = sorted(
    [(phrase, weight, sign) for lexicon, sign in ((POSITIVE, 1), (NEGATIVE, -1)) for phrase, weight in lexicon.items()],
    key=lambda x: -len(x[0]),
)
_COMPILED = [
    (weight, sign, re.compile(r"\b" + re.escape(phrase) + r"\b"), re.compile(_NEGATORS + re.escape(phrase) + r"\b"))
    for phrase, weight, sign in _PATTERNS
]


def score_text(text):
    text = (text or "").lower()
    raw = 0.0
    for weight, sign, pattern, negated_pattern in _COMPILED:
        total = len(pattern.findall(text))
        if total:
            negated = len(negated_pattern.findall(text))
            raw += sign * weight * (total - 2 * negated)
            text = pattern.sub(" ", text)
    return math.tanh(raw / 2)
