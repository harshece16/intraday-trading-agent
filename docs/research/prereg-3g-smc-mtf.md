# Pre-registration — 3g: the "Smart Money" multi-timeframe setup (daily bias → 4H sweep → 1H order block → 15m entry)

**Written and committed before any code for this test exists.** The user shared a
Threads post (smartmoneythread00, 2026-09-23) on 2026-09-25 and asked for research
around implementing it. **It runs at the user's direction without external reviewer
review**, as the strategy search did, and that is recorded here.

**The source is a sales funnel, not evidence.** It ends "Join telegram channel get
perfect setup and analysis". It shows one hand-picked BTC/USD example and no track
record. Its author says it works best on XAU/USD, GBP/USD, AUD/USD, BTC/USD and
USD/CAD — 24-hour markets. It has never claimed anything about NSE cash equities.

## The prior, stated before any code

**The expected outcome is FAIL.** The 76-configuration search and its diagnostics
(`results-search-diagnostics.md`) found pre-friction R between −0.054 and +0.044
for every price-and-volume entry tested on NIFTY 100 intraday bars, and concluded
that "a next round has to change the **information**, not the rule". This setup
uses only price. It is tested anyway because it is a structurally different rule
(multi-timeframe, sweep-and-reclaim with a structural stop) that the search did
not contain, the user asked for it specifically, and **one configuration costs one
trial**. If it fails, that is one more confirmation of the search's conclusion, and
no variant is proposed.

## The rules, made mechanical

The post's rules are pictures and phrases. Every choice below is fixed now, before
any bar is read, and is an operationalisation of the post, not a quotation.

All higher-timeframe bars are built from the 5-minute cache, and **a bar is used
only once it is complete**.

### 1 — Daily bias for session D ("Set the bias")

From the full-session bars of D−1 and D−2:

- **Bullish** if close(D−1) > high(D−2).
- **Bearish** if close(D−1) < low(D−2).
- Otherwise **consolidation, no bias, no trade** on D.

The post's BTC example is exactly this rule ("Price closed below the lows → next
day bias is bearish"). Its "reversal" pictures also close beyond the prior day's
extreme, so they are covered by the same two lines.

### 2 — 4-hour liquidity sweep ("Identify the liquidity sweep")

NSE 4H bars follow the charting convention of anchoring to the session open:
**A = 09:15–13:15** and **B = 13:15–15:30**. The series is continuous across days,
so a day's A bar follows the previous day's B bar.

- Bullish bias → a **low sweep**: a completed 4H bar k with low(k) < low(k−1) and
  close(k) > low(k−1).
- Bearish bias → a **high sweep**: high(k) > high(k−1) and close(k) < high(k−1).

For session D, the sweep bar must be **B of D−1** (known at D's open) or **A of
D** (known at 13:15). Nothing older.

The sweep bar's extreme, **H\*** (the high for a bearish setup, the low for a
bullish one), is the **invalidation level**. Any later trade through it cancels
the setup.

### 3 — 1-hour order block ("High probability OB formation")

1H bars start at 09:15 on the hour-quarter (09:15, 10:15 … 15:15; the last one
is 15:15–15:30). Bearish case; the bullish case is the mirror.

- **Peak bar:** the 1H bar inside the sweep bar that contains H\*. If several
  do, the first.
- **OB candle:** the last 1H bar with close > open at or before the peak bar,
  searching back at most 6 bars.
- **OB zone:** [open(OB), high(OB)].
- **Confirmation:** the first completed 1H bar after the peak bar that **closes
  below open(OB)** — the post's "last buying candle ke open price ke niche close
  hona chahiye". Confirmation must come before any trade above H\*.
- **Premium line:** the midpoint between H\* and the lowest low from the peak bar
  through the confirmation bar.

### 4 — 15-minute entry model ("sweep + cemented candle")

Bearish case, as in §3; the bullish case is the exact mirror (low for high,
discount for premium, BUY for SHORT). **Both sides are traded**, as the post does.

On completed 15m bars of session D that end **after** the confirmation bar ends:

- **Sweep candle s:** high(s) > high(s−1), high(s) ≥ open(OB) (it trades into
  the zone), high(s) ≥ the premium line, and high(s) ≤ H\*.
- **Cemented candle c:** the first later 15m bar that **closes below low(s)**.
  If a bar makes a higher high first, and it still satisfies the sweep-candle
  conditions, it becomes the new s.
