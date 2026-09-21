# Phase 2 — closing report

**2026-09-21.** Written as reviewer Entry 12 directs: what was tested, what
was found, the trial count, and what remains unspent. **No new hypotheses are
proposed here.**

Supersedes `report-2026-09-21.md` as the current status document.

---

## 1. The conclusion

**Phase 2 tested nine things and found no tradable edge. The one real effect
it found is worth between 0.13× and 0.49× its own transaction cost.**

The binding constraint was never the entry signal. It is that **a round trip
costs 16.60 bp in cash intraday against a 42 bp stop**, and that the intraday
session itself carries a **negative drift** — measured at −6.42 bp on a
point-in-time index series, −6.73 bp on universe A's own window, and
independently at −0.0947R for random long entries through the backtester.

**Nothing here is a recommendation to trade.**

---

## 2. What was tested, and what was found

| # | Test | Result |
| --- | --- | --- |
| 1b | Lookahead proof, nine features | **PASS** — bit-identical on truncated series |
| 1 | Random-entry null, 200 seeds × 2 cost modes | **PASS, marginal** — −0.0495R vs ±0.05R |
| §A | Null diagnostic — what causes the harness bias | **Stated cause refuted.** Stop-first 0.00%, gap-through 6.8%; it is intraday drift on a long-heavy book |
| §B | Friction decomposition | **0.398R, not 0.254R** — the old figure was charges only |
| 2 | Per-feature scanner IC, ten tests | 3 survive BH + Bonferroni; **`trend`, the heaviest weight, returns t = −0.18** |
| 2-A/B/C | Are the three one factor? | **Yes.** Partial ICs drop `from_high` to 1.05 and `from_low` to 1.90 → **one qualifier** |
| 3c | Overnight vs intraday | **Mechanism holds.** Volatile names earn overnight, lose it intraday |
| §D.1 | Index-level split, survivorship-free | Split holds (+12.01 / −6.42); the **"40% survivorship" claim was withdrawn** as confounded |
| L30 | Like-for-like index fix | Overnight gap **23%, not 40%**; intraday gap **3%** |
| Univ B | Replication on 113 unseen stocks | **PASS** — `atr_pct` retains 0.85×; overnight spread 1.02× |
| **3a** | **Opening-range breakout — TRIAL 35** | **FAIL** — net −12.09 bp, t = −2.71 |
| **3b** | **Intraday momentum — stage 1** | **WITHDRAWN, no trial spent** — −1.60 bp and +0.70 bp |
| 3d | Post-earnings drift | **Skipped** — no free earnings-date source |

---

## 3. The one real effect, and what it is worth

High-volatility stocks earn their return **overnight** and give part of it
back **intraday**. It is monotone across quintiles, replicates on 113 stocks
no test had seen, and is stronger in recent years.

**It is not tradable.** All ratios below use the corrected **two-leg** hurdle
(Entry 12 §1) — a spread is two positions, each paying its own round trip:

| | Spread | Hurdle | Ratio |
| --- | --- | --- | --- |
| `atr_pct` quintile, universe A | +8.11 bp | 33.20 bp | **0.24×** |
| `atr_pct` top-5/bottom-5, universe A | +16.30 bp | 33.20 bp | **0.49×** |
| `atr_pct` quintile, universe B | +5.97 bp | 45.20 bp | **0.13×** |
| Overnight spread, universe B | +14.15 bp | 78.10 bp | **0.18×** |

**The correction matters.** These were previously reported at 0.49×, 0.98×,
0.26× and 0.36×. **The "0.98× — within 0.3 bp of break-even" line was the
single most encouraging number this project produced, and it was wrong by a
factor of two.** No conclusion reverses — every one was already a failure —
but the best result here is materially worse than it was reported as.

