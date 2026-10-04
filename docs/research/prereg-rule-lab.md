# Pre-registration — the single-rule paper lab (research look L54, forward) and its historical screen (research look L55)

**Written 2026-10-05 from 00:10 IST and committed before any rule-lab code exists, before any rule below has been computed on any data, and before any return of any rule has been read.** It fixes the rules, the trade, the costs, the statistics and the promotion path of two looks that share one rule library:

- **L54, the forward lab.** Every rule is run as a shadow paper book on the day's list, on each finished 5-minute bar of every session after deploy. No orders.
- **L55, the historical screen.** The same rules, through the same code, replayed on the cached Kite 5-minute bars of the NIFTY 100 **before 2026-01-01 only**, split by date into a discovery half and a confirmation half. This document, its code and its stage 0 are committed first; the screen itself runs **once, after an independent review**, and not before.

**Who asked.** The owner, 2026-10-04/05: "instead of applying all rules to one trade we should have rules apply like 1 rule per stock and predict based on that rule — candlestick pattern recognition or simple volume logic, if it's trending then buy, if people are selling then sell — apply small rules and trade in paper and then try to identify which of these mini rules work and apply them in live with most probability." And, as a follow-up: "use our GPU computing power to run it instantly, or research how to do this in the best way." Rule RES-33 (no new intraday look after 2026-09-30) allows a look the owner asked for; this is one, and the trial ledger records it as owner-requested.

**What it is not.** Not a strategy, not a trial, not a change to the engine. No order path, gate, position, capital, daily-loss counter, review card or Scorecard row reads or is touched by either look. A rule that passes every stage below is a *proposal* to the owner, nothing more (§7).

## 0. What is already known, and the expectation

These single rules are close relatives of things this project has already measured, and lost on:

| Earlier test | What it measured | Result |
| --- | --- | --- |
| Trials 128–202, control R4 (`results-combo-search.md`) | Every directional candlestick pattern of `candlestick_patterns.detect_patterns`, strength ≥ 2, traded in its direction for 15, 30 and 60 minutes, L40's sample, 5,074 trades each | −16.4 / −16.4 / −17.0 bp net a trade; **about +0.2 bp before costs** |
| Trial 40 (`results-confluence-deep.md`) | The confluence engine (trend, VWAP, momentum and candle triggers scored together), 668 trades | −0.43R net, **worse than random before costs** |
| Trial 35 (3a) | Opening-range breakout on high relative-volume names | FAIL, +1.6 to +3.0 bp gross a session |
| Trials 93–116 (family VB) | VWAP breakout on volume ≥ 2×, three timeframes | 24 of 24 FAIL |
| L49 | Gap, time-of-day relative volume, VWAP distance as rankers of the next 15/30/60 minutes | 0 of 13; best +1.27 bp |
| Test A, trial 39, §51, §69 | The Varsity checklist, which combines most of these conditions | −0.356R a trade, t −3.59 |

The new thing is the owner's design: one rule at a time, each with its own book, so a rule that works is not diluted by the others. The prior evidence says that is unlikely to rescue any of them. **The expectation, stated now: no rule passes the screen, in either look.** A pass would be a surprise and is treated as one: it needs a second, untouched period before anyone acts on it.

Data looked at while writing this, none of it a price, a volume or a return: the list of distinct session dates in `kite_history.db` for one symbol before 2026-01-01 (318 sessions, 2024-09-20 to 2025-12-31), the cache's table of contents (one interval, 5 minutes, 100 symbols), and the code named in §1.

## 1. The rule library, fixed

Eighteen rules. Each is self-contained: a fixed side, a fixed signal, the same entry and exit. There are **no variants** (one horizon, one notional, one threshold each), so **the family is 18 rules × 1 variant = 18 tests**.

**Terms.** For a stock on session *d*, the input is its 5-minute bars, oldest first, each stamped with its start time: today's bars `T[0], T[1], …` (T[0] is the 09:15 bar) and the bars of earlier sessions before them. A rule reads **finished bars only**, through `T[i]`.

