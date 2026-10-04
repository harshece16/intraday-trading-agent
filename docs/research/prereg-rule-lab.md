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

## Amendment 1 — 2026-10-05, about 00:25 IST, before any code and before any data beyond §0's dates

**Why.** The owner asked, through a video he sent (Craig Percoco, "Give Me 25 Minutes, I'll Give You 10,000 hours of Trading Knowledge", 2026-08-16), to "add these kind of logic in the app". Its testable logic is one rule with a risk-based exit, a way of reporting results in units of risk, and a ladder from replay to paper to live. The video's claims about money made are marketing and are not evidence for anything here. Nothing had been computed when this amendment was written.

**1. Two more rules, the moving-average pullback with an R-based exit.** The family becomes **20 rules × 1 variant = 20 tests**; every "18" in §4 to §6 reads 20, and stage 0's halt (§5) becomes "fewer than 10 rules powered".

| ID | Rule | Side | Signal on the finished bar `T[i]` |
| --- | --- | --- | --- |
| R19 | Pullback to a rising EMA20 | Long | i ≥ 1; `EMA(i) > EMA(i − 3)`; `close(i − 1) > EMA(i − 1)` (price was above the average); `low(i) ≤ EMA(i) < close(i)` (the bar touches it and closes back above) |
| R20 | Pullback to a falling EMA20 | Short | the mirror: `EMA(i) < EMA(i − 3)`; `close(i − 1) < EMA(i − 1)`; `high(i) ≥ EMA(i) > close(i)` |

- **Entry** as every rule: the next bar's open `E`, at or before 14:30.
- **Stop** beyond the signal candle: `S = low(i)` for R19, `high(i)` for R20. Risk a share `r = |E − S|`. **No trade** if the entry opens at or past the stop, or if `r / E` is below the round trip of `costs.round_trip_pct` at the notional (16.60 bp), the engine's own floor that a stop must cover the cost (rule CST-01).
- **Target** `E ± 3r` (3R).
- **Exit**, walking the finished bars from the entry bar on: the first bar whose low reaches the stop (long; high for the short) exits at the stop, or at the bar's open if it opened past it (a gap); the first bar whose high reaches the target exits at the target, or the open if it opened past it. **When one bar reaches both, the stop is taken.** With neither by 15:05, the exit is the open of the 15:05 bar, like every rule. This is the engine's paper stop handling (`_check_stop_take`: the first price at or past the stop fills, then slippage) read on bars: inside a bar the order of its high and low is unknown, so the conservative order is assumed. Slippage and charges apply to both legs as in §2.
- **One open trade per rule per stock**, as §2. The tradability guards apply.
- **Result**: net bp as every rule, which is the unit of the family test (§3, §4), and also **net R** = net ₹ / (r × qty).

**2. What the page reports for every rule**, in addition to §3, as information (none of it is a test):
- **Expectancy in R**, net of costs, for R19 and R20 (the other rules have no stop, so no R).
- **Win rate beside the break-even win rate** for the rule's realised payoff: `1 / (1 + b)`, with `b` = the mean net win ÷ the mean net loss (both after costs). For R19 and R20 the planned payoff is 3R, which costs make smaller; the realised figure is used.
- **Maximum consecutive losses**, in time order (session, then entry time).
- **Historical against forward, side by side**: once L55 has run, its mean net bp, win rate and trade count for each rule (the discovery and confirmation halves together), next to the forward lab's, and the **decay**: forward mean − historical mean, in bp. Before L55 runs, the column says so.

**3. The promotion ladder, in the owner's words: replay → paper → live, expecting returns to shrink at each step.** §7 stands, and its steps read as this ladder:
1. **Replay** = L55, the historical screen (discovery, then confirmation), or the forward screen (lab sessions 1–40).
2. **Paper** = the forward confirmation on 40 untouched lab sessions.
3. **Live, small first.** After the owner's explicit yes, and only through the existing live gate (§7.4), a confirmed rule would trade at **a quarter of the engine's normal risk, 0.25% of capital a trade instead of 1%**, for at least 20 sessions and 50 trades, before any increase; an increase is a second owner decision. The decay from each step to the next (replay → paper, paper → live) is reported in bp at each step. Nothing about this is automatic, and none of it is built now: the lab places no orders.

## Amendment 2 — 2026-10-05, about 00:35 IST, before any code ran and before any data beyond §0's dates

