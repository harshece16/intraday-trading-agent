"""Raw (non-partial) ICs on the SAME sample run A used, so A2's collapse is
like-for-like. Corrects my own inconsistency: step 2 used YEARS='4y' and the
follow-ups used '8y', so A's 1546 sessions are a superset of step 2's 561 and
the two cannot be compared directly.

Not a new hypothesis — the same measurement step 2 already ran, on the sample
A actually used. Reported as part of A.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/Users/harshgupta/Projects/webapp/backend")

from research.step2_followups import (build_rows, session_ic, report, SURVIVORS,
                                      attach_kite_target)

per_session = build_rows()
sessions = sorted(per_session)
print(f"\nSample actually used by A: {len(sessions)} sessions, "
      f"{sessions[0]} -> {sessions[-1]}", flush=True)

print("\nRAW ICs on that same sample (the denominator A2's partials collapse from):",
      flush=True)
out = {}
for key, sign in SURVIVORS:
    series = []
    for recs in per_session.values():
        ic = session_ic(recs, key, sign, "target")
        if ic is not None:
            series.append(ic)
    out[key] = report(f"{key} (raw, 8y sample)", series)

# How many of A's sessions predate step 2's window?
cut = "2023-09-25"
older = sum(1 for s in sessions if s < cut)
print(f"\n{older} of {len(sessions)} sessions ({100*older/len(sessions):.0f}%) "
      f"predate step 2's earliest session ({cut}).", flush=True)