| Term | Definition (code it reuses) |
| --- | --- |
| `W(i)` | the last 30 bars of the input up to and including `T[i]` (may reach into earlier sessions) |
| `ATR(i)` | `indicators.atr(W(i), 14)` |
| `PAT(i)` | the names returned by `candlestick_patterns.detect_patterns(W(i), ATR(i))`, the engine's own detector. Its trend conditions (a hammer only after a decline, etc.) apply as written there |
| `VWAP(i)` | `indicators.session_vwap(T[0..i])` |
| `EMA(i)` | the 20-bar EMA of closes, `indicators.ema_series` over the whole input, at `T[i]` |
| `RVOL(i)` | `volume(T[i])` ÷ the mean volume of the bar with the same start time in each of the up to 4 most recent earlier sessions in the input that have one; undefined with fewer than 2 such sessions |
| `PC` | the close of the last bar of the most recent earlier session in the input |
| `GAP` | `T[0].open / PC − 1`; the gap rules use it only when 0.5% ≤ \|GAP\| ≤ 10% (a larger gap is treated as a data or corporate-action event) |
| `OR` | the high and low of `T[0..2]`, `scanner.opening_range` |
| `U(i)` | `close(i) > VWAP(i)` and `close(i) > EMA(i)` and `EMA(i) > EMA(i − 3)` ("trending up"); `D(i)` is the mirror |

| ID | Rule | Side | Signal on the finished bar `T[i]` |
| --- | --- | --- | --- |
| R01 | Bullish engulfing | Long | "Bullish Engulfing" ∈ `PAT(i)` |
| R02 | Bearish engulfing | Short | "Bearish Engulfing" ∈ `PAT(i)` |
| R03 | Hammer | Long | "Hammer" ∈ `PAT(i)` |
| R04 | Shooting star | Short | "Shooting Star" ∈ `PAT(i)` |
| R05 | Bullish marubozu | Long | "Bullish Marubozu" ∈ `PAT(i)` |
| R06 | Bearish marubozu | Short | "Bearish Marubozu" ∈ `PAT(i)` |
| R07 | Inside-bar breakout up | Long | i ≥ 2; `T[i−1]` inside `T[i−2]` (high ≤ and low ≥); `close(i) > high(i−1)` |
| R08 | Inside-bar breakdown | Short | the mirror: `T[i−1]` inside `T[i−2]`; `close(i) < low(i−1)` |
| R09 | Buyers in control | Long | `RVOL(i) ≥ 2` and `close(i) > open(i)` |
| R10 | Sellers in control | Short | `RVOL(i) ≥ 2` and `close(i) < open(i)` |
| R11 | Trend turns up | Long | i ≥ 1; `U(i)` and not `U(i−1)` |
| R12 | Trend turns down | Short | i ≥ 1; `D(i)` and not `D(i−1)` |
| R13 | Opening-range breakout | Long | i ≥ 3; `close(i) > OR high`, and no bar `T[3..i−1]` closed above it |
| R14 | Opening-range breakdown | Short | i ≥ 3; `close(i) < OR low`, and no bar `T[3..i−1]` closed below it |
| R15 | Gap and go, up | Long | i = 0; `GAP ≥ +0.5%`; `close(0) > open(0)` |
| R16 | Gap and go, down | Short | i = 0; `GAP ≤ −0.5%`; `close(0) < open(0)` |
| R17 | Gap up fades | Short | i = 0; `GAP ≥ +0.5%`; `close(0) < open(0)` |
| R18 | Gap down fills | Long | i = 0; `GAP ≤ −0.5%`; `close(0) > open(0)` |

A term that is undefined (too little history) makes the rule silent on that bar.

## 2. The trade, fixed