**Why.** The owner also asked to "scan every profitable strategy from YouTube, mix it and apply". A separate research agent is cataloguing testable rules from popular trading videos. So the lab must take new rules and combinations later without code churn, and its error control must cover every rule ever added.

1. **Rules are data.** `rule_lab.REGISTRY` holds each rule as an id, a name, a side, a family, a signal function of the finished bar (or a declarative spec of the same features, `rule_lab.spec_signal`), an exit kind (30-minute horizon or the 3R exit of amendment 1) and its **cohort**, the amendment that added it. The twenty rules above are cohort 1. A combination is a rule that fires when all its parts fire on the same bar (`rule_lab.combination`).
2. **A rule or combination is added only by a dated amendment**, committed before its first forward session and before any of its returns is read, stating its exact definition. Each amendment is a new cohort.
3. **One error budget for the lab's whole life.** The family-wise error rate over every rule and combination ever added is held at 5% by spending it by cohort: cohort *k*'s looks are tested at **α_k = 5% × 2^−k** (cohort 1: 2.5%; cohort 2: 1.25%; ...). This replaces §4's and §6's 5% for the forward stages. At each forward look, **every rule ever registered enters the bootstrap's maximum**, and only the cohort under test can pass. A later cohort's forward screen runs on its own first 40 lab sessions after it was added.
4. The family size reported at each look is the number of rules and combinations registered by then, with each cohort's size.

## Amendment 3 — 2026-10-05, about 00:45 IST, before any code ran and before any return or any 2026 bar was read

**Why.** The owner, 2026-10-05: *"if we are testing micro rules or permutation combinations of rules and backtest on 2025 and 2026 data we should come at a certain set of rules that are profitable — very basic rules or a combination of 20 or just 1 — use CPU computing power — all P&Cs coming from YouTube and apply and backtest."* This turns L55 from a screen of single rules into a **combinatorial search**, and it **authorises one use of the 2026 held-out window** for the search's survivors. It replaces §5 (the discovery and confirmation halves of 2024–25). §1–§4, §6 and §7 stand, with amendments 1 and 2.

**1. Conditions.** Every registered rule's signal is a boolean **entry condition** with a side: today the 20 of cohort 1 (10 long, 10 short). The YouTube catalog's rules join as conditions only through a dated amendment (amendment 2), written before the search's run; the count below is then recomputed by stage 0 and the reviewer sees it.

**2. Exits, a common set of two.** Every combination is tried with both:
- **H30**: the next bar's open to the open 30 minutes later, or the 15:05 bar (§2);
- **R3**: a stop beyond the signal bar and a 3R target (amendment 1, including the cost floor on the stop and "stop first" inside a bar).
Same ₹50,000 notional, `config.COSTS` (MIS charges and 0.03% slippage a leg), one open trade per combination per stock.

**3. The search space, bounded and fixed now.** All conditions combined with AND, same side only:
- **all singles, all pairs, all triples** of conditions, × the 2 exits;
- **greedy forward selection** for larger sets: for each side and each exit, start from each of the **5 triples** with the highest clustered *t* (among those with at least 200 trades); at each step add the one same-side condition that raises *t* the most while keeping at least 200 trades; stop when no condition raises it or the set has **20 conditions** (or every same-side condition). Every set the greedy step evaluates is counted.
- With cohort 1 (10 conditions a side): 20 + 90 + 240 = 350 sets × 2 exits = **700 enumerated combinations**, plus at most 5 × 2 sides × 2 exits × 28 = **560 greedy evaluations**: a family of **at most 1,260**. The exact number of distinct combinations evaluated is counted by the code and is the family size of every statistic below.

**4. Sample.** **Discovery: every NIFTY 100 stock in the cache, every session 2024-09-20 to 2025-12-31** (the first two sessions only as history; 316 evaluable sessions). No split into halves for selection; the sample is split internally only for CSCV.

