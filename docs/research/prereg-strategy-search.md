# Pre-registration — #43 and a bounded strategy search, with one held-out confirmation

**Written and committed before any code in this search runs.** The user asked on
2026-09-24 for #43 plus a search, including replacing the Varsity checklist, for
something that is profitable on the long data, and gave two explicit authorisations:

1. **Spend the 2026 held-out window** on the final confirmation.
2. **Deploy any survivor in paper mode only.**

**It runs at the user's direction without external reviewer review**, and that is
recorded here. **The user was told before the search began** that a search over many
configurations will find a positive backtest by luck, and that the protection
against that is the trial count and the held-out look below, not the backtest number.

---

## What protects the answer

- **Every configuration is a counted trial**: trials **41 onward**, at the count of record (40).
- **The selection sample only** is searched: before 2026-01-02 (318 sessions). The held-out window (2026-01-02 → 2026-09-18, 176 sessions) is **not loaded into any search run**.
- **The Deflated Sharpe Ratio** is evaluated at the **total** trial count (40 + this search), using `evaluation.deflated_sharpe_ratio()`.
- **The held-out window is looked at once, for at most one configuration, and only if something passes selection.** If nothing passes, it stays unspent.

## The grid, fixed now (76 configurations)

### A — #43, the Varsity checklist on 5-minute bars (2 configurations)

The stop floor becomes `max(min_stop_atr × ATR, k × round-trip cost)`, which widens the stop rather than rejecting the setup, with **k ∈ {2, 3}**. Everything else is the live checklist, as in trial 39. It is implemented as a trader_brain parameter `min_stop_cost_widen`, default `None`, so live behaviour is unchanged.

### B — the Varsity checklist on slower bars (2 configurations)

Live checklist parameters on **15-minute** and **60-minute** bars, both sides.

### C — three non-checklist entry families (72 configurations)

The indicators are computed on the configuration's timeframe bars, using the same formulas as `indicators.py`. VWAP is session VWAP.

| Family | Long entry (short is the mirror) |
| --- | --- |
| **PB**, trend pullback | EMA20 > EMA50, close > VWAP, the previous bar's low ≤ EMA20, this bar closes above EMA20, RSI14 between 40 and 70 |
| **MR**, range mean reversion | ADX14 < 20, RSI14 ≤ 30 and close < VWAP − 1 ATR. **Signal exit** when the close crosses back through VWAP |
| **VB**, VWAP breakout on volume | The close crosses above VWAP from below, volume ≥ 2× the mean of the previous 20 bars, EMA20 > EMA50 |

**Grid:** family {PB, MR, VB} × timeframe {5m, 15m, 60m} × stop {1.5, 3.0} × ATR(timeframe) × exit {target 2R, hold to square-off} × side {both, short-only} = **72**.

- Short-only is included because of the measured −6.4 bp intraday drift. Long-only is not, for the same reason.
- "Hold to square-off" means a target 100 ATR away, so exits are the stop, a signal exit or the square-off.

### Common to every configuration

| | |
| --- | --- |
| Universe | NIFTY 100, **every tradable name** (no scanner picks). Scanner features measured zero or negative IC in step 2. |
| Entries | Families C: bar time from 09:45 to 14:30. **Checklist configurations A and B keep the live checklist's own window, 09:30 to 14:30** (they are "live parameters"). **1 entry per stock per day.** At most 3 open positions, as live. |
| Harness | `backtester.run_backtest()`: same-bar-close fills (pinned by #13's test), stop/target on the bar's high and low, gap-through at the open. Confidence gate off. |
| Costs | `config.COSTS`, a **16.63 bp** round trip (charges + 3 bp per leg of slippage) |
| Sizing | `RiskManager`: 1% risk, 33% notional cap, ₹1 lakh |
| Square-off | `config.SQUARE_OFF_TIME` = **15:08** |
| **5m bars** | The cache's native, start-labelled bars, as in trials 36–40. The square-off fires on the bar starting 15:10 and fills at its close. |
| **15m and 60m bars** | Aggregated from the 5m cache and **labelled by their END time**, so a signal on a bar acts at that bar's close. Each session's last bar is a partial bar ending at **15:10**, so the square-off fires at its close. **A start-labelled 15m or 60m bar never reaches 15:08, and would have carried positions overnight.** That is why this is specified. |

## Pass rules, fixed now

**Selection (every configuration):** PASS only if **all four** hold on the selection sample:
1. net R per trade **> 0 with t > 2**,
2. net R per trade **positive in both halves** (`splits.halves()`),
3. **Deflated Sharpe ≥ 0.95** at n_trials = **116** (40 + 76),
4. **at least 100 trades**.

**Held-out (at most one configuration):** of the selection passes, the one with the **highest Deflated Sharpe** is run once on the held-out window, with every parameter unchanged. It **CONFIRMS** only if net R per trade **> 0 with one-sided t > 1.65** and **at least 50 trades**.

**If nothing passes selection:**
- no held-out look is taken,
- nothing is deployed,
- the result is reported as **no edge found in this search space, at this cost**.

**If the held-out run fails:** nothing is deployed, and the window is recorded as spent.

**If it confirms:** the configuration is implemented in the live engine in **paper mode**, with the live checklist kept as a switchable alternative. Real money is a separate decision for the user after live paper evidence.

## Falsification, stated in advance

**The expected outcome is no pass.** Every entry signal tested here since phase 2 has been indistinguishable from random or worse (Test A; trials 35–40). If the 76 configurations show the spread of results that 76 no-edge strategies would, meaning a best net R around 0 and Deflated Sharpe well under 0.95, then **entry rules of this kind do not carry an edge at this cost in this universe**. The write-up will say so, and will not propose a wider grid.

## Accounting

- **Trials 41–116**, one per configuration, whatever the result.
- One run of the grid. Results are saved after each configuration; if the run is interrupted, it **resumes by skipping configurations already finished**, never re-running one. Any resume is disclosed. A configuration is re-run only if it crashed before printing a statistic.
- The held-out run, if taken, is **trial 117**, and the window is marked spent in `splits.py` and `trials.md`.
- The results file reports **all 76**, not only the best.
