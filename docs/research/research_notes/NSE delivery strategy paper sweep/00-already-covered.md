# 00 — Already covered: NSE delivery strategy paper sweep

Exclusion map for the paper-sweep search. Read-only; no trial or look spent.
Counts: trials.md header "203 spent, numbered to 205" (as of 2026-10-14);
pivot brief "Count of record: 204 trials" (2026-10-18). Trial 205 is
registered in prereg-us-momentum.md line 9, not in the trials.md table.

## 1. Tested and closed (exhaustive)

Source: trials.md unless marked. Looks (L-numbers) are in section 2.

### 1a. Trials 1–40

- trial 1: `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d`
- trial 2: `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d`
- trial 3: `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d`
- trial 4: `sahab_dimaag ['RELIANCE', 'INFY'] 5m 15d`
- trial 5: `sahab_dimaag ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'] 5m 55d walk-forward-3`
- trial 6: `sahab_dimaag NIFTY 100 scanner, top 25/day 5m 55d`
- trial 7: `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 10d`
- trial 8: `grid-search min_confidence_to_trade=40 min_rrr=1.2 nifty100 top5 5m 55d`
- trial 9: `grid-search min_confidence_to_trade=40 min_rrr=1.5 nifty100 top5 5m 55d`
- trial 10: `grid-search min_confidence_to_trade=40 min_rrr=1.8 nifty100 top5 5m 55d`
- trial 11: `grid-search min_confidence_to_trade=50 min_rrr=1.2 nifty100 top5 5m 55d`
- trial 12: `grid-search min_confidence_to_trade=50 min_rrr=1.5 nifty100 top5 5m 55d`
- trial 13: `grid-search min_confidence_to_trade=50 min_rrr=1.8 nifty100 top5 5m 55d`
- trial 14: `grid-search min_confidence_to_trade=60 min_rrr=1.2 nifty100 top5 5m 55d`
- trial 15: `grid-search min_confidence_to_trade=60 min_rrr=1.5 nifty100 top5 5m 55d`
- trial 16: `grid-search min_confidence_to_trade=60 min_rrr=1.8 nifty100 top5 5m 55d`
- trial 17: `grid-search min_confidence_to_trade=70 min_rrr=1.2 nifty100 top5 5m 55d`
- trial 18: `grid-search min_confidence_to_trade=70 min_rrr=1.5 nifty100 top5 5m 55d`
- trial 19: `grid-search min_confidence_to_trade=70 min_rrr=1.8 nifty100 top5 5m 55d`
- trial 20: `diagnostic re-run at live default config for segmentation analysis`
- trial 21: `diagnostic re-run, confidence gate off, for checklist-entry segmentation`
- trial 22: `diagnose_entry_edge checklist 5m 55d top5 gate-off`
- trial 23: `diagnose_entry_edge checklist 30m 55d top5 gate-off`
- trial 24: `diagnose_entry_edge baseline 5m 55d top5 gate-off`
- trial 25: `diagnose_entry_edge baseline 30m 55d top5 gate-off`
- trial 26: `swing_backtester long-only hold=1 top5 2y stop_atr=None`
- trial 27: `swing_backtester long-only hold=2 top5 2y stop_atr=None`
- trial 28: `swing_backtester long-only hold=3 top5 2y stop_atr=None`
- trial 29: `swing_backtester long-only hold=5 top5 2y stop_atr=None`
- trial 30: `sahab_dimaag NIFTY 100 scanner, top 5/day 5m 730d`
- trial 31: `swing_backtester long-only hold=1 top5 2y stop_atr=None`
- trial 32: `swing_backtester long-only hold=2 top5 2y stop_atr=None`
- trial 33: `swing_backtester long-only hold=3 top5 2y stop_atr=None`
- trial 34: `swing_backtester long-only hold=5 top5 2y stop_atr=None`
- trial 35 (3a): **FAIL**: net −12.09 bp/session, t = −2.71.
- trial 36 (#74 baseline): first −0.302R (n 71), second −0.207R (n 51).
- trial 37 (#74 fixed, cost_pct 0.166): **PASS** (worse in first half only): first −0.354R (n 33), second +0.032R (n 12).
- trial 38 (#40 baseline): first −0.354R (n 33), second +0.032R (n 12).
- trial 39 (#40 fixed): **PASS** (worse in first half only): first −0.360R (n 31), second +0.089R (n 7).
- trial 40 (confluence, deep cache): **FAIL**: net −0.430R/trade, t = −9.84, n = 668; gross −0.188R.

### 1b. Trials 41–116 (strategy search; every row marked "fail")

- trial 41: `A-ck43-k2`  · net -0.343R (n 1388) · fail
- trial 42: `A-ck43-k3`  · net -0.244R (n 900) · fail
- trial 43: `B-ck-15m`  · net -0.332R (n 1670) · fail
- trial 44: `B-ck-60m`  · net -0.182R (n 992) · fail
- trial 45: `C-PB-5m-s1.5-2R-both`  · net -0.444R (n 3218) · fail
- trial 46: `C-PB-5m-s1.5-2R-short`  · net -0.475R (n 3057) · fail
- trial 47: `C-PB-5m-s1.5-hold-both`  · net -0.376R (n 2144) · fail
- trial 48: `C-PB-5m-s1.5-hold-short`  · net -0.432R (n 2111) · fail
- trial 49: `C-PB-5m-s3.0-2R-both`  · net -0.173R (n 1437) · fail
- trial 50: `C-PB-5m-s3.0-2R-short`  · net -0.195R (n 1429) · fail
- trial 51: `C-PB-5m-s3.0-hold-both`  · net -0.170R (n 1332) · fail
- trial 52: `C-PB-5m-s3.0-hold-short`  · net -0.173R (n 1329) · fail
- trial 53: `C-PB-15m-s1.5-2R-both`  · net -0.265R (n 2051) · fail
- trial 54: `C-PB-15m-s1.5-2R-short`  · net -0.259R (n 1833) · fail
- trial 55: `C-PB-15m-s1.5-hold-both`  · net -0.244R (n 1688) · fail
- trial 56: `C-PB-15m-s1.5-hold-short`  · net -0.237R (n 1558) · fail
- trial 57: `C-PB-15m-s3.0-2R-both`  · net -0.155R (n 1261) · fail
- trial 58: `C-PB-15m-s3.0-2R-short`  · net -0.139R (n 1195) · fail
- trial 59: `C-PB-15m-s3.0-hold-both`  · net -0.164R (n 1221) · fail
- trial 60: `C-PB-15m-s3.0-hold-short`  · net -0.138R (n 1161) · fail
- trial 61: `C-PB-60m-s1.5-2R-both`  · net -0.149R (n 1046) · fail
- trial 62: `C-PB-60m-s1.5-2R-short`  · net -0.146R (n 944) · fail
- trial 63: `C-PB-60m-s1.5-hold-both`  · net -0.150R (n 1031) · fail
- trial 64: `C-PB-60m-s1.5-hold-short`  · net -0.146R (n 940) · fail
- trial 65: `C-PB-60m-s3.0-2R-both`  · net -0.083R (n 915) · fail
- trial 66: `C-PB-60m-s3.0-2R-short`  · net -0.077R (n 877) · fail
- trial 67: `C-PB-60m-s3.0-hold-both`  · net -0.085R (n 914) · fail
- trial 68: `C-PB-60m-s3.0-hold-short`  · net -0.077R (n 877) · fail
- trial 69: `C-MR-5m-s1.5-2R-both`  · net -0.647R (n 2962) · fail
- trial 70: `C-MR-5m-s1.5-2R-short`  · net -0.616R (n 1472) · fail
- trial 71: `C-MR-5m-s1.5-hold-both`  · net -0.637R (n 2883) · fail
- trial 72: `C-MR-5m-s1.5-hold-short`  · net -0.610R (n 1460) · fail
- trial 73: `C-MR-5m-s3.0-2R-both`  · net -0.344R (n 2198) · fail
- trial 74: `C-MR-5m-s3.0-2R-short`  · net -0.341R (n 1272) · fail
- trial 75: `C-MR-5m-s3.0-hold-both`  · net -0.343R (n 2198) · fail
- trial 76: `C-MR-5m-s3.0-hold-short`  · net -0.340R (n 1272) · fail
- trial 77: `C-MR-15m-s1.5-2R-both`  · net -0.380R (n 1361) · fail
- trial 78: `C-MR-15m-s1.5-2R-short`  · net -0.370R (n 617) · fail
- trial 79: `C-MR-15m-s1.5-hold-both`  · net -0.381R (n 1361) · fail
- trial 80: `C-MR-15m-s1.5-hold-short`  · net -0.371R (n 617) · fail
- trial 81: `C-MR-15m-s3.0-2R-both`  · net -0.208R (n 1215) · fail
- trial 82: `C-MR-15m-s3.0-2R-short`  · net -0.214R (n 598) · fail
- trial 83: `C-MR-15m-s3.0-hold-both`  · net -0.208R (n 1215) · fail
- trial 84: `C-MR-15m-s3.0-hold-short`  · net -0.214R (n 598) · fail
- trial 85: `C-MR-60m-s1.5-2R-both`  · net -0.189R (n 226) · fail
- trial 86: `C-MR-60m-s1.5-2R-short`  · net -0.127R (n 97) · fail
- trial 87: `C-MR-60m-s1.5-hold-both`  · net -0.189R (n 226) · fail
- trial 88: `C-MR-60m-s1.5-hold-short`  · net -0.127R (n 97) · fail
- trial 89: `C-MR-60m-s3.0-2R-both`  · net -0.092R (n 224) · fail
- trial 90: `C-MR-60m-s3.0-2R-short`  · net -0.062R (n 97) · fail
- trial 91: `C-MR-60m-s3.0-hold-both`  · net -0.092R (n 224) · fail
- trial 92: `C-MR-60m-s3.0-hold-short`  · net -0.062R (n 97) · fail
- trial 93: `C-VB-5m-s1.5-2R-both`  · net -0.589R (n 2949) · fail
- trial 94: `C-VB-5m-s1.5-2R-short`  · net -0.606R (n 1841) · fail
- trial 95: `C-VB-5m-s1.5-hold-both`  · net -0.573R (n 2164) · fail
- trial 96: `C-VB-5m-s1.5-hold-short`  · net -0.612R (n 1573) · fail
- trial 97: `C-VB-5m-s3.0-2R-both`  · net -0.216R (n 1394) · fail
- trial 98: `C-VB-5m-s3.0-2R-short`  · net -0.253R (n 1159) · fail
- trial 99: `C-VB-5m-s3.0-hold-both`  · net -0.221R (n 1287) · fail
- trial 100: `C-VB-5m-s3.0-hold-short`  · net -0.275R (n 1110) · fail
- trial 101: `C-VB-15m-s1.5-2R-both`  · net -0.283R (n 1706) · fail
- trial 102: `C-VB-15m-s1.5-2R-short`  · net -0.231R (n 1121) · fail
- trial 103: `C-VB-15m-s1.5-hold-both`  · net -0.276R (n 1494) · fail
- trial 104: `C-VB-15m-s1.5-hold-short`  · net -0.225R (n 1038) · fail
- trial 105: `C-VB-15m-s3.0-2R-both`  · net -0.155R (n 1164) · fail
- trial 106: `C-VB-15m-s3.0-2R-short`  · net -0.116R (n 897) · fail
- trial 107: `C-VB-15m-s3.0-hold-both`  · net -0.152R (n 1139) · fail
- trial 108: `C-VB-15m-s3.0-hold-short`  · net -0.117R (n 887) · fail
- trial 109: `C-VB-60m-s1.5-2R-both`  · net -0.136R (n 904) · fail
- trial 110: `C-VB-60m-s1.5-2R-short`  · net -0.131R (n 614) · fail
- trial 111: `C-VB-60m-s1.5-hold-both`  · net -0.143R (n 896) · fail
- trial 112: `C-VB-60m-s1.5-hold-short`  · net -0.124R (n 612) · fail
- trial 113: `C-VB-60m-s3.0-2R-both`  · net -0.079R (n 848) · fail
- trial 114: `C-VB-60m-s3.0-2R-short`  · net -0.074R (n 597) · fail
- trial 115: `C-VB-60m-s3.0-hold-both`  · net -0.080R (n 848) · fail
- trial 116: `C-VB-60m-s3.0-hold-short`  · net -0.075R (n 597) · fail

### 1c. Trials 117–204 and the momentum family

- trial 117 (3g, Smart Money multi-timeframe): **FAIL**: net −0.299R/trade, t = −5.56, n = 256.
- trial 118 (3h run 1): **VOID, not a verdict**. "Seen before voiding: net monthly excess +0.61% (t 1.99), both halves positive, CAGR gap +6.9 pp, DSR 0.28 → would have been FAIL."
- trial 119 (3h run 2, of record): **FAIL on the pre-registered rule**: net monthly excess +0.72%, t = 2.48 (passes); DSR 0.24 at 119 trials (fails, rule ≥ 0.95). Held-out NOT spent. 2026-09-26: contaminated by a look-ahead (split-adjusted ₹20 price floor, #135); FAIL stands; not re-run.
- trial 120 (3i Part A): **PASS on the family-level bar (N_family = 3)**: net excess +0.82%/month, t 2.91 (gate 2.394), family DSR 0.98. Project-wide DSR 0.62.
- trial 121 (Sahab Ranker C1): **FAIL** (family N = 2): net excess +0.08%/month, t 0.23.
- trial 122 (Sahab Ranker C2, ridge): **FAIL**: +0.14%/month, t 0.41.
- trial 123 (Jev book): pending. Verdict after 300 trades or 60 sessions; first round 2026-09-28.
- trial 124 (overnight ETF H1): **FAIL** (family N = 2): gross +2.41 bp, net −6.42 bp/night, t −5.88 over 2,655 nights.
- trial 125 (overnight ETF H2): **FAIL**: gated book −0.09 bp/night (t −0.15).
- trial 126 (A′, trial 126 rule): **SURVIVES trial 120's six criteria, narrowly and with a smaller edge**: net excess +0.71%/month, t 2.51 (gate 2.394), DSR 0.952 at N = 3. "At the family of 10 now counted it would not clear" (bound 2.807, DSR 0.825).
- trial 127 (W): family N = 10. **FAIL**: net excess +1.02%/month, t 2.76 (gate 2.807), DSR 0.871 (gate 0.95); against the running book +0.31%/month, t 0.97 (gate 1.65). "No change to the paper book."
- trials 128–202 (combo search, prereg-combo-search.md): 8 sources × 3 horizons × 3 rules, plus 3 pattern-alone controls; net of 16.63 bp. **FAIL**: 0 of 75 pass, none positive net; best −13.8 bp a trade; pattern alone −16.4 bp.
- trial 203 (Jev 2, family "LLM judgment", N_family = 3): pending; clustered t ≥ 2.39.
- trial 204 (frog-in-the-pan, momentum family N = 11): **FAIL**: this rule minus the base −0.39%/month, paired t −2.15 (needed ≥ +1.65); own net excess +0.32%/month, t 1.26 (gate 2.838), DSR 0.357. Confirmation on ranks 201–400 (L57): −0.15%/month, t −0.72.
- trial 205 (momentum family N = 12): registered, not run per the docs read. "This is the 12th trial in the slow cross-sectional momentum family (trial 204 was the 11th)… t ≥ 2.865. Once spent, the family's next bar is 2.891." (prereg-us-momentum.md line 9).
- Momentum-family bars as stated: N = 3 → 2.394 (trial 120); N = 10 → 2.807 (trials 126, 127); N = 11 → 2.838 (trial 204); N = 12 → 2.865 (prereg-us-momentum.md line 9); next → 2.891.
- Not this family: "new family 'insider buying', N = 2, t ≥ 2.24" (entry-timing-sweep-2026-09-27.md line 311).

### 1d. Other closed, withdrawn, void or measurement-only lines

- 3b: "WITHDRAWN at stage 1 without spending trial 36" (trials.md footer, line 275). Stage 1a/1b are L31 and L32, both DOES NOT CLEAR.
- 3c: measurements only, L23–L25 (no trial).
- 3d: feasibility only, L4 (trials.md row L4; skipped-3d-earnings-drift.md). Earnings-drift stage A is L39.
- 3e: "already pre-registered and not run" (phase3-scoping.md line 172; prereg-3e-wide-structure-short.md).
- 3f: "CLOSED at stage 0 — amendment 4 FAIL 93.41%" (progress.md line 68). "Looks spent: none. Trials spent: none." (results-3f-stage0.md lines 268, 376). Gate: results-3f-stage0.md line 347.
- PEAD (L39): **NO-GO**: gross +0.25%/month, NW t 1.41 (rule ≥ 0.37%).
- Rule-lab historical search (L55): closed; 0 survivors (Look 1: 104,655 combinations, 0 survivors; Look 2: 0 survivors among 24,026 powered combinations).
- Kronos (L40): FAIL at all three horizons. TSFM family (L46): FAIL 18 of 18. Qlib LightGBM (L47): FAIL.
- Test A (201-trade ungated run): not in the trial list (trials.md line 184).
- R1 (Test A re-run) and R2 (3h run 2 re-run, `963b0b2`): replications, not counted (trials.md rows R1 and R2, lines 290–291).
- Pivot brief closed list, quoted in section 4 (line 16): intraday entries, overnight ETF, PEAD, Sahab Ranker, Kronos/TSFM family, frog-in-the-pan.

## 2. Research looks L1–L57 (one phrase each)

Source: trials.md look table, rows L1–L57 (lines 200–264). L37 and L43–L45 are not table rows.

- L1: daily rank IC of the composite pre-market score vs session return (436 days).
- L2: loss attribution of the 201-trade sample (exit reason, gross vs net, side, payoff, holding time).
- L3: step 1b lookahead proof: nine pre-open features recomputed on truncated series.
- L4: step 3d feasibility: can a free source give earnings announcement dates, 2024-09 to 2026-09.
- L5: step 1 random-entry null test, 200 seeds × 2 cost modes: PASS at −0.0495R (measures the harness).
- L6: step 2 data gate, yfinance vs Kite on 29,949 stock-sessions: r = 0.9832; 18.55% differ by >25 bp.
- L7: step 2 rank IC, atr_pct (band feature).
- L8: step 2 rank IC, rs10.
- L9: step 2 rank IC, from_high.
- L10: step 2 rank IC, from_low (sign coded backwards).
- L11: step 2 rank IC, rsi (side-dependent band feature).
- L12: step 2 session difference, trend.
- L13: step 2 session difference, nr7.
- L14: step 2 session difference, inside.
- L15: step 2 session difference, pattern (Bulkowski swing).
- L16: step 2 session difference, reversal (Murphy reversal day).
- L17: step 2-A1 cross-correlations among atr_pct, from_high, from_low (exploratory; selects nothing).
- L18: step 2-A2 partial ICs of the survivors; also gates the held-out look (amendment 8).
- L19: step 2-B rank IC of the three survivors vs the tradable Kite target (09:20 open to 15:10 close).
- L20: step 2-C atr_pct quintile spread in bp vs round-trip cost (descriptive).
- L21: raw ICs on universe A's 8-year sample; denominator for L18.
- L22: null diagnostic, 20 seeds: attribution of the −0.05R harness bias.
- L23: 3c §A unconditional: overnight +16.78 bp (t +9.50); intraday −6.94 bp (t −2.80).
- L24: 3c §B volatility-sorted: mechanism holds, both legs monotone across 5 quintiles.
- L25: 3c §C tradable Kite window: intraday spread +8.11 bp vs 33.20 bp (0.24×); does not clear.
- L26: universe B replication of atr_pct: PASS at −0.0332 (t −6.68); spread +5.97 bp vs 22.60 bp (0.26×).
- L27: universe B unconditional means: overnight +19.84 bp; intraday −9.93 bp.
- L28: universe B volatility-sorted: overnight −14.15 bp (t −8.55, PASS); intraday not distinguishable from zero.
- L29: index-level split, NIFTY 50/100/BANK; not pre-registered (omission recorded).
- L30: like-for-like fix of L29 on universe A's 1,546 sessions: overnight +3.91 bp (23%); intraday −0.21 bp (3%).
- L31: 3b stage 1a, cross-sectional momentum: −1.60 bp (t −0.48) vs 33.20 bp gate; DOES NOT CLEAR.
- L32: 3b stage 1b, time-series momentum: +0.70 bp (t +0.61) vs 16.60 bp gate; DOES NOT CLEAR.
- L33: read-only chase of the 09-18 "9 passes, 0 orders" gap: one setup, re-evaluated 9 times.
- L34: universe expansion, B vs A reward:risk gate pass rate: FAIL (p_A 93.17%, p_B 92.83%).
- L35: event study on NSE filings, 9,586 events: no class clears 16.63 bp (BH).
- L36: results direction vs overnight gap: aligned gap +82.7 bp (t 4.78); aligned drift +5.9 bp at 30 min, 0 by the close.
- L37: **not in trials.md**. Order-book imbalance, prereg-orderbook.md (33.26 bp hurdle at lines 25, 96; 16.63 bp round trip at line 22). Status: "**pending**: 15 sessions from 2026-09-28" (entry-timing-sweep-2026-09-27.md line 88). No results file in docs/research.
- L38: 3i Part B, trial 120 rules on ranks 201–400, slippage 0.10%/side: CONFIRMS, +1.00%/month, t 3.31.
- L39: PEAD stage A, post-earnings drift, NIFTY 100: NO-GO (gross +0.25%/month, NW t 1.41).
- L40: Kronos zero-shot, next 15/30/60 minutes: top-minus-bottom spreads +0.27 / +0.51 / +1.61 bp vs 33.26 bp; FAIL at all three.
- L41: universe width stage 0, data gate: run 1 failed gate 6 on 2 of 67 jumps; run 2 passed all six. Records "L43 to L45 were not taken".
- L42: universe width B′: L38's rule (ranks 201–400) on the repaired panel: SURVIVES, +0.91%/month, t 3.00; counted in the family of 10. Records "L43, L44, L45 … were not taken".
- L43: **not taken**, ranks 401–600 (T3, "63, 56 and 30 months against the 120 required", reviewer-outbox.md line 138). Cited: trials.md rows L41 (line 250) and L42 (line 257); prereg-universe-width.md lines 797–804; results-universe-width.md lines 267–270.
- L44: **not taken**, ranks 601–800 (T4, 56 months; reviewer-outbox.md line 138). Same citations.
- L45: **not taken**, ranks 801–1,000 (T5, 30 months; reviewer-outbox.md line 138). Same citations.
- L46: six zero-shot foundation models in the L40 harness: FAIL 18 of 18.
- L47: LightGBM on Qlib Alpha158, trained on own 5-minute bars: FAIL at all three horizons.
- L48: breadth (A/D, McClellan, TRIN) and intermarket moves vs NIFTY 100 09:20 to 15:10: NO PASS; 0 of 8 survive BH at 5%.
- L49: scanner audit's four intraday features and the 09:45 gap reversal: FAIL, 0 of 13 tests.
- L50: bulk and block deal disclosures: VOID at stage 0 (21 directional events vs 60 required); no price read.
- L51: intraday index timing from lagged factor-portfolio returns: DOES NOT CLEAR at 30 or 60 minutes; 0 trades; the 2026 window is not read.
- L52: five newest forecasting models, forward: PENDING (about late December 2026).
- L53: after-tax value of trial 126's trade list, FIFO tax engine: after-tax CAGR 17.67% vs 17.28% for a Nifty200 Momentum 30 fund; TIES.
- L54: single-rule paper lab, forward: PENDING (157 single rules; collecting from the first session after deploy).
- L55: rule lab historical combinatorial search: Look 1, 0 survivors of 104,655 combinations; Look 2, 0 survivors among 24,026 powered combinations. Closed.
- L56: frog-in-the-pan stage 0: holdings and counts only; no return read.
- L57: frog-in-the-pan confirmation, ranks 201–400: **FAIL** (needed t ≥ +1.65); −0.15%/month, paired t −0.72.

- Conflict, not reconciled: trials.md line 275 footer says "Thirty-four looks, thirty-five trials." The look table has 53 rows (L1–L57 minus L37 and L43–L45).

## 3. Candidates reviewed in the sweep docs, never run

Verdicts are the docs' own words, quoted from the cited line. "(paraphrase)" marks a list the doc gives in prose. "Run" marks a candidate tested under another L- or trial number (our mapping, not the doc's).

### 3a. literature-sweep-2026-09-25.md §5 table (lines 236–248)
- #1 long-only momentum: "**Run as 3h (trial 119): FAIL on DSR 0.24; four other gates pass; +0.72%/mo net, t 2.48**" (line 240).
- #2 overnight index premium, Nifty futures: "Blocked by capital; revisit at ≥ ₹3–5 L" (line 241).
- #3 PEAD: "Candidate after 3h; needs post-2017 data" (line 242).
- #4 crypto funding carry: "Not pursued" (line 243).
- #5 crypto time-series momentum: "Not pursued" (line 244).
- #6 short Nifty variance premium: "Not pursued" (line 245); net evidence "retail **net −44%/yr on margin**".
- #7 intraday cash equity: "**Retired as the product**" (line 246).
- §2 market making (line 107): "Market making: no published retail profitability."
- §4 Reddit styles (lines 169–235): verdicts not extracted in this pass.

### 3b. predictive-tools-sweep-2026-09-29.md and data/predictive-tools-sweep/predictive_tools_{A,B,C}.md
- A #9 FinCast v1: "test **with a change**: size the checkpoint, confirm input format, apply the contamination rule". No FinCast row in trials.md (grep count 0).
- A #10 TimesFM-3.0: "test **with a change**: licence gate — research only, never near the engine". Named in the L52 row (trials.md line 255).
- A #1–#8 "test" rows: TimesFM-2.5, Moirai 2.0 R-small, FlowState-r1, Sundial ran in L46 (trials.md line 252). Chronos-2, TiRex-2, Toto 2.0 and Granite PatchTST-FM-r2 are named in L52 (trials.md line 255, pending).
- A #11 TiRex v1 "skip (TiRex-2 supersedes, and is Apache)" and #12 Chronos-Bolt "skip (Chronos-2 supersedes; speed fallback only)": both ran in L46. Verdict and run status disagree (section 6e, item i).
- A "skip", not run: #13 Granite TTM-r3 "skip for now (paper unreleased)"; #14 t0-alpha "skip"; #15 Time-MoE "skip (stale, point-only)"; #16 Timer "skip"; #17 Lag-Llama "skip"; #18 MOMENT-1 "skip (needs training)"; #19 TabPFN-TS "skip (wrong inductive bias; seconds per window)"; #20 TimeGPT-2.1 "skip"; #21 TimeCopilot "skip (not a model; LLM in the loop)"; #22 Moirai-MoE "skip (superseded)"; #23 Toto 1.0 "skip (2.0 supersedes)"; #24 UniTS "skip (training)"; #25 TOTEM "skip (training)".
- A #26 Kronos variants and forks: "skip as candidates; cite as the prior".
- B #2 factor-zoo intraday market timing (Bollerslev et al. 2025), predictive_tools_B.md line 83: "later; the only peer-reviewed net-of-cost intraday factor result; needs its own index-timing pre-registration". Not run. L51 is an index-timing look; no link to this paper is verified.
- B Qlib LightGBM + Alpha158: "Test, one look in the L40 harness". Run as L47 (FAIL).
- B Vibe-Trading Alpha Zoo: "Use as the factor code for #1; skip the agent". Not run.
- B #4 DeepLOB family: "Skip; revisit only if L37 clears and ≥3 months of depth exist". Not run.
- B Kronos NSE pre-registered negatives: "Attach to L40 as prior evidence". Not run separately.
- B "Skip" list (paraphrase): TradingAgents; virattt/ai-hedge-fund; FinMem / FinAgent / FinCon / QuantAgent / FinRobot; FinGPT-Forecaster; AlphaAgent / RD-Agent(Q) ("trial multiplier"); StockFormer; FinRL family; Alpha101 libraries ("skip as separate look"); tsfresh / featuretools; stockpy; 2026 financial-foundation-model repos.
- C #1 cross-sectional overnight-gap reversal (H2) + nq tilt: "skip at the bar; optional single closing measurement look at 09:45 only, expect FAIL". Run as L49 (FAIL, 0 of 13).
- C #3 Vaunox/quant-intraday: "skip; cite".
- C #4 NSE bulk/block-deal disclosures: "later, low priority: one event look". Run as L50 (VOID).
- C MFAST, arXiv 2609.23703: "later, only with a timestamped NSE announcement corpus".
- C #11 NifSent50 / Multi-Channel Sentiment Corpus (Nifty 500): "later, PEAD follow-up only". Labels "derived from the price move (circular)" (predictive_tools_C.md line 23).
- C "skip" list (paraphrase): #8 Warren Duffer; kronos-nse-terminal; GIFT Nifty implied open; vajra-quant ("daily, = index"); Nightwatch; ViperQ; The Accuracy Illusion ("skip as signal; keep as corroboration; adopt n_eff scoring rule").
- C #12 practitioner evidence since 2026-09-01: "Nothing found is a \"test\" at the project's bar." (line 67).
- Sweep summary: "No candidate has independent out-of-sample evidence, net of costs, on intraday stocks, Indian or otherwise." (predictive-tools-sweep-2026-09-29.md line 17); "Let L40 finish and report first." (line 100).

### 3c. entry-timing-sweep-2026-09-27.md, Part A ranked table (lines 105–122)
- 1 Order-book imbalance / depth pull: "Run L37 as registered; expect a fail. Do not add features." Not run (L37 not in trials.md).
- 2 News-day "stocks in play" ORB: "Only candidate for one new trial, low prior".
- 3 SIP ORB as published: "Already refuted in family; do not run as published."
- 4 QQQ 5-min ORB: "Refuted."
- 5 Market intraday momentum: "Refuted; do not reopen."
- 6 Trend-day noise area + VWAP trailing stop: "Not worth a trial".
- 7 Gap-and-go / gap-fade: "Already refuted."
- 8 Meta-labeling: "Not a source of edge."
- 9 Volatility / India VIX / relative-volume gating: "Not on its own."
- 10 Expiry-day effects: "Out of mandate".
- 11 Closing-auction imbalance: "Collect data first; not testable this year."
- 12 Index-rebalance effective-day pressure: "Reject for intraday."

### 3d. entry-timing-sweep-2026-09-27.md, §5 rejected (lines 164–178)
- SIP ORB as published: edge "~4–8 bp per rupee of position (my estimate)".
- QQQ/NIFTY index ORB: "full-sample replication Sharpe −0.06; Indian out-of-sample −21.8%; trial 35".
- Market intraday momentum: "L32 +0.70 bp; ~2.6 bp in the US original".
- Noise-area / VWAP trend-day momentum: "~4 bp gross even at US costs".
- VWAP breakout, pullback, mean reversion, checklist on any timeframe: "trials 41–116, gross −0.05R to +0.04R." (line 170).
- Gap-and-go / gap-fade: "results gaps are priced by the open (L36)".
- Meta-labeling: "it filters a primary, and ours has nothing to filter".
- VIX / volatility gating alone: "scales a sub-cost gross".
- Expiry-day plays: "documented edge is option writing, which is outside the mandate; option buying measured negative".
- Closing-auction imbalance: "no history yet, and the engine squares off before the auction" (line 175).
- Index-rebalance close: "daily-scale, reverses within days, about 5 events a year per index".
- Vendor or community "high Sharpe" ORB/intraday claims: "6-month samples, no out-of-sample, benchmark misstated".

### 3e. entry-timing-sweep-2026-09-27.md, Part B ranked table (lines 229–249) and sketches
- 1 Volatility-scaled momentum: "Trial 1" (sweep-local label; sketch line 272). No trial row in trials.md.
- 2 Market state / dynamic crash protection: "Second arm of Trial 1".
- 3 Index trend filter to cash: "Reject as a lead. At most a reported-only variant".
- 4 Rebalance date / tranching: "No trial. Record forward shadow tranches as a measurement".
- 5 Residual momentum: "Defer. Ranks below #6".
- 6 Frog-in-the-pan / information discreteness: "Trial 3, shadow only" (sweep-local label; sketch line 335: "only after 1 and 2"). Our mapping: run as trial 204 (section 1c).
- 7 Promoter open-market buying: "Trial 2" (sweep-local label; sketch line 311: "new family 'insider buying', N = 2, t ≥ 2.24"). No trial row in trials.md.
- 8 NIFTY inclusion / exclusion: "Later: an event-study look first, not a trial".
- 9 Bulk/block deal buys: "Low. A look only". Run as L50 (VOID).
- 10 Deliverable %: "Reject for now".
- 11 FII/DII flows as a timer: "Reject".
- 12 Short-term reversal: "Reject".
- 13 NSE factor indices: "Use as a fallback implementation, not a signal".
- 14 Timing new capital: "No trial. Add new money at the next monthly rebalance".
- Part B rejected (lines 343–354): trend filter; deliverable %; FII/DII; short-term reversal ("already lost here (121–122)"); bulk/block; turn-of-month and rebalance day ("timing luck is variance, not edge"); residual momentum; re-weighting inside the book; PEAD, overnight ETF, 1–5-day swings ("already closed (§84, §87, §37)").

### 3f. stock-picking-sweep-2026-09-28.md
- "Worth a pre-registered test, in order:" (line 120). Items (paraphrase): 1 the unchanged 3i rule on ranks 401–600, then 601–800 (line 122); 2 NSE-style tradability screens beyond rank 400; 3 value composite in the top 400–500; 4 low-volatility sleeve.
- "Skip:" (line 127), items (paraphrase): quality (ROE, leverage); momentum-plus-quality blends; 52-week-high proximity (§85 input); size tilt; earnings momentum ("closed by §84"); reversal, beta, IVOL, liquidity, illiquidity, price ("tested in §85"); micro-caps and SME.
- NSE momentum index tiers (lines 101–117): descriptive, no trial; script reference at line 69 (`data/stock-picking-sweep/tiers_2025_descriptive.py`). Line 116: "every tier fell harder than its parent in the 2024–25 slump".
- Recommended floor (lines 226–228): "Floor: within the top 800 by 126-session median traded value", ", loosest defensible 1,000" (line 226); "Traded on at least 95% of the last 126 sessions." (line 227); "EQ series on every one of the last 60 sessions." (line 228).

### 3g. profitability-sweep-2026-10-01.md §5 (lines 134–160), decision labels
- (a) "After-tax replay of trial 126's trades" (line 115), mapped to L53 by us: **Measure**.
- Tax-loss and ₹1.25 lakh gain harvesting: **Measure** inside L53.
- 2002–09 confirmation, unchanged rule: **Owner decides**
- Tax-aware hold rule: **Pre-register** once the owner fixes rule and family
- Conditional volatility overlay, de-risk only: **Leave** unless the owner wants a drawdown trial
- Bear-market filter: **Leave**
- Residual momentum; frog-in-the-pan tie-break: **Leave** (2026-09-27 sweep also rejected residual)
- 52-week high, lookback grids, industry momentum, weighting, 30 names: **Leave**
- Alpha 50-style signal (1-year Jensen alpha): **Leave**; its index fund is a product route
- Restrict to NIFTY 100; widen to 400: **Leave**
- Low-vol sleeve, momentum × low-vol: **Leave** (risk reduction)
- Dividend-yield sleeve; value; quality: **Leave**
- Dual momentum NIFTYBEES/GOLDBEES/liquid; static Nifty–gold mix: **Leave** (allocation, not excess); runnable at ₹5,500
- Buyback tender reserve: **Leave** (grade C, small)
- Turn-of-month; pre-announcement; sector rotation: **Leave**
- LLM news check on the book: **Leave**; forward-only after a memory audit, if ever
- Covered calls, put-writing: **Leave**
- Option buying, 0DTE, "sure-shot" selling, copy trading, smallcases, marketplaces: **Leave**
- LLM trading agents, AI funds, leaderboards: **Leave**
- Pairs, overnight; market making, speed: **Leave**
- Selling research (WorldQuant BRAIN, Numerai): **Leave** (outside the project)
- §4 measurements (a)–(e): "Measure". "Then at most one or two trials." (line 125).

### 3h. phase3-scoping.md §1 and §3
- §1 (line 151): "**None found.** Searched: USDINR intraday seasonality, day-of-week and expiry effects, RBI reference-rate and fixing-time effects, RBI intervention intraday."
- §3 rank 1 (line 161), "NSE cash: short high-`atr_pct`, long low-`atr_pct`, intraday": "**Closed.** Phase 2 §3."
- §3 rank 2 (line 162), "NIFTY options bought at the open, sold at the close (Muravyev & Ni direction)": data cell "**No, and not obtainable from Kite**: expired options have no history"; status cell "Not viable. The hedge is unreachable, the unhedged effect is undocumented, and there's no data."
- §3 rank 3 (line 163), "NSE cash: Gao-style last-half-hour timing on the index's first-half-hour sign": "**Withdrawn** (3b stage 1). 3b's pre-registration forbids re-registering it."
- Line 171: "**CDS and MCX GOLDPETAL** have low hurdles (3.8–8.8 bp) but **no documented effect**".
- Line 172: "**3e** (PR #77, wide-structure NSE shorts) is already pre-registered and not run."

## 4. Candidates named as untested, verbatim

pivot-brief-2026-10-18.md line 16:
> Count of record: 204 trials. Lines closed and not to be reopened: intraday entries (76-config sweep, confluence, universe width), overnight ETF, PEAD, Sahab Ranker, Kronos/TSFM family, frog-in-the-pan.

pivot-brief-2026-10-18.md line 30 (Pivot B row):
> | B. New strategy families, delivery horizon only | Pre-registered search over families not yet tried: cross-sectional low-vol/quality overlays on the momentum book, turn-of-month, buyback/promoter-buy events, sector rotation, gold/debt dual momentum. | 1 trial each; momentum-family bar now t ≥ 2.865 | Literature says net-positive evidence exists only at ≥ 1-month horizons; these are the untested ones. Expected hit rate: low. |

pivot-brief-2026-10-18.md line 46 (§4 item 5):
> > 5. **Research pipeline (one pre-registered trial at a time, each only after the previous one's results file is committed; start after 1–4 are merged):** pick from the untested delivery families (low-vol/quality overlay as a non-inferiority rule, turn-of-month, promoter open-market buys, dual momentum with gold). Family-level bar, both halves, forward band, no held-out read.

pivot-brief-2026-10-18.md line 55:
> - **Replace the paid Jev judge in Jev2 with a local Qwen** as a *new, pre-registered arm* (same prompts, same blind decomposition). Saves API spend, gives a second judge to compare, raises N_family by one. Only worth doing if Jev2 is still alive at its 300-trade read.

pivot-brief-2026-10-18.md line 57:
> - **News/filing classification** for the research pipeline (B), locally, so a trial over thousands of filings costs nothing per call.

phase3-scoping.md line 157:
> **None of them clears 1×.** The three with a stated size are ranked below. Every one is either already tested in-house or needs an instrument this account can't reach, so **this section recommends no pre-registration**. It is recorded so the ranking isn't rediscovered.

phase3-scoping.md lines 161–163 (§3 candidate rows):
> | 1 | NSE cash: short high-`atr_pct`, long low-`atr_pct`, intraday | +16.30 bp top-5/bottom-5 (in-house, replicated on universe B) | **33.20 bp (two-leg)** | **0.49×** | NSE 5m, 2+ years | **Yes** | **Closed.** Phase 2 §3. Subject to the negative-intraday-drift caveat: the long leg starts −6.4 bp behind. |
> | 2 | NIFTY options bought at the open, sold at the close (Muravyev & Ni direction) | +30 bp of premium, **US, delta-hedged**, gross | 110 bp (one leg, premium ≤ ₹84.6) | **0.27×** | NIFTY option 5m history | **No, and not obtainable from Kite**: expired options have no history | Not viable. The hedge is unreachable, the unhedged effect is undocumented, and there's no data. |
> | 3 | NSE cash: Gao-style last-half-hour timing on the index's first-half-hour sign | +2.6 bp **US**; **+0.70 bp India in-house** | 10.63 bp charges / 16.60 bp with slippage | **0.25× US; 0.04× India** | NSE 5m | **Yes** | **Withdrawn** (3b stage 1). 3b's pre-registration forbids re-registering it. |

phase3-scoping.md lines 171–172:
> - **CDS and MCX GOLDPETAL** have low hurdles (3.8–8.8 bp) but **no documented effect**. A CDS or MCX hypothesis would be an exploratory search, not a literature-backed test. It would also need a **forward-collected 5-minute cache** (§1d) before it could run. If the user wants that line opened, the honest first step is to start collecting data, not to pre-register.
> - **3e** (PR #77, wide-structure NSE shorts) is already pre-registered and not run. It has no literature effect size, so it isn't ranked here. Its case is the friction arithmetic, not a documented effect.

## 5. Data available, and data not available or rejected

### 5a. Available locally (backend/data, listed 1 Nov 2026; .db files are gitignored)
- Kite 5-minute cash: "**Yes.** NIFTY 100, 2024-09-20 → 2026-09-18, 3.63M bars. **The only segment cached.**" (phase3-scoping.md line 103). Cache: backend/data/kite_history.db (409,325,568 bytes, 20 Sep).
- Daily bhav: backend/data/bhav/ (25 Sep), bhav_daily/ (28 Oct), bhav_live/ (30 Oct). 2026 held-out bhav: bhav_daily_2026_heldout/ (26 Sep).
- Corporate actions: backend/data/corp_actions/ (30 Oct). "The 743 corporate actions that differ between the panels" (results-universe-width.md line 267).
- Index and universe files: backend/data/nse_indices/ (31 Oct); nifty100.csv (6,601 bytes, 18 Oct); universe_b.csv (3,401 bytes, 21 Sep); universe_b_rows.json (14,047,250 bytes, 21 Sep); universe_b_overnight_rows.json (9,316,367 bytes, 21 Sep).
- overnight_1m.db (445,665,280 bytes, 27 Sep): use not checked in this pass.
- Kronos: backend/data/kronos.db (745,472 bytes, 30 Sep); kronos_shadow_2026-09-30.json (1,265,340 bytes, 30 Sep).
- Live paper state, not research data: sahab_journal.db (2,602,766,336 bytes, 1 Nov); jev_book_state.json; jev2_book_state.json; momentum_book_state.json.
- Event data used in looks: NSE filings, 9,586 events (L35). Bulk deals: "21 directional NIFTY 100 bulk events in the Kite cache" (L50 row, trials.md line 258). Block deals: 251 stock-days (same row).
- 3f membership match (results-3f-stage0.md): "member-months 2010-01 → 2025-12 | 19,261" (line 279); "**17,992** | **93.41%**" for the amendment-4 match within 6 bp (lines 342–343); "absent … | 940" (line 343). Gate line 135: "**95.17%** — gate ≥ 95% **PASS**" (see flag g).
- yfinance: used only as a gate check against Kite, r = 0.9832 (L6).

### 5b. Not available, or rejected
- BSE cash intraday: row "BSE cash | Yes: 2,967 bars, RELIANCE | n/a | No" (phase3-scoping.md line 104, local-cache column).
- NFO futures, expired contracts, intraday: "**No.** `continuous=True` returns \"invalid interval for continuous data\" at 5 minutes; it gives **day** candles only" (phase3-scoping.md line 105).
- NFO options, expired contracts, intraday: "**No.** \"Historical data won't be available for the expired option contract\" (forum 15361)" (line 106). Listing-only history from 2026-08-04 (same row).
- MCX futures, expired contracts, intraday: "**No intraday.** Continuous **day** candles \"from 2011 onwards\" (forum 10751)" (line 107).
- CDS futures (line 108): "**Monthly contracts only**"; "**Weekly contracts returned 0 bars.**"; expired contracts: "**None, not even daily continuous**".
- phase3-scoping.md line 110: "**This is the binding data constraint for every non-equity segment.**"
- Order-book depth history: "the depth data does not exist here" (predictive_tools_B.md line 85). backend/depth_sampler.py writes depth going forward; no backend/data/depth_samples directory (1 Nov listing).
- Closing-auction history: "no history yet, and the engine squares off before the auction" (entry-timing-sweep-2026-09-27.md line 175). Part A rank 11: "Collect data first; not testable this year."
- Tiers beyond rank 400: "T3, T4 and T5 have 63, 56 and 30 months against the 120 required" (reviewer-outbox.md line 138). L43–L45 "not taken" (prereg-universe-width.md lines 797–804; trials.md L41 and L42 rows).
- 2026 held-out window: "Held-out untouched" (trials.md line 258, L50 row); "the 2026 window is not read" (trials.md line 260, L51 row). Boundary differs: backend/research/splits.py:30 `HELD_OUT_START = "2026-01-02"`; backend/research/slow_momentum.py:51 `HELD_OUT_START = "2026-01"` (flag h).
- NifSent50 labels: "NifSent50 labels derived from the price move (circular)" (predictive_tools_C.md line 23, table row 11).
- kronos-nse-terminal: "reports 63.4% / Sharpe 1.47 on 60 trades with no dates or cost table" (predictive_tools_C.md line 48).
- FinCast v1 (predictive_tools_A.md #9): "test **with a change**: size the checkpoint, confirm input format, apply the contamination rule".
- TimesFM-3.0 (predictive_tools_A.md #10): "licence gate — research only, never near the engine".

## 6. Round-trip cost figures

Survey (run 2026-11-01, repo root): `grep -rn -i -E 'round[- ]trip|two-leg|two legs' . --include='*.md' --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=graphify-out --exclude='00-already-covered.md' | grep -E '[0-9]'` gives 339 lines. Per-figure counts are lines containing the string in that survey (a line can hold more than one figure): 16.60 bp 32; 16.6 bp 28; 16.63 bp 21; 33.26 bp 7; 33.20 bp 7; 33.05 bp 2; 22.60 bp 4; 14.27 bp 5; 10.60 bp 3; 6.95 bp 7; 15.34 4; 18.10 0. The earlier counts (250 and 397 lines; 27 and 20 hits) did not reproduce and are not used.

### 6a. Intraday cash (MIS), index, FNO, MCX, CDS
- 16.60 bp: "16.60 bp (10.60 bp charges + 6.00 bp slippage)" results-fix74-cost-pct.md:7; "6.00 bp slippage + 10.60 bp charges = 16.60 bp" results-step2-followups.md:163; "**16.60 bp** round trip." results-3c-overnight-intraday.md:19.
- 16.63 bp: "Net return per trade = direction × target − 16.63 bp." prereg-combo-search.md:27 (also :18); "16.63 bp round trip" prereg-orderbook.md:22; "two legs at 16.63 bp" results-scanner-features.md:7.
- 33.20 bp (two legs at 16.60 bp): "+8.11 bp against 33.20 bp, not 16.60" results-3c-overnight-intraday.md:108; "**33.20 bp (two-leg)**" phase3-scoping.md:161.
- 33.26 bp (two legs at 16.63 bp): prereg-orderbook.md:25; results-scanner-features.md:7; "the bar is +33.26 bp" results-tsfm-family.md:34.
- 10.63 bp: NSE cash intraday row "| NSE cash intraday | 10.63" phase3-scoping.md:71; "NSE cash at ₹5,500 gives 10.63 bp" phase3-scoping.md:81.
- 6.95 bp: "charges 5.95 bp plus slippage 1.00 bp = **6.95 bp**" prereg-index-timing.md:93.
- 14.27 bp: "₹1,00,000 notional … **14.27 bp**" prereg-jev2-book.md:180. Flag (b): prereg-jev-book.md:78 "**14.3 bp**".
- NFO options, % of premium: "| NFO options (bp of premium" row, phase3-scoping.md:74 (110.16 bp; 109.53 at ₹5,500 per the same row).
- MCX futures 8.80 bp (phase3-scoping.md:75); CDS futures 7.20 / 5.05 / 4.41 / 3.81 bp (phase3-scoping.md:76); "3.8–8.8 bp" hurdle at phase3-scoping.md:171.

### 6b. Universe B and delivery at ₹33,000
- 22.60 bp: "**22.60 bp** | Entry 6 §D — **double the configured slippage per leg**, charges unchanged" prereg-L34-universe-b-rrr-gate.md:122; "a **22.60 bp** round trip rather than 16.60 bp" prereg-universe-b-addendum-overnight.md:106.
- Delivery at ₹33,000: "| ₹33,000 | **16.60 bp** | **33.05 bp** |" (columns Intraday (MIS) and Delivery (CNC)), results-entry7-d-feasibility.md:155; "Delivery round trip at ₹33,000 | 33.05 bp" reviewer-outbox.md:664.
- Delivery at ₹33,000, doubled slippage: "**39.05 bp**" results-universe-b-overnight.md:105.
- Delivery at ₹5,000: "**60.08 bp**" results-entry7-d-feasibility.md:154.

### 6c. Delivery (CNC), momentum book and 3f/3h
- 56.1 bp at ₹5,500: "| 1 (the user's rule) | ₹5,500 | 50.1 bp | 6.0 bp | **56.1 bp** |" prereg-3f-momentum-delivery.md:76. Rows 77–80: 84.0 (₹2,750), 111.9 (₹1,833), 167.7 (₹1,100), 865.0 (₹183, "30 (the index's size)").
- 57.2 bp, stale tariff: "`costs.DELIVERY_COSTS` carries `dp_charge_per_sell = 15.93` and `exchange_txn_pct = 0.00297`; the published figures are **15.34** and **0.00307**" prereg-3f-momentum-delivery.md:88–92; "make the round trip **57.2 bp**, 1.1 bp too high" (same note). Flag (d).
- 493 bp: "| **₹5,500 real** (15 names → ₹367 each) | DP ₹18.10 per sell alone = **493 bp** |" prereg-3h-slow-momentum-delivery.md:64.
- ~59 bp at ₹6,667 per name: "At ₹6,667 per name: buy 16.9 bp, sell 15.4 bp + 27.2 bp DP → **~59 bp" prereg-3h-slow-momentum-delivery.md:153. "At ₹1 lakh (paper) delivery costs ~59 bp per round trip on ₹6,667" literature-sweep-2026-09-25.md:148. Flag (j).
- ~41 bp at ₹3 lakh: "| ₹3,00,000 (15 names → ₹20,000 each) | ~41 bp |" prereg-3h-slow-momentum-delivery.md:66.
- Turn-of-month: "~41 bp gross vs ~10 bp round trip" profitability-sweep-2026-10-01.md:154; "~41 bp gross/window vs ~10 bp ETF round trip" data/profitability-sweep/R4-low-turnover-families.md:19.
- DP charge: "₹15.34 + 18% GST = ₹18.10 per scrip per sell-day" prereg-3h-slow-momentum-delivery.md:150; "Zerodha's ₹15.34 already includes GST (#135)" backend/research/slow_momentum.py:70. Flag (c).
- Literature §3 table, lines 130–138 (as the doc states them): NSE cash delivery "**~25 bp charges** (STT 20 bp of it) + slippage"; Nifty futures "**6.0 bp** + ~6 bp per monthly roll"; Sensex futures "5.5 bp"; Nifty weekly option "₹70 ≈ 72 bp of premium at ₹150"; MCX crude mini / natgas mini "7–8 bp"; MCX gold mini "2.0 bp"; crypto spot "47 bp fees **+ 100 bp TDS withheld on every sale**"; Delta perps "11.8 bp taker / 4.7 bp maker".

### 6d. Parameters in code
- backend/config.py:562–576 COSTS: brokerage_per_order 20.0 (line 563, "whichever is lower" with brokerage_pct 0.03 at line 564); stt_pct_sell 0.025 (line 565, intraday equity); exchange_txn_pct 0.00307 (line 567); stamp_duty_pct_buy 0.003; gst_pct 18.0; slippage_pct 0.03 (line 576, comment "This is a rough estimate, not measured").
- backend/costs.py:53: `slippage = 2 * notional * costs_cfg.get("slippage_pct", 0.0) / 100`.
- backend/costs.py:62–69 DELIVERY_COSTS: stt_pct_sell 0.1; stt_pct_buy 0.1; exchange_txn_pct 0.00307; stamp_duty_pct_buy 0.015; gst_pct 18.0; slippage_pct 0.03; dp_charge_per_sell 15.34 (comment: "Rs 15.34 per scrip", GST included, #79).
- backend/momentum_book.py:109 `DP_PER_SELL = 15.34`; line 706 adds `DP_PER_SELL if dp` to the sell cost.
- backend/research/slow_momentum.py:70 `DP_PER_SELL = 15.34`.

### 6e. Conflicts flagged, not reconciled
- (a) Round trip 16.60 bp (results-fix74-cost-pct.md:7) vs 16.63 bp (prereg-combo-search.md:18, :27; prereg-orderbook.md:22). Two-leg 33.20 (results-3c-overnight-intraday.md:108) vs 33.26 (prereg-orderbook.md:25; results-tsfm-family.md:34).
- (b) Charges 10.60 bp (results-fix74-cost-pct.md:7) vs 10.63 bp (phase3-scoping.md:71, :81). Jev book: "**14.3 bp**" (prereg-jev-book.md:78) vs 14.27 bp (prereg-jev2-book.md:180).
- (c) DP per sell: ₹15.34 GST-inclusive (backend/research/slow_momentum.py:70; costs.py:66 comment) vs "₹15.34 + 18% GST = ₹18.10" (prereg-3h-slow-momentum-delivery.md:150) and "DP ₹18.10 per sell alone = **493 bp**" (:64).
- (d) Stale tariff note in prereg-3f-momentum-delivery.md:88–92 (15.93 DP, 0.00297 exchange charge) vs backend/costs.py (15.34, 0.00307).
- (e) Slippage baselines: 3 bp per leg (backend/config.py:576); "Slippage 5 bp in the book, 3 bp in `costs.py`" (live-momentum-gaps-2026-10-18.md:41); "The slippage of 0.05% a side" (prereg-3i-momentum-corrected-data.md:237); "Trial 126 fails at 0.07% slippage a side instead of 0.05%" (profitability-sweep-2026-10-01.md:120); "slippage doubled to 0.10%/" (trials.md line 246, L38); universe B "double the configured slippage per leg" (22.60 bp, 6b).
- (f) Trial count: trials.md line 275 "Thirty-four looks, thirty-five trials." vs 53 look rows; trials.md header "203 spent, numbered to 205" vs pivot brief "Count of record: 204 trials".
- (g) 3f gate: results-3f-stage0.md line 135 "95.17% … gate ≥ 95% PASS" vs amendment-4 match "93.41%" (lines 342–343, FAIL); progress.md line 68 "CLOSED at stage 0 — amendment 4 FAIL 93.41%".
- (h) Held-out boundary: backend/research/splits.py:30 "2026-01-02" vs backend/research/slow_momentum.py:51 "2026-01".
- (i) predictive_tools_A.md #11 TiRex v1 and #12 Chronos-Bolt marked "skip" but recorded as run in L46.
- (j) ₹1 lakh vs ₹6,667: literature-sweep-2026-09-25.md:148 pairs "₹1 lakh (paper)" with "on ₹6,667"; prereg-3h-slow-momentum-delivery.md:153 uses ₹6,667 per name.
- (k) Survey count: 250 lines in an earlier pass, 339 now (see the section 6 intro).
- (l) L37 status: entry-timing-sweep-2026-09-27.md line 88 "pending: 15 sessions from 2026-09-28"; no L37 row in trials.md (grep count 0).

