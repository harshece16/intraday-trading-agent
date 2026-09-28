# Pre-registration — does a zero-shot Kronos forecast rank the next intraday move? (research look L38; a trial only if it clears)

**Written 2026-09-28, before any Kronos forecast has been computed on project data.** Background and sources: `research/kronos-research-2026-09-28.md`. This fixes the model, data, features, targets, statistics and gate so the measurement cannot be shaped by its result. It runs at the user's direction ("let's go with Kronos", 2026-09-28); the independent reviewer reads this draft before code is written.

**What it is not.** Not a strategy, not a backtest, not a trial. No order path, no config, no gate changes. The Varsity checklist stays retired (§75); the evidence gate stays at zero automatic entries (§70).

## 1. Hypothesis

A K-line foundation model pre-trained on other markets, used zero-shot on NIFTY 100 five-minute bars, produces a forecast whose cross-sectional rank predicts the signed return over the next 15, 30 or 60 minutes by more than the round trip costs. The 119 trials so far measured hand-coded functions of the same bars at ≈ 0 R before friction (§69); this is a different function class on the same information, and the expected answer, from §69 and the TSFM literature, is **no**.

## 2. Model, fixed

- **Kronos-small** with **Kronos-Tokenizer-base**, zero-shot, no fine-tuning of either.
- Pinned to Hugging Face revisions whose commit dates are **before 2025-09-01**, chosen as the *latest* such revision of each; the hashes and dates go in the results file. **If no revision of either predates 2025-09-01, the selection window moves to start after the earliest revision's date, and if that leaves fewer than 60 sessions before 2026-01-02 the look is void and recorded as such.**
- Code: shiyu-coder/Kronos at a pinned commit, vendored under `backend/research/kronos_vendor/` or installed into a research-only venv from `backend/research/requirements-kronos.txt`. Nothing in `backend/requirements.txt` changes. `tests/test_research_splits.py::test_no_live_module_imports_research` continues to hold.
- Inference settings: `max_context=512`, `T=1.0`, `top_p=0.9`, `top_k=0`, `pred_len=12`. `sample_count` is **3**, unless stage 0 shows a full run at 3 would exceed 36 hours of wall clock on the Mac, in which case it is **1**; the choice is made on timing alone, before any forecast is compared with a return, and recorded.
- Seeds fixed (`random`, `numpy`, `torch`, value 123, the repo's own test seed) at the start of every stock-session so a run is reproducible.

## 3. Data, fixed

- **Bars:** Kite 5-minute cache (`kite_history.load(symbol, "5m")`), the same bars every phase-2 test used. Input columns open, high, low, close, volume; `amount` derived as `predict()` derives it (volume × mean price). Only **closed** bars enter the lookback (a bar with start time `t − 5 min` or earlier at decision time `t`), the §42 rule.
- **Universe:** point-in-time NIFTY 100 membership (`backend/research/nifty100_membership.py`, `set_asof` per session) intersected with the cache. A session counts only if ≥ 20 stocks have a full 512-bar lookback and the targets below.
- **Selection sample:** sessions from **2025-09-01** to **2025-12-31**, minus the last **5** sessions before `splits.HELD_OUT_START` (2026-01-02) as embargo. About 80 sessions. **The 2026 window is not read.** Halves are the first and second half of the session list.
- **Held-out for confirmation:** not spent by this look. If the gate clears, confirmation runs on sessions that accrue after `splits.UNSEEN_AFTER` (2026-09-20) once ≥ 40 exist, or on the 2026 window if the user chooses to spend it. Stated now so the choice is not made after seeing the selection result.
- **Adjustment consistency:** stage 0 records `kite_history.fetch_runs()`. The sample must come from bars adjusted in a single fetch run; if it does not, the sessions spanning a step are dropped and listed.

## 4. Decision times, fixed

Six per session, at the close of the 5-minute bar ending **09:45, 10:30, 11:15, 12:00, 12:45, 13:30** IST. The last leaves the 60-minute target inside the session with 60 minutes to spare before the 15:08 square-off the checklist used. No decision time after 13:30, so the "two in three entries after 14:00" structure that sank §72 cannot arise.

## 5. Features, fixed (from the forecast at time t, nothing later)

Let `c₀` be the last closed bar's close and `ĉ_k` the forecast close `k` bars ahead (mean over samples, as `predict()` returns).

1. `f15 = (ĉ₃ − c₀) / c₀` in bp
2. `f30 = (ĉ₆ − c₀) / c₀` in bp
3. `f60 = (ĉ₁₂ − c₀) / c₀` in bp

Each feature is tested **only against its matched horizon**: three tests, one family. No other feature, transformation, ensemble or threshold is read.

**Control:** `m60 = (c₀ − c₋₁₂) / c₋₁₂`, the last 60 minutes' return, computed from the same lookback. It is not a candidate; it is the momentum any model can echo, and each feature's **partial IC given m60** is reported next to its raw IC. A feature whose partial IC does not also clear the gate is a momentum echo and does not pass.

## 6. Targets, fixed

Signed return in bp from the **open of the bar after t** (entry at the next bar, never the decision bar) to the **close of the bar 3 / 6 / 12 bars later**, for f15 / f30 / f60 respectively. Long-short symmetric: no side is favoured, so the negative intraday drift (reviewer brief) cancels in a cross-sectional rank and is reported separately for the top and bottom quintiles.

## 7. Measurement, fixed

Per feature × matched horizon, exactly as `research/step2_feature_ic.py` and `prereg-orderbook.md`:

- **Rank IC** across the stock-times of a session (Spearman between feature and target), then mean, standard error and t **across sessions**. Never pooled over stock-times.
- **Partial rank IC** given m60, the same way.
- **Quintile spread:** per session, mean target of the top feature quintile minus the bottom quintile, in bp; mean and t across sessions. Also each quintile's own mean, so a long-only or short-only reading is visible.
- Percentage of sessions with IC > 0; both halves separately.
- **Power line:** with the session count obtained, the smallest IC and the smallest spread detectable at t = 2, so a null reads "no effect larger than X".
- Multiple comparisons: Benjamini–Hochberg at q = 0.10 across the family of **3** (the three raw quintile-spread tests). The partial-IC-given-m60 check in §8 is **outside that family**: it is a validity condition on a feature that has already cleared, not a fourth search shot, so it neither enlarges the family nor gets a BH-adjusted threshold of its own (amendment 1).

## 8. Gate for a trial, fixed now

> A feature earns a pre-registered trial only if, on the selection sample, its quintile spread **exceeds 33.26 bp (two legs at the 16.63 bp round trip) with t > 2 across ≥ 60 sessions**, is **positive in both halves**, survives **BH at q = 0.10 across the 3 tests**, and its **partial IC given m60 is also positive with t > 2**. A single-side reading (one quintile alone clearing 16.63 bp with t > 2) is reported but does not by itself earn a trial; it earns a note in the results file.

If a feature clears, the trial is pre-registered separately in the existing search harness (`research/strategy_search.py` conventions: 16.63 bp cost, next-bar fills, both halves, DSR at the trial count then standing), and confirmed once on the confirmation sample named in §3 before anything reaches even the review queue.

**If nothing clears:** the finding is that a bar-trained foundation model, zero-shot, does not rank NIFTY 100 intraday moves past cost, and with §69 this closes the "nonlinear ML on price bars" line. Research look L38, no trial spent.

## 9. Stage 0 — checks before any IC is computed, in this order, each a halt if it fails

1. **Install matches upstream.** The Kronos repo's own regression test (`tests/test_kronos_regression.py`, MSE 0.008979 / 0.003741 at context 512 / 256, pred_len 30, seed 123) passes on the Mac against the pinned revisions. Establishes that our inference path is the authors'.
2. **Revision dates** recorded; the §2 rule applied.
3. **Lookahead proof.** For 20 random stock-times, the forecast computed from bars ≤ t is bit-identical to the forecast computed from the same lookback with all later bars present in the source table. The `predict()` path takes only the lookback rows, so this should pass trivially; it is run because #199 exists.
4. **Timing** on 200 forecasts; `sample_count` decided by the §2 rule.
5. **Adjustment run check** (§3).
6. **Coverage:** sessions and stock-times available per half; halt if either half has < 30 sessions.

Only after all six are written into the results file does the IC pass run, **once**.

## 10. One run

One run of the IC pass. A re-run is allowed only for a crash before any statistic was printed, or a declared bug with both runs recorded. No parameter of §2–§8 changes after the first number is seen.

## 11. Trial accounting

Research look **L38**. Trials remain **119**. If the gate clears, the trial that follows has its own pre-registration and its own number.

## 12. What needs the user's decision (per the reviewer's limits)

- **A heavy dependency** (torch, ~800 MB, and the Kronos package) in a research-only environment. The user's 2026-09-28 instruction is taken as that decision for research use; nothing enters the live path.
- **Spending the 2026 held-out window** for confirmation, if the gate clears. Not decided here.
- **Compute on the Mac** for a night or a weekend, while the engine keeps running; the run must not compete with the engine for Kite (it reads the cache only).

## Amendments

1. **2026-09-28, before any code, per reviewer Entry 19.** §7 now states that the partial-IC-given-m60 condition is a validity check on an already-cleared feature and sits outside the BH family of three, rather than leaving that implicit. No threshold, feature, target or window changed.
