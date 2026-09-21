# Results — 3a, opening-range breakout on high relative volume (trial 35)

## Verdict: **FAIL**

**Primary statistic (top-20 relative volume, friction rule, five-position
cap): mean net return −12.09 bp per session, t = −2.71, over 303 sessions.**
The pass rule required net > 0 with t > 2 and a positive sign in both
halves. The net is negative, significantly so, and negative in both halves.

**This is not "untestable".** Amendment 3.3's power check: sd of session
means **77.67 bp**, n = **303**, so the smallest net effect detectable at
t = 2 is **8.92 bp**, under the 16.60 bp threshold. The pre-flight count was
**303 sessions** against the 60 required. Neither rule fired. The null reads
as: *no net edge larger than 8.92 bp exists in this design on this sample —
and the point estimate is a loss.*

One run. No re-run, no crash. Trial count **34 → 35**.

| Provenance | |
| --- | --- |
| Last amendment before code | `815ba4c` (amendment 3, Entry 9) |
| Code + synthetic fill tests | `3841124` — postdates the amendment (amendment 1 j) |
| Pre-flight, committed on its own before the run | `9f9ac61` |
| Data | Kite 5-min cache, universe A, 100 names, 2024-09-20 → 2026-01-01, **selection only**; held-out bars dropped at load |
| Machine output | `step3a_preflight.json`, `step3a_result.json`, `data/step3a_trades.json` |

## Pre-flight (no return read)

| | Top-20 set | All 100, no filter |
| --- | --- | --- |
| Candidate signals | 5,275 | 28,600 |
| **Removed by the friction rule** (stop < 110.67 bp) | **1,139 (21.6%)** | 12,745 (44.6%) |
| Surviving | 4,136 | 15,855 |

319 selection sessions in the cache; 303 have a top-20 set (the first 14
cannot, by the eligibility rule, and 2 more lack opening bars). Median
opening-range width **107.3 bp** — descriptive only. *Under the withdrawn
median-width rule (111 bp) this design would have been withdrawn unrun;
Entry 9's per-trade rule is why it was testable at all.*

## Primary result

| | Net bp | t | Gross bp | t | Net R | Gross R | Trades | Sessions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **All** *(pass rule)* | **−12.09** | **−2.71** | +4.52 | +1.01 | −0.08 | +0.01 | 1,656 | 303 |
| First half (before 2025-05-15) | −1.18 | −0.15 | +15.43 | +1.93 | −0.01 | +0.07 | 801 | 144 |
| Second half (from 2025-05-15) | **−21.96** | **−5.03** | −5.36 | −1.23 | −0.14 | −0.04 | 855 | 159 |
| Longs | −14.72 | −2.09 | +1.89 | +0.27 | −0.10 | −0.01 | 891 | 272 |
| Shorts | −13.31 | −1.77 | +3.29 | +0.44 | −0.08 | +0.01 | 765 | 265 |

Session means are the unit (amendment 1 a). Secondary, no pass rule: pooled
per-trade mean net **−15.87 bp**.

- **Gross is +4.52 bp and not distinguishable from zero (t = +1.01).** The
  breakout, conditioned on relative volume, does not continue far enough to
  be measured, let alone to cover 16.60 bp. Net − gross = −16.61 bp, the
  modelled round trip, as it should be.
- **The halves disagree, and in the wrong order for a tradable effect.** The
  first half's gross of +15.43 bp (t = +1.93, not significant) is gone in
  the second half (−5.36 bp). I am **not** reading that as decay — it is two
  sub-sample numbers and no trend test was pre-registered — only recording
  that neither half is net positive.
- **No side asymmetry.** Longs and shorts lose about the same. §D.1's
  −6.42 bp long-book handicap is not visible here at this sample size.
- Exits: 1,408 timeout at 15:10, 246 stops, 2 gap-through stops. Median stop
  185 bp; 5.47 trades per session.

## Secondary lines — descriptive, no pass rule, not trials

Shown after the verdict, as Entry 10 §D requires.

| | Net bp | t | Gross bp | t | Trades |
| --- | --- | --- | --- | --- | --- |
| Uncapped, top-20 set | −14.99 | −5.38 | +1.61 | +0.58 | 4,136 |
| Uncapped, all 100, **no relative-volume filter** | −13.64 | −6.25 | +2.96 | +1.36 | 15,040 |

All three lines say the same thing: gross within a few bp of zero, net
about one round trip below it. **The relative-volume filter adds nothing
measurable** (+1.61 bp gross with it, +2.96 bp without). Per Entry 9 neither
line justifies a follow-up variant, and none is proposed.

(The all-100 line has 15,040 trades against the pre-flight's 15,855
surviving because it is restricted to the same 303 sessions as the primary
line, so the three are comparable.)

## What this does and does not establish

- **Establishes:** this one pre-specified opening-range design, on NIFTY 100
  names at 5-minute resolution, loses about the cost of trading it. ~~It is
  the fifth time the project has found gross ≈ 0 and net ≈ −cost.~~
  *(Withdrawn, Entry 11: an uncited count, and wrong in kind. The `atr_pct`
  spreads, universe B and 3c found a small, sometimes significant gross
  effect that fell short of cost. 3a is different: its gross, +4.52 bp at
  t = +1.01, is not distinguishable from zero at all.)*
- **Does not establish** that no opening-range design works. One variant is
  not a search — and the pre-registration forbids turning this into one: no
  09:15–09:45 range, no ATR stop, no different filter, no different cap.
- **Caveats carried:** `costs.py`'s rates are **unverified** against the
  broker's current tariff, which sits under the 16.60 bp hurdle (Entry 8
  §C.9). Survivorship: today's NIFTY 100 on history. ~15 months of data. The
  implementation is self-contained, so **no harness-bias figure applies** and
  the result is not directly comparable to §51's −0.356R (amendment 2).
- **Held-out window: untouched.** A fail earns no held-out look.

## Stopped

Per Entry 8 §F.4 and Entry 10 §F: stopped for review. 3b not started; no
universe B replication proposed.