- **Entry:** SHORT at close(c). The bar c must end **no later than 14:30**.
- **Stop:** high(s). **Target:** 2R — the post's stated minimum is "1:2 or 1:3",
  and 2R is the less demanding of the two.
- Any trade above H\* before entry cancels the setup for the day.
- **One setup per stock per day.**

## Harness — identical to the strategy search except where stated

| | |
| --- | --- |
| Universe | NIFTY 100, every tradable name. The post's "trade only 3–4 pairs" has no NSE analogue. |
| Bars | The native **5-minute** cache. The 15m entry fires on the 5m bar whose end equals the 15m bar's end, so the fill is the 15m close; stops, targets and the square-off are checked on 5m bars. |
| Fills | `backtester.run_backtest()`: signal-bar-close fills, stop/target on high/low, gap-through at the open, stop first when a bar spans both. |
| Stop and target | Passed as a per-trade plan (the checklist's existing mechanism). No stop floor — none is in the post. |
| Costs | `config.COSTS`, a 16.63 bp round trip |
| Sizing | `RiskManager`: 1% risk, 33% notional cap, ₹1 lakh, at most 3 open positions |
| Square-off | 15:08. **Nothing is held overnight.** |

**Why intraday only.** NSE cash equity cannot be shorted overnight, and a long-only
delivery version faces a ~33 bp round trip. The project is an intraday engine.
This makes the setup **stricter than the post**: in a 24-hour market a sweep can
be traded for as long as it takes; here a sweep on A of D leaves roughly 75
minutes to 14:30.

## Stage 0 — feasibility. Reads no forward price. Not a look, not a trial

Run the detector over the **selection sample only** and report:

1. the number of **raw entry signals** (before the 3-position cap),
2. by side, by sweep bar (B of D−1 vs A of D), and by entry hour,
3. the **stop distance in bp** (median, quartiles), and the implied friction per
   trade in R = 16.63 bp ÷ stop bp.

**Gate:** if raw signals **< 100**, stop. Stage 1 cannot reach the ≥ 100-trade
rule, no trial is spent, and 3g is closed at stage 0.

**Also stop if** the median stop is under 16.63 bp. Friction would then exceed
1R per median trade, and no pre-friction edge the search ever measured
(|R| ≤ 0.054) comes near covering it.

## Stage 1 — the backtest. **Trial 117**

Run once on the **selection sample only** (before 2026-01-02).

**PASS only if all four hold**, the strategy search's selection rules unchanged:

1. net R per trade **> 0 with t > 2**,
2. net R per trade **positive in both halves** (`splits.halves()`),
3. **Deflated Sharpe ≥ 0.95** at **n_trials = 117**,
4. **at least 100 trades**.

**Report as well, deciding nothing:** gross and pre-friction R, friction in R, exit
mix, side split, and MFE/MAE in R — the diagnostics' columns, so 3g sits on the
same table as the 11 search configurations.

**Held-out (trial 118), only on a selection PASS:** run once on 2026-01-02 →
2026-09-18 with every rule unchanged. **CONFIRMS** only if net R > 0 with one-sided
t > 1.65 and at least 50 trades. The user authorised spending this window and
paper deployment of a confirmed survivor on 2026-09-24. **A confirmed survivor goes
to paper mode only; real money stays the user's decision.**

## Falsification, stated in advance

- **Pre-friction R within ±0.05R** → the setup's entries carry no information, the
  same as the 76. Reported as such. **No variant is proposed** — not 1:3, not a
  different bias rule, not a different 4H anchor. Those would be the curve-fitting
  this file exists to prevent.
- **Pre-friction R > +0.05R but net ≤ 0** → a real but untradable effect. Reported
  as a ratio of its cost, as phase 2 did for `atr_pct`.
- **Positive net that fails only the DSR or halves rule** → not a pass.

## Accounting

- Stage 0 is not a trial and not a look: it reads no price after a signal.
- Stage 1 is **trial 117**, whatever the result. One run. A re-run only for a crash
  before any statistic is printed.
- The held-out run, if taken, is **trial 118**, and the window is marked spent.
- A lookahead test (events on a truncated series equal the full series' events up
  to the truncation) and unit tests on synthetic bars for each rule are committed
  **with the code, before stage 0 runs**.
