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

## Strategy trials — count as of 2026-11-02: **204 spent, numbered to 206** — 118 void, 119 3h, 120 3i Part A (PASS), 121–122 Ranker (FAIL), 123 Jev book (forward, pending), 124–125 overnight ETF (FAIL), 126 A′ (survives narrowly, smaller), 127 wide book (FAIL), 128–202 forecast × candlestick combinations (FAIL, 0 of 75), 203 Jev 2 (forward, pending; registered 2026-10-05, not yet spent), 204 frog-in-the-pan tie-break (FAIL, spent 2026-10-14), 205 trial 126's rule on US stocks (registered 2026-10-26 in `prereg-us-momentum.md`, not yet spent; waits on the owner buying a survivorship-free data source), 206 promoter open-market purchases held five sessions (FAIL, spent 2026-11-02; first slot of the "insider buying" family, N = 2, t ≥ 2.24; `prereg-insider-buys.md`, `results-insider-buys.md`)

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
| 203 | **Jev 2** — the Jev judge on a blind state, seven narrow Nouls combined by a frozen rule with a skip band, all 25 names, fills shared with Jev 1, forward paper test beside trial 123 · `prereg-jev2-book.md` (family "LLM judgment", N_family = 3, clustered t ≥ 2.39) · **pending** — no trial is spent until the verdict (after 300 buy/short decisions or 60 sessions; first round on the first session after the restart that follows its review) |
| 124 | **Overnight ETF H1 — hold NIFTYBEES 15:24 → 09:19** · `prereg-overnight-etf.md` · code `b192b90` · **FAIL** (family N = 2): gross +2.41 bp, net −6.42 bp/night, t −5.88 over 2,655 nights; negative every year; SETFNIF50 −4.35 bp (t −2.71) · `results-overnight-etf.md` |
| 125 | **Overnight ETF H2 — nightly ridge go/no-go** · **FAIL**: gated book −0.09 bp/night (t −0.15), held 8.8% of nights; beats always-hold only by staying out · `results-overnight-etf.md` |
| 126 | **Universe width A′ — trial 120's rule on the repaired price panel (#175, #177, #178) with honest fills** (band locks, no-trade days, trade-for-trade pricing) · `prereg-universe-width.md` with amendments 1–4 · code `3d210ce` · **SURVIVES trial 120's six criteria, narrowly and with a smaller edge**: net excess +0.71%/month, **t 2.51** (gate 2.394), DSR 0.952 at N = 3, both halves and last three years positive, CAGR 20.6% vs 11.9%, 516 round trips. Recorded trial 120 was +0.82%, t 2.91, CAGR 22.3%. **At the family of 10 now counted it would not clear** (bound 2.807, DSR 0.825) — information, written before the run. **The pass is narrow: about 0.02 points more slippage a side would fail the Deflated Sharpe criterion.** Measures the panel and the fills together; not independent of trial 120 · `results-universe-width.md` |
| 127 | **Universe width W — one book over the 400 most-traded, screened** (no trade-for-trade in 60 sessions, traded 120 of 126 days, ≥ ₹70 lakh a day), slippage by liquidity rank, 2014-05 → 2025-11 (138 months), family N = 10 · **FAIL**: net excess +1.02%/month, **t 2.76** (gate 2.807), DSR 0.871 (gate 0.95); against the running book +0.31%/month, **t 0.97** (gate 1.65), of which +0.17% is the universe and +0.14% the rule. Both halves, last three years, stress costs and Sharpe pass. K fell to 400 because the screened list is too short for 120 months at 600 or 800. **No change to the paper book** · `results-universe-width.md` |
| 128–202 | **Forecast × candlestick combinations** (`prereg-combo-search.md`): 8 sources (Kronos, six L46 models, Ensemble) × 3 horizons × 3 rules, plus 3 pattern-alone controls; directional trades net of 16.63 bp; bar t > 3.40 and DSR ≥ 0.95 at 75 · **FAIL**: 0 of 75 pass, none positive net; best −13.8 bp a trade; pattern alone −16.4 bp · `results-combo-search.md` |
| 204 | **Frog-in-the-pan tie-break — trial 126's book with vacancies filled from the top 30 by lowest information discreteness** (Da, Gurun & Warachka) instead of by rank, top 200, 2010-02 → 2025-11, honest fills, paired against the base · `prereg-fip-tiebreak.md` (`52e8977`) · code `cde4947` · momentum family N = 11 · **FAIL**: this rule minus the base **−0.39%/month, paired t −2.15** (needed ≥ +1.65); −0.37% with every cost at zero; own net excess +0.32%/month, t 1.26 (gate 2.838), DSR 0.357, last three years negative; CAGR 15.6% vs the base's 20.6%; turnover 281% vs 211%. Confirmation on ranks 201–400 (L57): −0.15%/month, t −0.72. The falsification row "paired t ≤ −1.65" applies; the sign is not flipped. Run on the owner's instruction against the 2026-10-01 sweep's "Leave"; **no reviewer read it before the run**. No change to the paper book · `results-fip-tiebreak.md` |
| 206 | **Promoter open-market purchases ≥ ₹10 lakh per symbol per broadcast date, entry at the first open after the exchange broadcast, five sessions held, top-500 universe by trial 126's ranking, trial 126's costs plus 10 bp a side** (prior: Brochet, Lee & Srinivasan 2017) · `prereg-insider-buys.md` (`d091ea6`; amendments 1–2 in `7a7f726`, both before any return was read) · code `7a7f726` · insider-buying family N = 2, bar t ≥ 2.24 · 2,579 events, broadcasts 2015-11-19 → 2025-12-19, NSE PIT archive exported from the owner's browser (not committed) · **FAIL**: mean net excess over the equal-weighted universe **+4.4 bp per event, clustered t 0.37** (needed ≥ 2.24 and ≥ 25 bp); halves **−2.7 bp** (n 1,852, t −0.18) and +22.5 bp (n 727, t 1.22); last three years +22.3 bp (n 312, t 0.94); DSR 0.447; median −39 bp; win rate 46%. Gross +67 bp and net +22 bp per event against a benchmark of +17 bp: the round trip's 45 bp of cost takes what the pop leaves. Falsification rows "fail on t or DSR, mean > 0" and "fail on a half" apply; line closed, the family's second slot unspent. Independently reviewed before the run (amendment 2); entry 35 of `backtest_trials.json`; no 2026 row read · `results-insider-buys.md` |

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
| — | **Predictive tools sweep** (`predictive-tools-sweep-2026-09-29.md`): 55 candidates in three parts — time-series foundation models for the L40 harness, finance ML libraries and agent frameworks, India-specific tools and the newest evidence. Read published evidence, repository trackers and model cards; **ran no model and read no project return**. Found that most 2026 models post-date the L40 selection sample and can be tested only forward or on the held-out window | 2026-09-29 | No — a candidate list, no pass rule · `data/predictive-tools-sweep/` |
| — | **Stock-picking sweep, descriptive read of the 2025 bhavcopies** by liquidity tier, ranks 1 to 1,892: traded value, number of trades, days with no trade, band locks, series membership, two daily-range spread estimators. Read daily prices; computed **no momentum score and no strategy return**. 611 symbols appeared in both EQ and BE/BZ during 2025 (#175). Once T3 of `prereg-universe-width.md` runs, ranks 401–600 stop being unread for the base momentum rule | 2026-09-28 | No — description, no pass rule · `stock-picking-sweep-2026-09-28.md` · `data/stock-picking-sweep/tiers_2025_descriptive.py` and `.out.txt` |
| L41 | **Universe width, stage 0** (`prereg-universe-width.md`) — data gate for the repaired price panel of #175 and the honest-fill simulator. Two runs. **Run 1 failed gate 6** on 2 of 67 one-day jumps (AURUM 2020, a dividend of 98.8% of the price; KESORAMIND 2025, a demerger that left 4.7%); the jump list also showed 7 overstated dividend amounts (#178). **Run 2 passed all six gates**: loader parity 0 differences, the 200- and 400-stock lists 100% those 3i read, the simulator reproduces trial 120 and L38 to 4e-15. 743 corporate-action factors differ between the two panels, 42 inside the 400 most-traded. **Tier existence: ranks 401–600, 601–800 and 801–1,000 have 63, 56 and 30 months against the 120 required, so looks L43 to L45 were not taken** and no return beyond rank 419 is read; the wide book runs at K = 400 from 2014-05. No strategy return read | 2026-09-28 | No — a data gate · `data/momentum_width_stage0_run1.json`, `_run2.json`, `momentum_width_panel_differences.json` |
| L40 | **Kronos zero-shot forecast, does it rank the next 15, 30 or 60 minutes** (`prereg-kronos-feature-ic.md`, amendments 1 to 4) · **FAIL** at all three: top-minus-bottom quintile spread +0.27 / +0.51 / +1.61 bp (t 0.63 / 0.78 / 1.43) against 33.26 bp; rank IC 0.010 / 0.018 / 0.022, partial IC given m60 below t 2 at every horizon; no BH survivor. Run of record on the owner's PC, sample_count 3, 78 sessions, 43,362 stock-times; the Mac's run stopped unread (amendment 4). The 2026 window is not read | 2026-09-30 | No — no trial spent · `results-kronos-feature-ic.md`, `data/kronos_l40_result.json` |
| L46 | **Six zero-shot foundation models in the L40 harness** (`prereg-tsfm-family.md`, amendments 1–2): Chronos-Bolt, TimesFM-2.5, Moirai 2.0, FlowState-r1, TiRex v1, Sundial · **FAIL** 18 of 18: spreads −2.3 to +0.5 bp against 33.26 bp, 16 of 18 negative; no BH survivor across 18. The 2026 window is not read | 2026-09-30 | No — no trial spent · `results-tsfm-family.md` |
| L47 | **LightGBM on Qlib's Alpha158, trained on the project's own five-minute bars** (`prereg-qlib-lgbm-alpha158.md`, amendment 1): trained 2024-09-20 to 2025-08-14, scored on L40's sample · **FAIL** at all three: spread +0.11 / +0.03 / +0.51 bp against 33.26 bp; rank IC 0.013–0.018 (t ≈ 2.1); no BH survivor within L47 or across the night's 24 tests | 2026-09-30 | No — no trial spent · `results-qlib-lgbm-alpha158.md` |
| L48 | Breadth and intermarket (run 2026-09-25 as "L35 / 3h"; renumbered on merge 2026-09-30) — does whole-NSE breadth (A/D ratio, McClellan, TRIN) or an overnight intermarket move (India VIX, S&P 500, USD/INR, crude, US 10Y) predict the 09:20→15:10 NIFTY 100 session? **NO PASS**: 0 of 8 survive BH at 5%; best USD/INR p = 0.073, its extreme tercile +10.8 bp = 0.65× the round trip. Held-out untouched | 2026-09-25 | No — measurement · `prereg-3h-breadth-intermarket.md` / `results-3h-breadth-intermarket.md` |
| L52 | **Five newest forecasting models, forward** (`prereg-2026-models-forward.md`): Chronos-2, TiRex-2, Toto 2.0, Granite PatchTST-FM r2, TimesFM-3.0, revisions pinned 2026-09-30, scored on the first 60 sessions from 2026-10-01 with L40's gate, BH across 15 | 2026-09-30 | **Pending** (run after the 60th session, about late December 2026) |
| L53 | **What the momentum book is worth to an individual after Indian costs and taxes** (`prereg-after-tax-l53.md`, amendments 1–2): trial 126's own trade list through a FIFO tax engine (FY 2026-27 rules on every year), ₹10 lakh, against index funds held and harvested every year · **TIES both**: after-tax CAGR 17.67% for the book against 17.28% for a Nifty200 Momentum 30 fund (TRI − 0.5 pp) → **+0.39 pp a year, 95% −5.99 to +7.33, halves −2.86 / +3.56**; against 11.86% for a NIFTY 100 fund → **+5.82 pp, 95% −2.05 to +15.36, halves +5.58 / +6.06**. Tax drag 2.87 pp a year on the book, 0.81 / 0.54 on the funds; the book needs ~2.1 pp a year pre-tax over the momentum fund to tie. After the index's launch (2020-09 on, index live, book still a backtest) +7.48 pp; before it −2.87 pp. The actual UTI fund tracked the TRI − 0.5 pp within 0.13 pp. Pre-tax, book minus N200M30 TRI 2020-09 to 2025-11 +0.78% a month (t 1.63), all 189 months +0.23% (t 0.83). Band proposal P1 s = 0.10 (95% −1.00 to +1.23, uninformative), not applied. First review NOT APPROVED (set-off order, interest, a tax sale that dropped names), fixed by amendment 2; second review approved; one pass 2026-10-01 01:49–01:51 IST. The 2026 window is not read | 2026-10-01 | No — no trial spent (count 202) · `results-after-tax-l53.md`, `data/l53_result.json` |
| L42 | **Universe width B′ — L38's rule (ranks 201–400) on the repaired panel with honest fills** · **SURVIVES** L38's rule: +0.91%/month net excess, t 3.00, both halves positive (+0.57% / +1.24%), CAGR 26.9% vs 15.2%. Recorded L38 was +1.00%, t 3.31. One fix was known to help before the run: a dividend of 98.8% of the price (AURUM, 2020-12) had been read as a loss, about 6.6 points of that month's +7.8 against L38. **L43, L44, L45 (ranks 401–600, 601–800, 801–1,000) were not taken**: 63, 56 and 30 months against the 120 required; only "not testable" records were written, no simulation | 2026-09-28 | Confirmation re-run, counted in the family of 10 · `results-universe-width.md` |
| L50 | **Bulk and block deal disclosures at the next open** — does the side of an NSE bulk deal predict the 09:20 → +15/30/60 min move past 16.63 bp? · **VOID at stage 0**: 21 directional NIFTY 100 bulk events in the Kite cache (26 counting members the cache lacks; at most 34 on any side rule) in 15 months (19 SELL, 2 BUY; 5 MIXED under the 2:1 net rule) against the 60 required, so the family is empty. Block deals (251 stock-days) list both counterparties and carry no side. **No price read, no return computed.** Independent review approved. Held-out untouched | 2026-09-30 | No — void, no trial · `prereg-bulk-block-deals.md` / `results-bulk-block-deals.md`, `data/l50_stage0.json` |
| L49 | **Scanner audit's four intraday features and the 09:45 gap reversal** (`prereg-scanner-features.md`, amendments 1–3) — do gap, time-of-day relative volume, VWAP distance or sector strength (scanner signs), or the previous-official-close → 09:45 reversal, rank the next 15/30/60 minutes in L40's harness? 13 tests, BH q = 0.10 · **FAIL, 0 of 13**: spreads −8.29 to +1.27 bp against 33.26 bp; six BH survivors, five of them with the opposite of the registered sign (sector −2.0 / −5.7 / −8.3 bp, IC to −0.087, t −7.7; VWAP distance −2.3 / −3.5 bp); rvol +1.27 bp at 30 min (t 2.26), 4% of the bar; gap reversal −2.98 bp (t −0.97), failing on the spread, not only the partial IC; not the source's H2. Stage 0 run 1 halted at check 4 (NSE's LAST ≠ Kite's last trade), fixed by amendment 2 before any feature was computed; independent review approved. 78 sessions, 43,362 stock-times. The 2026 window is not read | 2026-09-30 | No — no trial spent · `results-scanner-features.md`, `data/l49_result.json`, `data/l49_stage0.json` |
| L51 | **Intraday index timing from lagged factor-portfolio returns** (`prereg-index-timing.md`, amendments 1–6; new family "intraday index timing", with L48): 23 NIFTY 100 factor series × 4 lags → numpy Ridge, monthly expanding refits, trade NIFTY futures when the forecast exceeds the 6.95 bp round trip; two configurations (30 and 60 minutes) · **DOES NOT CLEAR at either horizon**: 0 trades (0 of 858 and 0 of 390 decisions above cost; largest forecast 0.25 / 0.63 bp). Headline, the predictor part's IC: +0.039 (clustered t 1.16) and +0.036 (t 0.63), second half negative at both → **no direction**; the pre-registered IC +0.016 / +0.013, out-of-sample R² negative. Power: a planted IC of 0.38 made +2.10 bp a trade at 30 minutes (t 1.24). Scored once at `c2d77c2` after a second independent review; the 2026 window is not read | 2026-09-30 | No — no trial spent · `results-index-timing.md`, `data/l51_result.json`, `data/l51_decisions.csv` |
| L54 | **The single-rule paper lab, forward** (`prereg-rule-lab.md`, amendments 1–4 and 7; owner-requested under RES-33, 2026-10-05): 157 single rules — cohort 1, 20 of the lab's own (candlestick patterns, inside-bar breaks, volume 2× on an up or down bar, trend turns, opening-range breaks, gap rules, EMA20 pullbacks with a 3R exit); cohort 2, 87 from the YouTube and practitioner catalogs — each a shadow paper book on the day's list, next bar's open, 30 minutes or 15:05, ₹50,000, `config.COSTS`. ; cohort 4 ("cohort 2b", amendment 7, 2026-10-05, during the first session and before any of its returns existed), 50 basic rules: the other 16 candlestick patterns of the engine's detector, Doji and inside-bar breakouts, ADX, Fibonacci retracement, Ichimoku, Keltner, parabolic SAR, Donchian, VWAP bands and cross, OBV divergence, two time-of-day filters, double top/bottom and flags. Screen after 40 lab sessions (Romano–Wolf, α 2.5% for cohort 1 and 1.25% for cohort 2; 0.625% reserved for a daily cohort 3; 0.3125% for cohort 4, on its own first 40 sessions), confirmation on the next 40 | 2026-10-05 | **Pending** (collecting from the first session after deploy). No trial until a confirmed rule is proposed (one trial per proposal) |
| L55 | **The rule lab's historical combinatorial search** (`prereg-rule-lab.md` amendments 3–4): singles, pairs, triples and a bounded greedy search of same-side conditions × 2 exits, over the 107 conditions at most 116,746 combinations, Kite cache 2024-09-20 to 2025-12-31; Romano–Wolf over the family, PBO by CSCV, deflated Sharpe of the best; at most 5 survivors get one 2026 pass (owner-authorised, below). **Look 1, run once**, 02:23–02:30 IST 2026-10-05 from `b065fff`, clean tree, family hash matching stage 0 (`data/l55_result.json`, `results-rule-lab-l55.md`): 104,655 combinations evaluated, 0 survivors; eligible combinations not stored by look 1. RW stepdown vacuous (critical value 7.17e7 from n ≤ 6 sets in the unfiltered family); no survivor under the prereg as written; the evidence that no edge exists is the 105 powered singles, all negative net of costs (best −12.8 bp, t −4.4), and PBO 0.33; whether any ≥ 200-trade combination has a positive mean was not tested. **The 2026 pass does not run.** **Look 2, run once** (amendment 6's filtered re-judgement, a deliberate second look), 03:12–03:22 IST from `9271c63`, clean tree (`data/l55_result_look2.json`): 24,026 combinations with ≥ 200 trades and ≥ 40 sessions in the maximum, critical t 4.82 (now meaningful), 168 of 24,026 with a positive net mean, largest t 1.91 (greedy filter stacks on R17, +21 bp, second half +1.6 bp), PBO 0.33, **0 survivors**. `--confirm-2026` not run; 2026 as disclosed | 2026-10-05 | **Look 1: FAIL — no survivor; the stepdown itself was vacuous. Look 2: FAIL — 0 survivors among 24,026 powered combinations.** No trial spent; count stays 202. The search is closed |
| L56 | **Frog-in-the-pan stage 0** (`prereg-fip-tiebreak.md`): holdings and counts of the base and the tie-break books, top 200 and ranks 201–400; no strategy return read · parity with trial 126's and L42's recorded holdings exact; ID coverage 100% / 99.98%; 5.8 / 5.5 of 15 holdings differ; buys a year 45.7 vs 33.7 and 55.0 vs 42.2 · `results-fip-tiebreak.md` | 2026-10-14 | **Pass on all three gates; trial 204 not withdrawn.** No trial spent by this look |
| L57 | **Frog-in-the-pan confirmation on ranks 201–400** (`prereg-fip-tiebreak.md`, same run as trial 204): the tie-break minus the base, 189 months · **−0.15%/month, paired t −0.72**; own net excess +0.75%/month (t 2.79) vs the base's +0.91% (t 3.00); lower volatility and a shallower drawdown, lower return · `results-fip-tiebreak.md` | 2026-10-14 | **FAIL (needed t ≥ +1.65).** Counted with trial 204, not separately |
| — | **Profitability sweep** (`profitability-sweep-2026-10-01.md`): four research agents on India's momentum evidence and live index products, improving momentum, how people make money with current technology, and low-turnover strategy families. Read published evidence, regulators' data, NSE index and AMFI fund series; **ran no strategy and computed no new project return**. One count was made from trial 126's stored 2010–25 series (a book started in September 2024 is the only one of 184 start months the band would have tripped). Found no candidate likelier to pass than the book, tax as its largest unmodelled cost, and five zero-trial measurements to do first (L53 is one). **2026 held-out data was read by all four agents; see the exposure log below** | 2026-10-01 | No — a candidate list, no pass rule · `data/profitability-sweep/` |

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
| 2026-10-01 | L53 author, while checking file formats | The first 600 bytes of R1's NIFTY200 Momentum 30 TRI file (TRI on 25–30 Sep 2026) and of the UTI Nifty200 Momentum 30 fund's NAV file (NAV on 18–29 Sep 2026) were printed | None. Recorded in `prereg-after-tax-l53.md` §0 with the research sweep's own 2026 reads of these series |
| 2026-10-01 | L53 independent reviewer | `prereg-after-tax-l53.md` §0 as committed (`ec7cb12`), which printed the NIFTY200 Momentum 30 TRI levels of 25–30 Sep 2026 and the UTI fund's NAV of 18–29 Sep 2026 (redacted by amendment 2) | None |
| 2026-11-02 | main session (trial 206) | The NSE insider-trading archive export, fetched from inside the owner's Chrome at the owner's instruction, covers broadcasts to 2026-11-02; its 4,458 rows broadcast in 2026 sit in the gitignored `backend/data/pit/` file. The first stage-0 run (before amendment 2) counted them per month and dropped 608 held-out events; amendment 2 drops them as the file is read. No 2026 session was loaded | Row counts only; no price or return |

