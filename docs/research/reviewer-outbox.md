# Reviewer outbox

Replies to `reviewer-inbox.md`. Newest at the top, with the entry number.

---

## Re: Entry 1 — partial. Steps 1b, trials.md and splits.py done; step 1 running; two decisions needed

**Status: NOT done.** Step 1b is complete and passed. Step 1 (null test) is
**running now** and will take ~5 hours; it is not finished, so the full
ten-section status report is not yet written. Per the inbox's "or blocked"
clause this is going back early, because there are two decisions I should not
take alone and one of them is blocking the schedule.

Full detail: `docs/research/report-2026-09-20.md` is the previous report and
has **not** been rewritten yet — it will be, once step 1 lands.

### Done

| Item | Result |
| --- | --- |
| `trials.md` mirror, all 34 entries | `e7320e5` |
| `splits.py` + import-boundary test | `e1db066` — 20 tests, suite 244 green |
| Pre-registration, step 1b | `e340127`, committed **before** the run |
| **Step 1b lookahead proof** | **PASS — all nine features** |
| Pre-registration, step 1 | `e4545e0`, committed **before** the code was written |
| Test A replication | exact: 201 trades, net −0.3560R, t = −3.589 |
| Q2 earnings feasibility | **recommend skipping 3d** — see below |

### Step 1b — no lookahead in any of the nine features

16 tests. The assertion is that a feature computed for session T is
**bit-identical whether or not the input series contains session T and
everything after it**. Day T's own bar is excluded (profile close equals the
last *prior* bar's close), Bulkowski patterns change not at all when future
bars are removed, and `march_effect` takes `(month, side)` and no price data —
a published constant, not an in-sample fit.

Vacuity guards held: ≥20 whole-profile comparisons, ≥10 per field, and at
least one swing pattern actually fired. **Nothing is excluded from step 2.**

### Test A replication — the inferred t is now measured

My earlier `t ≈ −1.0` for gross was an estimate. Measured:

| | n | mean | sd | t | 95% CI |
| --- | --- | --- | --- | --- | --- |
| NET | 201 | −0.3560R | 1.4063 | **−3.589** | [−0.5504, −0.1616] |
| GROSS | 201 | −0.1021R | 1.3948 | **−1.038** | **[−0.2949, +0.0907]** |

Friction +0.2539R. The gross interval contains zero, so the estimate was
right and is now properly derived.

**Sizing facts you asked to be recorded**, and they confirm your description:

| | |
| --- | --- |
| Realised R | median **₹101.2**, mean ₹122.2 (₹35.5 – ₹603.2) |
| Stop distance | median **42.4 bp**, mean 50.9 bp |
| Notional | median ₹19,702 = the ₹33,000 cap × the 0.6 size factor |
| Cost/trade | ₹25.55 |
| `trail_after_r` | `None` — brackets are fixed, confirmed |

The 1% risk rule never binds: at a 42 bp stop it would permit ~₹236k of
notional against a ₹33k cap. **The cap sizes every position**, then the size
factor scales it.

One correction to your figure: the per-trade average of 1/(1+RR) over the real
trades' actual ratios (median 2.238) is **31.26%**, not 31.9%. Used as the
reference line only, per your instruction.

### Step 1 — running, ~5 hours, and this is the blocker

Pre-registered and started as specified: real harness (`run_backtest` with the
null injected, not a re-implementation), 200 seeds × 2 cost modes, matched on
frequency, brackets, hour profile, long/short mix and stop sizing via joint
bootstrap triples.

**Measured cost: ~45 s per seed → ~5 hours for 400 runs.** Parallelising is
not available: each worker needs ~1.2 GB for the candle cache and the machine
has ~1.1 GB free.

Two single-seed probes during calibration gave gross **−0.068R** and
**−0.029R** (one seed's standard error is ~0.06R, so these are noise
individually). I mention them only because their midpoint sits near the
**±0.05R** band, so the pass rule may turn out to be tight. I am **not**
adjusting it — it is pre-registered.

### Decisions I need from you

**D1 — accept the 5-hour serial run, or approve a documented deviation?**
The prereg says 100 symbols, 495 sessions, 200 seeds. Running each seed on a
random ~25-symbol subset would cut it to ~75 minutes.
*Options:* (a) let the faithful run finish, ~5 h; (b) approve the subset
deviation, recorded as resource-driven.
**Recommendation: (a).** It is already running, the deviation is not settled
by the pre-registration, and changing the design for speed right after seeing
a preliminary number is the habit this process exists to prevent. Take (b)
only if the schedule matters more than the cleanliness.

**D2 — RESOLVED 2026-09-20: skip 3d.** Recorded in
`docs/research/skipped-3d-earnings-drift.md`. Original question below for the
record.

**D2 — install `lxml` to retry earnings dates, or skip 3d now?**
The 15-minute check found no free path to historical earnings *announcement*
dates for 2024-09 → 2026-09:
- `earnings_dates` — blocked, missing `lxml`
- `calendar` — next earnings date only (Oct 2026), no history
- `quarterly_income_stmt` — 5 quarters, only back to **2025-03**, and these
  are fiscal quarter-**end** dates, not announcement dates; the lag between
  them varies by weeks per company and would misdate the event
- `info` — one timestamp, flagged `isEarningsDateEstimate: True`

*Options:* (a) skip 3d and record why; (b) install `lxml` and retry.
**Recommendation: (a).** `lxml` is small and reversible, but it is a
dependency addition your brief says to check first, and even with it
yfinance's historical depth for NSE names is uncertain — likely spending the
dependency and still missing the window.

### Repo state

Branch `research/phase-2-new-hypotheses`, 6 commits, 1,403 insertions.

Added: `docs/research/{orientation,report-2026-09-20,trials,prereg-lookahead,prereg-null-test}.md`,
`backend/research/{__init__,splits}.py`, `backend/tests/{test_research_splits,test_lookahead_proof}.py`.
**Modified: none. Deleted: none.**

**Live order path and credentials untouched.** The only `backend/` additions
are the research package and two test files; no engine, broker, risk, config
or credential file was read, modified or executed. `min_confidence_to_trade:
0` is passed per-run as a research override — the live default is unchanged
and the gate is not "fixed".
