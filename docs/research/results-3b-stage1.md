# 3b stage 1 — results

**Pre-registered:** `prereg-3b-intraday-momentum.md` + amendment 1
(`fef1fd7`, Entry 12) + amendment 2 (`9d8d892`, Entry 13).
**Code:** `e3a5028` — committed **after** both amendments, **before** the run.
**Run:** 2026-09-21, once. Selection dates only; **1,310,103 held-out bars
dropped before any other code could see them**. No Kite calls.

**Trial count: unchanged at 35. No trial was spent.** Research looks
**L31** and **L32**.

---

## Verdict: NEITHER line clears. 3b is WITHDRAWN.

> **Stage 1a (cross-sectional):** quintile top-minus-bottom spread
> **−1.60 bp, t = −0.48**, against a gate of **+33.20 bp**. Not merely short
> of the hurdle — **negative**.
>
> **Stage 1b (time-series, adapted):** **+0.70 bp, t = +0.61**, against a
> gate of **+16.60 bp**.
>
> **Per the pre-registration, 3b is not re-registered with a different signal
> window, holding period or filter.**

**And the staging worked.** The two-stage split proposed before any 3b number
existed withdrew the hypothesis in a **12-second measurement** instead of
spending trial 36 on a backtest. That was its whole purpose.

---

## Sample

| | |
| --- | --- |
| Cached sessions | 318 |
| **Usable sessions** (≥ 20 stocks) | **316** |
| Span | 2024-09-23 → 2026-01-01 |
| Halves split at | **2025-05-16** (fixed before the run) |
| Held-out bars dropped | **1,310,103** |
| Stock-sessions with no prior close (1b only) | 97 |

---

## Stage 1a — cross-sectional momentum (L31)

Signal: 09:15 open → 09:45 close. Target: **09:50 open → 15:10 close**
(amendment 1 §3, matching what a stage-2 trade could actually have captured).

### Mean 09:50 → 15:10 return by momentum quintile

| Q1 (weakest) | Q2 | Q3 | Q4 | Q5 (strongest) |
| --- | --- | --- | --- | --- |
| −0.35 bp | −1.17 bp | −3.59 bp | −1.87 bp | −2.08 bp |

**No gradient, and every bucket is negative.** The strongest-momentum
quintile does not outperform the weakest — it slightly underperforms it.

| Line | Spread | t | Gate |
| --- | --- | --- | --- |
| **Quintile top-minus-bottom** | **−1.60 bp** | **−0.48** | **> +33.20 bp — FAILS** |
| First half | −0.08 bp | −0.01 | — |
| Second half | −3.12 bp | −0.90 | — |
| *top-5 / bottom-5* | *−4.76 bp* | *−0.77* | *descriptive only, no pass rule* |

**Both halves are negative**, so there is no half carrying a result the other
destroys.

**Power: MDE at t = 2 is 6.70 bp** (sd 59.59, n = 316). The design could have
detected an effect **five times smaller than the gate**, and found one that is
negative. **This is a decisive null, not an underpowered one.**

**The descriptive top-5/bottom-5 line does not rescue it and could not** — it
is marked no-pass-rule in the pre-registration, and it is worse anyway
(−4.76 bp).

---

## Stage 1b — the published time-series effect, adapted (L32)

Market proxy: equal-weighted mean of the universe. Signal:
**sign(previous close → 09:45 close)**, including the overnight gap. Target:
**14:40 open → 15:10 close**.

| Line | Mean | t | Gate |
| --- | --- | --- | --- |
| **Market sign × last half hour** | **+0.70 bp** | **+0.61** | **> +16.60 bp — FAILS** |
| First half | −0.03 bp | −0.02 | — |
| Second half | +1.43 bp | +1.05 | — |
| *Per-stock, own signal* | *−0.38 bp* | *−0.59* | *descriptive only* |

**The sign is at least right** — first-half-hour direction does very weakly
predict the last half hour, 53.3% of sessions positive — but at **+0.70 bp
against a 16.60 bp round trip it is worth 4% of its own cost.**

**This is an adapted version and the adaptation is stated, not buried.** The
published effect runs **to the close**; an intraday cash position must square
off, so this measures to the 15:10 bar. A result about the adaptation is not
a result about the literature's design, and no claim is made about the
latter.

---

## What this establishes, and what it does not

**Establishes:** neither intraday momentum construction — cross-sectional or
time-series — is worth its transaction cost on the NIFTY 100 over these 316
sessions, at a resolution fine enough to have seen an effect five times
smaller than the hurdle.

**Does not establish** that no momentum design works. One variant per line is
not a search, and the pre-registration forbids turning this into one.

**Consistent with everything else measured here.** Stage 1a's quintiles are
all negative, which is the same intraday drag found at index level
(−6.42 bp, t = −4.02) and in the null diagnostic (random long entries
−0.0947R). An intraday book starts behind, and momentum does not overcome it.

---

## Caveats carried

- **Survivorship bias:** today's NIFTY 100 applied to history.
- **316 sessions** — the Kite cache starts 2024-09-20, so this is a much
  shorter sample than the daily-bar work.
- **`costs.py` rates are unverified** against the broker's current tariff.
  That caveat sits under the 16.60 and 33.20 bp hurdles alike.
- **Selection sample only.** The held-out window is untouched.
- **No harness-bias figure applies** — like 3a, this is self-contained, so
  the −0.05R measured on `run_backtest()` does not transfer and none is
  asserted.