| 2026-09-30/10-01 | profitability sweep, R1 (India momentum evidence) | NSE daily total-return indices for 16 Nifty indices (momentum, quality, low-volatility, value, alpha and their parents) to 2026-09-30 and their factsheets of that date; AMFI NAVs of 43 direct funds through 2026-09; NSE's 2026 momentum whitepaper (data to 2026-02-27); a momentum ETF document (May 2026); passive AUM at 2026-02-27 | **Yes** — each index's live excess over its parent and over Nifty100 Equal Weight through 2026-09, drawdowns to 2026-09-30, 2026 year-to-date returns, fund returns and tracking differences. No project strategy return |
| 2026-09-30/10-01 | profitability sweep, R2 (improving momentum) | Factsheets of 2026-09-30 for Nifty200 Momentum 30, Alpha Low-Volatility 30 and Quality 30; an independent point-in-time momentum × low-volatility table on the NIFTY 500, 2014–26 | Published returns, read as literature |
| 2026-09-30/10-01 | profitability sweep, R3 (technology and money) | SEBI's FY25–26 F&O studies (FY26 includes 2026-01 to 03); India VIX levels in March 2026; the September 2026 F&O series (NIFTY −6.7%); SEBI orders and circulars of 2026; NSE's algo-vendor list of 2026-09-22; a real-money crypto test of August–September 2026 | Read as literature; no NSE return computed |
| 2026-09-30/10-01 | profitability sweep, R4 (low-turnover families) | 2026 rows of the Quality 30, Value 20, Dividend Opportunities 50 and Nifty 50 factsheets to 2026-09-30; GOLDBEES 2026 monthly prices; balanced-advantage fund pages (2026); an overnight/intraday repository to 2026-09-30; md0n's NIFTYBEES turn-of-month and dual-momentum results 2021–26; mfapi NAV files holding 2026 rows (filtered out); a count of 25 buyback rows in `corp_actions/ca_2026.csv` (count only); two 2026 buyback articles | Dividend Opportunities 50's five-year excess to 2026-09 read; no strategy return |
| 2026-10-05 | rule lab, L55 stage 0 | A count of 5-minute rows dated 2026 in `kite_history.db`, by symbol (`COUNT(*)`, no price, volume or signal). **Owner's authorisation of one future 2026 pass**, recorded here: *"if we are testing micro rules or permutation combinations of rules and backtest on 2025 and 2026 data we should come at a certain set of rules that are profitable"* (2026-10-05). The pass is for at most 5 pre-declared L55 survivors, once, after an independent review | None (row count only). The pass, when it runs, gets its own row |

**Consequence:** index-level 2026 held-out evidence has been partly seen
(open/close tracking on six sessions, a factsheet's 2026 figures). A future
index-timing confirmation on 2026 should say so and exclude those sessions.

**Added 2026-10-01 (profitability sweep).** After the four rows above, a 2026
confirmation of momentum at the index level, low volatility, quality, value,
dividend yield, alpha, dual momentum or gold, turn-of-month, overnight or
buybacks is partly seen; prefer forward confirmation. The same sweep read
NSE's momentum index history from 2005 and accounts of India's 2008 momentum
crash, so **2002–09 is partly seen at the index level** too; a 2002–09
confirmation must disclose it. The full list is §9 of
`profitability-sweep-2026-10-01.md`.
