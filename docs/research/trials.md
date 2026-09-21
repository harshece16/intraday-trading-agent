# Backtest trial log

Committed, append-only mirror of `backend/data/backtest_trials.json`, which is
gitignored and therefore does not survive a clone. This file exists so the
multiple-testing count can be audited by someone who was not at the machine
that produced it.

**Why it matters.** The Deflated Sharpe Ratio
(`evaluation.deflated_sharpe_ratio`) discounts an observed Sharpe by the
number of configurations tried. That count is the denominator of every
significance claim in this project. Losing it, or understating it, makes every
backtest look better than it is.

## Rules

- **Every backtest run of a strategy variant increments the count.** The
  counter is `evaluation.log_trial(label)`.
- **Measurements do not increment it.** An IC computation, a return
  decomposition, or any read that does not select a strategy is a *research
  look*, recorded in its own section below.
- **A replication of an already-counted run does not increment it.**
  Re-running an identical configuration to recover its trade list is not a new
  attempt at finding an edge. Such runs are recorded here explicitly, marked
  *replication, not counted*.
- When the JSON and this file disagree, **the JSON is the source of truth** for
  the count; this file is the auditable record of what those counts were.

---

## Strategy trials — count as of 2026-09-20: **34**

| n | Label |
| --- | --- |
| 1 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 2 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 3 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 4 | `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d` |
| 5 | `sahab_dimaag ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'] 5m 55d walk-forward-3` |
| 6 | `sahab_dimaag NIFTY 100 scanner, top 25/day 5m 55d` |
| 7 | `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 10d` |
| 8 | `grid-search min_confidence_to_trade=40 min_rrr=1.2 nifty100 top5 5m 55d` |
| 9 | `grid-search min_confidence_to_trade=40 min_rrr=1.5 nifty100 top5 5m 55d` |
| 10 | `grid-search min_confidence_to_trade=40 min_rrr=1.8 nifty100 top5 5m 55d` |
| 11 | `grid-search min_confidence_to_trade=50 min_rrr=1.2 nifty100 top5 5m 55d` |
| 12 | `grid-search min_confidence_to_trade=50 min_rrr=1.5 nifty100 top5 5m 55d` |
| 13 | `grid-search min_confidence_to_trade=50 min_rrr=1.8 nifty100 top5 5m 55d` |
| 14 | `grid-search min_confidence_to_trade=60 min_rrr=1.2 nifty100 top5 5m 55d` |
| 15 | `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 55d` |
| 16 | `grid-search min_confidence_to_trade=60 min_rrr=1.8 nifty100 top5 5m 55d` |
| 17 | `grid-search min_confidence_to_trade=70 min_rrr=1.2 nifty100 top5 5m 55d` |
| 18 | `grid-search min_confidence_to_trade=70 min_rrr=1.5 nifty100 top5 5m 55d` |
| 19 | `grid-search min_confidence_to_trade=70 min_rrr=1.8 nifty100 top5 5m 55d` |
| 20 | `diagnostic re-run at live default config for segmentation analysis` |
| 21 | `diagnostic re-run, confidence gate off, for checklist-entry segmentation` |
| 22 | `diagnose_entry_edge checklist 5m 55d top5 gate-off` |
| 23 | `diagnose_entry_edge checklist 30m 55d top5 gate-off` |
| 24 | `diagnose_entry_edge baseline 5m 55d top5 gate-off` |
| 25 | `diagnose_entry_edge baseline 30m 55d top5 gate-off` |
| 26 | `swing_backtester long-only hold=1 top5 2y stop_atr=None` |
| 27 | `swing_backtester long-only hold=2 top5 2y stop_atr=None` |
| 28 | `swing_backtester long-only hold=3 top5 2y stop_atr=None` |
| 29 | `swing_backtester long-only hold=5 top5 2y stop_atr=None` |
| 30 | `sahab_dimaag NIFTY 100 scanner, top 5/day 5m 730d` — the gated deep backtest (report Test B) |
| 31 | `swing_backtester long-only hold=1 top5 2y stop_atr=None` |
| 32 | `swing_backtester long-only hold=2 top5 2y stop_atr=None` |
| 33 | `swing_backtester long-only hold=3 top5 2y stop_atr=None` |
| 34 | `swing_backtester long-only hold=5 top5 2y stop_atr=None` |

