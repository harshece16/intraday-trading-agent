# Results — 3g, the "Smart Money" multi-timeframe setup (trial 117)

**2026-09-25. FAIL. Net −0.299R per trade over 256 trades, t = −5.56, negative in
both halves, Deflated Sharpe 0.0.** Pre-registered in `prereg-3g-smc-mtf.md`
(commit `48c36ed`), code and tests committed in `5989ba0`, both before any run.
One run of each stage. **The held-out window was not looked at. Nothing is
deployed.** It ran at the user's direction without external reviewer review.

Selection sample: 316 sessions, 2024-09-25 → 2026-01-01. Halves 158 / 158
(2024-09-25 → 2025-05-16, 2025-05-19 → 2026-01-01).

## Stage 0 — feasibility, no forward price read: PASS

| | |
| --- | --- |
| Raw entry signals, before the 3-position cap | **267** (gate ≥ 100: pass) |
| Side | 138 short, 129 long |
| Sweep bar | 210 on A of D (09:15–13:15), 57 on B of D−1 |
| Entry hour, by the cemented 15m bar's END | 09: 8 · 10: 14 · 11: 15 · 12: 8 · 13: 41 · **14: 181** |
| Stocks / sessions with a signal | 89 / 170 |
| Stop distance | median **46.3 bp**, quartiles 33.9–63.9 bp, min 12.8 bp (gate median ≥ 16.63 bp: pass) |
| Implied friction at the median stop | **0.36R** |

**Two in three entries come in the 14:00 hour.** That is structural, not a
parameter: most sweeps are the 09:15–13:15 bar, which is not known until 13:15,
and the 1H confirmation and 15m entry follow it. On a 24-hour market the setup
has all night to play out. Here it has until the 15:08 square-off.

## Stage 1 — trial 117: FAIL

| | Trades | Net R | t | Win % |
| --- | --- | --- | --- | --- |
| First half | 129 | **−0.363** | −5.00 | 27.9 |
| Second half | 127 | **−0.233** | −2.94 | 40.9 |
| **Pooled** | **256** | **−0.299** | **−5.56** | 34.4 |

| Rule | Needed | Got | |
| --- | --- | --- | --- |
| Net R > 0, t > 2 | > 0, > 2 | −0.299, −5.56 | fail |
| Both halves positive | both > 0 | −0.363, −0.233 | fail |
| Deflated Sharpe at 117 trials | ≥ 0.95 | 0.0 | fail |
| Trades | ≥ 100 | 256 | pass |

## Why, on the search diagnostics' columns

| | Trades | **Pre-friction R** | Gross R | Net R | Friction R | MFE median | Reach ≥ 1R | Reach ≥ 2R |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **3g SMC MTF** | 256 | **+0.070** | −0.063 | −0.299 | 0.369 | 0.51 | 25.8% | 4.7% |

| Exit | Trades | Net R |
| --- | --- | --- |
| Square-off at 15:08 | **170 (66%)** | −0.107 |
| Stop | 64 | −1.354 |
| 2R target | 22 | +1.285 |

- **The trade rarely gets to finish.** Two thirds are closed by the square-off,
  and only 4.7% ever reach the 2R target. That follows from the late entries in
  stage 0.
- **Friction is 0.369R**, five times the pre-friction figure. Even taken at face
  value, +0.070R covers **0.19×** of its own cost.
- **Longs and shorts lose the same**: −0.301R and −0.297R.
- The backtester labels entries by the 5m bar's **start**, so its hour split
  (13: 96, 14: 111) is shifted five minutes from stage 0's; they are the same
  trades.

## The falsification branch

The pre-registration's second branch reads "pre-friction R > +0.05R but net ≤ 0
→ a real but untradable effect". **+0.070R clears +0.05R, but that branch should
have required significance, and it does not have it.** Using the net-R spread
(0.86R) as the estimate, its standard error over 256 trades is about 0.054R, so
**t ≈ 1.3**. It is not distinguishable from zero, the same as the 76 search
configurations (−0.054 to +0.044). The wording gap is recorded here rather than
used to claim an effect.

**No variant is proposed**: not 1:3, not a different bias rule, not a different
4H anchor, not a longer hold. The pre-registration ruled those out in advance.

## Accounting

- Stage 0: not a trial, not a look.
- Stage 1: **trial 117**. Count now **117**.
- Held-out window: **unspent**.
- `backend/data/backtest_trials.json` still holds 34 entries, although
  `trials.md` says it is the source of truth; the search's trials 41–116 were not
  logged to it either. `trials.md` is the complete record. This predates 3g and
  is noted, not changed.

## Conclusion

**The setup fails on NSE cash intraday for the same reason every price-only rule
has failed here: the entries carry no measurable information, and the round
trip is the loss.** It adds one structural reason of its own: a 4-hour sweep
cannot be confirmed before 13:15, so most trades are closed by the square-off
before the setup's own target can be reached. The source's claims were made for
24-hour FX, gold and crypto markets, and nothing here tests them there.