**The overnight route is closed at this capital.** Harvesting it needs a
daily **delivery** round trip: 12.01 bp of index-level return against
33.05 bp of cost = **0.36×**. Holding continuously to avoid that is simply
being long the index. **Futures are unreachable** — NIFTY notional
₹15.19 lakh, smallest liquid stock future ₹4.14 lakh, on verified lot sizes.

---

## 4. Trial count

**35 strategy trials. Phase 2 spent exactly one: 3a.**

**32 research looks** (L1–L32), logged individually in `trials.md` so the
step-2 BH family size is auditable from that file alone.

**3b cost no trial.** The two-stage split — a cheap measurement gating an
expensive backtest — was proposed before any 3b number existed and withdrew
the hypothesis in seconds. Had it run as a single trial, the count would be
36 and the answer identical.

The count is also **conservative by up to 4**: four swing configurations were
re-run and double-counted, left uncorrected because an overstated count makes
the Deflated Sharpe stricter.

---

## 5. What remains unspent

**The 2026 held-out window has never been looked at**, for any hypothesis, at
any point in phase 2.

It was deliberately preserved three times:

1. Not spent on `atr_pct`, because §C already showed it cannot clear cost, so
   confirmation would change no decision.
2. Not spent on 3c, for the same reason.
3. Not spent on 3a or 3b, because both failed and **a FAIL earns no held-out
   look**.

**Universe B was used instead** wherever a confirmation sample was needed —
113 stocks no test had seen, at no cost to the held-out window.

**It remains the most valuable evidence this project has**, and it is
uncontaminated.

---

## 6. What went wrong, and was recorded

Listed because the corrections are part of the result.

| What | Consequence |
| --- | --- |
| §D4 data-quality gate coded as a report, not a halt | Its judgement was made after seeing the ICs |
| Step-1b lookahead test never committed | A step was accepted on evidence nobody could re-run |
| `from_low`'s sign coded backwards | Relabelled, not re-run; the scanner's signal is **backwards** |
| History window changed 4y → 8y unnoticed | Surfaced that **`from_high` does not replicate** (t = +3.33 → +1.73) |
| (b2) filter tested the wrong string | Printed "0 of 0" as if it were a finding |
| Friction reported as charges only | 0.254R → **0.398R** (#53) |
| Verdict benchmark was a formula, not a measurement | 31.9% → **25.0%**; "worse than a coin flip" → **indistinguishable from random** |
| Spread compared against one round trip | **0.98× → 0.49×**, and four other ratios halved |
| Reviewer Entry 5 stranded on an unmerged branch | A shared channel put on a branch then walked away from |
| A frontend regression shipped in #52 | A live Kite session displayed as disconnected |
| The journal funnel labelled the checklist entry threshold as "cleared the confidence gate" | Two different gates conflated. The 09-18 "9 passes, 0 orders" gap was **1 setup re-evaluated 9 times**, blocked by the confidence gate at 53/60 and fully logged — the gap was in the analysis, not the engine |

---

## 7. Standing caveats

- **Survivorship bias**: today's index membership applied to history, worst
  on volatility sorts — which is where the one real effect lives.
- **`costs.py` rates are unverified** against the broker's current tariff.
  Every bp hurdle in this document rests on them.
- **Futures charges and SPAN margins were never verified** and are recorded
  as unverified rather than estimated.
- **Selection sample only**, everywhere.
- **The Kite cache starts 2024-09-20**, so 3a and 3b ran on ~316 sessions.
- **No harness-bias figure applies to 3a or 3b** — both are self-contained.

---

## 8. State of the system

**Paper mode. No real-money order has ever been placed** — all 16 journal
trade legs are `mode='paper'`, verified twice.

The live engine is unchanged by any of this work: `trader_brain.py`,
`risk_manager.py`, `scanner.py`, `costs.py` and `confidence.py` are
untouched, and an AST test proves no live module imports `research`.

Eight paper round trips stand at **−₹168.71 net, −₹5.26 gross** — charges are
**97% of the loss**, the same arithmetic as everything above.