### What a reviewer should notice in this list

- **Entries 7–19 are a single 13-point grid search** over
  `min_confidence_to_trade` × `min_rrr`. That is 38% of the entire trial
  count spent on one parameter sweep of a strategy later shown to have no
  edge. It is exactly the search behaviour the DSR exists to penalise, and it
  is correctly counted.
- **Entries 26–29 and 31–34 are the same four swing configurations run
  twice.** The second run (31–34) was a re-execution on 2026-09-20. Under the
  replication rule above it arguably should not have incremented the counter,
  but `swing_backtester.py` logs unconditionally and it did. **The count is
  therefore conservative by up to 4** — it may overstate the number of
  genuinely distinct attempts. Left as-is: an overstated trial count makes the
  DSR stricter, not laxer, and correcting it downward would weaken a
  significance bar in our own favour.
- Entries 20–25 are diagnostics and segmentation runs. They re-ran strategy
  configurations, so counting them is defensible, though several are closer to
  measurement than to search.

**Test A of the status report — the 201-trade ungated run — is not in this
list.** It was executed through `run_backtest()` directly by an ad-hoc script
rather than through `backtester.py`'s `main()`, which is where `log_trial()`
is called. That is a gap in the counter's coverage: **driving `run_backtest()`
programmatically bypasses the trial log entirely.** Every phase-2 run does
exactly that, so phase 2 must log its trials here by hand.

---

## Research looks — measurements, not strategy selections

These do **not** increment the DSR trial count. They are recorded because a
look at the data is still a look, and a reviewer should be able to count them.

| # | Look | Date | Counted? |
| --- | --- | --- | --- |
| L1 | Daily rank IC of the composite pre-market score vs session return (436 days) — reported in `swing_backtester.py` output | 2026-09-20 | No — measurement |
| L2 | Loss attribution over the 201-trade sample: exit-reason split, gross vs net, by side, payoff arithmetic, holding time | 2026-09-20 | No — measurement on an existing trade list |
| L3 | Step 1b lookahead proof — nine pre-open features recomputed on truncated series | 2026-09-20 | No — a correctness check, no returns computed |
| L4 | Step 3d feasibility: can a free source give earnings announcement dates for 2024-09..2026-09? | 2026-09-20 | No — nothing backtested; see skipped-3d-earnings-drift.md |
| L5 | Step 1 random-entry null test, 200 seeds × 2 cost modes — **complete**, PASS at −0.0495R | 2026-09-20 | No — measures the harness, selects no strategy · `results-step1-null-test.md` |
| L6 | Step 2 data-quality gate (§D4): yfinance open→close vs Kite first-open→last-close on 29,949 overlapping stock-sessions — r = 0.9832, 18.55% differ by >25 bp | 2026-09-21 | No — a data check, produces no p-value |
| L7 | Step 2 rank IC — `atr_pct` (**band feature**, see results §Problem 2) | 2026-09-21 | No — measurement · `results-step2-feature-ic.md` |
| L8 | Step 2 rank IC — `rs10` | 2026-09-21 | No — measurement |
| L9 | Step 2 rank IC — `from_high` | 2026-09-21 | No — measurement |
| L10 | Step 2 rank IC — `from_low` (**sign coded backwards**, see results §Problem 1) | 2026-09-21 | No — measurement |
| L11 | Step 2 rank IC — `rsi` (**side-dependent band feature**) | 2026-09-21 | No — measurement |
| L12 | Step 2 session-difference — `trend` (up minus down, one test per §D2) | 2026-09-21 | No — measurement |
| L13 | Step 2 session-difference — `nr7` | 2026-09-21 | No — measurement |
| L14 | Step 2 session-difference — `inside` | 2026-09-21 | No — measurement |
| L15 | Step 2 session-difference — `pattern` (Bulkowski swing) | 2026-09-21 | No — measurement |
| L16 | Step 2 session-difference — `reversal` (Murphy reversal day) | 2026-09-21 | No — measurement |

