# Pre-registration — step 1, random-entry null test

**Committed before the test was written or run.** Supersedes amendment 5's
"compare 31.9% against resolved trades" line and report §4's expected result.

## What this is for

A harness check, **not** a strategy. If the backtester has a bias — an exit
rule that resolves one barrier preferentially, a fill convention that leaks
edge, a sizing path that distorts R — then every result produced by it is
suspect, including the verdict. This measures the harness by giving it
entries that cannot possibly contain information.

## What is deliberately *not* the pass rule

**Whether the real strategy's 28.41% resolved-target rate sits inside the null
distribution is a finding about the strategy, not a check on the harness.** It
is reported in the results section, not the pass section.

**31.9% is the wrong benchmark for a resolved-only rate**, and the reference
figure is 31.26% rather than 31.9% in any case (the per-trade average of
1/(1+RR) over the real trades' actual target/stop ratios, median 2.238).

The reason is timeout asymmetry: with a 15:15 square-off, the nearer barrier
(the 1R stop) resolves faster in expectation, so trades heading for the far
target are disproportionately still open when the timeout fires and are
removed from the resolved set. Under a driftless null the resolved-only target
rate therefore sits **below** 1/(1+RR). The size of that gap is a property of
the bar path and the session clock, which is exactly what a simulation
measures and a formula does not.

**The simulated null distribution is the benchmark.** The 1/(1+RR) figure is
plotted as a reference line only.

## The null strategy

Entries carry no information by construction: the signal is drawn from a
random number generator and ignores every bar it is shown. Everything else is
matched to the real strategy, so the only difference between the two runs is
the presence of a signal.

Matched from the replicated Test A trade list (201 trades, 495 sessions):

| Property | Real value to match |
| --- | --- |
| Trades per session | 0.406 |
| Long / short mix | 120 / 81 = 59.7% long |
| Entry hour profile | 09:44, 10:84, 11:35, 12:21, 13:10, 14:7 |
| Stop distance | bootstrapped, median 42.4 bp |
| Target/stop ratio | bootstrapped, median 2.238 |
| Size factor | bootstrapped from implied values |

Stop distance, target ratio and size factor are bootstrapped as **joint
triples** from real trades rather than sampled independently, so correlations
between them are preserved.

**The null is run through the real harness** — `backtester.run_backtest()`
with the null function injected into `STRATEGY_FUNCTIONS` — not through a
re-implementation of bracket logic. A re-implementation would test the
re-implementation. The whole point is to exercise the same bar-walking, exit
precedence, fill convention, sizing and timeout code the verdict used.

## Universe, period, cost model

- 100 NIFTY 100 symbols, 495 sessions, 2024-09-20 → 2026-09-18, 5-minute Kite
  cache, same `allowed_by_day` scanner picks as Test A.
- Confidence gate off (`min_confidence_to_trade: 0`, `scorecard=[]`) — a
  research-run override only; the live default is untouched.
- **Pass-rule run: `costs.ZERO_COSTS` and zero slippage.**
- **Reported again with `config.COSTS` and normal slippage.**

## Pass / fail

**Primary (harness validation), on the zero-cost run:**

> The **seed-mean gross expectancy must lie within ±0.05R of zero.**

A slightly **negative** value is expected and is not a failure. Two
conventions in the harness are deliberately conservative:

- **stop-first on the same bar** — when a bar's range spans both barriers, the
  stop is taken, because a backtest cannot know which came first intrabar;
- **gap-through at the open** — a gap past a barrier fills at the open, not at
  the barrier price.

Both cost the null a little, and both are correct choices for a backtest that
should not flatter itself.

**Fail:** seed-mean gross expectancy outside ±0.05R. A *positive* mean outside
that band is the more alarming direction — it would mean the harness
manufactures edge from nothing, and every result in this project would need
re-examination before any further hypothesis is run.

**Seeds:** ≥200. Report the full distribution (mean, sd, min, max, and the
2.5/97.5 percentiles), not a point estimate.

## Results to report (findings, not pass conditions)

1. Where the real strategy's **28.41%** resolved-only target rate falls in the
   null's distribution of the same statistic, as a percentile.
2. Where the real strategy's **gross expectancy of −0.1021R** falls in the
   null's zero-cost distribution, as a percentile.
3. The null's resolved-only target rate against the 31.26% reference line, to
   quantify the timeout asymmetry described above.
4. Realised R in rupees and stop distance in bp for the null, so it can be
   compared with the real run's ₹101.2 median and 42.4 bp median.

## Trial counting

**Not a strategy trial.** No strategy is selected and nothing is ranked; this
measures the instrument. Recorded in `trials.md` under *research looks*.

The Test A replication that produced the matching distributions is likewise
**not** a trial — identical configuration to an already-counted run,
re-executed only to recover its trade list. Recorded under *replications*.

## Known limitations, stated in advance

- Entries are random **in time**, but still constrained by the harness's own
  gates (one entry per symbol per session, max open positions, the scanner's
  `allowed_by_day` picks). The null therefore tests the harness *as used*,
  not an unconstrained bracket simulation. That is the intended scope.
- Matching the hour profile matches *when* trades open, not the market
  conditions that made the real strategy fire then. The null is not a claim
  about what the strategy would have done differently.
- A pass bounds bias at roughly ±0.05R. An edge smaller than that could still
  be hidden or manufactured by the harness and would not be detected.