- **Entry** at the **open of the next bar**, `T[i+1]`, which must start exactly 5 minutes after `T[i]` (a gap in the bars: no trade) and **no later than 14:30**.
- **Exit** at the open of the bar starting **30 minutes (6 bars) after the entry bar**. If that time is 15:05 or later, the exit is the **open of the 15:05 bar**, the last bar that starts before the engine's 15:08 square-off. If the exit bar is missing, the first bar after its time is used; if none exists before the session ends, the trade is **void** (kept, flagged, not scored).
- **No stop, no target.** This keeps the test about the signal: a stop changes the payoff's shape and adds a parameter. It also means a single trade can lose more than an engine trade could. Stated here so nobody reads the lab's numbers as the engine's.
- **One open trade per rule per stock.** A signal is taken only when no trade of that rule in that stock is open at the entry bar's start; re-entering at the open where the previous trade exits is allowed. Rules are independent of one another: two rules can hold the same stock at once.
- **Tradability, as the engine applies it** (`TradingEngine._entry_block_reason`): a short rule skips a stock the scanner marks long-only (a fixed price band), and every short is skipped while `config.SCANNER["allow_shorts"]` is off. The engine's *strategy* gates (market bias, daily loss, open-position and sector caps, the confidence gate) are not applied: they would make one rule's record depend on the others and on the engine.
- **Size**: a fixed notional of **₹50,000** a trade, `qty = floor(50,000 / entry price)`, at least 1. At this size Zerodha's brokerage is below its ₹20 cap, so the round trip is the project's standard **16.60 bp** hurdle.
- **Costs**: `config.COSTS` through `costs.py` — `apply_slippage` on both fills (0.03% a leg, the paper engine's figure) and `leg_cost` on both legs (Zerodha intraday MIS: brokerage, STT on the sell, exchange, SEBI, IPFT, stamp, GST).
- **Return of record**: `net_bp = net ₹ / (qty × entry open) × 10⁴`, net of slippage and charges. Gross (`side × (exit open / entry open − 1) × 10⁴`) is also stored.

The trade is the same in both looks. The historical screen calls the forward lab's own function on each stock-session, so the definitions cannot drift.

## 3. The statistic, fixed

Per rule, over a stage's trades (void trades excluded): number of trades *n*, sessions with a trade *G*, win rate (net > 0), **mean net bp per trade *m***, and its **session-clustered standard error**

  se = √( G/(G−1) · Σ_g ( Σ_{j ∈ g} (x_j − m) )² ) / n,

with *t* = m / se and the 95% interval m ± 1.96 se. Sessions are the clusters because trades on one session share the market's move. *Both halves*: the stage's sessions split in two chronologically (`research/splits.halves`); the mean net bp per trade in each half.

## 4. Testing many rules at once: one method, used at every stage

**Primary method: the Romano–Wolf stepdown on studentised statistics, with a stationary bootstrap of sessions, controlling the family-wise error rate at 5% (one-sided: a rule passes only for a positive mean).**

- Bootstrap: B = 10,000 replicates, seed 20261005. Each replicate draws a sequence of the stage's sessions by the stationary bootstrap (Politis and Romano, 1994) with mean block length **5 sessions** in the historical screen and **3** in the forward stages (40 sessions). A drawn session brings **all** its trades of **every** rule, so the dependence between rules (an engulfing bar is often a high-volume bar) is kept.
- In each replicate, for each rule, t\*ₖ = (m\*ₖ − mₖ) / se\*ₖ (recentred, the same clustered se). A rule with no trade in a replicate drops out of that replicate's maximum.
- Stepdown (Romano and Wolf, 2005, the studentised algorithm): start with every rule in the family; c = the 95th percentile of maxₖ t\*ₖ over the rules still in; every rule with tₖ > c is rejected (passes the test); remove them and repeat until a step rejects nothing.

**Why this one.** White's Reality Check (2000) and Hansen's SPA test (2005) answer "does the best rule beat nothing?", not "which rules work?"; the owner's question is the second. Romano–Wolf answers it rule by rule with the same family-wise guarantee, and because it reads the joint bootstrap distribution it does not over-penalise correlated rules the way Bonferroni or Holm do. Benjamini–Hochberg controls the false discovery rate, which allows some false passes; with a path that ends at the owner's live-money decision, a family-wise bar is the right one. Sullivan, Timmermann and White (1999) applied exactly this bootstrap logic to technical trading rules and found that most of their apparent edge was data snooping. The deflated Sharpe ratio (Bailey and López de Prado, 2014) discounts the single best strategy for the number tried; it is the project's bar for a strategy trial and stays so at the proposal stage (§7), but it does not say which of several rules pass. The probability of backtest overfitting by combinatorially symmetric cross-validation (Bailey, Borwein, López de Prado and Zhu, 2017) is reported for the historical screen as a **diagnostic only** (16 date blocks, all 12,870 splits, the rank of the in-sample best rule out of sample); it decides nothing.

Sources: H. White, "A Reality Check for Data Snooping", *Econometrica* 68(5), 2000; P. R. Hansen, "A Test for Superior Predictive Ability", *Journal of Business & Economic Statistics* 23(4), 2005; J. P. Romano and M. Wolf, "Stepwise Multiple Testing as Formalized Data Snooping", *Econometrica* 73(4), 2005; D. N. Politis and J. P. Romano, "The Stationary Bootstrap", *JASA* 89(428), 1994; R. Sullivan, A. Timmermann and H. White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* 54(5), 1999; D. H. Bailey and M. López de Prado, "The Deflated Sharpe Ratio", *Journal of Portfolio Management* 40(5), 2014; D. H. Bailey, J. Borwein, M. López de Prado and Q. J. Zhu, "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4), 2017; Y. Benjamini and Y. Hochberg, *JRSS B* 57(1), 1995. These references were written from the author's knowledge, not re-fetched tonight; the reviewer may check them.

## 5. L55, the historical screen

- **Data**: the Kite 5-minute cache, `backend/data/kite_history.db`, opened **read-only** (`mode=ro`). The SQL stops at **2026-01-01 00:00 IST** and the loader asserts that the newest bar it holds is dated 2025. `kite_history` is not imported (it opens the file for writing).
- **Universe**: every NIFTY 100 symbol in the cache, every session it has bars. This is today's membership, so the sample has survivorship bias (stocks that left the index are missing); the forward lab trades the day's 25 most-traded stocks, a subset. Both are disclosed, neither corrected.
- **Inputs per stock-session**: that session's bars and up to the 4 previous sessions' bars, the same shape the engine's 5-day fetch holds. Long-only status is not known historically, so no short is skipped; at the 15:08 square-off every bar the rule needs exists in the cache.
- **Discovery half D**: sessions **2024-09-20 to 2025-05-15**. **Confirmation half C**: sessions **2025-05-16 to 2025-12-31**. (158 evaluable sessions each: the first two sessions of the cache only serve as history, because `RVOL` needs two earlier sessions.) The confirmation half's first sessions read the discovery half's last bars as history only; every trade is intraday, so no trade crosses the boundary.
- **Stage 0, before any return** (`rule_lab_screen.py --stage0`): sessions and symbols per half, bars per stock-session (complete = 75), duplicate or out-of-order bars, zero-volume bars, the newest bar's date, and **signal and trade counts per rule per half** (counts need no outcome). It reads no exit price and computes no return. A rule with fewer than **200 trades in D** cannot be powered and is **void**: it leaves the family before the run, and stage 0's record says which. Stage 0 halts the look if any bar of 2026 is read, if fewer than 90% of stock-sessions have at least 70 bars, or if fewer than 9 rules are powered.
- **Pass in D**: n ≥ 200, G ≥ 20, mean > 0, positive in both halves of D, and rejected by the Romano–Wolf stepdown over the powered family at 5%.
- **Pass in C**, for the rules that passed D only: n ≥ 100, mean > 0, positive in both halves of C, and rejected by the Romano–Wolf stepdown over **those rules** at 5%.
- A rule that passes both is a **historical candidate**. It goes straight to the forward confirmation stage (§6), because D and C together already did a screen's job. Nothing else changes for it: it still needs the forward confirmation, the owner and the live gate.
- **One run.** After the independent review, once, on the owner's PC or the Mac outside 08:30–15:45 IST. A re-run only for a crash before any statistic is written. The results file and its ledger row are written whatever the result.

## 6. L54, the forward lab

- **Where it runs.** Inside the engine's tick, after the tick's own work in the open phase, on the candles the tick already fetched for the day's list; inside a `try`/`except` that logs and returns, so an exception in the lab cannot stop or change the tick. It re-reads a stock only when a new 5-minute bar has finished, and stops for the tick when it has used a fixed time budget, leaving the rest for the next tick (its cost is measured and reported in the README). It writes only its own tables (`rule_lab_trades`, `rule_lab_sessions`).
- **What it records.** One row per trade: rule, stock, session, side, the signal bar, the entry bar and price, the exit bar and price, quantity, gross and net bp, net ₹, the feed (Kite or delayed), and status (open, closed, void). A row is written once at entry and once at exit, and a closed row is never changed. A restart re-reads the session's bars and finds the same trades, so a restart neither loses nor duplicates one (each trade is keyed by rule, stock, session and entry bar). A trade whose exit bar had not arrived by the session's last tick (on the delayed feed, the 15:05 bar arrives after the engine stops fetching) is closed from that session's bars when a later session's input holds them: the engine's 5-day fetch includes the earlier sessions. If they have not arrived within 5 sessions, the trade is void.
- **A lab session** is a trading session on which the lab evaluated at least 10 stocks. The lab's first session is the first after deploy.
- **The screen look**: once, after the close of the **40th lab session**, over trades of lab sessions 1–40. Pass: n ≥ 200, G ≥ 20, mean > 0, positive in both halves, and rejected by the Romano–Wolf stepdown over all 18 rules at 5% (a rule with fewer than 200 trades cannot pass but stays in the bootstrap's maximum, which only makes the bar stricter). A passing rule is a **candidate**. A rule that fails is **screen failed**, permanently: there is no second screen.
- **The confirmation look**: for each candidate, once, after its **next 40 lab sessions** (sessions 41–80 for a forward candidate; for a historical candidate, the 40 lab sessions after the historical screen's results are committed). Pass: n ≥ 100, mean > 0, positive in both halves of those 40 sessions, and rejected by the Romano–Wolf stepdown over the candidates being confirmed at that look at 5%. A passing rule is **confirmed**; one that fails is **confirmation failed**, permanently.
- **Before a look** the page shows each rule's running figures, labelled as interim. They are never tested: a rule is judged only at its look, so watching the page does not change the error rate.

## 7. Promotion, in full

1. **Screen** (L54 sessions 1–40, or L55 discovery then confirmation): pass → *candidate*.
2. **Confirmation** on a fresh, untouched forward period of 40 lab sessions: pass → *confirmed*.
3. **Proposal.** A confirmed rule may be **proposed** to the owner in writing, with its record from every stage. The proposal is where a **strategy trial is spent**: one trial per proposed rule, entered in `trials.md` with the next number, and the deflated Sharpe ratio of the rule at the then trial count is reported.
4. **Live.** Only with the **owner's explicit yes**, and then only through the project's existing live gate: its own pre-registered engine change, the confidence gate and Scorecard (the backtest-evidence row must stop failing for the live configuration), the readiness check and RES-27.

**Nothing is ever promoted automatically.** No code reads a rule's status to change what the engine does. The statuses on the page are computed for display.

## 8. Bookkeeping

- L54 and L55 are **research looks**, recorded in `trials.md` when this is committed, as owner-requested under RES-33. **Neither spends a strategy trial**: the trial count stays 202 until a proposal is made (§7.3).
- L55 reads only the selection sample before 2026-01-01; the 2026 held-out window is not opened, and the held-out exposure log gains no row.
- L54's sessions are new data, after `splits.UNSEEN_AFTER`; they have been seen by no test.
- **Amendments** before L54's first session or before L55's run are allowed, dated, with the reason; none after.