| L17 | Step 2-A1 cross-correlations among `atr_pct`, `from_high`, `from_low` (exploratory) | 2026-09-21 | No — descriptive, selects nothing · `prereg-step2-followups.md` |
| L18 | Step 2-A2 partial ICs, each survivor residualised on the others | 2026-09-21 | No — measurement; also gates the held-out look per amendment 8 |
| L19 | Step 2-B rank IC of the three survivors vs the **tradable Kite target** (09:20 open → 15:10 close), 2024-09-20 → 2026-01-01 | 2026-09-21 | No — measurement; pass rule committed before running |
| L20 | Step 2-C `atr_pct` quintile spread in bp vs round-trip cost | 2026-09-21 | No — descriptive, no backtest · `results-step2-followups.md` |
| L21 | Raw ICs on A's own 8y sample — the correct denominator for L18, added after finding I had changed `YEARS` from 4y to 8y between step 2 and the follow-ups | 2026-09-21 | No — the same measurement as L7/L9/L10 on a different sample; logged rather than folded into L18 silently |

| L22 | Null diagnostic (Entry 3 §A) — 20 seeds with trade lists persisted; (a)-(d) attribution of the −0.05R harness bias | 2026-09-21 | No — measures the harness · `results-null-diagnostic.md` |

| L23 | 3c §A unconditional decomposition — overnight **+16.78bp** (t=+9.50), intraday **−6.94bp** (t=−2.80) | 2026-09-21 | No — measurement · `prereg-3c-overnight-intraday.md` |
| L24 | 3c §B volatility-sorted — **mechanism HOLDS**, both legs monotone across 5 quintiles | 2026-09-21 | No — measurement |
| L25 | 3c §C tradable Kite window — intraday spread +8.11bp vs 16.60bp cost, **does not clear** | 2026-09-21 | No — measurement |

| L26 | Universe B replication of `atr_pct` — 113 F&O-eligible names outside the NIFTY 100 — **PASS** at −0.0332, t = −6.68 (0.85× of A), but spread +5.97bp vs 22.60bp bar = **0.26×** | 2026-09-21 | No — measurement · `results-universe-b-replication.md` |

| L27 | Universe B unconditional means — overnight **+19.84bp** (t=+10.57), intraday **−9.93bp** (t=−3.45) | 2026-09-21 | No — measurement · `prereg-universe-b-addendum-overnight.md` |
| L28 | Universe B volatility-sorted — overnight spread **−14.15bp, t=−8.55, PASS** (1.02× of A); intraday +5.97bp, t=+1.63, **not distinguishable from zero in either window** | 2026-09-21 | No — measurement |

| L29 | Entry 7 §D.1 index-level split (NIFTY 50/100/BANK, point-in-time) — split holds with the same sign and similar size (+12.01 / −6.42). **NOT PRE-REGISTERED — omission recorded (Entry 8 §B.3).** BANKNIFTY measured beyond the instruction. The "40% survivorship" reading is **withdrawn** (§B.4): the gap confounds survivorship, period and weighting | 2026-09-21 | No — measurement · `results-entry7-d-feasibility.md` |
| L30 | Like-for-like fix of L29 — index means on **exactly universe A's 1,546 sessions** (^CNX100, ^NSEI) | pending | No — measurement, no pass rule · `prereg-L30-index-like-for-like.md` |

**Thirty looks, thirty-four trials.** L7–L16 are the ten members of the
step-2 BH family; they are listed individually so the family size is
auditable from this file alone. The held-out confirmation look for the three
survivors has **not** been taken — see `results-step2-feature-ic.md`
§Problem 3. L17–L20 are pre-registered in `prereg-step2-followups.md` and are
selection-split only; **L18 and L19 also act as gates** on whether that look
happens at all, under the tightened rule in `prereg-step2-feature-ic.md`
amendment 8.

---

## Replications — re-runs of already-counted configurations

| # | What | Reason | Counted? |
| --- | --- | --- | --- |
| R1 | Test A re-run — identical configuration (201 trades, 495 sessions, gate off) to recover its trade list for the null test's matching distributions, and to derive the gross expectancy's sd, t and CI properly | Needed the per-trade data the original run did not save | **No — replication, not counted** |

---

## Phase-2 runs

Nothing yet. Every phase-2 strategy run will be appended to the strategy table
above with its pre-registration file named, and every measurement to the
research-looks table.
