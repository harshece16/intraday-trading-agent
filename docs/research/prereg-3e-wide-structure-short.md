# Pre-registration — 3e, wide-structure intraday, short side only

**Written and committed before any 3e code exists.** Requested by the user on
2026-09-23 as "1 + 2" of the whole-flow review: a wider trade structure (1)
with a short lean (2).

**NOT RUN.** Two gates, both required, the same two-step as 3a and 3b:
**reviewer review of this pre-registration**, then **the user's explicit
go-ahead to run it**. Writing it is not the go-ahead.

Trial numbering assumes PR #76 (#74, trials 36 and 37) is merged. If it is
not, the numbers below shift down by two and nothing else changes.

---

## Why this, and why now

Phase 2's binding constraint was never the entry signal. It was the trade's
**shape**: a 16.60 bp round trip against a **median 42.4 bp stop** is
**0.40R of friction on every trade** (`friction_decomposition.json`). The
checklist's entries were indistinguishable from random at that shape, but
whether they have an edge **at a wider shape** has never been measured.

Friction in R is `16.60 / stop_bp`. At a 100 bp stop it is **0.166R**, and
**0.40R → 0.17R is the only lever in this project that changes the cost
arithmetic by more than 2×**.

The short lean comes from §D.1: the intraday session drifts **−6.42 bp**
(index-level, 2005–2025) and **−6.73 bp** on universe A's window, and random
long entries lose **−0.0947R** through the backtester. **Stated plainly: at a
100 bp stop that drift is worth only about 0.06R per trade.** It is a
tailwind, not an edge, and it is not the reason this might work. It is the
reason the long side is dropped rather than tested as a second arm.

---

## What was deliberately NOT included

Every exclusion here is a variant that will **not** be run later, whatever
3e's result:

- **A long arm.** It would be a second trial, and the drift argument says it
  starts behind.
- **60-minute bars.** One horizon only. 15m keeps enough bars per session for
  the pattern, volume and higher-timeframe rules to mean something.
- **A separate "trend day" filter.** The checklist already requires Dow-trend
  and always-in agreement, on the entry timeframe and on a 3× higher one.
  That is the trend requirement; nothing is added on top.
- **First-hour momentum as the signal.** That is 3b's signal, withdrawn at
  stage 1. 3b's pre-registration forbids re-registering it with a different
  window.
- **A reward-to-risk gate or a fixed target.** See §Stage 2, "Exit".
- **The scanner's picks.** Step 2 measured its heaviest feature (`trend`) at
  t = −0.18. Its `atr_pct` preference points the wrong way (t = −6.13). Every
  tradable NIFTY 100 name is eligible instead, which also buys power.

---

## Stage 1 — trade-count feasibility (research look L35, no trial)

**This counts entries. It computes no exit, no return and no P&L.** The
script must not contain exit logic at stage 1; the reviewer should check that.

### Construction

| | |
| --- | --- |
| Universe | **A** (NIFTY 100), `scanner.tradability_exclusion()` applied per session |
| Data | Kite 5-min cache, already downloaded. No Kite calls. |
| Bars | **15-min, aggregated from 5-min**, aligned to 09:15 (09:15, 09:30, …, 15:15). A 15-min bar needs all three 5-min bars, or it is dropped. |
| Period | **Selection only**: sessions before `splits.HELD_OUT_START` (2026-01-02). **Held-out candles are dropped before any other code sees them**, as in `fix74_cost_pct.py`. |
| Signal | `trader_brain_signal(entry_mode="checklist")` on the 15-min bars, **short side only** (`bear` checklist pass). |
| Entry window | Signal bar closes at or after **09:45** (the first 15-min bar after the opening half hour) and no later than **14:30** |
| Position rules | Entries per stock per session **1**. Concurrent positions **3**, slots reopen on exit. Chronological order, ties broken by symbol, alphabetical. |

**Stage 1 needs the position cap, so it needs to know when positions
close.** It uses only the **scheduled** exit at 15:10: every position is
assumed to hold its slot until 15:10. That is an upper bound on slot usage,
so it gives a **lower bound** on the trade count. It needs no prices after
entry.

### Stage-1 gate, fixed before running

The sd of R is **assumed at 1.0R**, fixed now. It is narrower than Test A's
1.41R because stage 2 has no target, so R runs from −1R (plus friction) to
wherever the close is. Stage 2 reports the realised sd.

> **Required trades** = `splits.required_trades(1.0, 0.15)` = **349**. That
> is enough to detect a **0.15R** net edge at two-sided 5% with 80% power.
> 0.15R is 15 bp per trade at a 100 bp stop, **about one round trip**, the
> smallest edge worth trading.
>
> **Stage 1 clears only if the lower-bound trade count is at least 349.**
> Below that, 3e is reported as **untestable at this frequency on the
> selection sample** (`splits.trades_per_session_bar`), no trial is spent,
> and it is **not** re-registered with looser rules to raise the count.

---

## Stage 2 — the strategy (trial 38, only if stage 1 clears)

