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

## Strategy trials — count as of 2026-09-28: **127** — 118 void, 119 3h, 120 3i Part A (PASS), 121–122 Ranker (FAIL), 123 Jev book (forward, pending), 124–125 overnight ETF (FAIL), 126 A′ (survives narrowly, smaller), 127 wide book (FAIL)

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
| 35 | **Phase 2 — 3a** opening-range breakout on top-20 relative volume, both sides, 5-cap, universe A, selection only · `prereg-3a-opening-range.md` (+ amendments 1–3, last `815ba4c`) · code `3841124` · **FAIL**: net −12.09 bp/session, t = −2.71 · `results-3a-opening-range.md` |
| 36 | **#74 bug-fix pair — baseline** `sahab_dimaag` checklist, cost_pct 0.12, Test A harness, selection only, both halves · code `dbe7514` · first −0.302R (n 71), second −0.207R (n 51) · `results-fix74-cost-pct.md` |
| 37 | **#74 bug-fix pair — fixed** cost_pct 0.166 (derived from `costs.py`), same harness · **PASS** (worse in first half only): first −0.354R (n 33), second +0.032R (n 12) — no edge, 63% fewer trades · `results-fix74-cost-pct.md` |
| 38 | **#40 bug-fix pair — baseline** `sahab_dimaag` checklist, rrr_without_level 2.0 gross, cost_pct 0.166, Test A harness, selection only, both halves · code `d79eeb9` · first −0.354R (n 33), second +0.032R (n 12) — reproduces trial 37 exactly · `results-fix40-no-level-target.md` |
| 39 | **#40 bug-fix pair — fixed** no formulaic target when no level lies beyond · **PASS** (worse in first half only): first −0.360R (n 31), second +0.089R (n 7) — no edge, 16% fewer trades · `results-fix40-no-level-target.md` |
| 40 | **Confluence engine on the deep cache** `entry_mode: confluence`, live params, Test A harness, selection only (317 sessions) · `prereg-confluence-deep.md` · code `08524d1` · **FAIL**: net −0.430R/trade, t = −9.84, n = 668; gross −0.188R (worse than the random-entry null); both halves negative · run at the user's direction without reviewer review · `results-confluence-deep.md` |
| 41 | **Strategy search** `A-ck43-k2` · net -0.343R (n 1388) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 42 | **Strategy search** `A-ck43-k3` · net -0.244R (n 900) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 43 | **Strategy search** `B-ck-15m` · net -0.332R (n 1670) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 44 | **Strategy search** `B-ck-60m` · net -0.182R (n 992) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 45 | **Strategy search** `C-PB-5m-s1.5-2R-both` · net -0.444R (n 3218) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 46 | **Strategy search** `C-PB-5m-s1.5-2R-short` · net -0.475R (n 3057) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 47 | **Strategy search** `C-PB-5m-s1.5-hold-both` · net -0.376R (n 2144) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 48 | **Strategy search** `C-PB-5m-s1.5-hold-short` · net -0.432R (n 2111) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 49 | **Strategy search** `C-PB-5m-s3.0-2R-both` · net -0.173R (n 1437) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 50 | **Strategy search** `C-PB-5m-s3.0-2R-short` · net -0.195R (n 1429) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 51 | **Strategy search** `C-PB-5m-s3.0-hold-both` · net -0.170R (n 1332) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 52 | **Strategy search** `C-PB-5m-s3.0-hold-short` · net -0.173R (n 1329) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 53 | **Strategy search** `C-PB-15m-s1.5-2R-both` · net -0.265R (n 2051) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 54 | **Strategy search** `C-PB-15m-s1.5-2R-short` · net -0.259R (n 1833) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 55 | **Strategy search** `C-PB-15m-s1.5-hold-both` · net -0.244R (n 1688) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 56 | **Strategy search** `C-PB-15m-s1.5-hold-short` · net -0.237R (n 1558) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 57 | **Strategy search** `C-PB-15m-s3.0-2R-both` · net -0.155R (n 1261) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 58 | **Strategy search** `C-PB-15m-s3.0-2R-short` · net -0.139R (n 1195) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 59 | **Strategy search** `C-PB-15m-s3.0-hold-both` · net -0.164R (n 1221) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 60 | **Strategy search** `C-PB-15m-s3.0-hold-short` · net -0.138R (n 1161) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 61 | **Strategy search** `C-PB-60m-s1.5-2R-both` · net -0.149R (n 1046) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 62 | **Strategy search** `C-PB-60m-s1.5-2R-short` · net -0.146R (n 944) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 63 | **Strategy search** `C-PB-60m-s1.5-hold-both` · net -0.150R (n 1031) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 64 | **Strategy search** `C-PB-60m-s1.5-hold-short` · net -0.146R (n 940) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 65 | **Strategy search** `C-PB-60m-s3.0-2R-both` · net -0.083R (n 915) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 66 | **Strategy search** `C-PB-60m-s3.0-2R-short` · net -0.077R (n 877) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 67 | **Strategy search** `C-PB-60m-s3.0-hold-both` · net -0.085R (n 914) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 68 | **Strategy search** `C-PB-60m-s3.0-hold-short` · net -0.077R (n 877) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 69 | **Strategy search** `C-MR-5m-s1.5-2R-both` · net -0.647R (n 2962) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 70 | **Strategy search** `C-MR-5m-s1.5-2R-short` · net -0.616R (n 1472) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 71 | **Strategy search** `C-MR-5m-s1.5-hold-both` · net -0.637R (n 2883) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 72 | **Strategy search** `C-MR-5m-s1.5-hold-short` · net -0.610R (n 1460) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 73 | **Strategy search** `C-MR-5m-s3.0-2R-both` · net -0.344R (n 2198) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 74 | **Strategy search** `C-MR-5m-s3.0-2R-short` · net -0.341R (n 1272) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 75 | **Strategy search** `C-MR-5m-s3.0-hold-both` · net -0.343R (n 2198) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 76 | **Strategy search** `C-MR-5m-s3.0-hold-short` · net -0.340R (n 1272) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 77 | **Strategy search** `C-MR-15m-s1.5-2R-both` · net -0.380R (n 1361) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 78 | **Strategy search** `C-MR-15m-s1.5-2R-short` · net -0.370R (n 617) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 79 | **Strategy search** `C-MR-15m-s1.5-hold-both` · net -0.381R (n 1361) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 80 | **Strategy search** `C-MR-15m-s1.5-hold-short` · net -0.371R (n 617) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 81 | **Strategy search** `C-MR-15m-s3.0-2R-both` · net -0.208R (n 1215) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 82 | **Strategy search** `C-MR-15m-s3.0-2R-short` · net -0.214R (n 598) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 83 | **Strategy search** `C-MR-15m-s3.0-hold-both` · net -0.208R (n 1215) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 84 | **Strategy search** `C-MR-15m-s3.0-hold-short` · net -0.214R (n 598) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 85 | **Strategy search** `C-MR-60m-s1.5-2R-both` · net -0.189R (n 226) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 86 | **Strategy search** `C-MR-60m-s1.5-2R-short` · net -0.127R (n 97) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 87 | **Strategy search** `C-MR-60m-s1.5-hold-both` · net -0.189R (n 226) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 88 | **Strategy search** `C-MR-60m-s1.5-hold-short` · net -0.127R (n 97) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 89 | **Strategy search** `C-MR-60m-s3.0-2R-both` · net -0.092R (n 224) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 90 | **Strategy search** `C-MR-60m-s3.0-2R-short` · net -0.062R (n 97) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 91 | **Strategy search** `C-MR-60m-s3.0-hold-both` · net -0.092R (n 224) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 92 | **Strategy search** `C-MR-60m-s3.0-hold-short` · net -0.062R (n 97) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 93 | **Strategy search** `C-VB-5m-s1.5-2R-both` · net -0.589R (n 2949) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 94 | **Strategy search** `C-VB-5m-s1.5-2R-short` · net -0.606R (n 1841) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 95 | **Strategy search** `C-VB-5m-s1.5-hold-both` · net -0.573R (n 2164) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 96 | **Strategy search** `C-VB-5m-s1.5-hold-short` · net -0.612R (n 1573) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 97 | **Strategy search** `C-VB-5m-s3.0-2R-both` · net -0.216R (n 1394) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 98 | **Strategy search** `C-VB-5m-s3.0-2R-short` · net -0.253R (n 1159) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 99 | **Strategy search** `C-VB-5m-s3.0-hold-both` · net -0.221R (n 1287) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 100 | **Strategy search** `C-VB-5m-s3.0-hold-short` · net -0.275R (n 1110) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 101 | **Strategy search** `C-VB-15m-s1.5-2R-both` · net -0.283R (n 1706) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 102 | **Strategy search** `C-VB-15m-s1.5-2R-short` · net -0.231R (n 1121) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 103 | **Strategy search** `C-VB-15m-s1.5-hold-both` · net -0.276R (n 1494) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 104 | **Strategy search** `C-VB-15m-s1.5-hold-short` · net -0.225R (n 1038) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 105 | **Strategy search** `C-VB-15m-s3.0-2R-both` · net -0.155R (n 1164) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 106 | **Strategy search** `C-VB-15m-s3.0-2R-short` · net -0.116R (n 897) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 107 | **Strategy search** `C-VB-15m-s3.0-hold-both` · net -0.152R (n 1139) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 108 | **Strategy search** `C-VB-15m-s3.0-hold-short` · net -0.117R (n 887) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 109 | **Strategy search** `C-VB-60m-s1.5-2R-both` · net -0.136R (n 904) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 110 | **Strategy search** `C-VB-60m-s1.5-2R-short` · net -0.131R (n 614) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 111 | **Strategy search** `C-VB-60m-s1.5-hold-both` · net -0.143R (n 896) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 112 | **Strategy search** `C-VB-60m-s1.5-hold-short` · net -0.124R (n 612) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 113 | **Strategy search** `C-VB-60m-s3.0-2R-both` · net -0.079R (n 848) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 114 | **Strategy search** `C-VB-60m-s3.0-2R-short` · net -0.074R (n 597) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 115 | **Strategy search** `C-VB-60m-s3.0-hold-both` · net -0.080R (n 848) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 116 | **Strategy search** `C-VB-60m-s3.0-hold-short` · net -0.075R (n 597) · fail · `prereg-strategy-search.md` / `results-strategy-search.md` |
| 117 | **3g — Smart Money multi-timeframe setup** (daily bias → 4H sweep → 1H order block → 15m sweep + cemented candle), 5m harness, selection only · `prereg-3g-smc-mtf.md` · code `5989ba0` · **FAIL**: net −0.299R/trade, t = −5.56, n = 256; both halves negative; pre-friction +0.070R (t ≈ 1.3) · `results-3g-smc-mtf.md` |
| 118 | **3h — slow momentum held in delivery, run 1** (`prereg-3h-slow-momentum-delivery.md`, code `f55da3c`) · **VOID, not a verdict**: after the run, adjusted prices showed phantom −90% days on known split dates — NSE's bhavcopy PREVCLOSE is never split/bonus-adjusted, and weekday-only download missed weekend special sessions (amendment 2). Seen before voiding: net monthly excess +0.61% (t 1.99), both halves positive, CAGR gap +6.9 pp, DSR 0.28 → would have been FAIL · `data/slow_momentum_stage1_run1_void.json` · counted as a trial so the DSR denominator grows |
| 119 | **3h — slow momentum held in delivery, run 2 (of record)** — top-15 of the 200 most-traded NSE names by vol-adjusted 6/12-month return, monthly, rank-30 hysteresis, delivery costs incl. DP charge, vs the same universe equal-weighted · code `0b81a1e` · **FAIL on the pre-registered rule**: net monthly excess +0.72% **t = 2.48** (passes), both halves positive (passes: +0.58%/mo, +0.86%/mo), net CAGR 18.4% vs 9.6% (+8.8 pp, passes), 523 round trips (passes), **DSR 0.24 at 119 trials (fails, rule ≥ 0.95)** · held-out NOT spent · `results-3h-slow-momentum-delivery.md` · **2026-09-26: contaminated by a look-ahead (split-adjusted ₹20 price floor, #135); FAIL stands; not re-run** |
| 120 | **3i Part A — slow momentum in delivery on corrected NSE data** (official corporate actions + dividends, equities only; 3h's rules unchanged), top 200, 2010-02 → 2025-11 · `prereg-3i-momentum-corrected-data.md` · code `890dfba` + amendment 1 `3fbe5ed` · **PASS on the family-level bar (N_family = 3)**: net excess +0.82%/month, **t 2.91** (gate 2.394), family DSR 0.98, both halves and last three years positive, CAGR 22.3% vs 12.0%, 519 round trips. Project-wide DSR 0.62 (would fail N = 120 — information). Re-reads trial 119's months: not independent · `results-3i-momentum-corrected-data.md` |
| 121 | **Sahab Ranker C1 — IC-weighted composite of 14 literature inputs, walk-forward, 3i book** · `prereg-ranker-engine.md` · code `e31114c` · **FAIL** (family N = 2): net excess +0.08%/month, t 0.23; loses to the momentum rule by 0.77%/month (paired t −1.90); unseen ranks 201–400 t 0.80 · `results-ranker-engine.md` |
| 122 | **Sahab Ranker C2 — ridge regression, same inputs** · **FAIL**: +0.14%/month, t 0.41; loses to momentum by 0.71%/month (paired t −1.77); unseen t 0.78 · `results-ranker-engine.md` |
| 123 | **The Jev book** — TypeSafe Jev (LLM judge) on the daily shortlist, forward paper test · `prereg-jev-book.md` · **pending** (verdict after 300 trades or 60 sessions; first round 2026-09-28) |
| 124 | **Overnight ETF H1 — hold NIFTYBEES 15:24 → 09:19** · `prereg-overnight-etf.md` · code `b192b90` · **FAIL** (family N = 2): gross +2.41 bp, net −6.42 bp/night, t −5.88 over 2,655 nights; negative every year; SETFNIF50 −4.35 bp (t −2.71) · `results-overnight-etf.md` |
| 125 | **Overnight ETF H2 — nightly ridge go/no-go** · **FAIL**: gated book −0.09 bp/night (t −0.15), held 8.8% of nights; beats always-hold only by staying out · `results-overnight-etf.md` |
| 126 | **Universe width A′ — trial 120's rule on the repaired price panel (#175, #177, #178) with honest fills** (band locks, no-trade days, trade-for-trade pricing) · `prereg-universe-width.md` with amendments 1–4 · code `3d210ce` · **SURVIVES trial 120's six criteria, narrowly and with a smaller edge**: net excess +0.71%/month, **t 2.51** (gate 2.394), DSR 0.952 at N = 3, both halves and last three years positive, CAGR 20.6% vs 11.9%, 516 round trips. Recorded trial 120 was +0.82%, t 2.91, CAGR 22.3%. **At the family of 10 now counted it would not clear** (bound 2.807, DSR 0.825) — information, written before the run. **The pass is narrow: about 0.02 points more slippage a side would fail the Deflated Sharpe criterion.** Measures the panel and the fills together; not independent of trial 120 · `results-universe-width.md` |
| 127 | **Universe width W — one book over the 400 most-traded, screened** (no trade-for-trade in 60 sessions, traded 120 of 126 days, ≥ ₹70 lakh a day), slippage by liquidity rank, 2014-05 → 2025-11 (138 months), family N = 10 · **FAIL**: net excess +1.02%/month, **t 2.76** (gate 2.807), DSR 0.871 (gate 0.95); against the running book +0.31%/month, **t 0.97** (gate 1.65), of which +0.17% is the universe and +0.14% the rule. Both halves, last three years, stress costs and Sharpe pass. K fell to 400 because the screened list is too short for 120 months at 600 or 800. **No change to the paper book** · `results-universe-width.md` |

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
| L25 | 3c §C tradable Kite window — intraday spread +8.11bp vs **33.20bp** (two legs, Entry 12 §1) = **0.24×**, does not clear | 2026-09-21 | No — measurement |

| L26 | Universe B replication of `atr_pct` — 113 F&O-eligible names outside the NIFTY 100 — **PASS** at −0.0332, t = −6.68 (0.85× of A), but spread +5.97bp vs 22.60bp bar = **0.26×** | 2026-09-21 | No — measurement · `results-universe-b-replication.md` |

| L27 | Universe B unconditional means — overnight **+19.84bp** (t=+10.57), intraday **−9.93bp** (t=−3.45) | 2026-09-21 | No — measurement · `prereg-universe-b-addendum-overnight.md` |
| L28 | Universe B volatility-sorted — overnight spread **−14.15bp, t=−8.55, PASS** (1.02× of A); intraday +5.97bp, t=+1.63, **not distinguishable from zero in either window** | 2026-09-21 | No — measurement |

| L29 | Entry 7 §D.1 index-level split (NIFTY 50/100/BANK, point-in-time) — split holds with the same sign and similar size (+12.01 / −6.42). **NOT PRE-REGISTERED — omission recorded (Entry 8 §B.3).** BANKNIFTY measured beyond the instruction. The "40% survivorship" reading is **withdrawn** (§B.4): the gap confounds survivorship, period and weighting | 2026-09-21 | No — measurement · `results-entry7-d-feasibility.md` |
| L30 | Like-for-like fix of L29 — index means on **exactly universe A's 1,546 sessions**. Overnight gap **+3.91bp (23%, not 40%)**; intraday gap **−0.21bp (3%)**. Weighting confound remains | 2026-09-21 | No — measurement, no pass rule · `prereg-L30-index-like-for-like.md` |

| L31 | 3b **stage 1a** — cross-sectional momentum, quintile spread **−1.60 bp, t = −0.48** vs a 33.20 bp gate. **DOES NOT CLEAR** (MDE 6.70 bp) | 2026-09-21 | No — measurement · `prereg-3b-intraday-momentum.md` |

| L32 | 3b **stage 1b** — adapted time-series, **+0.70 bp, t = +0.61** vs a 16.60 bp gate. **DOES NOT CLEAR** — 4% of its own cost | 2026-09-21 | No — measurement · `prereg-3b-intraday-momentum.md` amendment 1 §2 |

| L33 | Read-only chase of the 09-18 "9 passes, 0 orders" gap — it was **1 setup re-evaluated 9 times**, blocked by the confidence gate (53/60) and fully logged. Corrects the journal summary's mislabelled "cleared confidence" column and surfaces **19 direction-conflict blocks** | 2026-09-21 | No — read-only journal query, no returns computed · `journal-summary-2026-09-21.md` §3b |

| L34 | Universe expansion — does universe B (113 F&O-eligible names outside the NIFTY 100) clear the reward:risk gate more often than universe A? **FAIL**: p_A **93.17%** vs p_B **92.83%**, z = **−2.80**. B's targets sit **+21.4%** further but its stops sit **+26.8%** further, so the ratio is worse — and **B is still worse at zero cost** (95.02% vs 94.85%), so this is geometry, not friction. Proxy **saturates at 93% vs the live 9.6%** — weak evidence about the live intraday gate. Held-out untouched | 2026-09-22 | No — measurement · `prereg-L34-universe-b-rrr-gate.md` / `results-L34-universe-b-rrr-gate.md` |
| L35 | Event study on NSE filings — 9,586 events, 6 classes × 3 windows, direction-aligned vs 16.63 bp with BH. **No class clears.** ORDERS is significantly *negative* (−8.6 bp, t −2.97, "sell the news"); RESULTS move 3× normal (121 bp / 30 min) but the lexicon cannot read their direction (0 signed events) — a volatility finding. Held-out untouched | 2026-09-25 | No — measurement · `prereg-event-study.md` / `results-event-study.md` |
| L36 | Results direction from the filed YoY profit (XBRL `ProfitLossForPeriod`) — 167 results events. **Direction is right: the overnight gap is +82.7 bp aligned, t 4.78. But after the open the aligned drift is +5.9 bp at 30 min and 0 by the close** — priced by the open, nothing tradable intraday. NSE's index thins after Jan 2025 (~2 quarters covered). Held-out untouched | 2026-09-25 | No — measurement · `prereg-results-direction.md` / `results-results-direction.md` |
| L38 | **3i Part B — the same momentum rules on ranks 201–400 by liquidity, never read by any test** (confirmation of trial 120, slippage doubled to 0.10%/side) · **CONFIRMS**: +1.00%/month net excess, t 3.31 (rule t ≥ 1.65), both halves positive, CAGR 28.6% vs 15.4%. **Held-out confirmation (same prereg): 2026-01 → 2026-08, Part A rules: +1.28%/month, 6 of 8 months positive, t 1.08 — sign check passes** | 2026-09-26 | Confirmation, not a trial · `prereg-3i-momentum-corrected-data.md` / `results-3i-momentum-corrected-data.md` |
| L39 | **PEAD Stage A — post-earnings drift, point-in-time NIFTY 100, XBRL era** (top-tercile earnings surprise, 60-session hold, 30 slots) · **NO-GO**: gross +0.25%/month, NW t 1.41 (rule ≥ 0.37% and t ≥ 1.8); net +0.11%/month. PEAD dropped; the surprise is barred as a feature in later models | 2026-09-26 | Measurement, no trial · `prereg-pead-stage-a.md` / `results-pead-stage-a.md` |
| — | **Stock-picking sweep, descriptive read of the 2025 bhavcopies** by liquidity tier, ranks 1 to 1,892: traded value, number of trades, days with no trade, band locks, series membership, two daily-range spread estimators. Read daily prices; computed **no momentum score and no strategy return**. 611 symbols appeared in both EQ and BE/BZ during 2025 (#175). Once T3 of `prereg-universe-width.md` runs, ranks 401–600 stop being unread for the base momentum rule | 2026-09-28 | No — description, no pass rule · `stock-picking-sweep-2026-09-28.md` · `data/stock-picking-sweep/tiers_2025_descriptive.py` and `.out.txt` |
| L41 | **Universe width, stage 0** (`prereg-universe-width.md`) — data gate for the repaired price panel of #175 and the honest-fill simulator. Two runs. **Run 1 failed gate 6** on 2 of 67 one-day jumps (AURUM 2020, a dividend of 98.8% of the price; KESORAMIND 2025, a demerger that left 4.7%); the jump list also showed 7 overstated dividend amounts (#178). **Run 2 passed all six gates**: loader parity 0 differences, the 200- and 400-stock lists 100% those 3i read, the simulator reproduces trial 120 and L38 to 4e-15. 743 corporate-action factors differ between the two panels, 42 inside the 400 most-traded. **Tier existence: ranks 401–600, 601–800 and 801–1,000 have 63, 56 and 30 months against the 120 required, so looks L43 to L45 were not taken** and no return beyond rank 419 is read; the wide book runs at K = 400 from 2014-05. No strategy return read | 2026-09-28 | No — a data gate · `data/momentum_width_stage0_run1.json`, `_run2.json`, `momentum_width_panel_differences.json` |
| L40 | **Kronos zero-shot forecast, does it rank the next 15, 30 or 60 minutes** (`prereg-kronos-feature-ic.md`, amendments 1 to 3). Stage 0 run on 2026-09-29: all six checks pass, sample_count 1 by the timing rule (62.6 h at 3). The one IC pass started 20:55 on 2026-09-29, 43,362 stock-times over 79 sessions (2025-09-01 to 2025-12-23); **no statistic read yet**. The 2026 window is not read | 2026-09-29 | Pending · `data/kronos_l40_stage0.json` |
| L42 | **Universe width B′ — L38's rule (ranks 201–400) on the repaired panel with honest fills** · **SURVIVES** L38's rule: +0.91%/month net excess, t 3.00, both halves positive (+0.57% / +1.24%), CAGR 26.9% vs 15.2%. Recorded L38 was +1.00%, t 3.31. One fix was known to help before the run: a dividend of 98.8% of the price (AURUM, 2020-12) had been read as a loss, about 6.6 points of that month's +7.8 against L38. **L43, L44, L45 (ranks 401–600, 601–800, 801–1,000) were not taken**: 63, 56 and 30 months against the 120 required; only "not testable" records were written, no simulation | 2026-09-28 | Confirmation re-run, counted in the family of 10 · `results-universe-width.md` |

**3f stage 0 (2026-09-24) spent neither a look nor a trial** — it built the
point-in-time membership and checked data coverage and vendor agreement,
reading no forward return; see `results-3f-stage0.md`. The vendor gate
halted as pre-registered (38%), then failed again as amendment 3 (53.98%,
a specification error: yfinance's Close is split-adjusted); amendment 4, the
last correction it got (Entry 17), ran once and **failed at 93.41%** — 3f
is closed at stage 0 with no look or trial spent.

**Thirty-four looks, thirty-five trials.** **3b was WITHDRAWN at stage 1 without spending trial 36** — the two-stage split, proposed before any 3b number existed, did what it was for. L7–L16 are the ten members of the
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
| R2 | 3h run 2 re-run with a holdings log added (`963b0b2`), identical configuration; statistics byte-identical (t 2.4750323417390483 both) | Needed the month-by-month holdings to quantify phantom split drops and ETF exposure | **No — replication, not counted** |

---

## Phase-2 runs

**Trial 35 — 3a, 2026-09-21, FAIL** (one run, no re-run). Every phase-2 strategy run is appended to the strategy table
above with its pre-registration file named, and every measurement to the
research-looks table.


---

## Held-out exposure log

Reads of data dated on or after `HELD_OUT_START` (2026-01-02), whether or not
a statistic was computed. The window is only as clean as this list says.

| Date | Who | What was read | Statistic computed from it? |
| --- | --- | --- | --- |
| 2026-09-26 | edge-map workflow (design/verify agents) | NSE bhavcopies for 2026-07-30, 2026-07-31 and 2026-09-22 → 25 (the September ones are after `UNSEEN_AFTER`), to check ETF/index open-close tracking and file formats | Tracking gaps between ETF and index prices; no strategy return |
| 2026-09-26 | edge-map workflow | yfinance 1-minute bars for NIFTYBEES and SETFNIF50, 2026-09-17 → 25, to estimate ETF spreads | Spread estimates only |
| 2026-09-26 | edge-map workflow | NIFTY200 Momentum 30 factsheet (Aug 2026), including its 2026 year-to-date and 1-year returns | Published index returns, read as literature |
| 2026-09-26 | main session | Downloaded all 2026 NSE equity bhavcopies (182 files) into the cache while refreshing it; moved unread to `backend/data/bhav_daily_2026_heldout/`, which selection code cannot read (#135) | None |
| 2026-09-26 | prediction-engine workflow (critic and verifiers) | NSE pre-open snapshot of 2026-09-25 09:08 (which securities are in the auction); yfinance 1-minute NIFTYBEES bars for 5–6 September 2026 sessions (ETF opening-print behaviour); Nifty/BankNifty futures bhavcopies 2025 for the nightly premium decay | Opening-print dispersion and futures decay; no strategy return on 2026 |
| 2026-09-26 | main session | Re-fetched the same NSE pre-open snapshot to confirm NIFTYBEES/SETFNIF50 are not in the pre-open auction | None (membership only) |
| 2026-09-26 | main session (3i held-out confirmation, pre-registered) | All 2026 bhavcopies to 2026-09-25 and NSE's 2026 corporate actions; the held-out run of 3i Part A's rules over 2026-01 → 2026-08 | **Yes — the pre-registered held-out statistic (spent once, for the momentum family)** |
| 2026-09-28 | stock-picking sweep (evidence agent) | Published returns of NSE momentum, value, quality and low-volatility indices and of index funds tracking them, to 31 August 2026, from NSE's monthly dashboards, factsheets and AMFI NAVs | Live excess of each index over its parent; no strategy return. **A later 2026 check of a wider momentum book, or of a value or low-volatility rule, is partly seen** |

**Consequence:** index-level 2026 held-out evidence has been partly seen
(open/close tracking on six sessions, a factsheet's 2026 figures). A future
index-timing confirmation on 2026 should say so and exclude those sessions.