**5. Statistics over the whole family, net of costs.** Per combination: trades, sessions with a trade, mean net bp a trade and its session-clustered *t* (§3), win rate, both halves of the sample.
- **Primary: the Romano–Wolf stepdown** (§4) over **every combination evaluated**, stationary bootstrap of sessions, mean block 5, B = 10,000, seed 20261005, one-sided, **FWER 5%**.
- **Probability of backtest overfitting** (CSCV): the 316 sessions in **16 consecutive blocks**, all 12,870 ways to choose 8 as in-sample; in each, the combination with the best in-sample mean net bp (among those with at least 50 in-sample trades) and its relative rank out of sample; PBO = the share of splits where it falls in the bottom half.
- **Deflated Sharpe ratio** of the best combination's per-session net series at **n_trials = the family size** (`evaluation.deflated_sharpe_ratio`).
- **Survivors**: combinations rejected by the Romano–Wolf stepdown, with **at least 200 trades and 40 sessions**, positive mean and **both halves positive**; and only if **PBO < 0.5** (otherwise the search as a whole is judged overfit and there are none). If more than **5** qualify, the 5 with the highest *t* that are not nested in a higher-ranked survivor (a set containing a higher survivor's conditions, same side and exit, is skipped). **At most 5 survivors.**

**6. The 2026 confirmation, once.** The owner's quote above is his authorisation, dated 2026-10-05; it is recorded in `trials.md`'s held-out log when this is committed. **The 2026 window is not pristine**: the project's first phase ran its backtests on 2026 bars (README "Backtest results", 2026-06-29 to 2026-09-11, and the 2026 swing backtests), and the momentum family spent its held-out look on 2026 (`trials.md`). A 2026 pass is therefore weaker evidence than "held-out" usually means, and will be reported so.
- **What is read before the pass:** nothing from 2026 except a count of rows (`COUNT(*)` by symbol, for the runtime estimate). No 2026 price, volume or signal.
- **When:** only after the discovery run and an **independent review of the whole design and the discovery result**, in a single pass, on **2026-01-01 to the newest cached session**.
- **What runs:** only the pre-declared survivors (at most 5), their conditions and exits exactly as found. Pass for each: at least 100 trades, mean net bp > 0, both halves of the 2026 sample positive, and rejected by the Romano–Wolf stepdown over **the survivors** at 5%.
- **Then:** a survivor that passes is a **historical candidate** (§5's role, now filled by the search): it is registered in the forward lab as a new cohort by a dated amendment, and must still pass the forward confirmation on 40 untouched lab sessions (§6), the owner's yes and the live gate (§7, amendment 1's ladder). Nothing goes live without the owner.

**7. Compute.** Each condition is computed once per stock-bar into a boolean array, by the forward lab's own signal functions (so the definitions cannot drift); a combination is the bitwise AND of its conditions' arrays. Each exit's outcome is computed once per (stock-bar, exit); a combination's trades are its signal bars with the one-open-trade rule applied. Stage 0 estimates the runtime and memory from a timed sample. The discovery run is on the owner's PC, or on the Mac outside 08:30–15:45 IST.

**8. Stage 0, before any return.** Data checks as §5 (now over the whole discovery sample), the 2026 row count only, the condition counts (how often each fires; no outcome), the family size, the number of combinations with at least 200 signal bars, and the timing estimate. **Halt** if any 2026 bar is read, if fewer than 90% of stock-sessions have at least 70 bars, or if fewer than 50 combinations have at least 200 signals.

**9. Bookkeeping.** L55 stays a research look; it spends no trial (the count stays 202). A survivor that becomes a proposal spends one trial (§7.3). The 2026 window's use is entered in the held-out exposure log when the pass runs.

## Amendment 4 — 2026-10-05, about 01:10 IST: the two strategy catalogs join as cohort 2, before any of their returns was read

**Why.** Both catalogs the owner asked for are in: popular YouTube trading videos (40 entries, 34 testable, with 8 recommended combinations CMB-1 to CMB-8) and named practitioners, GitHub, Reddit, Quantpedia, TradingView and SSRN (49 entries). They are kept as working files of this session (`yt-strategies/catalog.json`, `strategies-other/catalog.json`); every registered condition names its catalog entry in `rule_lab.REGISTRY[id]["sources"]`.

**What had been read when this was written.** The conditions below were coded (`backend/rule_lab_catalog.py`) before this amendment, and while timing the code their **signal counts** were printed for one stock (RELIANCE, 2024-09-24 to 2025-12-31). No exit price, return, or 2026 bar was read. The definitions are the code and docstrings at this amendment's commit; nothing in them changes after it.

**1. Cohort 2: 87 intraday conditions** (43 long, 44 short), each an entry signal on a finished 5-minute bar, with the same trade as every rule (§2) and the common exits (§3 below). 15- and 60-minute conditions use bars resampled from 09:15 and fire on the 5-minute bar that completes the higher bar.

| IDs | Condition (catalog entry) |
| --- | --- |
| Y01L/S | 5-EMA alert candle broken (YT-MA-01; subasish_pani_5ema). The long is the 5-minute mirror, not the taught 15-minute one |
| Y02L/S | EMA9/15 trend, EMA9 slope ≥ 0.10% over 3 bars, touch of EMA9, trigger candle (YT-MA-02) |
| Y03L/S | EMA9 crosses EMA21, the catalog's control (YT-MA-03) |
| Y04L/S | EMA200 side, EMA20 beyond EMA50, EMA20 touched in 3 bars, Stoch RSI reset from 20/80 (YT-MA-04 = CMB-1) |
| Y05L/S | VWAP hold-and-bounce / rejection after 6 closes on one side, volume ≥ its 6-bar mean (YT-VW-01) |
| Y06L/S | From 10:45: VWAP side, close through a Fibonacci pivot, Stoch RSI %K beyond %D (YT-VW-02) |
| Y07L/S | First close beyond the 09:15–10:10 range (YT-OR-02; unger_first_hour_breakout) |
| Y08L/S | Failed break of the 15-minute range, faded, first time today (YT-OR-03, fade part) |
| Y09L/S | First-hour sweep: a later hourly bar beyond the first hour's extreme, closing back inside (YT-OR-04) |
| Y11S | Three up days, gap ≥ 0.5%, the first red bar of the morning broken (YT-GP-02) |
| Y12AL/S, Y12BL/S | Narrow CPR (≤ 0.25%): bounce off its edge; close through max(R1, PDH) / min(S1, PDL) (YT-PV-01; B is CMB-6 without its VWAP term) |
| Y13L/S | Close through a classic pivot level (YT-PV-02) |
| Y14L/S | From 09:40: ADX(14) on 15-minute bars > 20, Supertrend(10,3) on side, close through a Fibonacci pivot (YT-PV-03) |
| Y15L/S | Supertrend(12,3) flip beyond DEMA200 (YT-ST-01). **Expected void**: DEMA200 needs about 400 bars and the 5-day input holds about 375 |
| Y16L/S | EMA200 side, Stoch RSI back from an extreme within 4 bars, ≥ 2 of 3 Supertrends on side (YT-ST-02) |
| Y17L/S | MACD cross, Supertrend(10,3) flipped within 3 bars, price within 0.2% of VWAP (YT-ST-03) |
| Y18L/S | Close beyond Bollinger(30,2), RSI(13) < 25 / > 75, not in a squeeze (YT-OS-04) |
| Y19L/S | MACD cross beyond zero, EMA200 side (YT-OS-05) |
| Y20L/S | Heikin-Ashi reversal after a doji and a stochastic extreme (YT-OS-06) |
| Y21L/S | Inside bar then a close beyond the mother bar, in an EMA10 trend (YT-PA-01) |
| Y22L/S | False break of a 20-bar extreme: engulfing or sweep (YT-PA-02) |
| Y23L/S | Retest of the previous session's point of control with a wick (YT-PA-04); the POC is approximated from 5-minute bars |
| Y24L/S | 15-minute inside candle, then a 15-minute close beyond it (YT-PA-05) |
| Y26L/S | VWAP side, close through max(OR high, PDH, next Fibonacci pivot), RVOL ≥ 1.5, 09:30–14:30 (CMB-2) |
| Y27L/S | Close beyond Bollinger(20,2) with RSI(14) < 30 / > 70, then a close past that bar's other end (CMB-7) |
| O01L/S | Williams volatility breakout, open ± 0.6 × yesterday's range, first close beyond (williams_volatility_breakout; one k fixed) |
| O02L/S | Williams oops: open beyond yesterday's low/high by ≥ 0.3 × its range, first close back inside, by 11:00 (prior-day range in place of ADR10) |
| O03L/S | Turtle soup on 5-minute bars (raschke_turtle_soup) |
| O04L/S | Raschke 80-20 (raschke_80_20) |
| O05L/S | Raschke anti on 15-minute bars (raschke_anti) |
| O06L/S | Narrow CPR trend day with today's CPR beyond yesterday's, first close beyond the opening range (cpr_narrow_trend_day; the fixed 0.25% width in place of its 60-day percentile) |
| O07L, O07S | GFR long and RDP short (cpr_untested_short_index_patterns) |
| O08L/S | Supertrend(10,3) flip on 15-minute bars (supertrend_10_3) |
| O09L/S | TTM squeeze release on 15-minute bars (ttm_squeeze_lazybear) |
| F01–F09 L/S | Filters and building blocks, one copy a side: ATR rising (YT-FL-01), RVOL ≥ 1.5, by 11:00, 15-minute EMA20/50 trend, EMA200 side, Supertrend(10,3) flip, ADX(15m) > 20, engulfing or hammer (shooting star), VWAP side. Alone, each is a (silly) rule of its own and is counted as one |

**2. Causality.** Every series is computed bar by bar from the past; a higher-timeframe bar is read only once its last 5-minute bar has finished. `test_every_condition_is_causal` checks each condition by deleting the bars after the signal bar.

**3. Exits: the common set only.** Every condition trades with H30 and R3 (§2, amendment 1), never its catalog's own stop, target or signal exit (opposite cross, next pivot, gap fill, middle band, 2R or 1.5R targets, end of day). A bounded exit set could be added by a later amendment, as its own cohort; this keeps the family's size the product of conditions and two exits.

**4. Combinations.** The catalogs' recommended combinations are in the family: CMB-1 is Y04, CMB-2 is Y26, CMB-7 is Y27; CMB-4 (R19 or R20 with F08), CMB-5 (F06 with F05 and F07), CMB-6 (Y12B with F09) and CMB-8 (a trigger with F04) are pairs and triples of the enumeration; CMB-3 has four parts (R13 with F02, F03 and F04, and the short mirror) and is **added explicitly**, both exits.

**5. Excluded, with the project's earlier result, and not re-run:** plain opening-range breakout and Zarattini's stocks-in-play ORB (trial 35, −12.09 bp a session; R13/R14 stay as cohort 1 already registered them); market and gamma intraday momentum (L31, L32, L51); gap fill (L49, and R17/R18); SMC/ICT liquidity sweeps (trial 117, −0.299R); the Varsity EMA checklist (trials 1–44); Raschke's Holy Grail (the PB family, 24 of 24 fail); morning/evening star (control R4 of trials 128–202); the 9:20 straddle, averaging-in and "never lose" entries (not cash entry rules). **Deferred, not built**: the cross-sectional top-gainer first pullback (YT-MA-06; needs every stock at once), and the four rules that need a swing-structure engine with a confirmation delay (YT-MA-07, YT-OS-02, YT-OS-03, YT-PA-03); a later amendment may add them as their own cohort. **Not a rule here**: the end-of-day reversal (entries stop at 14:30; a measurement for another look), the noise-area and half-hour periodicity rules (index or cost-bound).

**6. Shorts in the shadow lab.** The forward lab trades short rules **whatever `config.SCANNER["allow_shorts"]` says**: shadow trades are not orders. A stock the scanner marks long-only (a fixed price band, where a short cannot be covered) still skips its shorts. This replaces §2's sentence about `allow_shorts`. The historical search has no long-only information and skips no short (§5).

**7. Cohort 3, reserved: daily and multi-day rules.** The catalogs' daily rules (Connors RSI(2), cumulative RSI, double 7s, IBS and Turnaround Tuesday on NIFTYBEES; Rayner Teo's 50-day pullback; Crabel NR7 × ORB; Kullamägi's episodic pivot and breakout; Minervini's trend template; Darvas, pocket pivots, Stockbee bursts, Turtles, Carver EWMAC, KAMA, floor/ceiling regime, MACD, RS55, polarity flips, VCP and EMA-band swings; and the monthly high-volume premium and tug-of-war) need a daily-bar harness with delivery costs and the bhavcopy panel. They are **not built or run here**. They will be pre-registered as cohort 3 in their own amendment, with **α₃ = 0.625%** of the lab's budget reserved for them, and still nothing dated 2026 before the one confirmation pass.

**8. L55's family now.** 107 conditions (53 long, 54 short): all singles, pairs and triples of same-side conditions × 2 exits = **102,296**, plus CMB-3's 4 combinations, plus at most **14,450** greedy evaluations: **at most 116,750 combinations**, the exact number counted by the code. The Romano–Wolf stepdown streams over replicates and combinations, so its memory does not grow with the family. Cohort 1's twenty alone (amendment 3) would have been at most 1,260; the wider search pays for its width with a higher bar.

**9. The forward lab** runs cohort 2 from the same first session as cohort 1. Cohort 2's screen is after its own 40th lab session, at **α₂ = 1.25%**, with all 107 rules in the bootstrap's maximum (amendment 2).

*Correction to amendment 4 §8, 2026-10-05 01:20 IST, before any return: an arithmetic slip. Singles, pairs and triples × 2 exits are 102,292; with CMB-3's 4 the enumeration is 102,296, and the family is at most **116,746** (stage 0 counted it). No definition changes.*