Fixed now so stage 1's count cannot shape it.

| Parameter | Value | Why |
| --- | --- | --- |
| Signal, universe, bars, window, position rules | **Exactly as stage 1** | |
| Direction | **Short only** | §Why |
| **Entry fill** | **Open of the bar after the signal bar**, less modelled slippage | Never the signal bar's own close (3a amendment 1 b). `run_backtest()` enters at the signal close, so 3e uses a **self-contained harness**, as 3a did (3a amendment 2). |
| **Stop** | **max(the checklist's structural stop, entry × 1.0100)**: the pattern's own extreme, widened to at least **1.00%** above entry if it is closer | The whole hypothesis. 1.00% puts friction at 0.166R. One value only. |
| **Exit** | **Stop, or the 15:10 bar close**. No target, no trailing stop, no signal exit. | A 1.5R target on a 100 bp stop needs a ~190 bp intraday move, which a fixed cap would rarely allow. Holding to the close lets the realised R distribution show whether the wider shape carries an edge, without choosing a target. |
| Stop fills | **Identical to 3a amendment 1 (c)**: intrabar touch → stop price plus slippage (a short buys back); bar opening beyond the stop → that bar's open. The entry bar may stop. | |
| Sizing | **Fixed ₹33,000 notional** (the live notional cap on ₹1 lakh) | bp is primary, R is derived |
| Costs | `config.COSTS` via `costs.leg_cost()` + `apply_slippage()`: the full **16.60 bp** round trip | Unverified against the broker's current tariff. That caveat is carried. |
| Confidence gate | **Off** (`min_confidence_to_trade = 0`, `scorecard = []`), as in Test A | The gate measures the scorecard, not the setup |

`friction_R`, computed as `16.60 / median stop_bp`, is reported **before**
any statistic. If the realised median stop is not within 100–130 bp, the
harness is wrong and the run is stopped as a crash, before any return is read.

### What is reported

1. Trades, sessions and trades per session. `friction_R`.
2. **Net R per trade**: mean, sd, t, 95% CI. **This is the primary statistic.**
3. Net bp per trade, and gross (pre-charges, post-slippage) R per trade, so
   friction is visible as the difference.
4. Exit shares, stop vs 15:10, with the mean R of each.
5. **Both halves**, `splits.halves()` of the selection sessions, each with (2).
6. **MDE at t = 2** from the realised sd, reported before the mean is read.

### Stage-2 pass rule

> **PASS only if** net R per trade over the selection sample is **> 0 with
> t > 2**, **and** net R per trade is **positive in both halves**.
>
> **Anything else is a FAIL.** A positive gross with a negative net is a
> FAIL. A positive mean with t < 2 is a FAIL, not "promising".
>
> **Untestable branch:** if the realised trade count is under 349, or the
> realised MDE at t = 2 exceeds 0.15R, the result is reported as
> **untestable**, not as a null and not as a pass.

### The falsification branch, stated in advance

> **If friction falls to about 0.17R as designed but gross R stays near zero,
> as it was at 5 minutes (+0.04R pre-friction, CI ±0.19R), then the wider
> shape only slows the bleed. It does not create an edge, and that would be
> a worse fact than a plain FAIL**: it would mean the checklist has no edge
> at *either* horizon. That closes intraday checklist trading at this capital
> as a line of work, and the write-up will say so rather than propose a third
> horizon.

---

## Held-out — only on a PASS, and only with the user's say-so

The 2026 held-out window (176 sessions from 2026-01-02; see `splits.py` for
why it is not pristine) has **not been looked at for any hypothesis**.
**A FAIL or an untestable result earns no held-out look.**

On a stage-2 PASS, the held-out run happens **only after the user explicitly
approves spending it**. The rule is fixed now:

> **Held-out confirms only if** net R per trade is **> 0 with one-sided
> t > 1.65**, with the identical configuration: no parameter touched between
> selection and held-out.

---

## What 3e cannot establish

- **One variant is not a search.** No second stop width, horizon, side,
  filter or exit, whatever the result.
- **Selection sample only** until the held-out step above.
- **Survivorship bias**: today's NIFTY 100 applied to history.
- **The Kite cache starts 2024-09-20**, so selection is about 318 sessions.
- **Slippage is modelled at 3 bp per leg, never measured.** No real-money
  order has ever been placed. A PASS here says nothing about fills at size.
- **No harness-bias figure transfers.** The harness is self-contained, so the
  −0.05R measured on `run_backtest()` does not apply.

## Code boundary

All 3e code lives in `backend/research/`. **No live module changes**:
`trader_brain.py` is called, not edited. The 15-min aggregation, the short
filter, the stop widening and the exit all live in the research script, and
the AST fence test (`tests/test_research_splits.py::test_no_live_module_imports_research`) stands. The
aggregation and the fill rules each get a unit test before the run.

---

## Stop

**Stopped here for review.** No 3e code exists. Nothing runs without the
reviewer's review of this file **and** the user's explicit go-ahead.
